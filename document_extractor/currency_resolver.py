"""Fill in a currency the rules extractor left null because of a bare "$" (D25).

Runs after `rules_extractor.extract`. The rules extractor never calls a
model; this stage is optional, so the comparison can show rules alone and
rules plus this stage as separate rows.
"""

import re
from collections.abc import Callable, Mapping

from typesafe_sdk import Choice, ChoiceAnswer

from document_extractor.jev import JevError
from document_extractor.schema import Invoice

# The shape of `Jev.ask`. Taking a function instead of a Jev object lets tests
# pass a fake without any network or API key.
AskJev = Callable[[str, Mapping[str, Choice]], Mapping[str, ChoiceAnswer]]

# Starting value (D25, Q34). Calibration is TypeSafe's claim, so the final
# value comes from the live snippet run and is recorded in D25.
MIN_CONFIDENCE = 0.8
# "$" straight before a number ("$12,731.44", "$ 25.99").
DOLLAR_AMOUNT = re.compile(r"\$\s?\d")

QUESTION_KEY = "currency"
CURRENCY_QUESTION = Choice(
    instructions=(
        "This is the text of an invoice whose amounts are printed with a bare '$'. "
        "Which currency are the amounts written in? Use the clues on the page: "
        "addresses, phone prefixes, email domains, tax registration names. "
        "The customer's address can be in a different country from the seller's."
    ),
    # Only codes from this list can come back, so the worst case is "missing",
    # never a currency that was not offered (D25, Q33).
    criteria={
        "USD": "United States dollar",
        "CAD": "Canadian dollar",
        "AUD": "Australian dollar",
        "NZD": "New Zealand dollar",
        "SGD": "Singapore dollar",
        "HKD": "Hong Kong dollar",
        "NAD": "Namibian dollar",
        "MXN": "Mexican peso (also printed with '$')",
        "unclear": "The page gives no reliable clue to the currency",
    },
)


def resolve_currency(
    invoice: Invoice,
    page_text: str,
    ask: AskJev,
    min_confidence: float = MIN_CONFIDENCE,
) -> Invoice:
    """Return `invoice` with its currency filled in when Jev is confident."""
    if invoice.currency is not None:
        return invoice  # the rules already found it; never second-guess them
    if not DOLLAR_AMOUNT.search(page_text):
        return invoice  # null for another reason, not a bare "$" (D25, Q32)
    try:
        answer = ask(page_text, {QUESTION_KEY: CURRENCY_QUESTION})[QUESTION_KEY]
    except JevError:
        # An outage must show up as missing fields, not crash the extraction
        # and never turn into a guess (D25).
        return invoice
    currency = currency_from_answer(answer, min_confidence)
    if currency is None:
        return invoice
    # model_copy returns a new Invoice; the rules extractor's result is not changed.
    return invoice.model_copy(update={"currency": currency})


def currency_from_answer(answer: ChoiceAnswer, min_confidence: float) -> str | None:
    """The accept-or-leave-null rule, shared with the live check script."""
    if answer.choice == "unclear" or answer.confidence < min_confidence:
        return None  # wrong is worse than missing (D11)
    return answer.choice
