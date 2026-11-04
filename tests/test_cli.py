import json
import time
from collections import Counter
from collections.abc import Callable, Mapping
from decimal import Decimal
from pathlib import Path

import pytest
from typesafe_sdk import Choice, ChoiceAnswer

from document_extractor import cli
from document_extractor.cli import (
    CallMeter,
    format_line_summary,
    format_meter,
    main,
    metered_ask,
    metered_llm,
    print_line_result,
)
from document_extractor.jev import JevError
from document_extractor.llm_extractor import LlmExtractionError
from document_extractor.pdf_reader import NoTextLayerError
from document_extractor.schema import Invoice, LineItem
from document_extractor.scoring import LineDatasetScore, Outcome, score_invoice
from document_extractor.token_usage import TokenUsage

DEV_DIRECTORY = Path(__file__).parent.parent / "samples" / "dev"
GERMAN_PDF = DEV_DIRECTORY / "a_clean-de-grid-eu-decimals.pdf"

Extract = Callable[[Path], Invoice]


def label_for(pdf_path: Path) -> Invoice:
    label_path = pdf_path.with_name(pdf_path.stem + ".expected.json")
    return Invoice.model_validate_json(label_path.read_text(encoding="utf-8"))


def fake_llm(extract: Extract) -> Mapping[str, Extract]:
    """The extractors mapping with a fake in the `llm` slot (D28)."""
    return {"llm": extract}


def raising(error: Exception) -> Extract:
    def extract(pdf_path: Path) -> Invoice:
        raise error

    return extract


# --- extract ----------------------------------------------------------------


def test_extract_prints_the_invoice_as_json(
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = main(["extract", str(GERMAN_PDF)])  # default: rules (D28)

    printed = capsys.readouterr()
    assert exit_code == 0
    invoice = Invoice.model_validate_json(printed.out)  # stdout is only JSON
    outcomes = score_invoice(invoice, label_for(GERMAN_PDF))
    assert set(outcomes.values()) == {Outcome.CORRECT}


def test_the_arithmetic_warning_goes_to_stderr_not_into_the_json(
    capsys: pytest.CaptureFixture[str],
) -> None:
    off_by_one = Invoice(
        subtotal=Decimal("100.00"), tax=Decimal("19.00"), total=Decimal("120.00")
    )
    exit_code = main(
        ["extract", str(GERMAN_PDF), "--extractor", "llm"],
        extractors=fake_llm(lambda pdf_path: off_by_one),
    )

    printed = capsys.readouterr()
    assert exit_code == 0
    assert json.loads(printed.out)["total"] == "120.00"
    assert "subtotal 100.00 + tax 19.00" in printed.err


@pytest.mark.parametrize(
    "error",
    [LlmExtractionError("reply cut off"), NoTextLayerError("is it a scan?")],
)
def test_a_failed_extraction_is_an_error_not_an_empty_invoice(
    error: Exception, capsys: pytest.CaptureFixture[str]
) -> None:
    exit_code = main(
        ["extract", str(GERMAN_PDF), "--extractor", "llm"],
        extractors=fake_llm(raising(error)),
    )

    printed = capsys.readouterr()
    assert exit_code == 1
    assert printed.out == ""  # no all-null JSON stands in for a failure (D28)
    assert str(error) in printed.err


def test_a_missing_file_is_an_error(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main(["extract", "no-such-invoice.pdf"])

    printed = capsys.readouterr()
    assert exit_code == 1
    assert "no-such-invoice.pdf" in printed.err


@pytest.mark.parametrize(
    ("extractor", "key_name"),
    [("llm", "OPENAI_API_KEY"), ("rules-jev", "TYPESAFE_API_KEY")],
)
def test_a_missing_key_stops_before_any_pdf_is_read(
    extractor: str,
    key_name: str,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.delenv(key_name, raising=False)
    # The file does not exist: reaching the PDF would print a different error.
    exit_code = main(["extract", "no-such-invoice.pdf", "--extractor", extractor])

    printed = capsys.readouterr()
    assert exit_code == 1
    assert key_name in printed.err
    assert "no-such-invoice.pdf" not in printed.err


# --- score ------------------------------------------------------------------


@pytest.fixture
def sample_tree(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A small samples/ folder, so score tests do not change whenever the real
    sample set grows (D30). Two public dev invoices and one "private" one."""
    for name, target in [
        ("a_clean-de-grid-eu-decimals", tmp_path / "dev"),
        ("b_INV-2026-0129", tmp_path / "dev"),
        # A public sample renamed: a test cannot rely on the git-ignored
        # real invoices, which a fresh clone does not have (D30).
        ("a_clean-de-grid-eu-decimals", tmp_path / "private" / "dev"),
    ]:
        target.mkdir(parents=True, exist_ok=True)
        new_name = "r_test" if "private" in target.parts else name
        for suffix in (".pdf", ".expected.json"):
            (target / f"{new_name}{suffix}").write_bytes(
                (DEV_DIRECTORY / f"{name}{suffix}").read_bytes()
            )
    (tmp_path / "heldout").mkdir()
    monkeypatch.setattr(cli, "SAMPLES_DIRECTORY", tmp_path)
    return tmp_path


def test_score_reports_the_rules_extractor(
    sample_tree: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    exit_code = main(["score"])  # defaults: rules on dev (D28)

    printed = capsys.readouterr()
    assert exit_code == 0
    # de: 7 correct. 0129: subtotal, total and currency missing (D24).
    assert "3 invoices, 0 failed extractions" in printed.out
    assert "overall         correct 18  missing 3  wrong 0" in printed.out
    assert "b_INV-2026-0129" in printed.out


def test_score_includes_the_private_folder_of_the_set(
    sample_tree: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    seen: list[Path] = []

    def recording(pdf_path: Path) -> Invoice:
        seen.append(pdf_path)
        return Invoice()

    main(["score", "--extractor", "llm"], extractors=fake_llm(recording))

    # dev and private/dev, never held-out unless named (D6, D30).
    assert sorted(pdf_path.stem for pdf_path in seen) == [
        "a_clean-de-grid-eu-decimals",
        "b_INV-2026-0129",
        "r_test",
    ]


def test_score_prints_a_subtotal_per_source(
    sample_tree: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    main(["score"])

    printed = capsys.readouterr().out
    # One line per source prefix present (D30): a_ IEB, b_ InvoiceBenchmark, r_ yours.
    assert "  ieb           correct 7  missing 0  wrong 0" in printed
    assert "  invoicebench  correct 4  missing 3  wrong 0" in printed
    assert "  real          correct 7  missing 0  wrong 0" in printed
    assert "sinabis" not in printed  # no c_ samples in this tree


def test_a_failed_extraction_scores_as_missing_and_is_counted(
    sample_tree: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    exit_code = main(
        ["score", "--extractor", "llm"],
        extractors=fake_llm(raising(LlmExtractionError("HTTP 500"))),
    )

    printed = capsys.readouterr()
    assert exit_code == 0
    assert "3 invoices, 3 failed extractions" in printed.out
    # 20 missing, not 21: 0129's label has no tax, so a null tax is correct.
    assert "overall         correct 1  missing 20  wrong 0" in printed.out


# --- call meters: time, tokens and Jev visibility (D29) -------------


class FakeJev:
    """Has what `metered_ask` reads: `ask` and the last call's usage."""

    def __init__(self) -> None:
        self.last_usage: TokenUsage | None = None
        self.fail_next = False

    def ask(
        self, state: str, questions: Mapping[str, Choice]
    ) -> Mapping[str, ChoiceAnswer]:
        if self.fail_next:
            self.last_usage = None
            raise JevError("HTTP 500")
        self.last_usage = TokenUsage(input_tokens=328, output_tokens=34)
        return {}


def test_jev_calls_failures_and_tokens_are_counted() -> None:
    meter = CallMeter()
    jev = FakeJev()
    ask = metered_ask(jev, meter)

    ask("page text", {})
    jev.fail_next = True
    with pytest.raises(JevError):  # still raised: the resolver handles it (D25)
        ask("page text", {})

    assert meter == CallMeter(
        calls=2, failed_calls=1, input_tokens=328, output_tokens=34
    )


class FakeLlm:
    """Has what `metered_llm` reads: `extract` and the last call's usage."""

    def __init__(self, usage: TokenUsage | None, error: Exception | None) -> None:
        self.last_usage: TokenUsage | None = None
        self.usage = usage
        self.error = error

    def extract(self, pdf_path: Path) -> Invoice:
        self.last_usage = self.usage
        if self.error is not None:
            raise self.error
        return Invoice()


def test_llm_replies_and_tokens_are_counted_even_when_extraction_fails() -> None:
    meter = CallMeter()
    usage = TokenUsage(input_tokens=1200, output_tokens=300)
    metered_llm(FakeLlm(usage, error=None), meter)(GERMAN_PDF)
    # A refused reply raises, but it came back and was billed.
    refused = metered_llm(FakeLlm(usage, LlmExtractionError("refused")), meter)
    with pytest.raises(LlmExtractionError):
        refused(GERMAN_PDF)
    # An HTTP error brings no reply, so there is nothing to count.
    broken = metered_llm(FakeLlm(None, LlmExtractionError("HTTP 500")), meter)
    with pytest.raises(LlmExtractionError):
        broken(GERMAN_PDF)

    assert meter == CallMeter(calls=2, input_tokens=2400, output_tokens=600)


def test_the_llm_line_prices_the_tokens() -> None:
    meter = CallMeter(calls=3, input_tokens=1200, output_tokens=300)
    # 1200 x $0.10 / 1M + 300 x $0.50 / 1M = $0.00012 + $0.00015
    assert format_meter("llm", meter) == (
        "llm             3 replies, 1200 input + 300 output tokens, "
        "$0.000270 at gpt-6-luna prices (cached input not discounted)"
    )


def test_the_jev_line_shows_calls_failures_and_unreported_tokens() -> None:
    meter = CallMeter(
        calls=2,
        failed_calls=1,
        input_tokens=328,
        output_tokens=34,
        calls_without_token_counts=1,
    )
    assert format_meter("rules-jev", meter) == (
        "jev             2 calls, 1 failed, 328 input + 34 output tokens, "
        "1 without token counts"
    )


def test_score_reports_the_time_per_invoice(
    sample_tree: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    main(["score"])
    assert "s per invoice" in capsys.readouterr().out


# The full rules output on sample_tree, captured before line output was added:
# line items must not change what the rules and rules-jev runs print (D34).
RULES_SCORE_OUTPUT = """\
a_clean-de-grid-eu-decimals    all correct
b_INV-2026-0129                {'currency': 'missing', 'subtotal': 'missing', 'total': 'missing'}
r_test                         all correct

3 invoices, 0 failed extractions
overall         correct 18  missing 3  wrong 0
  ieb           correct 7  missing 0  wrong 0
  invoicebench  correct 4  missing 3  wrong 0
  real          correct 7  missing 0  wrong 0
vendor_name     correct 3  missing 0  wrong 0
invoice_number  correct 3  missing 0  wrong 0
issue_date      correct 3  missing 0  wrong 0
currency        correct 2  missing 1  wrong 0
subtotal        correct 2  missing 1  wrong 0
tax             correct 3  missing 0  wrong 0
total           correct 2  missing 1  wrong 0

time            0.00 s per invoice, 0.00 s total
"""


def test_rules_score_output_is_unchanged(
    sample_tree: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # A fixed clock, so the time line is the same on every run.
    monkeypatch.setattr(time, "perf_counter", lambda: 0.0)
    main(["score"])
    assert capsys.readouterr().out == RULES_SCORE_OUTPUT


# --- line items (D34.5) ------------------------------------------------------

INDENT = " " * 32


def line(
    description: str | None,
    line_total: str | None,
    quantity: str | None = None,
    unit_price: str | None = None,
) -> LineItem:
    return LineItem(
        description=description,
        quantity=None if quantity is None else Decimal(quantity),
        unit_price=None if unit_price is None else Decimal(unit_price),
        line_total=None if line_total is None else Decimal(line_total),
    )


def printed_lines(
    predicted: Invoice, expected: Invoice, capsys: pytest.CaptureFixture[str]
) -> list[str]:
    print_line_result(predicted, expected)
    return capsys.readouterr().out.splitlines()


def test_the_line_result_lists_counts_failing_fields_unpaired_and_invented(
    capsys: pytest.CaptureFixture[str],
) -> None:
    expected = Invoice(
        line_items=[
            line("Widget", "10.00", quantity="2", unit_price="5.00"),
            line("Freight", "9.00"),
            line("Bolts", "3.00"),
        ]
    )
    predicted = Invoice(
        line_items=[
            line("Widget", "10.00", quantity="2", unit_price="5.00"),
            line("Bolts", "30.00"),
            line(None, "9.50"),
        ]
    )

    # Row numbers are 1-based, as a person counts rows on the page.
    assert printed_lines(predicted, expected, capsys) == [
        (
            f"{INDENT}lines: 3 labelled, 3 predicted, 1 paired by total, "
            "1 paired by description, 1 labelled unpaired, 1 invented"
        ),
        (
            f"{INDENT}L3-P2 (description) line_total wrong: "
            "got Decimal('30.00'), label Decimal('3.00')"
        ),
        (
            f"{INDENT}L2 unpaired: {{'description': 'Freight', 'quantity': None, "
            "'unit_price': None, 'line_total': Decimal('9.00')}"
        ),
        (
            f"{INDENT}P3 invented: {{'description': None, 'quantity': None, "
            "'unit_price': None, 'line_total': Decimal('9.50')}"
        ),
    ]


def test_a_missing_field_in_a_pair_is_printed_with_its_outcome(
    capsys: pytest.CaptureFixture[str],
) -> None:
    expected = Invoice(line_items=[line("Widget", "10.00", quantity="2")])
    predicted = Invoice(line_items=[line("widget ", "10.00")])

    # "widget " against "Widget" is correct (D12); the null quantity is not.
    assert printed_lines(predicted, expected, capsys)[1:] == [
        f"{INDENT}L1-P1 (total) quantity missing: got None, label Decimal('2')",
    ]


@pytest.mark.parametrize(("line_items", "shown"), [(None, "None"), ([], "[]")])
def test_no_prediction_prints_one_line(
    line_items: list[LineItem] | None,
    shown: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    expected = Invoice(line_items=[line("Widget", "10.00"), line("Bolts", "3.00")])

    assert printed_lines(Invoice(line_items=line_items), expected, capsys) == [
        f"{INDENT}lines: no prediction ({shown}), 2 labelled unpaired"
    ]


def test_a_null_label_prints_skipped(capsys: pytest.CaptureFixture[str]) -> None:
    predicted = Invoice(line_items=[line("Widget", "10.00")])

    assert printed_lines(predicted, Invoice(), capsys) == [
        f"{INDENT}lines: skipped, label null"
    ]


def test_line_summary_block() -> None:
    score = LineDatasetScore(
        invoice_count=2,
        skipped_count=1,
        per_field={
            "description": Counter({Outcome.CORRECT: 3, Outcome.WRONG: 1}),
            "quantity": Counter({Outcome.CORRECT: 2, Outcome.MISSING: 2}),
            "unit_price": Counter({Outcome.CORRECT: 4}),
            "line_total": Counter({Outcome.CORRECT: 3, Outcome.WRONG: 1}),
        },
        overall=Counter({Outcome.CORRECT: 12, Outcome.MISSING: 2, Outcome.WRONG: 2}),
        invented=1,
        unpaired_labels=1,
        largest_name="a_big",
        largest_labelled=3,
        overall_without_largest=Counter({Outcome.CORRECT: 4}),
    )

    assert format_line_summary(score) == [
        "line items",
        "lines overall   correct 12  missing 2  wrong 2",
        "description     correct 3  missing 0  wrong 1",
        "quantity        correct 2  missing 2  wrong 0",
        "unit_price      correct 4  missing 0  wrong 0",
        "line_total      correct 3  missing 0  wrong 1",
        "invented 1",
        "labelled unpaired 1",
        "largest invoice: a_big, 3 labelled rows",
        "lines excl. top correct 4  missing 0  wrong 0",
        "skipped 1 invoices (label null)",
    ]


def test_a_line_summary_with_nothing_scored_names_no_largest_invoice() -> None:
    summary = format_line_summary(LineDatasetScore(skipped_count=2))

    assert "largest invoice: none" in summary
    assert not any(text.startswith("lines excl. top") for text in summary)
    assert summary[-1] == "skipped 2 invoices (label null)"


def test_llm_score_prints_lines_per_invoice_and_the_block_before_time(
    sample_tree: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    main(["score", "--extractor", "llm"], extractors=fake_llm(lambda _: Invoice()))

    printed = capsys.readouterr().out.splitlines()
    # de and r_test have 4 labelled rows each, 0129 has 5.
    four_unpaired = f"{INDENT}lines: no prediction (None), 4 labelled unpaired"
    assert printed.count(four_unpaired) == 2
    assert f"{INDENT}lines: no prediction (None), 5 labelled unpaired" in printed
    block = printed.index("line items")
    assert printed[block - 1] == ""  # a blank line, like the header block
    # 13 rows x 4 fields, all missing.
    assert printed[block + 1] == "lines overall   correct 0  missing 52  wrong 0"
    time_line = next(i for i, text in enumerate(printed) if text.startswith("time"))
    meter_line = next(i for i, text in enumerate(printed) if text.startswith("llm"))
    assert block < time_line < meter_line
