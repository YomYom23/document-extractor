"""The shape of an extracted invoice.

Both extractors (rules and LLM) must return an `Invoice`, and the scorer compares
against hand-labelled `Invoice` JSON, so this file is the contract between all of them.
"""

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

# Shared by both models. `forbid` makes an unexpected key (for example one an LLM
# invented) raise an error instead of being silently dropped.
STRICT_MODEL_CONFIG = ConfigDict(extra="forbid")


class LineItem(BaseModel):
    model_config = STRICT_MODEL_CONFIG

    # Every field is nullable: "not found" must be representable so an extractor
    # can return None instead of guessing (decision D11).
    description: str | None = None
    quantity: Decimal | None = None  # Decimal, not int: invoices bill 1.5 hours
    unit_price: Decimal | None = None
    line_total: Decimal | None = None


class Invoice(BaseModel):
    model_config = STRICT_MODEL_CONFIG

    vendor_name: str | None = None
    invoice_number: str | None = None  # str, not int: "INV-0042" and "007" are common
    issue_date: date | None = None
    # ISO 4217 code such as "USD". None when the page only shows an ambiguous
    # symbol like "$" (decision D18).
    currency: str | None = None

    # Decimal, never float: floats cannot store most decimal amounts exactly,
    # and the scorer demands a match to the cent (decision D10).
    subtotal: Decimal | None = None
    tax: Decimal | None = None
    total: Decimal | None = None

    # None means "could not tell"; [] means "the invoice has no items" (decision D18).
    line_items: list[LineItem] | None = None
    # Deliberately no check that subtotal + tax == total here. If the schema
    # refused inconsistent numbers, a wrong extraction could not be built and
    # the scorer could not measure it. That check lives in its own function.


__all__ = ["Invoice", "LineItem"]
