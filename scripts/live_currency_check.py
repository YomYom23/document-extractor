"""Billed live check of the Jev currency resolver (D25). Run only on request.

    uv run python -m scripts.live_currency_check

(`-m` from the repo root puts the root on the import path, so
`document_extractor` imports; `python scripts/...` would not.)

Needs TYPESAFE_API_KEY in this repo's .env (git-ignored). Sends the 11
snippets plus the two bare-"$" dev invoices (13 Jev calls, a fraction of a
cent) and prints each answer, then how many would be correct, missing or
wrong at several thresholds, so D25's threshold can be set from evidence.
"""

import json
from pathlib import Path

from document_extractor.currency_resolver import (
    CURRENCY_QUESTION,
    QUESTION_KEY,
    currency_from_answer,
)
from document_extractor.jev import Jev
from document_extractor.pdf_reader import read_pdf
from document_extractor.schema import Invoice
from scripts.dotenv_key import load_key_from_dotenv

REPO_ROOT = Path(__file__).parent.parent
THRESHOLDS = (0.5, 0.6, 0.7, 0.8, 0.9, 0.95)
DOLLAR_SAMPLES = ("a_clean-us-clean-simple", "a_currency-nad-bare-dollar")


def test_cases() -> list[tuple[str, str, str | None]]:
    """(name, page text, expected currency) for every case to send."""
    snippets = json.loads(
        (REPO_ROOT / "samples" / "currency_snippets.json").read_text(encoding="utf-8")
    )
    cases = [
        (f"snippet {number}", snippet["text"], snippet["expected"])
        for number, snippet in enumerate(snippets, start=1)
    ]
    for sample_name in DOLLAR_SAMPLES:
        pdf_path = REPO_ROOT / "samples" / "dev" / f"{sample_name}.pdf"
        label_path = pdf_path.with_name(f"{sample_name}.expected.json")
        label = Invoice.model_validate_json(label_path.read_text(encoding="utf-8"))
        page_text = "\n".join(page.text for page in read_pdf(pdf_path).pages)
        cases.append((sample_name, page_text, label.currency))
    return cases


def main() -> None:
    load_key_from_dotenv("TYPESAFE_API_KEY")
    jev = Jev()
    results = []
    for name, page_text, expected in test_cases():
        answer = jev.ask(page_text, {QUESTION_KEY: CURRENCY_QUESTION})[QUESTION_KEY]
        results.append((expected, answer))
        print(
            f"{name:28} expected {expected!s:7} jev {answer.choice:8} "
            f"confidence {answer.confidence:.2f}"
        )

    print("\nthreshold  correct  missing  wrong")
    for threshold in THRESHOLDS:
        counts = {"correct": 0, "missing": 0, "wrong": 0}
        for expected, answer in results:
            # Same outcome rules as the scorer (D21): a null where the label
            # is null is correct; a code where it differs is wrong.
            currency = currency_from_answer(answer, threshold)
            if currency == expected:
                counts["correct"] += 1
            elif currency is None:
                counts["missing"] += 1
            else:
                counts["wrong"] += 1
        print(
            f"{threshold:9.2f}  {counts['correct']:7}  {counts['missing']:7}  "
            f"{counts['wrong']:5}"
        )


if __name__ == "__main__":
    main()
