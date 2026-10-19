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

### Live run, 2026-10-17 (`uv run python -m scripts.live_currency_check`, 13 billed Jev calls)
Jev's pick was right on all 13: every code, and `unclear` (0.95) on the snippet with no clue. Confidence was 0.94 to 1.00 except two:
the NZ seller billing an Australian customer (NZD, 0.82) and the US seller billing a Canadian customer (USD, 0.73), which are the two cases I had
flagged as judgment calls.

| threshold | correct | missing | wrong |
| --- | --- | --- | --- |
| 0.5 to 0.7 | 13 | 0 | 0 |
| 0.8 | 12 | 1 | 0 |
| 0.9 | 11 | 2 | 0 |
| 0.95 | 10 | 3 | 0 |

Threshold stays at 0.8. No threshold produced a wrong answer, so 13 cases do not show where wrong answers start; lowering to 0.7 would gain only
the US-to-Canada case, whose low confidence matches its real ambiguity. Revisit with more `$` invoices.

## D26. LLM extractor (`document_extractor/llm_extractor.py`, step 6; grilling Q39 to Q46)
Checked against developers.openai.com on 2026-10-17: `openai` 3.34.0 is current; `client.responses.parse(model=, input=, text_format=<Pydantic model>)`
returns `response.output_parsed`; strict structured outputs need every field `required` and `additionalProperties: false`, and support `pattern` and
`format: date` on strings. The 3.x SDK is built on `httpx2`.
- Model `gpt-6-luna` ($0.10 / $0.50 per million input / output tokens; a full 13-invoice run is estimated under $0.02). The model id is one setting, so a
  `gpt-6.1-sol` row can be added later.
- The model fills its own schema, `LlmInvoice`, not `Invoice` (amends D10). Why: the SDK turns a `Decimal` field into "number or any string" with no pattern,
  so `"$12,731.44"` would pass the API and then fail our validation. In `LlmInvoice` money is a string matching `^-?\d+\.\d{2}$` and currency matches
  `^[A-Z]{3}$`; the API enforces both while the model writes. Code converts it to `Invoice`.
- Header fields only; `line_items` is `null`, as in the rules extractor (D24).
- Input is the `pdf_reader` page text, the same input the rules extractor gets, so the comparison measures extraction and not PDF reading.
- Prompt: instructions only, no examples. They are D19's label conventions (printed values, ISO currency from symbol and address, the invoice's own date
  format, `null` when not on the page, D11). No sample text, dev or held-out, appears in the prompt (D6).
- Request: `reasoning={"effort": "low"}`, `max_output_tokens=4000` (reasoning tokens count against it), `store=False`.
- An API error, a refusal or an incomplete reply raises `LlmExtractionError`. The scoring run counts that invoice's fields as missing and reports the number
  of failed calls separately. A failure never becomes guessed values.
- Tests: contract tests drive the real SDK with only the HTTP layer mocked (request body, parsed reply, refusal, incomplete reply, HTTP 500); unit tests
  for the `LlmInvoice` to `Invoice` conversion. The billed live run covers the 9 dev invoices only, on request, with `OPENAI_API_KEY` in `.env`.
  A monthly budget is set on the OpenAI project (D8).

### Live run 1, 2026-10-17 (`uv run python -m scripts.live_llm_check`, 9 billed calls, dev only)
0 failed calls. 54 of 54 non-date header fields correct, including what the rules missed (US currency, 0129's subtotal and total from sentences).
`issue_date` was wrong on all 9, with years built from the printed day and month digits: `30.04.2026` gave 3004-04-30, `09/03/2026` gave 0909-03-03,
`12 February 2026` gave 1202-12-12. The same failure on every layout and format points at how the date is requested, not at reading. Leading hypothesis,
unverified: the strict `format: date` constraint. Open: diagnose before changing anything (see the handoff plan); the rules extractor had 7 of 9 dates
correct and none wrong.

### Diagnosis, 2026-10-19 (10 billed calls, all on `a_clean-de-grid-eu-decimals.pdf`, which prints `Date: 30.04.2026`; scratch scripts, not in the repo)
- The model's raw JSON text already holds the bad year (`"issue_date":"3034-04-30"`); parsing passes it through. Not a parsing bug.
- 3 calls per variant: `issue_date` as a string with pattern `^\d{4}-\d{2}-\d{2}$` instead of `format: date` gave `3004-30-30`, `3004-30-04`,
  `3004-06-30`; the original schema without the "read numeric dates in the format of the seller's country" sentence gave `3004-04-30` twice and
  `3046-04-30`; three integer fields gave 2026 / 4 / 30 on all 3.
- Cause: asking for one `YYYY-MM-DD` string at all. The year is written first and the model fills it by copying the page's leading digits. `format: date`
  and the prompt wording are not the cause. The bad year changes between calls, so one call per variant would not have shown this.

### Amendment (grilling Q47): the date is asked for as three numbers
- `LlmInvoice` replaces `issue_date` with `issue_year`, `issue_month`, `issue_day`, each `int | None`. `to_invoice` builds the `date`.
- If any of the three is null, `issue_date` is null: a partial date is never completed by guessing (D11).
- If the three do not form a real date (month 30, 30 February), `issue_date` is null rather than an error, because the other six fields are still good.
  It scores as missing, not wrong.
- Rejected: keeping one string and adding examples to the prompt. Examples invented for the prompt would not break D6, but they only steer the model away
  from the failure; three fields remove it, need no prompt text, and do not depend on which date formats the examples happen to cover.

### Live run 2, 2026-10-19 (after Q47; `uv run python -m scripts.live_llm_check`, 9 billed calls, dev only)
0 failed calls. 63 of 63 header fields correct, `issue_date` 9 of 9, including `09/03/2026`, which the rules extractor leaves `null` as ambiguous (D24).
This is one run per invoice; live run 1 and the diagnosis showed the date answer can change between calls, so the held-out run is the real check.

## D27. Null-source register (`docs/null-sources.md`)
Every code path that can leave a field `null` is listed there with its trigger, the reason, and its dev cost, so each cause can be studied for a
fix later. Any new path that can produce a `null` (including the CLI's handling of errors) gets an entry in the same commit.

## D28. CLI (`document_extractor/cli.py`, step 7; grilling Q48 to Q56)
- Two subcommands: `extract <pdf>` prints one invoice as JSON (D7); `score` runs one extractor over a sample set and prints the counts (D21).
- Run as `uv run document-extractor ...`, through a `[project.scripts]` entry point that calls `document_extractor.cli:main`.
- Parser: `argparse` (stdlib). `click` and `typer` were the alternatives; for two subcommands they would add dependencies and save little.
  `argparse` returns untyped (`Any`) values, so they are copied into typed variables right after parsing.
- `--extractor rules|rules-jev|llm`, default `rules`, the only free one with no key or network. The names are the comparison's three rows (D25).
- "rules + Jev" is `extract_with_currency_resolver(pdf_path, ask)` in `currency_resolver.py`, not CLI code, so it can be tested alone. It reads
  the PDF twice (rules extractor, then page text for Jev); that costs milliseconds.
- `extract`: stdout carries only the invoice JSON. The D22 arithmetic warning and errors go to stderr. No text layer or a failed LLM call prints an
  error, no JSON, and exits 1: a failure is never shown as an all-null invoice. A Jev failure is not an error: the currency stays `null` (D25).
- `score --extractor X --set dev|heldout`, default `dev`; held-out runs only when named (D6). A failed extraction is scored as an all-null invoice
  (seven missing fields, except where the label is null too) and the number of failures is printed separately (D26). Its report replaces `scripts/live_llm_check.py`, which is deleted;
  `scripts/live_currency_check.py` stays because it runs the `$` snippets, not invoices.
- Keys come from the environment only; locally `uv run --env-file .env document-extractor ...` (uv 0.12.13 has `--env-file`). A missing key for
  `llm` or `rules-jev` prints an error and exits 1 before any PDF is read.
- Test seam: `main(argv, extractors=None) -> int`. Tests pass the arguments as a list, read output with `capsys`, run the real rules extractor on dev,
  and pass fakes for `llm` and `rules-jev`, so no test uses the network.
- Added while building (not grilled): a `[build-system]` using `uv_build` with `module-root = ""`. Without one uv never installs the project, so
  `[project.scripts]` is skipped and the command does not exist. Side effect: `document_extractor` is now importable from anywhere in the venv.
  Also added: `extract` on a path that is not a file prints an error and exits 1 instead of a pdfplumber traceback.

### Held-out run, 2026-10-19 (first run of any extractor on held-out; 4 billed OpenAI calls, 0 Jev calls)
`uv run --env-file .env document-extractor score --extractor <name> --set heldout`, 4 invoices, 28 header fields, 0 failed extractions.

| extractor | correct | missing | wrong |
| --- | --- | --- | --- |
| rules | 26 | 2 | 0 |
| rules-jev | 26 | 2 | 0 |
| llm | 28 | 0 | 0 |

Both rules misses are `a_clean-zm-banner` (Zambia): `Date: 18-Mar-2025` is a format `parse_date` does not know (null-sources N5), and the
currency is printed only as `K` (kwacha, label ZMW), which `detect_currency` does not know (N12). Jev was not called: the page has no `$`
amount (N14), so rules-jev equals rules here. The score report does not show whether Jev was called or failed; that was checked by hand.

## D29. Comparison write-up (`docs/comparison.md`, step 8; grilling Q57 to Q63)
- Lives in `docs/comparison.md`. Contents: correct / missing / wrong per extractor on dev and held-out, totals and per field; every miss traced to
  its `docs/null-sources.md` entry; cost and time per invoice; what changed on the way (D25 threshold, D26 date fix); limits (synthetic samples
  from two generators, 4 held-out invoices, how many runs).
- Extractors are ranked on accuracy only: wrong first, then missing (D11). Cost and time are reported beside the ranking, never folded into it.
- `score` measures instead of estimating (Q59): wall time per invoice for every extractor; for `llm`, the input and output tokens the API reports
  per reply (`response.usage`; output includes reasoning tokens), priced at D26's $0.10 / $0.50 per million. Cached-input discounts are ignored,
  so the cost is an upper bound. A reply that fails schema validation raises before its usage can be read, so its tokens are not counted.
  `LlmExtractor` exposes the usage of its last call as `last_usage`.
- `score --extractor rules-jev` prints how many times Jev was asked and how many calls failed (Q60). The CLI wraps the `ask` function it hands to
  the resolver; `resolve_currency` is unchanged. Jev's SDK reports token usage too (`SystemOneResponse.usage`, each count `None` when the API
  leaves it out), so `Jev` exposes `last_usage` and `score` prints Jev's tokens. Only D25's input price is known, so Jev's cost is not priced.
- `llm` and `rules-jev` run 3 times on all 13 invoices before the write-up (Q61): at most 39 OpenAI and 6 Jev calls.
- Extractors are frozen at the commit the runs use (Q62). The held-out set has now been seen, so fixing anything it exposed (N5 `18-Mar-2025`,
  N12 `K`) would tune the rules to it; such fixes are later work, measured on new held-out samples.
- The write-up ends with a verdict, backed by the numbers, on whether a hybrid extractor is justified (D5, Q63). Building one is a separate decision.

### Result, 2026-10-19 (commit `b488ce4`; 39 billed OpenAI calls, 6 Jev calls, $0.0051 for the LLM)
Written up in `docs/comparison.md`. All 13 invoices, 91 fields: llm 91 / 0 / 0 in all 3 runs; rules-jev 84 / 7 / 0 in all 3; rules 82 / 9 / 0.
No extractor gave a wrong value. Verdict: the LLM ranks first, and a hybrid is not justified, because it could at best match the LLM's 91 of 91.

## D30. Wider sample set with real invoices (grilling Q64 to Q76)
- Real invoices are your own received invoices, digital PDFs only (Q64). 10 were supplied; the credit note is out of scope (Q67), leaving 9 from three
  templates: Stripe-hosted (6), IONOS (2), Lucid Software (1, two pages). No other source of real, openly licensed, digital invoices was found.
- They and their labels live in git-ignored `samples/private/<set>/` (Q69, Q75) and are sent to OpenAI (`store=False`) and Jev when scored. Only
  aggregate scores are written into the docs. `score --set X` reads `samples/X/` and `samples/private/X/`.
- Labels hold the printed value (Q71). The Stripe text layer has `\x00` where the page shows a hyphen (`9B5AC24F-0001`), so an extractor that
  copies the text layer scores wrong. Repairing it would be a later `pdf_reader` fix.
- Synthetic additions (Q65, Q73): 25 more IEB v1 invoices (all 5 in-scope "hard", 4 multi-page of 2 to 8 pages, 4 each of clean, freight, currency,
  tax; seeded pick, seed 42) and 20 Sinabis invoices (CC BY 4.0, a second layout engine; English, not scanned, text layer, one per issuer country,
  seed 42), read out of the 9.9 GB zip with HTTP range requests. English only (Q66). Multi-page allowed; credit notes, scans and dual-currency
  invoices stay out (Q67).
- Split (Q74): synthetic 50/50 within each category (held-out gets the smaller half); your invoices by template, so held-out templates are unseen:
  Stripe and Lucid in held-out, IONOS in dev. The 4 old held-out invoices moved to dev (Q68). Result: dev 36 public + 2 private, held-out 22 public
  + 7 private.
- New labels are header-only: `line_items` is `null` (not scored, D12; the multi-page IEB invoices have up to 117 lines). Drafted from the PDF text
  and cross-checked (Q72): IEB against its answer keys (all 25 agree), Sinabis against its manifest (number, date, currency, total; all 20 agree),
  your 9 by you. Conventions found while labelling: a vendor printed only as a trade name (`PATHWISE VISION`) is labelled as printed;
  shipping, delivery, discount and withholding lines are not fields, so subtotal + tax can differ from total (D19, D20); a currency with no
  decimals (JPY, HUF) is labelled as printed (`88106`).
- `score` prints a subtotal per source prefix (`a_` ieb, `b_` invoicebench, `c_` sinabis, `r_` real) under the overall line (Q76).
- Tests: `test_rules_extractor_on_dev_samples` is pinned to the 9 invoices the rules were written from (D24); the frozen rules' results on the new
  dev invoices are measured by `score`, not asserted. CLI score tests run on a temporary sample tree, so they do not change when samples are added.
