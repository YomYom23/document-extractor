"""Compare an extracted invoice to its hand-written label.

Each field is correct, missing or wrong (D21). A null where the label has a value
is missing, and a value against a null label is wrong (D11). Money, dates and
invoice number must match exactly; text is compared after normalising (D12).
"""

from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass, field
from enum import StrEnum

from document_extractor.schema import Invoice

# D34: header fields only until line-item scoring is built.
HEADER_FIELDS = (
    "vendor_name",
    "invoice_number",
    "issue_date",
    "currency",
    "subtotal",
    "tax",
    "total",
)


class Outcome(StrEnum):
    CORRECT = "correct"
    # The extractor said "not found". Bad, but safe.
    MISSING = "missing"
    # The extractor gave a different value. Worse than missing (D11): a
    # confident wrong total is the dangerous failure.
    WRONG = "wrong"


# Only free text is compared loosely (D12). Invoice number and currency are
# identifiers: "inv-0042" and "INV-0042" could be two different invoices.
TEXT_FIELDS = frozenset({"vendor_name"})


def score_invoice(predicted: Invoice, expected: Invoice) -> dict[str, Outcome]:
    """Score each header field of `predicted` against `expected`."""
    return {
        field_name: score_field(
            getattr(predicted, field_name),
            getattr(expected, field_name),
            is_text=field_name in TEXT_FIELDS,
        )
        for field_name in HEADER_FIELDS
    }


def normalise_text(text: str) -> str:
    # casefold, not lower: it also handles non-English letters (German "ß").
    # split() with no argument drops leading/trailing spaces and collapses
    # runs of whitespace, so "  ACME   ltd " becomes "acme ltd".
    return " ".join(text.casefold().split())


def score_field(
    predicted_value: object, expected_value: object, *, is_text: bool = False
) -> Outcome:
    if is_text and isinstance(predicted_value, str) and isinstance(expected_value, str):
        predicted_value = normalise_text(predicted_value)
        expected_value = normalise_text(expected_value)
    if predicted_value == expected_value:
        return Outcome.CORRECT
    if predicted_value is None:
        return Outcome.MISSING
    return Outcome.WRONG


@dataclass
class DatasetScore:
    """Counts, not a percentage: a blend would hide whether an extractor
    leaves fields empty (safe) or fills them wrongly (dangerous), D21."""

    invoice_count: int = 0
    # A Counter returns 0 for an outcome never seen, so callers can index
    # any Outcome without checking whether it occurred.
    per_field: dict[str, Counter[Outcome]] = field(
        default_factory=lambda: {name: Counter() for name in HEADER_FIELDS}
    )
    overall: Counter[Outcome] = field(default_factory=Counter)


def score_dataset(pairs: Iterable[tuple[Invoice, Invoice]]) -> DatasetScore:
    """Score many (predicted, expected) pairs and add up the outcomes."""
    dataset_score = DatasetScore()
    for predicted, expected in pairs:
        dataset_score.invoice_count += 1
        for field_name, outcome in score_invoice(predicted, expected).items():
            dataset_score.per_field[field_name][outcome] += 1
            dataset_score.overall[outcome] += 1
    return dataset_score
