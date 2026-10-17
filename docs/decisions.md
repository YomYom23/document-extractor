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

## D21. Scorer design (`document_extractor/scoring.py`, step 3)
Applies D11 and D12; the open choices below are the recommended ones, pending your questions.
- Each header field gets one of three outcomes: `correct`, `missing` (extractor returned `null`, label has a value) or `wrong` (extractor returned
  a value that differs from the label). If the label is `null`, a `null` is `correct` and any value is `wrong`: inventing a value the page lacks is the worst failure.
- Header fields scored: vendor name, invoice number, issue date, currency, subtotal, tax, total. Line items stay out until later (D12).
- Comparison: `Decimal` equality for money (`Decimal("10.0") == Decimal("10.00")`, so trailing zeros do not matter), `date` equality, exact string for invoice number and
  currency, lower-case and collapsed-whitespace string for vendor name.
- Results are reported as counts of correct / missing / wrong per field and overall. No single blended percentage, because D11 says wrong is worse than missing and
  a blend would hide which one an extractor is doing.
- Pure functions: `score_invoice(predicted, expected)` and `score_dataset(...)`. No file or PDF access inside the scorer; the CLI (later) feeds it.
- The arithmetic warning (D20) is a separate function in its own file section and is not part of any score.

## D22. Arithmetic warning (`document_extractor/arithmetic_check.py`; built before step 4, implements D20)
Recommended choices, pending your questions.
- Own module, not part of `scoring.py`: it needs no label, so the CLI can run it on a real extraction with no expected answer. The scorer never imports it (D20).
- `arithmetic_warning(invoice) -> str | None`: a message saying which numbers disagree, or `None` when they agree. Alternative: return a bool. A message is better because
  a bare "failed" does not tell a reader what to look at.
- Exact `Decimal` comparison, no tolerance (D10): the page prints rounded figures, so a correct extraction adds up to the cent. A tolerance would hide a real one-cent misread.
- If subtotal, tax or total is `null` the check cannot run and returns `None`. A `null` tax is not treated as zero: that would be a guess (D11).
- Only subtotal + tax = total. Summing line items against the subtotal waits until line items are scored (D12).
- Two of the 12 samples print a rebate, so they must produce a warning even though their labels are right (D20). That is the first test.

## D23. PDF reader (`document_extractor/pdf_reader.py`, step 4)
Recommended choices, pending your questions. Checked: `pdfplumber` 0.11.10 is current on PyPI and MIT-licensed; all 12 samples are one page and have a text layer.
- `read_pdf(pdf_path) -> PdfDocument`. `PdfDocument` holds a list of `PdfPage`; each page has `width`, `height`, `text` (for the LLM) and `words` (for the rules
  extractor). Each `Word` has `text`, `x0`, `x1`, `top`, `bottom`. All frozen dataclasses of our own.
- No `pdfplumber` object leaves this module. Why: swapping the library (D14) then touches one file, and `pdfplumber` returns untyped dicts that would otherwise spread
  through code checked by `mypy --strict`.
- Coordinates are kept as `pdfplumber` gives them: points (1/72 inch), origin at the top-left, `top` growing down the page.
- Words, not `pdfplumber`'s ready-made lines. Its lines join side-by-side columns ("Columbus, OH 43215 Invoice #: ACM-100145"), so the rules extractor
  needs the word positions to separate them. `text` stays for the LLM, which reads the merged lines fine.
- A list of pages even though every sample is one page, so a two-page invoice does not need a new interface later. Multi-page extraction is still out of scope (D19).
- If no page has any words, raise `NoTextLayerError`. Why: a scan would otherwise reach the extractors as an empty page, come back all `null`, and be scored as "missing",
  which hides the real cause (D2: digital PDFs only).
- Tests open the real sample PDFs and check known words and positions, plus a blank PDF for the error. Only `read_pdf` is tested; it is the module's one seam.

## D24. Rules extractor (`document_extractor/rules_extractor.py`, step 5; grilling Q24 to Q31)
Every rule comes from the 8 dev samples only (D19). No model is used (the Jev currency resolver is a separate stage, D25).
- Scope: header fields only. `line_items` is `null` until line items are scored (D12).
- Lines: words are on the same line when they overlap vertically by at least 60% of the shorter word's height (measured on dev: same-line pairs at least 71%,
  different lines at most 48%; label and value `top` can differ by 2.9 pt, so a fixed point tolerance would be fragile). A line is cut into segments
  (visual columns) where the gap between words exceeds 12 pt (measured: spaces at most 5.4 pt, column gaps at least 24.1 pt).
- Invoice number and issue date: a label ending in a colon (`Invoice No:`, `Invoice Number:`, `Invoice #:`, `Date:`) found anywhere in a line, because the `b_` samples
  have no columns. The value is the text after it in the same segment, or the next segment if the label ends its segment. `Due Date:` and `Due:` never count.
- Subtotal, tax, total: the label (`Subtotal`; `Tax`, `Sales Tax`, `VAT`, `MwSt`, `TVA`, `BTW`; `Total`) must start a segment, and the value is the first amount to its right on
  that line. Why not anywhere in the line: `b_INV-2026-0129`'s sentence "The subtotal including VAT is EUR 196,147.20" would also be read as the tax, a wrong value. Starting
  a segment leaves 0129's subtotal and total missing instead, which D11 prefers.
- Amounts are parsed one at a time: the last `.` or `,` followed by exactly two digits at the end is the decimal point; other `.`, `,` and spaces are thousands separators.
  Without exactly two decimals it is not an amount, so `VAT No: 4334037646` is never read as tax.
- Currency, from the total's line: an ISO code (`EUR`) wins; otherwise `€` = EUR, `£` = GBP, a leading `R` = ZAR; a bare `$` gives `null` (D25 resolves it).
- Dates: dotted dates are day.month.year; month names are unambiguous; slash dates are decided by a part over 12, and are `null` when both parts are 12 or under.
- Vendor name: the first segment from the top that is not a title (`INVOICE`, `TAX INVOICE`) or logo initials (three capitals or fewer), cut before any label.
- Tests: `extract(pdf_path)` on each dev sample, scored with `score_invoice`; never a `wrong` field, and each sample's `missing` fields are pinned. `parse_amount`
  and `parse_date` get tables of literal inputs and outputs.
- Expected on dev before any code: 51 of 56 header fields correct, 5 missing (US currency and date, FR date, 0129 subtotal and total), 0 wrong.
  Measured after building: 50 correct, 6 missing, 0 wrong. The prediction missed that 0129's currency is also lost, because currency is read from the
  total's line and 0129 has no total line.

### Open problem: ambiguous slash dates
`09/03/2026` can be 9 March (FR) or 3 September (US). The rules extractor returns `null` for these, costing the FR and US dev dates. Candidate fixes to decide later:
a country signal from the address or phone prefix, or a Jev resolver stage like the currency one (D25), with the page text as state.

## D25. Jev currency resolver (`document_extractor/currency_resolver.py`, step 5b; grilling Q32 to Q38 and the earlier agreement)
A sixth part (amends D16). The rules extractor stays model-free; this stage runs after it. The final comparison has three rows: rules, rules + Jev currency, LLM.
- Runs only when the rules extractor's currency is `null` and the page has a `$` amount. Other lost currencies (0129, no total line) are a total-finding
  problem, not this stage's.
- One Jev `Choice` over USD, CAD, AUD, NZD, SGD, HKD, NAD, MXN, plus `unclear`. A code outside the list cannot come back, so the worst case is missing.
- State is the whole page text: phone prefix, email domain and both addresses are the clues, and the question says the currency is the one the amounts
  are written in (the bill-to country can differ). Cost per invoice is negligible ($0.042 per million input tokens).
- The answer is used only when it is a code (not `unclear`) with confidence at least 0.8. Calibration is the vendor's claim; the final threshold is set
  from the live snippet run and recorded here.
- A Jev failure leaves the currency `null` and the extraction carries on: an outage shows up as missing fields, never as a crash or a guess.
- `document_extractor/jev.py` is a trimmed copy of lead-bot's wrapper (Choice only), not an import across repos. Dependency `typesafe-sdk>=0.7.5,<0.8`.
- Tests use a fake `ask` function. A separate, billed live script runs the real Jev on the snippets and the `$` samples, only on request, with
  `TYPESAFE_API_KEY` in this repo's git-ignored `.env`.
- New data: `samples/dev/a_currency-nad-bare-dollar.pdf` (Invoice Extraction Benchmark v1, CC BY 4.0), labelled `NAD`, dev grows to 9. Added after the
  rules were written, so it is also an unseen test for them. Plus about 10 short `$` snippets with correct codes, drafted by me and checked by you.
