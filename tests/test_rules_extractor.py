from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from document_extractor.rules_extractor import extract, parse_amount, parse_date
from document_extractor.schema import Invoice
from document_extractor.scoring import Outcome, score_invoice


@pytest.mark.parametrize(
    ("printed", "expected"),
    [
        ("346.50", Decimal("346.50")),
        ("13,680.00", Decimal("13680.00")),  # UK/US: comma thousands
        ("1.151,18", Decimal("1151.18")),  # DE/NL/FR: dot thousands
        ("84,60", Decimal("84.60")),
        ("1 440.12", Decimal("1440.12")),  # ZA: space thousands
        ("375,905.60", Decimal("375905.60")),
        # Not amounts: an amount must end in exactly two decimals (D24).
        ("4334037646", None),  # a VAT number
        ("31-1234567", None),  # a tax ID
        ("7.5", None),  # a tax rate
        ("1.234", None),
        # The decimal separator cannot also be the thousands separator.
        ("1.151.18", None),
    ],
)
def test_parse_amount(printed: str, expected: Decimal | None) -> None:
    assert parse_amount(printed) == expected


@pytest.mark.parametrize(
    ("printed", "expected"),
    [
        ("30.04.2026", date(2026, 4, 30)),  # dotted is always day.month.year
        ("28 July 2025", date(2025, 7, 28)),
        ("12 February 2026", date(2026, 2, 12)),
        ("13/06/2025", date(2025, 6, 13)),  # 13 can only be the day
        ("06/13/2025", date(2025, 6, 13)),
        # Both parts 12 or under: day/month or month/day? Left null (D24).
        ("09/03/2026", None),
        ("03/12/2024", None),
        ("31.02.2026", None),  # no 31 February
        ("30 days", None),
    ],
)
def test_parse_date(printed: str, expected: date | None) -> None:
    assert parse_date(printed) == expected


DEV_DIRECTORY = Path(__file__).parent.parent / "samples" / "dev"

# Fields the rules are expected to miss on each dev sample (D24). Pinned, so a
# rule change that finds or loses a field shows up here. Unlisted: none missed.
EXPECTED_MISSING = {
    # Added after the rules were written (D25): an unseen test for them.
    "a_currency-nad-bare-dollar": {"currency"},  # bare $: the Jev stage's job
    "a_clean-us-clean-simple": {"currency", "issue_date"},  # bare $, 03/12/2024
    "a_clean-fr-right-header": {"issue_date"},  # 09/03/2026
    "b_INV-2026-0129": {"subtotal", "total", "currency"},  # only in sentences;
    # currency is read from the total's line, so no total means no currency
}


@pytest.mark.parametrize(
    "pdf_path", sorted(DEV_DIRECTORY.glob("*.pdf")), ids=lambda path: path.stem
)
def test_rules_extractor_on_dev_samples(pdf_path: Path) -> None:
    label_path = pdf_path.with_name(pdf_path.stem + ".expected.json")
    expected = Invoice.model_validate_json(label_path.read_text(encoding="utf-8"))

    outcomes = score_invoice(predicted=extract(pdf_path), expected=expected)

    wrong_fields = {
        name for name, outcome in outcomes.items() if outcome is Outcome.WRONG
    }
    missing_fields = {
        name for name, outcome in outcomes.items() if outcome is Outcome.MISSING
    }
    # The hard rule: rules may miss a field, never invent a wrong one (D11).
    assert wrong_fields == set()
    assert missing_fields == EXPECTED_MISSING.get(pdf_path.stem, set())
