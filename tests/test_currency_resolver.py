import json
from collections.abc import Mapping
from decimal import Decimal
from pathlib import Path

from typesafe_sdk import Choice, ChoiceAnswer

from document_extractor.currency_resolver import (
    CURRENCY_QUESTION,
    DOLLAR_AMOUNT,
    resolve_currency,
)
from document_extractor.jev import JevError
from document_extractor.schema import Invoice

NAMIBIAN_PAGE = "Windhoek\nTel +264 52 555 0619\nTOTAL $12,731.44"


class FakeJev:
    """Stands in for `Jev.ask`: returns a fixed answer and records each call."""

    def __init__(self, choice: str, confidence: float) -> None:
        self.answer = ChoiceAnswer(
            type="choice",
            choice=choice,
            confidence=confidence,
            probabilities={choice: confidence},
        )
        self.calls: list[tuple[str, Mapping[str, Choice]]] = []

    def ask(
        self, state: str, questions: Mapping[str, Choice]
    ) -> Mapping[str, ChoiceAnswer]:
        self.calls.append((state, questions))
        return {question_key: self.answer for question_key in questions}


def bare_dollar_invoice() -> Invoice:
    # What the rules extractor returns for a "$" page: currency unknown.
    return Invoice(total=Decimal("12731.44"), currency=None)


def test_a_confident_answer_fills_the_currency() -> None:
    jev = FakeJev("NAD", confidence=0.95)
    resolved = resolve_currency(bare_dollar_invoice(), NAMIBIAN_PAGE, jev.ask)
    assert resolved.currency == "NAD"
    assert resolved.total == Decimal("12731.44")  # nothing else changes
    state, _questions = jev.calls[0]
    assert state == NAMIBIAN_PAGE  # Jev sees the whole page (D25)


def test_a_known_currency_is_never_sent_to_jev() -> None:
    jev = FakeJev("NAD", confidence=0.95)
    invoice = Invoice(currency="EUR")
    assert resolve_currency(invoice, "TOTAL € 10.406,52", jev.ask) == invoice
    assert jev.calls == []


def test_below_the_threshold_stays_null() -> None:
    jev = FakeJev("NAD", confidence=0.79)  # D25 threshold is 0.8
    assert (
        resolve_currency(bare_dollar_invoice(), NAMIBIAN_PAGE, jev.ask).currency is None
    )


def test_unclear_stays_null_however_confident() -> None:
    jev = FakeJev("unclear", confidence=1.0)
    assert (
        resolve_currency(bare_dollar_invoice(), NAMIBIAN_PAGE, jev.ask).currency is None
    )


def test_a_page_without_a_dollar_amount_is_not_sent() -> None:
    # Currency is null for another reason (0129: no total line). Not this
    # stage's job (D25, Q32).
    jev = FakeJev("USD", confidence=1.0)
    page = "The total amount due is EUR 196,147.20."
    assert resolve_currency(bare_dollar_invoice(), page, jev.ask).currency is None
    assert jev.calls == []


def test_a_jev_failure_leaves_the_currency_null() -> None:
    def failing_ask(
        state: str, questions: Mapping[str, Choice]
    ) -> Mapping[str, ChoiceAnswer]:
        raise JevError("timed out")

    invoice = bare_dollar_invoice()
    assert resolve_currency(invoice, NAMIBIAN_PAGE, failing_ask) == invoice


def test_snippet_answers_are_codes_jev_can_return() -> None:
    # A snippet expecting a code missing from the Choice could never pass the
    # live check, which would look like a model error instead of a data error.
    snippets_path = Path(__file__).parent.parent / "samples" / "currency_snippets.json"
    snippets = json.loads(snippets_path.read_text(encoding="utf-8"))
    assert len(snippets) >= 10
    offered_codes = set(CURRENCY_QUESTION.criteria) - {"unclear"}
    for snippet in snippets:
        assert snippet["expected"] is None or snippet["expected"] in offered_codes
        assert DOLLAR_AMOUNT.search(snippet["text"])  # else the stage skips it
