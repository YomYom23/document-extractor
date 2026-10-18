"""Extract invoice header fields with an OpenAI model (D5, D15, D26).

The model never fills `Invoice` directly. It fills `LlmInvoice`, whose money
fields are strings with a strict pattern the API enforces while the model
writes; `to_invoice` then turns them into the shared `Invoice`.
"""

from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Annotated

from openai import APIError, OpenAI
from pydantic import BaseModel, ConfigDict, Field, StringConstraints, ValidationError

from document_extractor.pdf_reader import read_pdf
from document_extractor.schema import Invoice

DEFAULT_MODEL = "gpt-6-luna"  # D26, Q39

# D19's label conventions, so the model follows the rules the labels follow.
# Instructions only, no examples: examples drawn from samples would tune it to
# the dev set, and held-out text must never reach the prompt (D6).
INSTRUCTIONS = """\
You extract header fields from the text of one invoice.

Return null for any field the page does not show. Never guess, and never
compute a value that is not printed.

- vendor_name: the seller's name as printed (not the customer's).
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
"""

# "12731.44": digits, a dot, exactly two decimals, no symbol or separators.
# Without this the SDK would offer the model "number or any string", and
# "$12,731.44" would pass the API but fail `Invoice` (D26).
MoneyText = Annotated[str, StringConstraints(pattern=r"^-?\d+\.\d{2}$")]
CurrencyCode = Annotated[str, StringConstraints(pattern=r"^[A-Z]{3}$")]


class LlmInvoice(BaseModel):
    """The schema sent to the model. No defaults: strict structured outputs
    require every field, so "not on the page" must be an explicit null."""

    model_config = ConfigDict(extra="forbid")

    vendor_name: str | None = Field(description="The seller's name as printed")
    invoice_number: str | None = Field(description="Exactly as printed")
    issue_date: date | None = Field(description="The invoice date, not the due date")
    currency: CurrencyCode | None = Field(description="ISO 4217 code, e.g. EUR")
    subtotal: MoneyText | None
    tax: MoneyText | None
    total: MoneyText | None


def to_invoice(llm_invoice: LlmInvoice) -> Invoice:
    """Convert the model's answer into the shared `Invoice` (D26)."""

    def money(text: str | None) -> Decimal | None:
        # Decimal from the text, never via float, so the cents stay exact (D10).
        return Decimal(text) if text is not None else None

    return Invoice(
        vendor_name=llm_invoice.vendor_name,
        invoice_number=llm_invoice.invoice_number,
        issue_date=llm_invoice.issue_date,
        currency=llm_invoice.currency,
        subtotal=money(llm_invoice.subtotal),
        tax=money(llm_invoice.tax),
        total=money(llm_invoice.total),
        line_items=None,  # header fields only (D26)
    )


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

    def extract(self, pdf_path: Path) -> Invoice:
        """Same signature as `rules_extractor.extract` (D5), same input text (D26)."""
        page_text = "\n".join(page.text for page in read_pdf(pdf_path).pages)
        return self.extract_from_text(page_text)

    def extract_from_text(self, page_text: str) -> Invoice:
        try:
            response = self._client.responses.parse(
                model=self._model,
                instructions=INSTRUCTIONS,
                input=page_text,
                text_format=LlmInvoice,
                # Reasoning tokens count against max_output_tokens; 4000
                # leaves room so reasoning cannot crowd out the JSON (D26).
                reasoning={"effort": "low"},
                max_output_tokens=4000,
                # Nothing is ever fetched back, so OpenAI need not keep it.
                store=False,
            )
        except APIError as error:
            # Timeouts, connection errors and 4xx/5xx all derive from APIError.
            raise LlmExtractionError(f"OpenAI call failed: {error}") from error
        except ValidationError as error:
            # parse() validates the reply itself. A reply cut off mid-JSON
            # (status "incomplete") fails here, before we could check status.
            raise LlmExtractionError(
                f"reply did not fit the schema: {error}"
            ) from error

        if response.status == "incomplete":
            reason = (
                response.incomplete_details.reason
                if response.incomplete_details
                else None
            )
            raise LlmExtractionError(f"reply cut off: {reason}")
        llm_invoice = response.output_parsed
        if llm_invoice is None:
            # A refusal arrives as a "refusal" block, so nothing was parsed.
            raise LlmExtractionError("no parsed answer (refused or empty)")
        return to_invoice(llm_invoice)
