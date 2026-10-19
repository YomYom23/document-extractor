import json
from collections.abc import Callable, Mapping
from decimal import Decimal
from pathlib import Path

import pytest

from document_extractor.cli import main
from document_extractor.llm_extractor import LlmExtractionError
from document_extractor.pdf_reader import NoTextLayerError
from document_extractor.schema import Invoice
from document_extractor.scoring import Outcome, score_invoice

DEV_DIRECTORY = Path(__file__).parent.parent / "samples" / "dev"
GERMAN_PDF = DEV_DIRECTORY / "a_clean-de-grid-eu-decimals.pdf"

Extract = Callable[[Path], Invoice]


def label_for(pdf_path: Path) -> Invoice:
    label_path = pdf_path.with_name(pdf_path.stem + ".expected.json")
    return Invoice.model_validate_json(label_path.read_text(encoding="utf-8"))


def fake_llm(extract: Extract) -> Mapping[str, Extract]:
    """The extractors mapping with a fake in the `llm` slot (D28, Q56)."""
    return {"llm": extract}


def raising(error: Exception) -> Extract:
    def extract(pdf_path: Path) -> Invoice:
        raise error

    return extract


# --- extract ----------------------------------------------------------------


def test_extract_prints_the_invoice_as_json(
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = main(["extract", str(GERMAN_PDF)])  # default: rules (Q51)

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
    assert printed.out == ""  # no all-null JSON stands in for a failure (Q53)
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


def test_score_reports_the_rules_extractor_on_dev(
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = main(["score"])  # defaults: rules on dev (Q51, Q54)

    printed = capsys.readouterr()
    assert exit_code == 0
    # The free rules run of 2026-10-19 (docs/null-sources.md).
    assert "9 invoices, 0 failed extractions" in printed.out
    assert "overall         correct 56  missing 7  wrong 0" in printed.out
    assert "b_INV-2026-0129" in printed.out


def test_score_uses_dev_unless_held_out_is_named(
    capsys: pytest.CaptureFixture[str],
) -> None:
    seen: list[Path] = []

    def recording(pdf_path: Path) -> Invoice:
        seen.append(pdf_path)
        return Invoice()

    main(["score", "--extractor", "llm"], extractors=fake_llm(recording))

    assert len(seen) == 9
    assert {pdf_path.parent.name for pdf_path in seen} == {"dev"}


def test_a_failed_extraction_scores_as_missing_and_is_counted(
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = main(
        ["score", "--extractor", "llm"],
        extractors=fake_llm(raising(LlmExtractionError("HTTP 500"))),
    )

    printed = capsys.readouterr()
    assert exit_code == 0
    assert "9 invoices, 9 failed extractions" in printed.out
    # 62 missing, not 63: 0129's label has no tax, so a null tax is correct.
    assert "overall         correct 1  missing 62  wrong 0" in printed.out
