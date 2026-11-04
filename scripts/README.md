# scripts

## Overview

One-off live checks that call billed APIs. They are run by hand, only on
request, never by the test suite. Run each from the repo root with
`uv run python -m scripts.<name>`, so `document_extractor` is importable.

## Interface

- `live_currency_check.py`: `main()` sends the 11 snippets in
  `samples/currency_snippets.json` and the two bare-`$` dev invoices to Jev
  (13 calls), prints each answer, then the correct / missing / wrong counts at
  thresholds 0.5 to 0.95. This is the evidence for `MIN_CONFIDENCE` in
  [document_extractor](../document_extractor/README.md) (D25). `test_cases()`
  builds the list it sends.
- `dotenv_key.py`: `load_key_from_dotenv(key_name)` copies one key from the
  repo's `.env` into the environment.

## Invariants

- A key's value is never printed.
- The accept-or-leave-null rule is `currency_from_answer` from
  `document_extractor.currency_resolver`, not a copy, so the script measures
  what the resolver does.
- Outcomes are counted the way the scorer counts them (D21): a null where the
  label is null is correct.

## Side Effects

- Reads `.env`, `samples/currency_snippets.json` and two PDFs and labels from
  `samples/dev/`.
- Sets the key in `os.environ`, and exits with a message if `.env` or the key
  is missing.
- Makes billed TypeSafe calls (a fraction of a cent per run).

## Verification

- Not covered by tests. Run `uv run ruff check scripts` and `uv run mypy .`;
  run the script itself only when a live check is wanted.
