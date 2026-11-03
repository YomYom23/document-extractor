"""Compare an extracted invoice to its hand-written label.

Each field is correct, missing or wrong (D21). A null where the label has a value
is missing, and a value against a null label is wrong (D11). Money, dates and
invoice number must match exactly; text is compared after normalising (D12).
Line items are paired first, by total and then by description, and scored as a
separate block (D34.5).
"""

from collections import Counter, defaultdict
from collections.abc import Callable, Hashable, Iterable
from dataclasses import dataclass, field
from enum import StrEnum

from document_extractor.schema import Invoice, LineItem

# Header fields; line fields are LINE_FIELDS, scored as a separate block (D34.5).
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


# --- Line items (D34.5) ------------------------------------------------------

LINE_FIELDS = ("description", "quantity", "unit_price", "line_total")


class PairPass(StrEnum):
    TOTAL = "total"
    DESCRIPTION = "description"


@dataclass(frozen=True)
class LinePair:
    """One labelled row and its predicted partner. A missing side is None:
    an unpaired labelled row, or an invented predicted row."""

    label_index: int | None
    predicted_index: int | None
    pass_: PairPass | None


def description_key(line: LineItem) -> str | None:
    return None if line.description is None else normalise_text(line.description)


def pair_by_key(
    labels: list[int],
    predictions: list[int],
    label_key: Callable[[int], Hashable | None],
    predicted_key: Callable[[int], Hashable | None],
) -> list[tuple[int, int]]:
    """Pair rows that share a non-null key, k-th with k-th in page order."""
    waiting: dict[Hashable, list[int]] = defaultdict(list)
    for j in predictions:
        key = predicted_key(j)
        if key is not None:
            waiting[key].append(j)
    pairs = []
    for i in labels:
        key = label_key(i)
        if key is not None and waiting[key]:
            pairs.append((i, waiting[key].pop(0)))
    return pairs


def pair_lines(predicted: list[LineItem], expected: list[LineItem]) -> list[LinePair]:
    """Pair labelled rows with predicted rows (D34.5).

    Pass 1 pairs identical totals; inside a group of equal totals, identical
    descriptions pair first and the rest in page order. Pass 2 pairs the
    leftovers by identical description. Everything else stays unpaired, so a
    dropped row never shifts later rows onto the wrong partner.
    """
    partner: dict[int, tuple[int, PairPass]] = {}

    def free_labels() -> list[int]:
        return [i for i in range(len(expected)) if i not in partner]

    def free_predictions() -> list[int]:
        taken = {j for j, _ in partner.values()}
        return [j for j in range(len(predicted)) if j not in taken]

    labels_by_total: dict[Hashable, list[int]] = defaultdict(list)
    for i, line in enumerate(expected):
        if line.line_total is not None:
            labels_by_total[line.line_total].append(i)
    for total, group_labels in labels_by_total.items():
        group_predictions = [
            j for j in range(len(predicted)) if predicted[j].line_total == total
        ]
        same_description = pair_by_key(
            group_labels,
            group_predictions,
            lambda i: description_key(expected[i]),
            lambda j: description_key(predicted[j]),
        )
        used_labels = {i for i, _ in same_description}
        used_predictions = {j for _, j in same_description}
        rest_labels = [i for i in group_labels if i not in used_labels]
        rest_predictions = [j for j in group_predictions if j not in used_predictions]
        # Page order is the last tie-break, used only where the totals agree.
        for i, j in [*same_description, *zip(rest_labels, rest_predictions)]:
            partner[i] = (j, PairPass.TOTAL)

    for i, j in pair_by_key(
        free_labels(),
        free_predictions(),
        lambda i: description_key(expected[i]),
        lambda j: description_key(predicted[j]),
    ):
        partner[i] = (j, PairPass.DESCRIPTION)

    pairs = [
        LinePair(i, *partner[i]) if i in partner else LinePair(i, None, None)
        for i in range(len(expected))
    ]
    pairs += [LinePair(None, j, None) for j in free_predictions()]
    return pairs


@dataclass(frozen=True)
class ScoredPair:
    pair: LinePair
    outcomes: dict[str, Outcome]


@dataclass(frozen=True)
class InvoiceLineScore:
    """Every pair of one invoice with its field outcomes, in pair_lines order."""

    pairs: list[ScoredPair]

    @property
    def labelled(self) -> int:
        return sum(p.pair.label_index is not None for p in self.pairs)

    @property
    def predicted(self) -> int:
        return sum(p.pair.predicted_index is not None for p in self.pairs)

    @property
    def by_total(self) -> int:
        return sum(p.pair.pass_ is PairPass.TOTAL for p in self.pairs)

    @property
    def by_description(self) -> int:
        return sum(p.pair.pass_ is PairPass.DESCRIPTION for p in self.pairs)

    @property
    def unpaired_labels(self) -> int:
        return sum(p.pair.predicted_index is None for p in self.pairs)

    @property
    def invented(self) -> int:
        return sum(p.pair.label_index is None for p in self.pairs)


def score_lines(predicted: Invoice, expected: Invoice) -> InvoiceLineScore | None:
    """Pair and score the line items; None when the label is null (D34.6)."""
    if expected.line_items is None:
        return None
    labelled = expected.line_items
    # A null prediction ("could not tell") leaves every labelled row unpaired,
    # the same as "no rows".
    predictions = predicted.line_items or []
    scored = []
    for pair in pair_lines(predictions, labelled):
        # Unpaired rows count in full, null fields included: score_field would
        # call a null label against "no row" correct.
        if pair.predicted_index is None:
            outcomes = dict.fromkeys(LINE_FIELDS, Outcome.MISSING)
        elif pair.label_index is None:
            outcomes = dict.fromkeys(LINE_FIELDS, Outcome.WRONG)
        else:
            label = labelled[pair.label_index]
            prediction = predictions[pair.predicted_index]
            outcomes = {
                field_name: score_field(
                    getattr(prediction, field_name),
                    getattr(label, field_name),
                    is_text=field_name == "description",
                )
                for field_name in LINE_FIELDS
            }
        scored.append(ScoredPair(pair, outcomes))
    return InvoiceLineScore(scored)


@dataclass
class LineDatasetScore:
    # Invoices scored; invoices with a null label are counted in skipped_count.
    invoice_count: int = 0
    skipped_count: int = 0
    per_field: dict[str, Counter[Outcome]] = field(
        default_factory=lambda: {name: Counter() for name in LINE_FIELDS}
    )
    overall: Counter[Outcome] = field(default_factory=Counter)
    invented: int = 0
    unpaired_labels: int = 0
    # The invoice with the most labelled rows (the first one on a tie), and the
    # overall counts without it, because one invoice holds 38% of dev rows.
    largest_name: str | None = None
    largest_labelled: int = 0
    overall_without_largest: Counter[Outcome] = field(default_factory=Counter)


def score_line_dataset(
    results: Iterable[tuple[str, Invoice, Invoice]],
) -> LineDatasetScore:
    """Score many (name, predicted, expected) results and add up the lines."""
    dataset = LineDatasetScore()
    largest_overall: Counter[Outcome] = Counter()
    for name, predicted, expected in results:
        score = score_lines(predicted, expected)
        if score is None:
            dataset.skipped_count += 1
            continue
        dataset.invoice_count += 1
        invoice_overall: Counter[Outcome] = Counter()
        for scored in score.pairs:
            for field_name, outcome in scored.outcomes.items():
                dataset.per_field[field_name][outcome] += 1
                invoice_overall[outcome] += 1
        dataset.overall += invoice_overall
        dataset.invented += score.invented
        dataset.unpaired_labels += score.unpaired_labels
        if score.labelled > dataset.largest_labelled:
            dataset.largest_name = name
            dataset.largest_labelled = score.labelled
            largest_overall = invoice_overall
    dataset.overall_without_largest = dataset.overall - largest_overall
    return dataset
