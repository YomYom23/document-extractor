from datetime import date
from decimal import Decimal

from document_extractor.schema import Invoice
from document_extractor.scoring import (
    HEADER_FIELDS,
    Outcome,
    score_dataset,
    score_invoice,
)


def make_invoice(**overrides: object) -> Invoice:
    """A fully filled invoice; each test changes only the field it is about."""
    fields: dict[str, object] = {
        "vendor_name": "Acme Ltd",
        "invoice_number": "INV-0042",
        "issue_date": date(2026, 3, 1),
        "currency": "USD",
        "subtotal": Decimal("100.00"),
        "tax": Decimal("8.00"),
        "total": Decimal("108.00"),
    }
    fields.update(overrides)
    return Invoice.model_validate(fields)


def test_identical_invoice_scores_every_header_field_correct() -> None:
    outcomes = score_invoice(predicted=make_invoice(), expected=make_invoice())
    assert set(outcomes) == set(HEADER_FIELDS)
    assert all(outcome is Outcome.CORRECT for outcome in outcomes.values())


def test_null_where_the_label_has_a_value_is_missing() -> None:
    outcomes = score_invoice(
        predicted=make_invoice(total=None), expected=make_invoice()
    )
    assert outcomes["total"] is Outcome.MISSING
    assert outcomes["tax"] is Outcome.CORRECT


def test_a_different_value_is_wrong_not_missing() -> None:
    outcomes = score_invoice(
        predicted=make_invoice(total=Decimal("180.00")), expected=make_invoice()
    )
    assert outcomes["total"] is Outcome.WRONG


def test_null_label_with_null_prediction_is_correct() -> None:
    outcomes = score_invoice(
        predicted=make_invoice(tax=None), expected=make_invoice(tax=None)
    )
    assert outcomes["tax"] is Outcome.CORRECT


def test_a_value_where_the_label_is_null_is_wrong() -> None:
    outcomes = score_invoice(
        predicted=make_invoice(currency="USD"), expected=make_invoice(currency=None)
    )
    assert outcomes["currency"] is Outcome.WRONG


def test_money_ignores_trailing_zeros_but_not_cents() -> None:
    expected = make_invoice(total=Decimal("108.00"))
    assert (
        score_invoice(make_invoice(total=Decimal(108)), expected)["total"]
        is Outcome.CORRECT
    )
    assert (
        score_invoice(make_invoice(total=Decimal("108.01")), expected)["total"]
        is Outcome.WRONG
    )


def test_vendor_name_ignores_case_and_whitespace() -> None:
    outcomes = score_invoice(
        predicted=make_invoice(vendor_name="  ACME   ltd "), expected=make_invoice()
    )
    assert outcomes["vendor_name"] is Outcome.CORRECT


def test_invoice_number_must_match_exactly() -> None:
    outcomes = score_invoice(
        predicted=make_invoice(invoice_number="inv-0042"), expected=make_invoice()
    )
    assert outcomes["invoice_number"] is Outcome.WRONG


def test_dataset_counts_outcomes_per_field_and_overall() -> None:
    pairs = [
        (make_invoice(), make_invoice()),
        (make_invoice(total=None), make_invoice()),
        (make_invoice(total=Decimal("1.00"), tax=None), make_invoice()),
    ]
    dataset_score = score_dataset(pairs)

    assert dataset_score.invoice_count == 3
    assert dataset_score.per_field["total"][Outcome.CORRECT] == 1
    assert dataset_score.per_field["total"][Outcome.MISSING] == 1
    assert dataset_score.per_field["total"][Outcome.WRONG] == 1
    assert dataset_score.per_field["tax"][Outcome.MISSING] == 1
    # 3 invoices x 7 fields = 21 outcomes; 3 are not correct.
    assert dataset_score.overall[Outcome.CORRECT] == 18
    assert dataset_score.overall[Outcome.MISSING] == 2
    assert dataset_score.overall[Outcome.WRONG] == 1
