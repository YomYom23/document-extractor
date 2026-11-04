"""Command line: `extract` one invoice, or `score` an extractor on a sample set (D7, D28).

Argument handling only. Extraction lives in the extractor modules and
scoring in `scoring.py`, so everything here is wiring and printing.
"""

import argparse
import os
import sys
import time
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from typesafe_sdk import Choice, ChoiceAnswer

from document_extractor import rules_extractor
from document_extractor.arithmetic_check import arithmetic_warning
from document_extractor.currency_resolver import (
    AskJev,
    extract_with_currency_resolver,
)
from document_extractor.jev import Jev, JevError
from document_extractor.llm_extractor import (
    DEFAULT_MODEL,
    INPUT_DOLLARS_PER_MILLION_TOKENS,
    OUTPUT_DOLLARS_PER_MILLION_TOKENS,
    LlmExtractionError,
    LlmExtractor,
)
from document_extractor.pdf_reader import NoTextLayerError
from document_extractor.schema import Invoice
from document_extractor.scoring import (
    LINE_FIELDS,
    LineDatasetScore,
    Outcome,
    score_dataset,
    score_invoice,
    score_line_dataset,
    score_lines,
)
from document_extractor.token_usage import TokenUsage

# Every extractor has this shape (D5), so the CLI treats the three alike.
Extract = Callable[[Path], Invoice]

EXTRACTOR_NAMES = ("rules", "rules-jev", "llm")  # the comparison's rows (D25)
# The key each billed extractor's SDK reads from the environment (D28).
REQUIRED_KEYS = {"rules-jev": "TYPESAFE_API_KEY", "llm": "OPENAI_API_KEY"}
SAMPLES_DIRECTORY = Path(__file__).parent.parent / "samples"
# The file-name prefix says where a sample came from (samples/ATTRIBUTION.md,
# D30). `score` prints a subtotal per source so "how does it do on real
# invoices" is not hidden inside the overall count (D30).
SOURCE_NAMES = {"a": "ieb", "b": "invoicebench", "c": "sinabis", "r": "real"}


def set_directories(sample_set: str) -> list[Path]:
    """Public samples plus the git-ignored private ones of the same set (D30)."""
    return [SAMPLES_DIRECTORY / sample_set, SAMPLES_DIRECTORY / "private" / sample_set]


def source_of(pdf_path: Path) -> str:
    prefix = pdf_path.name.split("_", 1)[0]
    return SOURCE_NAMES.get(prefix, "other")


# The failures that mean "this invoice could not be extracted". Anything else
# is a bug and should crash loudly with a traceback, not be counted.
EXTRACTION_FAILURES = (LlmExtractionError, NoTextLayerError)


class CliError(Exception):
    """A problem the user can fix (a missing file or key): message, exit 1."""


@dataclass
class CallMeter:
    """What one run spent on a billed model (D29). Reported, never scored."""

    calls: int = 0
    failed_calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    # Calls whose reply left out a token count; the totals then fall short.
    calls_without_token_counts: int = 0

    def record(self, usage: TokenUsage) -> None:
        if usage.input_tokens is None or usage.output_tokens is None:
            self.calls_without_token_counts += 1
        self.input_tokens += usage.input_tokens or 0
        self.output_tokens += usage.output_tokens or 0


# What the meters need from Jev and the LLM extractor. Protocols, not the real
# classes, so tests can pass small fakes with no network.
class UsageReportingJev(Protocol):
    last_usage: TokenUsage | None

    def ask(
        self, state: str, questions: Mapping[str, Choice]
    ) -> Mapping[str, ChoiceAnswer]: ...


class UsageReportingExtractor(Protocol):
    last_usage: TokenUsage | None

    def extract(self, pdf_path: Path) -> Invoice: ...


def metered_ask(jev: UsageReportingJev, meter: CallMeter) -> AskJev:
    """`jev.ask`, counting calls, failures and tokens (D29). The resolver
    still sees every JevError, so it still leaves the currency null (D25)."""

    def ask(state: str, questions: Mapping[str, Choice]) -> Mapping[str, ChoiceAnswer]:
        meter.calls += 1
        try:
            return jev.ask(state, questions)
        except JevError:
            meter.failed_calls += 1
            raise
        finally:
            # `finally` runs on success and failure alike: a reply that came
            # back and was then rejected was still billed.
            if jev.last_usage is not None:
                meter.record(jev.last_usage)

    return ask


def metered_llm(llm: UsageReportingExtractor, meter: CallMeter) -> Extract:
    """`llm.extract`, counting the replies that came back and their tokens
    (D29). Failures are already counted by `score` as failed extractions."""

    def extract(pdf_path: Path) -> Invoice:
        try:
            return llm.extract(pdf_path)
        finally:
            # No usage means no reply (HTTP error, no text layer): not billed.
            if llm.last_usage is not None:
                meter.calls += 1
                meter.record(llm.last_usage)

    return extract


def main(
    argv: Sequence[str] | None = None,
    extractors: Mapping[str, Extract] | None = None,
) -> int:
    """Entry point. Returns the exit code: 0 success, 1 failure (D28)."""
    arguments = build_parser().parse_args(argv)
    # argparse gives back `Any` values; give them real types once, here,
    # so mypy checks everything after this point.
    command: str = arguments.command
    extractor_name: str = arguments.extractor
    # Filled by the real billed extractors; stays at zero for injected fakes.
    meter = CallMeter()
    try:
        extract = (
            extractors[extractor_name]
            if extractors is not None
            else build_extractor(extractor_name, meter)
        )
        if command == "extract":
            run_extract(Path(arguments.pdf), extract)
        else:
            run_score(
                set_directories(str(arguments.set)), extract, extractor_name, meter
            )
    except (CliError, *EXTRACTION_FAILURES) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="document-extractor",
        description="Extract header fields and line items from digital PDF invoices.",
    )
    # required=True: running with no command prints usage instead of nothing.
    commands = parser.add_subparsers(dest="command", required=True)

    extract_command = commands.add_parser("extract", help="print one invoice as JSON")
    extract_command.add_argument("pdf", help="path to a digital PDF invoice")

    score_command = commands.add_parser(
        "score", help="score an extractor against a labelled sample set"
    )
    # Held-out is for the final comparison only, so it must be asked for (D6).
    score_command.add_argument("--set", choices=("dev", "heldout"), default="dev")

    # Added to each command, not the top-level parser, so the flag goes after
    # the command: `extract invoice.pdf --extractor llm`.
    for command_parser in (extract_command, score_command):
        command_parser.add_argument(
            "--extractor", choices=EXTRACTOR_NAMES, default="rules"
        )
    return parser


def build_extractor(name: str, meter: CallMeter) -> Extract:
    """The real extractor for `name`. Checks its key before any PDF is read."""
    key_name = REQUIRED_KEYS.get(name)
    if key_name is not None and not os.environ.get(key_name):
        raise CliError(
            f"{key_name} is not set. Locally: uv run --env-file .env document-extractor ..."
        )
    if name == "llm":
        return metered_llm(LlmExtractor(), meter)
    if name == "rules-jev":
        ask = metered_ask(Jev(), meter)
        return lambda pdf_path: extract_with_currency_resolver(pdf_path, ask)
    return rules_extractor.extract


def run_extract(pdf_path: Path, extract: Extract) -> None:
    if not pdf_path.is_file():
        raise CliError(f"{pdf_path} is not a file")
    invoice = extract(pdf_path)
    # stdout gets only the JSON, so `> invoice.json` or a pipe gets clean data.
    print(invoice.model_dump_json(indent=2))
    warning = arithmetic_warning(invoice)
    if warning is not None:
        # A hint for a human, not part of the result (D20, D22).
        print(f"warning: {warning}", file=sys.stderr)


def run_score(
    directories: list[Path], extract: Extract, extractor_name: str, meter: CallMeter
) -> None:
    pairs: list[tuple[Invoice, Invoice]] = []
    pairs_by_source: dict[str, list[tuple[Invoice, Invoice]]] = {}
    # Only the LLM extracts line items (D34), so only its runs print them:
    # rules and rules-jev output stays as it was.
    show_lines = extractor_name == "llm"
    line_results: list[tuple[str, Invoice, Invoice]] = []
    failed_extractions = 0
    seconds_spent = 0.0

    # Sorted by file name across both folders, so private invoices sit among
    # the public ones by source prefix instead of in a block at the end.
    pdf_paths = sorted(
        (path for directory in directories for path in directory.glob("*.pdf")),
        key=lambda path: path.name,
    )
    for pdf_path in pdf_paths:
        label_path = pdf_path.with_name(pdf_path.stem + ".expected.json")
        expected = Invoice.model_validate_json(label_path.read_text(encoding="utf-8"))
        # perf_counter, not time.time: it is meant for measuring durations and
        # cannot jump if the system clock is adjusted mid-run.
        started = time.perf_counter()
        try:
            predicted = extract(pdf_path)
        except EXTRACTION_FAILURES as error:
            # Scored as all-null, never as guessed values; counted apart so
            # "the call broke" is not mistaken for "the extractor did not know" (D26).
            failed_extractions += 1
            print(f"{pdf_path.stem:30} FAILED: {error}")
            predicted = Invoice()
        finally:
            seconds_spent += time.perf_counter() - started
        pairs.append((predicted, expected))
        pairs_by_source.setdefault(source_of(pdf_path), []).append(
            (predicted, expected)
        )
        print_invoice_result(pdf_path.stem, predicted, expected)
        if show_lines:
            print_line_result(predicted, expected)
            line_results.append((pdf_path.stem, predicted, expected))

    dataset_score = score_dataset(pairs)
    print(
        f"\n{dataset_score.invoice_count} invoices, "
        f"{failed_extractions} failed extractions"
    )
    print(format_counts("overall", dataset_score.overall))
    for source in sorted(pairs_by_source):
        source_score = score_dataset(pairs_by_source[source])
        print(format_counts(f"  {source}", source_score.overall))
    for field_name, counts in dataset_score.per_field.items():
        print(format_counts(field_name, counts))
    if show_lines:
        print()
        for text in format_line_summary(score_line_dataset(line_results)):
            print(text)
    # Time and spend are printed after the counts and are not part of any
    # score: extractors are ranked on accuracy only (D29).
    invoice_count = max(dataset_score.invoice_count, 1)  # no division by zero
    print(
        f"\n{'time':16}{seconds_spent / invoice_count:.2f} s per invoice, "
        f"{seconds_spent:.2f} s total"
    )
    if extractor_name in REQUIRED_KEYS:  # only billed extractors have a meter
        print(format_meter(extractor_name, meter))


def format_meter(extractor_name: str, meter: CallMeter) -> str:
    tokens = f"{meter.input_tokens} input + {meter.output_tokens} output tokens"
    if extractor_name == "llm":
        dollars = (
            meter.input_tokens * INPUT_DOLLARS_PER_MILLION_TOKENS
            + meter.output_tokens * OUTPUT_DOLLARS_PER_MILLION_TOKENS
        ) / 1_000_000
        line = (
            f"{'llm':16}{meter.calls} replies, {tokens}, ${dollars:.6f} at "
            f"{DEFAULT_MODEL} prices (cached input not discounted)"
        )
    else:
        # Jev is not priced: only its input price is known (D25, D29).
        line = f"{'jev':16}{meter.calls} calls, {meter.failed_calls} failed, {tokens}"
    if meter.calls_without_token_counts:
        line += f", {meter.calls_without_token_counts} without token counts"
    return line


def print_invoice_result(name: str, predicted: Invoice, expected: Invoice) -> None:
    outcomes = score_invoice(predicted, expected)
    not_correct = {
        field_name: outcome.value
        for field_name, outcome in outcomes.items()
        if outcome is not Outcome.CORRECT
    }
    print(f"{name:30} {not_correct or 'all correct'}")
    # The value next to its label for every wrong field, so a wrong answer can
    # be judged (extractor error or label error) without a re-run.
    for field_name, outcome in outcomes.items():
        if outcome is Outcome.WRONG:
            print(
                f"{'':32}{field_name}: got {getattr(predicted, field_name)!r}, "
                f"label {getattr(expected, field_name)!r}"
            )


def print_line_result(predicted: Invoice, expected: Invoice) -> None:
    """The line items of one invoice, under its header line (D34.5). Rows are
    numbered from 1: L for labelled rows, P for predicted ones."""
    score = score_lines(predicted, expected)
    if score is None:
        print(f"{'':32}lines: skipped, label null")
        return
    if not predicted.line_items:
        print(
            f"{'':32}lines: no prediction ({predicted.line_items!r}), "
            f"{score.unpaired_labels} labelled unpaired"
        )
        return
    print(
        f"{'':32}lines: {score.labelled} labelled, {score.predicted} predicted, "
        f"{score.by_total} paired by total, {score.by_description} paired by "
        f"description, {score.unpaired_labels} labelled unpaired, "
        f"{score.invented} invented"
    )
    labelled = expected.line_items or []
    predictions = predicted.line_items
    # Failing fields of pairs first, then unpaired labels, then invented rows.
    for scored in score.pairs:
        pair = scored.pair
        if pair.label_index is None or pair.predicted_index is None:
            continue
        label = labelled[pair.label_index]
        prediction = predictions[pair.predicted_index]
        for field_name, outcome in scored.outcomes.items():
            if outcome is not Outcome.CORRECT:
                print(
                    f"{'':32}L{pair.label_index + 1}-P{pair.predicted_index + 1} "
                    f"({pair.pass_}) {field_name} {outcome}: "
                    f"got {getattr(prediction, field_name)!r}, "
                    f"label {getattr(label, field_name)!r}"
                )
    for scored in score.pairs:
        if scored.pair.predicted_index is None and scored.pair.label_index is not None:
            row = labelled[scored.pair.label_index].model_dump()
            print(f"{'':32}L{scored.pair.label_index + 1} unpaired: {row!r}")
    for scored in score.pairs:
        if scored.pair.label_index is None and scored.pair.predicted_index is not None:
            row = predictions[scored.pair.predicted_index].model_dump()
            print(f"{'':32}P{scored.pair.predicted_index + 1} invented: {row!r}")


def format_line_summary(score: LineDatasetScore) -> list[str]:
    """The line block printed after the header counts (D34.5)."""
    summary = [
        "line items",
        format_counts("lines overall", score.overall),
        *(format_counts(name, score.per_field[name]) for name in LINE_FIELDS),
        f"invented {score.invented}",
        f"labelled unpaired {score.unpaired_labels}",
    ]
    # One invoice holds 38% of dev rows, so the counts are also shown without
    # it; with nothing scored there is no largest invoice to leave out.
    if score.largest_name is None:
        summary.append("largest invoice: none")
    else:
        summary += [
            (
                f"largest invoice: {score.largest_name}, "
                f"{score.largest_labelled} labelled rows"
            ),
            format_counts("lines excl. top", score.overall_without_largest),
        ]
    summary.append(f"skipped {score.skipped_count} invoices (label null)")
    return summary


def format_counts(name: str, counts: Counter[Outcome]) -> str:
    # All three outcomes every time: "wrong 0" is the number that matters
    # most (D11), so it is printed even when it is zero.
    return (
        f"{name:16}correct {counts[Outcome.CORRECT]}  "
        f"missing {counts[Outcome.MISSING]}  wrong {counts[Outcome.WRONG]}"
    )
