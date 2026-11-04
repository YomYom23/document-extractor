# document-extractor Blueprint

## System Overview

A learning and portfolio project (D1) that extracts structured header fields
and line items from digital PDF invoices (D2) into one fixed schema (D3), and measures how
well each approach does against hand-labelled samples (D6). Three extractors
are compared on the same inputs: hand-written rules, rules plus a Jev currency
resolver, and an OpenAI model. Use it from the command line (D7):

```sh
uv run document-extractor extract invoice.pdf --extractor rules
uv run --env-file .env document-extractor score --set dev --extractor llm
```

## Subdirectories & System Boundaries

- document_extractor: [./document_extractor/README.md](./document_extractor/README.md) -
  the schema, PDF reader, the three extractors, the scorer and the CLI.
- scripts: [./scripts/README.md](./scripts/README.md) - billed live checks,
  run by hand from the repo root.
- docs: no code. [decisions.md](./docs/decisions.md) holds the current rules
  (D1 onward; the D numbers in the code point here), with a one-line-per-entry
  [decisions-index.md](./docs/decisions-index.md) and the frozen old log in
  [decisions-history.md](./docs/decisions-history.md),
  [comparison.md](./docs/comparison.md) is the write-up of the scores, and
  [null-sources.md](./docs/null-sources.md) lists why each field can come
  back null.
- samples: no code. `dev/` and `heldout/` hold PDFs with
  `<name>.expected.json` labels; sources and licences are in
  [ATTRIBUTION.md](./samples/ATTRIBUTION.md). `private/` is git-ignored.
- tests: the pytest suite, a `test_<module>.py` for each module except
  `token_usage.py`, plus `test_samples.py` for the labels. Network calls are
  faked; `scripts/` has no tests.

## Global Invariants

- Every extractor has the signature `extract(pdf_path) -> Invoice`.
- Missing is `null`, never a guess; money is `Decimal`.
- The LLM extracts line items; the rules extractors do not (D34). Line items
  are scored as a separate block.
- The held-out set is for the final comparison only. Its text never shapes a
  rule or a prompt.
- Each change ends with pytest, ruff and mypy all clean (D13).

## Global Side Effects

- Billed calls to OpenAI (`OPENAI_API_KEY`) and TypeSafe
  (`TYPESAFE_API_KEY`), read from the git-ignored `.env`.
- Reads PDFs and label JSON under `samples/`. Nothing is written to disk.

## System Verification

- Run: `uv run pytest`, `uv run ruff check .` and `uv run mypy .`
