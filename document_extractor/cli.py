"""Command line: `extract` one invoice, or `score` an extractor on a sample set (D7, D28).

Argument handling only. Extraction lives in the extractor modules and
scoring in `scoring.py`, so everything here is wiring and printing.
"""

import argparse
import os
import sys
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path

from document_extractor import rules_extractor
from document_extractor.arithmetic_check import arithmetic_warning
from document_extractor.currency_resolver import extract_with_currency_resolver
from document_extractor.jev import Jev
from document_extractor.llm_extractor import LlmExtractionError, LlmExtractor
from document_extractor.pdf_reader import NoTextLayerError
from document_extractor.schema import Invoice
from document_extractor.scoring import Outcome, score_dataset, score_invoice

# Every extractor has this shape (D5), so the CLI treats the three alike.
Extract = Callable[[Path], Invoice]

EXTRACTOR_NAMES = ("rules", "rules-jev", "llm")  # the comparison's rows (D25)
# The key each billed extractor's SDK reads from the environment (Q55).
REQUIRED_KEYS = {"rules-jev": "TYPESAFE_API_KEY", "llm": "OPENAI_API_KEY"}
SAMPLES_DIRECTORY = Path(__file__).parent.parent / "samples"

# The failures that mean "this invoice could not be extracted". Anything else
# is a bug and should crash loudly with a traceback, not be counted.
EXTRACTION_FAILURES = (LlmExtractionError, NoTextLayerError)


class CliError(Exception):
    """A problem the user can fix (a missing file or key): message, exit 1."""


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
    try:
        extract = (
            extractors[extractor_name]
            if extractors is not None
            else build_extractor(extractor_name)
        )
        if command == "extract":
            run_extract(Path(arguments.pdf), extract)
        else:
            run_score(SAMPLES_DIRECTORY / str(arguments.set), extract)
    except (CliError, *EXTRACTION_FAILURES) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="document-extractor",
        description="Extract header fields from digital PDF invoices.",
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


def build_extractor(name: str) -> Extract:
    """The real extractor for `name`. Checks its key before any PDF is read."""
    key_name = REQUIRED_KEYS.get(name)
    if key_name is not None and not os.environ.get(key_name):
        raise CliError(
            f"{key_name} is not set. Locally: uv run --env-file .env document-extractor ..."
        )
    if name == "llm":
        return LlmExtractor().extract
    if name == "rules-jev":
        jev = Jev()
        return lambda pdf_path: extract_with_currency_resolver(pdf_path, jev.ask)
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


def run_score(set_directory: Path, extract: Extract) -> None:
    pairs: list[tuple[Invoice, Invoice]] = []
    failed_extractions = 0

    for pdf_path in sorted(set_directory.glob("*.pdf")):
        label_path = pdf_path.with_name(pdf_path.stem + ".expected.json")
        expected = Invoice.model_validate_json(label_path.read_text(encoding="utf-8"))
        try:
            predicted = extract(pdf_path)
        except EXTRACTION_FAILURES as error:
            # Scored as all-null, never as guessed values; counted apart so
            # "the call broke" is not mistaken for "the extractor did not know" (D26).
            failed_extractions += 1
            print(f"{pdf_path.stem:30} FAILED: {error}")
            predicted = Invoice()
        pairs.append((predicted, expected))
        print_invoice_result(pdf_path.stem, predicted, expected)

    dataset_score = score_dataset(pairs)
    print(
        f"\n{dataset_score.invoice_count} invoices, "
        f"{failed_extractions} failed extractions"
    )
    print(format_counts("overall", dataset_score.overall))
    for field_name, counts in dataset_score.per_field.items():
        print(format_counts(field_name, counts))


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


def format_counts(name: str, counts: Counter[Outcome]) -> str:
    # All three outcomes every time: "wrong 0" is the number that matters
    # most (D11), so it is printed even when it is zero.
    return (
        f"{name:16}correct {counts[Outcome.CORRECT]}  "
        f"missing {counts[Outcome.MISSING]}  wrong {counts[Outcome.WRONG]}"
    )
