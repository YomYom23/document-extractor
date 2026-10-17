# Decision log

One entry per decision: what was chosen, the alternatives, and why. Decided 2026-10-16 in a grilling session.

## D1. Purpose: learning and portfolio project
Not a product. Multi-tenancy, billing and deployment are out of scope until stated otherwise.
Every architecture decision is made together, and each component is explained before its code is written.

## D2. Input: digital-PDF invoices only
Alternatives: scanned PDFs, photos, other document types (receipts, contracts, forms).
Why: scans need an OCR or vision stage first, which is a separate project. Invoices have clear fields and
can be checked by eye. Scans and photos are a possible second phase.

## D3. Output: one fixed invoice schema
Alternative: a schema the user defines at run time. Why not: the fixed schema can be validated and scored.

## D4. Decision log lives in the repo
This file. Chat explanations stay short; the reasons live here.

## D5. Two extractors behind one signature
Rules (regex and position heuristics) first, LLM second, both exposed as `extract(pdf_path) -> Invoice`.
Alternative: a hybrid. Why not yet: building both pure versions shows where each fails and gives a real comparison.
A hybrid is only worth building if the scores justify it.

## D6. Measure with a labelled test set and a scoring script
10 to 15 real or public invoices, each with hand-written expected JSON. The scoring script is written before any
extractor so every change is measured. Generated invoices can add layout variety later.

## D7. Interface: CLI only
`extract invoice.pdf` prints JSON. The learning is in extraction and evaluation. An HTTP API can wrap the same
function later.

## D8. LLM access: hosted API with a hard spend cap
Samples are public or non-sensitive, so a local model is not needed.

## D9. Schema fields
Vendor, invoice number, issue date, currency, subtotal, tax, total, line items
(description, quantity, unit price, line total). Left out for now: due date, addresses, payment terms.
Why: every field must be hand-labelled on every sample. Subtotal + tax = total is a cheap consistency check.

## D10. Pydantic models with `Decimal` and `date`
Money is `Decimal`, never `float` (`0.1 + 0.2 != 0.3`). Alternative: stdlib dataclasses with hand-written
validation. Why Pydantic: it validates for us, and structured-output APIs take Pydantic schemas directly.

## D11. Missing fields are `null`, never guessed
Every field is nullable. Scoring counts a wrong value as worse than a missing one, because a confident wrong total
is the dangerous failure. No confidence scores for now. The LLM prompt must explicitly allow null.

## D12. Scoring rules
Exact match for money, dates and invoice number. Text fields are compared after normalising case and whitespace.
Header fields only at first. Line items come later, scored as a set matched by line total.

## D13. Project hygiene
`.idea/` and `.venv/` are git-ignored. pytest, ruff and mypy are dev dependencies; each step ends with all three clean.
No commits until the project actually starts.

## D14. PDF reader: `pdfplumber`
Alternatives: `pypdf` (plain text only), `PyMuPDF` (AGPL). Why: the rules extractor needs word coordinates ("the number
right of the label Total"), and the licence is permissive. It sits behind its own small function so it can be swapped.

## D15. LLM provider: OpenAI
Why: existing account and key, and its schema-enforced responses fit D10. Before writing the extractor, confirm the
current structured-output API from the docs.

## D16. Layout: five parts plus a thin CLI
`schema`, `pdf_reader`, `rules_extractor`, `llm_extractor`, `scoring`, `cli`. Each is one concept to understand and
can be tested alone.

## D17. Build order
1. schema, 2. samples and labels, 3. scoring, 4. PDF reader, 5. rules extractor, 6. LLM extractor, 7. CLI,
8. comparison write-up. Each step starts with an explanation and a log entry, then your questions, then code.

## D18. Schema details (`document_extractor/schema.py`)
- `Invoice` and `LineItem` are Pydantic models with `extra="forbid"`: an invented field raises instead of being dropped.
- `line_items` is `None` for "could not tell" and `[]` only when the extractor sees an empty table. The scorer treats the two differently.
- `currency` is an ISO 4217 code ("USD"). An ambiguous symbol like "$" gives `None`. No check against a currency list yet.
- No arithmetic rule (subtotal + tax = total) in the schema. A model that refused inconsistent numbers could not represent a wrong extraction, so the scorer could not measure it. The check will be a separate function.
- Pydantic turns a JSON number such as `19.99` into `Decimal("19.99")` exactly (checked on pydantic 2.14.1), so JSON input does not reintroduce float error.
- The package is `document_extractor/` at the repo root, with `pythonpath = ["."]` in pytest config. mypy runs in strict mode.

## D19. Samples and labels (`samples/`)
- 12 synthetic invoices as `samples/<set>/<name>.pdf` + `<name>.expected.json` (an `Invoice` in JSON). `dev/` has 8, `heldout/` has 4.
  The split was a seeded random shuffle (seed 42), not chosen by difficulty. Held-out labels are for the final comparison only: no rule is written
  from them and the LLM prompt never contains them (D6).
- Sources (licences checked): 8 from Invoice Extraction Benchmark v1 (CC BY 4.0), one per visibly different layout template; 4 from InvoiceBenchmark (MIT),
  one per text layout (2 table, 1 paragraph, 1 mixed). Attribution is in `samples/ATTRIBUTION.md`. Both are synthetic, and each comes from a single generator,
  so layout variety is lower than real supplier invoices. A third source was dropped: the Kaggle datasets need a login, and the other candidates were images.
- Labels were drafted from the PDF text, not from the datasets' answer keys. My arithmetic checks: quantity x unit price = line total on every row, and the lines
  sum to the subtotal. The datasets' answer keys agree on every header field and line total except one invoice (see label conventions).
- Label conventions: values are what the page prints. Where the page prints a figure the schema has no field for (rebate, shipping, withholding), the label
  keeps the printed subtotal, tax and total, so subtotal + tax can differ from total. Currency is the ISO code a human reader would give, using the
  address and symbol together. Dates in the sample's own format (dd/mm or mm/dd) are read as that country's format. Where a line states only an amount
  ("we invoice EUR 10,773.40"), quantity and unit price are `null`.
- Left out for now: multi-page, credit notes, scans and photos, dual-currency payable invoices, and invoices whose totals do not add up.

## D20. The arithmetic check is a flag, not a correctness test (amends D9)
Two of the 12 samples print a rebate the schema has no field for, so subtotal + tax != total even when the extraction is right
(shipping, credit applied and withholding would do the same). The check will be a separate function that reports a warning.
It never marks an extraction wrong, and the scorer compares fields to the labels only. No `adjustments` field is added.
