"""Extract invoice header fields and line items with an OpenAI model (D5, D15,
D26, D34).

The model never fills `Invoice` directly. It fills `LlmInvoice`, whose money
fields are strings with a strict pattern the API enforces while the model
writes; `to_invoice` then turns them into the shared `Invoice`.
"""

from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Annotated

from openai import APIError, OpenAI

# The helper `responses.parse()` uses to turn a model into the request schema.
# Private to the SDK, so an upgrade can move it; the settings test catches that.
from openai.lib._parsing._responses import type_to_text_format_param
from openai.types.responses import (
    ResponseFormatTextJSONSchemaConfigParam,
    ResponseOutputMessage,
    ResponseOutputText,
)
from pydantic import BaseModel, ConfigDict, Field, StringConstraints, ValidationError

from document_extractor.pdf_reader import read_pdf
from document_extractor.schema import Invoice, LineItem
from document_extractor.token_usage import TokenUsage

DEFAULT_MODEL = "gpt-6-luna"  # D26: the model is one setting, so another can be added
# gpt-6-luna's prices in dollars per million tokens, checked 2026-10-17 (D26).
# Tied to DEFAULT_MODEL: a different model needs its own prices here.
INPUT_DOLLARS_PER_MILLION_TOKENS = 0.10
OUTPUT_DOLLARS_PER_MILLION_TOKENS = 0.50

# D19's label conventions, so the model follows the rules the labels follow.
# Instructions only, no examples: examples drawn from samples would tune it to
# the dev set, and held-out text must never reach the prompt (D6).
INSTRUCTIONS = """\
You extract header fields and line items from the text of one invoice.

Return null for any field the page does not show. Never guess, and never
compute a value that is not printed.

- vendor_name: the seller's name (not the customer's). If the page prints
  both a short or brand name and a fuller registered company name (usually
  ending in a legal suffix such as Ltd, Inc or GmbH), give the registered
  name. Otherwise give the name as printed. Never add address parts such as
  a city or postcode.
- invoice_number: exactly as printed.
- issue_date: the invoice date, not the due date. Read numeric dates in the
  format of the seller's country (day/month in most countries, month/day in
  the United States). If the order cannot be told, return null.
- currency: the ISO 4217 code a careful reader would give from the currency
  symbol together with the addresses. If the page leaves it unclear, null.
- subtotal, tax, total: the amounts as printed in the lines labelled subtotal,
  tax (VAT, GST, sales tax, ...) and total. Write them with a dot and exactly
  two decimals, no symbol and no thousands separators (12731.44). If the page
  prints no separate tax amount, tax is null. If it prints extra figures the
  schema has no field for (a rebate, shipping), still give the printed
  subtotal, tax and total; do not adjust them.
- line_items: the rows of the item table, in page order across all pages.
  A line is a row in that table with its own amount. Return [] if the invoice
  has no item rows, and null only if it has an item table you cannot read.
  - Not lines: rows of the totals block (subtotal, shipping, discount, tax,
    total) and table headers repeated on later pages.
  - description: everything in the row's description cell as one string with
    single spaces, joining a description that wraps onto the next line. Leave
    out item codes, position numbers and units of measure.
  - quantity and unit_price: as printed, with a dot for decimals, no symbol
    and no thousands separators, at most four decimals.
  - line_total: the row's amount, written like the header amounts. If the row
    has a discount, unit_price is the printed rate and line_total the amount
    after the discount.
  - A row charged as a percentage of a base amount: quantity is the base
    amount, unit_price is null, line_total is the charge.
  - A row priced in another currency and converted: quantity and unit_price
    are null, line_total is the converted amount in the invoice currency.
"""

# "12731.44": digits, a dot, exactly two decimals, no symbol or separators.
# Without this the SDK would offer the model "number or any string", and
# "$12,731.44" would pass the API but fail `Invoice` (D26).
MoneyText = Annotated[str, StringConstraints(pattern=r"^-?\d+\.\d{2}$")]
CurrencyCode = Annotated[str, StringConstraints(pattern=r"^[A-Z]{3}$")]
# "15" or "84.6050": quantities and unit rates can carry up to four decimals,
# so they do not use the two-decimal money pattern (D34.7).
QuantityText = Annotated[str, StringConstraints(pattern=r"^-?\d+(\.\d{1,4})?$")]


class LlmLineItem(BaseModel):
    """One row of the item table. Every field required, as in `LlmInvoice`."""

    model_config = ConfigDict(extra="forbid")

    description: str | None = Field(
        description="The row's description as one string, without item codes"
    )
    quantity: QuantityText | None = Field(
        description="As printed; for a percentage row, the base amount"
    )
    unit_price: QuantityText | None = Field(
        description="The printed rate, before any row discount"
    )
    line_total: MoneyText | None = Field(
        description="The row's amount, after any row discount"
    )


class LlmInvoice(BaseModel):
    """The schema sent to the model. No defaults: strict structured outputs
    require every field, so "not on the page" must be an explicit null."""

    model_config = ConfigDict(extra="forbid")

    vendor_name: str | None = Field(description="The seller's name as printed")
    invoice_number: str | None = Field(description="Exactly as printed")
    # Three numbers, not one "YYYY-MM-DD" string: asked for one string, the
    # model wrote the year first and filled it by copying the page's leading
    # digits (30.04.2026 -> 3004-04-30). Split, it read all three right (D26).
    issue_year: int | None = Field(
        description="Year of the invoice date, not the due date"
    )
    issue_month: int | None = Field(description="Month of the invoice date, 1 to 12")
    issue_day: int | None = Field(description="Day of the invoice date, 1 to 31")
    currency: CurrencyCode | None = Field(description="ISO 4217 code, e.g. EUR")
    subtotal: MoneyText | None
    tax: MoneyText | None
    total: MoneyText | None
    # Null is "could not read the table", [] is "no item rows" (D18).
    line_items: list[LlmLineItem] | None = Field(
        description="Item table rows in page order; [] if none, null if unreadable"
    )


def strict_text_format() -> ResponseFormatTextJSONSchemaConfigParam:
    """The strict JSON schema `responses.parse()` would send for `LlmInvoice`."""
    text_format = type_to_text_format_param(LlmInvoice)
    if text_format["type"] != "json_schema":
        raise TypeError(f"expected a json_schema format, got {text_format['type']}")
    return text_format


# Built once at import; the same request schema as before the move to create().
TEXT_FORMAT = strict_text_format()


def decimal_from_text(text: str | None) -> Decimal | None:
    # Decimal from the text, never via float, so the cents stay exact (D10).
    return Decimal(text) if text is not None else None


def to_invoice(llm_invoice: LlmInvoice) -> Invoice:
    """Convert the model's answer into the shared `Invoice` (D26)."""
    line_items = (
        None
        if llm_invoice.line_items is None
        else [
            LineItem(
                description=row.description,
                quantity=decimal_from_text(row.quantity),
                unit_price=decimal_from_text(row.unit_price),
                line_total=decimal_from_text(row.line_total),
            )
            for row in llm_invoice.line_items
        ]
    )
    return Invoice(
        vendor_name=llm_invoice.vendor_name,
        invoice_number=llm_invoice.invoice_number,
        issue_date=issue_date_from_parts(
            llm_invoice.issue_year, llm_invoice.issue_month, llm_invoice.issue_day
        ),
        currency=llm_invoice.currency,
        subtotal=decimal_from_text(llm_invoice.subtotal),
        tax=decimal_from_text(llm_invoice.tax),
        total=decimal_from_text(llm_invoice.total),
        line_items=line_items,
    )


def issue_date_from_parts(
    year: int | None, month: int | None, day: int | None
) -> date | None:
    """Join the model's three date numbers into a date, or None (D26)."""
    if year is None or month is None or day is None:
        # A missing part is never filled in by guessing (D11).
        return None
    try:
        return date(year, month, day)
    except ValueError:
        # Month 30 or 30 February: the date is unusable, but the other fields
        # are still good, so it counts as missing instead of failing the call.
        return None


class LlmExtractionError(Exception):
    """The call failed, was refused, or was cut off (D26). Never guessed around:
    the scoring run counts the invoice's fields as missing and counts the failure."""


class LlmExtractor:
    def __init__(
        self, client: OpenAI | None = None, model: str = DEFAULT_MODEL
    ) -> None:
        # Without a client the SDK builds one that reads OPENAI_API_KEY from
        # the environment. Tests pass a client with a fake HTTP layer.
        self._client = client if client is not None else OpenAI()
        self._model = model
        # The token counts of the most recent call, for `score`'s cost report
        # (D29). None before any call and after a call that returned nothing.
        self.last_usage: TokenUsage | None = None

    def extract(self, pdf_path: Path) -> Invoice:
        """Same signature as `rules_extractor.extract` (D5), same input text (D26)."""
        page_text = "\n".join(page.text for page in read_pdf(pdf_path).pages)
        return self.extract_from_text(page_text)

    def extract_from_text(self, page_text: str) -> Invoice:
        # Cleared first, so a failed call cannot leave the previous call's
        # tokens behind to be counted twice.
        self.last_usage = None
        try:
            # create(), not parse(): parse() validates the JSON before the
            # status can be read, so a cut-off reply looked like a schema break
            # and its tokens went unmetered (D34.7).
            response = self._client.responses.create(
                model=self._model,
                instructions=INSTRUCTIONS,
                input=page_text,
                text={"format": TEXT_FORMAT},
                # Reasoning tokens count against max_output_tokens. 16,000
                # covers the largest dev invoice's rows plus reasoning; the
                # model allows 128,000 (D34.7).
                reasoning={"effort": "low"},
                max_output_tokens=16000,
                # Nothing is ever fetched back, so OpenAI need not keep it.
                store=False,
            )
        except APIError as error:
            # Timeouts, connection errors and 4xx/5xx all derive from APIError.
            raise LlmExtractionError(f"OpenAI call failed: {error}") from error

        # Recorded before the status checks: a refused or cut-off reply was
        # still billed. output_tokens already includes the reasoning tokens.
        if response.usage is not None:
            self.last_usage = TokenUsage(
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
            )
        if response.status == "incomplete":
            reason = (
                response.incomplete_details.reason
                if response.incomplete_details
                else None
            )
            # Partial JSON is never used (D34.7).
            raise LlmExtractionError(f"reply cut off: {reason}")
        messages = [
            item for item in response.output if isinstance(item, ResponseOutputMessage)
        ]
        content = messages[-1].content if messages else []
        # A refusal arrives as a "refusal" block instead of "output_text".
        if not all(isinstance(part, ResponseOutputText) for part in content) or (
            not content
        ):
            raise LlmExtractionError("no parsed answer (refused or empty)")
        reply_text = "".join(
            part.text for part in content if isinstance(part, ResponseOutputText)
        )
        try:
            llm_invoice = LlmInvoice.model_validate_json(reply_text)
        except ValidationError as error:
            raise LlmExtractionError(
                f"reply did not fit the schema: {error}"
            ) from error
        return to_invoice(llm_invoice)
