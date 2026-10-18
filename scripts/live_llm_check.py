"""Billed live run of the LLM extractor on the 9 dev invoices (D26). On request only.

    uv run python -m scripts.live_llm_check

Needs OPENAI_API_KEY in this repo's .env (git-ignored) and a budget set on
the OpenAI project (D8). Held-out invoices are not sent: they are kept for
the final comparison (D6, D19). Prints each invoice's missing and wrong
fields, then per-field totals, with failed calls counted separately (D26).
"""

from pathlib import Path

from document_extractor.llm_extractor import LlmExtractionError, LlmExtractor
from document_extractor.schema import Invoice
from document_extractor.scoring import Outcome, score_dataset, score_invoice
from scripts.dotenv_key import load_key_from_dotenv

DEV_DIRECTORY = Path(__file__).parent.parent / "samples" / "dev"


def main() -> None:
    load_key_from_dotenv("OPENAI_API_KEY")
    extractor = LlmExtractor()
    pairs: list[tuple[Invoice, Invoice]] = []
    failed_calls = 0

    for pdf_path in sorted(DEV_DIRECTORY.glob("*.pdf")):
        label_path = pdf_path.with_name(pdf_path.stem + ".expected.json")
        expected = Invoice.model_validate_json(label_path.read_text(encoding="utf-8"))
        try:
            predicted = extractor.extract(pdf_path)
        except LlmExtractionError as error:
            # Scored as all-missing, never as guessed values; counted apart so
            # "the call broke" is not mistaken for "the model did not know".
            failed_calls += 1
            print(f"{pdf_path.stem:30} FAILED: {error}")
            predicted = Invoice()
        pairs.append((predicted, expected))

        outcomes = score_invoice(predicted, expected)
        not_correct = {
            field: outcome.value
            for field, outcome in outcomes.items()
            if outcome is not Outcome.CORRECT
        }
        print(f"{pdf_path.stem:30} {not_correct or 'all correct'}")
        # Show the value next to its label for every wrong field, so a wrong
        # answer can be judged (model error or label error) without a re-run.
        for field, outcome in outcomes.items():
            if outcome is Outcome.WRONG:
                print(
                    f"{'':32}{field}: got {getattr(predicted, field)!r}, "
                    f"label {getattr(expected, field)!r}"
                )

    dataset_score = score_dataset(pairs)
    print(f"\n{dataset_score.invoice_count} invoices, {failed_calls} failed calls")
    print({outcome.value: count for outcome, count in dataset_score.overall.items()})
    for field, counts in dataset_score.per_field.items():
        print(
            f"  {field:15}", {outcome.value: count for outcome, count in counts.items()}
        )


if __name__ == "__main__":
    main()
