from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from document_extractor.schema import Invoice, LineItem


def test_empty_invoice_is_valid_and_all_fields_are_none() -> None:
    invoice = Invoice()
    assert invoice.model_dump() == {
        "vendor_name": None,
        "invoice_number": None,
        "issue_date": None,
        "currency": None,
        "subtotal": None,
        "tax": None,
        "total": None,
        "line_items": None,
    }


def test_json_parses_into_real_types() -> None:
    invoice = Invoice.model_validate_json(
        '{"issue_date": "2026-10-16", "total": 19.99, "invoice_number": "007"}'
    )
    assert invoice.issue_date == date(2026, 10, 16)
    # A JSON number must become exactly 19.99, not the nearest float's long tail.
    assert invoice.total == Decimal("19.99")
    # Leading zeros survive because the invoice number is a string.
    assert invoice.invoice_number == "007"


def test_unparseable_value_raises() -> None:
    with pytest.raises(ValidationError):
        Invoice(total="abc")  # type: ignore[arg-type]


def test_unknown_field_is_rejected() -> None:
    with pytest.raises(ValidationError):
        Invoice.model_validate({"vendor_vibes": "good"})


def test_inconsistent_totals_are_still_representable() -> None:
    # The schema must allow wrong numbers so the scorer can measure wrong extractions.
    invoice = Invoice(
        subtotal=Decimal("10.00"), tax=Decimal("1.00"), total=Decimal("99.00")
    )
    assert invoice.total == Decimal("99.00")


def test_line_items_distinguish_unknown_from_empty() -> None:
    assert Invoice().line_items is None
    assert Invoice(line_items=[]).line_items == []


def test_line_item_round_trips_through_json() -> None:
    invoice = Invoice(
        line_items=[
            LineItem(
                description="Consulting",
                quantity=Decimal("1.5"),
                unit_price=Decimal("100.00"),
                line_total=Decimal("150.00"),
            )
        ]
    )
    assert Invoice.model_validate_json(invoice.model_dump_json()) == invoice
