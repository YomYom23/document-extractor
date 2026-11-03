from collections import Counter
from datetime import date
from decimal import Decimal

import pytest

from document_extractor.schema import Invoice, LineItem
from document_extractor.scoring import (
    HEADER_FIELDS,
    LINE_FIELDS,
    Outcome,
    PairPass,
    pair_lines,
    score_dataset,
    score_invoice,
    score_line_dataset,
    score_lines,
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


# --- Line items (D34.5) ------------------------------------------------------


def row(description: str | None, line_total: str | None) -> LineItem:
    """A line where only description and total matter; the rest is null."""
    return LineItem(
        description=description,
        line_total=None if line_total is None else Decimal(line_total),
    )


TOTAL = PairPass.TOTAL
DESCRIPTION = PairPass.DESCRIPTION

# Each case: labelled rows, predicted rows (as (description, line_total)) and
# the expected pairs as (label_index, predicted_index, pass_).
PAIRING_CASES = {
    "identical lists": (
        [("a", "1"), ("b", "2")],
        [("a", "1"), ("b", "2")],
        [(0, 0, TOTAL), (1, 1, TOTAL)],
    ),
    "a dropped middle row": (
        [("a", "1"), ("b", "2"), ("c", "3")],
        [("a", "1"), ("c", "3")],
        [(0, 0, TOTAL), (1, None, None), (2, 1, TOTAL)],
    ),
    "a misread total, same description": (
        [("a", "1")],
        [("a", "9")],
        [(0, 0, DESCRIPTION)],
    ),
    "a misread total, different description": (
        [("a", "1")],
        [("x", "9")],
        [(0, None, None), (None, 0, None)],
    ),
    "equal totals in page order": (
        [("a", "5"), ("b", "5")],
        [("a", "5"), ("b", "5")],
        [(0, 0, TOTAL), (1, 1, TOTAL)],
    ),
    "equal totals reordered": (
        [("a", "5"), ("b", "5")],
        [("b", "5"), ("a", "5")],
        [(0, 1, TOTAL), (1, 0, TOTAL)],
    ),
    "equal totals, descriptions differ": (
        [("a", "5"), ("b", "5")],
        [("x", "5"), ("y", "5")],
        [(0, 0, TOTAL), (1, 1, TOTAL)],
    ),
    "a dropped first duplicate": (
        [("a", "5"), ("b", "5")],
        [("b", "5")],
        [(0, None, None), (1, 0, TOTAL)],
    ),
    "a wrong total equal to another row's total": (
        [("a", "1"), ("b", "2")],
        [("a", "2"), ("b", "2")],
        [(0, 0, DESCRIPTION), (1, 1, TOTAL)],
    ),
    "null totals never pair by total": (
        [("a", None)],
        [("x", None)],
        [(0, None, None), (None, 0, None)],
    ),
    "a null total still pairs by description": (
        [("a", None)],
        [("a", None)],
        [(0, 0, DESCRIPTION)],
    ),
    "null descriptions never pair by description": (
        [(None, "1")],
        [(None, "9")],
        [(0, None, None), (None, 0, None)],
    ),
    "a null description still pairs by total": (
        [(None, "1")],
        [(None, "1")],
        [(0, 0, TOTAL)],
    ),
    "descriptions equal after normalising": (
        [("Widget  A", "1")],
        [(" widget a ", "9")],
        [(0, 0, DESCRIPTION)],
    ),
    "credit totals pair like any other": (
        [("refund", "-5.00")],
        [("refund", "-5")],
        [(0, 0, TOTAL)],
    ),
    "invented rows come after the labelled rows": (
        [("a", "1")],
        [("x", "8"), ("a", "1"), ("y", "9")],
        [(0, 1, TOTAL), (None, 0, None), (None, 2, None)],
    ),
    "no predicted rows": (
        [("a", "1")],
        [],
        [(0, None, None)],
    ),
}


@pytest.mark.parametrize(
    ("labelled", "predicted", "expected_pairs"),
    PAIRING_CASES.values(),
    ids=PAIRING_CASES.keys(),
)
def test_pair_lines(
    labelled: list[tuple[str | None, str | None]],
    predicted: list[tuple[str | None, str | None]],
    expected_pairs: list[tuple[int | None, int | None, PairPass | None]],
) -> None:
    pairs = pair_lines(
        predicted=[row(*r) for r in predicted], expected=[row(*r) for r in labelled]
    )
    got = [(p.label_index, p.predicted_index, p.pass_) for p in pairs]
    assert got == expected_pairs
    # Every labelled and every predicted row appears exactly once.
    label_indexes = [p.label_index for p in pairs if p.label_index is not None]
    predicted_indexes = [
        p.predicted_index for p in pairs if p.predicted_index is not None
    ]
    assert sorted(label_indexes) == list(range(len(labelled)))
    assert sorted(predicted_indexes) == list(range(len(predicted)))


def lines_invoice(rows: list[LineItem] | None) -> Invoice:
    return make_invoice(line_items=rows)


def test_paired_fields_are_scored_like_header_fields() -> None:
    label = LineItem(
        description="Widget A",
        quantity=Decimal(2),
        unit_price=Decimal("5.00"),
        line_total=Decimal("10.00"),
    )
    prediction = LineItem(
        description="  WIDGET a",
        quantity=None,
        unit_price=Decimal("5.50"),
        line_total=Decimal("10.0"),
    )
    score = score_lines(lines_invoice([prediction]), lines_invoice([label]))
    assert score is not None
    assert score.pairs[0].outcomes == {
        "description": Outcome.CORRECT,
        "quantity": Outcome.MISSING,
        "unit_price": Outcome.WRONG,
        "line_total": Outcome.CORRECT,
    }


def test_every_field_of_an_unpaired_labelled_row_is_missing() -> None:
    # Null label fields count too: score_field would call null vs null correct.
    score = score_lines(lines_invoice([]), lines_invoice([row("a", "1")]))
    assert score is not None
    assert score.pairs[0].outcomes == dict.fromkeys(LINE_FIELDS, Outcome.MISSING)
    assert score.unpaired_labels == 1
    assert score.invented == 0


def test_every_field_of_an_invented_row_is_wrong() -> None:
    all_null = LineItem()
    score = score_lines(
        lines_invoice([row("a", "1"), all_null]), lines_invoice([row("a", "1")])
    )
    assert score is not None
    assert score.pairs[1].outcomes == dict.fromkeys(LINE_FIELDS, Outcome.WRONG)
    assert score.invented == 1
    assert (score.labelled, score.predicted) == (1, 2)
    assert (score.by_total, score.by_description) == (1, 0)


def test_a_null_label_skips_the_invoice() -> None:
    assert score_lines(lines_invoice([row("a", "1")]), lines_invoice(None)) is None


@pytest.mark.parametrize("prediction", [None, []])
def test_a_null_or_empty_prediction_leaves_every_label_unpaired(
    prediction: list[LineItem] | None,
) -> None:
    score = score_lines(
        lines_invoice(prediction), lines_invoice([row("a", "1"), row("b", "2")])
    )
    assert score is not None
    assert score.unpaired_labels == 2
    assert score.predicted == 0


def test_line_dataset_sums_invoices_and_skips() -> None:
    results = [
        # 1 labelled row, all 4 fields correct.
        ("one", lines_invoice([row("a", "1")]), lines_invoice([row("a", "1")])),
        # 2 labelled rows: one pair (description wrong), one unpaired label.
        (
            "two",
            lines_invoice([row("x", "1")]),
            lines_invoice([row("a", "1"), row("b", "2")]),
        ),
        # Skipped: null label.
        ("skip", lines_invoice([row("a", "1")]), lines_invoice(None)),
        # Also 2 labelled rows, plus one invented row. The tie for the largest
        # invoice goes to the first one given ("two").
        (
            "tie",
            lines_invoice([row("a", "1"), row("b", "2"), row("z", "9")]),
            lines_invoice([row("a", "1"), row("b", "2")]),
        ),
    ]
    dataset = score_line_dataset(results)

    assert (dataset.invoice_count, dataset.skipped_count) == (3, 1)
    assert dataset.per_field["description"] == Counter(
        {Outcome.CORRECT: 3, Outcome.MISSING: 1, Outcome.WRONG: 2}
    )
    # one: 4 correct. two: 3 correct, 1 wrong, 4 missing. tie: 8 correct,
    # 4 wrong (the invented row).
    assert dataset.overall == Counter(
        {Outcome.CORRECT: 15, Outcome.MISSING: 4, Outcome.WRONG: 5}
    )
    assert (dataset.invented, dataset.unpaired_labels) == (1, 1)
    assert (dataset.largest_name, dataset.largest_labelled) == ("two", 2)
    assert dataset.overall_without_largest == Counter(
        {Outcome.CORRECT: 12, Outcome.WRONG: 4}
    )


def test_an_empty_line_dataset_has_no_largest_invoice() -> None:
    dataset = score_line_dataset([])
    assert dataset.invoice_count == 0
    assert dataset.largest_name is None
    assert dataset.overall_without_largest == Counter()
