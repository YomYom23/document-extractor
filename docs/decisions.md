# Decisions

The current rules, one entry per decision, in number order. Old wording, live runs and diagnoses are in
[decisions-history.md](decisions-history.md), which is frozen. A changed rule is edited in place here; a new rule gets the next free number.

### D1. Purpose: a learning and portfolio project (active)
**Rule:** Not a product. Multi-tenancy, billing and deployment are out of scope until stated otherwise. Every architecture decision is
made together, and each component is explained before its code is written.
**Scope:** process
**Why:** the point is to learn extraction and evaluation, and to show the work.
**Evidence:** [decisions-history.md](decisions-history.md), D1.

### D2. Input: digital-PDF invoices only (active)
**Rule:** Only invoices with a text layer are read. Scans, photos and other document types (receipts, contracts, forms) are out.
**Scope:** pdf_reader, samples
**Why:** scans need an OCR or vision stage first, which is a separate project. Invoices have clear fields and can be checked by eye.
**Rejected:** scanned PDFs and photos (a possible second phase); other document types.
**Evidence:** [decisions-history.md](decisions-history.md), D2.

### D3. Output: one fixed invoice schema (active)
**Rule:** Every extractor returns the same `Invoice` model.
**Scope:** schema, all extractors
**Why:** a fixed schema can be validated and scored.
**Rejected:** a schema the user defines at run time.
**Evidence:** [decisions-history.md](decisions-history.md), D3.

### D4. Decisions are recorded in the repo (active)
**Rule:** Each decision is written down in this file with its reason. Chat explanations stay short and point here.
**Scope:** process
**Why:** the reasons outlive the chat, and the code can cite them by number.
**Evidence:** [decisions-history.md](decisions-history.md), D4.

### D5. Extractors share one signature (active)
**Rule:** Every extractor is exposed as `extract(pdf_path) -> Invoice`. A hybrid extractor is built only if the scores justify it.
**Scope:** all extractors, cli
**Why:** building pure versions shows where each fails and gives a fair comparison.
**Rejected:** starting with a hybrid. D29's verdict found it not justified.
**Evidence:** [decisions-history.md](decisions-history.md), D5 and D29; [comparison.md](comparison.md).

### D6. Measure against a labelled set; held-out stays unseen (active)
**Rule:** Every change is measured against hand-written labels with the scorer. The held-out set is for the final comparison only: no rule is
written from it, and no prompt contains its text.
**Scope:** samples, scoring, all extractors
**Why:** a score is only honest on invoices the extractor was not shaped by.
**Evidence:** [decisions-history.md](decisions-history.md), D6.

### D7. Interface: CLI only (active)
**Rule:** The program is used from the command line. An HTTP API can wrap the same function later.
**Scope:** cli
**Why:** the learning is in extraction and evaluation, not in serving.
**Evidence:** [decisions-history.md](decisions-history.md), D7.

### D8. LLM access: a hosted API with a spend cap (active)
**Rule:** The LLM is a hosted API, with a monthly budget set on the provider project.
**Scope:** llm_extractor
**Why:** the samples are public or non-sensitive, so a local model is not needed.
**Evidence:** [decisions-history.md](decisions-history.md), D8.

### D9. Schema fields (active)
**Rule:** Header fields: vendor name, invoice number, issue date, currency, subtotal, tax, total. Line items: description, quantity, unit
price, line total. Left out: due date, addresses, payment terms.
**Scope:** schema, labels
**Why:** every field must be hand-labelled on every sample, so the list stays short.
**Changed by:** D20, D34
**Evidence:** [decisions-history.md](decisions-history.md), D9.

### D10. Pydantic models with `Decimal` and `date` (active)
**Rule:** `Invoice` and `LineItem` are Pydantic models. Money is `Decimal`, never `float`; dates are `date`.
**Scope:** schema
**Why:** `0.1 + 0.2 != 0.3` in floats. Pydantic validates for us.
**Rejected:** stdlib dataclasses with hand-written validation.
**Changed by:** D26
**Evidence:** [decisions-history.md](decisions-history.md), D10.

### D11. Missing is null, never guessed (active)
**Rule:** Every field is nullable. A field the page does not show is null, and an unsure extractor returns null. The scorer treats a wrong
value as worse than a missing one. No confidence scores.
**Scope:** schema, all extractors, scoring
**Why:** a confident wrong total is the dangerous failure.
**Evidence:** [decisions-history.md](decisions-history.md), D11.

### D12. Header comparison rules (active)
**Rule:** Money, dates and invoice number must match exactly. Text fields are compared after normalising case and whitespace.
**Scope:** scoring
**Why:** exact numbers are what an invoice is used for; case and spacing are presentation.
**Changed by:** D34
**Evidence:** [decisions-history.md](decisions-history.md), D12.

### D13. Each change ends clean (active)
**Rule:** pytest, ruff and mypy (strict) are dev dependencies, and each change ends with all three clean. `.idea/` and `.venv/` are
git-ignored.
**Scope:** process
**Why:** a broken check found later costs more than one fixed now.
**Evidence:** [decisions-history.md](decisions-history.md), D13.

### D14. PDF reader library: `pdfplumber`, behind one module (active)
**Rule:** `pdfplumber` reads the PDFs. Only `pdf_reader` imports a PDF library.
**Scope:** pdf_reader
**Why:** the rules extractor needs word coordinates, and the licence is permissive. One module makes the library swappable.
**Rejected:** `pypdf` (plain text only), `PyMuPDF` (AGPL).
**Changed by:** D32
**Evidence:** [decisions-history.md](decisions-history.md), D14.

### D15. LLM provider: OpenAI (active)
**Rule:** The LLM extractor uses OpenAI's structured outputs.
**Scope:** llm_extractor
**Why:** an existing account and key, and schema-enforced replies fit Pydantic models (D10).
**Evidence:** [decisions-history.md](decisions-history.md), D15.

### D16. Layout: one module per concept, plus a thin CLI (active)
**Rule:** `schema`, `pdf_reader`, `rules_extractor`, `llm_extractor`, `scoring` and `cli`, each testable alone.
**Scope:** document_extractor
**Why:** each module is one concept to understand.
**Changed by:** D25
**Evidence:** [decisions-history.md](decisions-history.md), D16.

### D17. Build order (retired)
**Rule:** None. The eight-step build order is finished and no longer guides work.
**Scope:** process
**Why:** retired because every step is built.
**Evidence:** [decisions-history.md](decisions-history.md), D17.

### D18. Schema details (active)
**Rule:**
1. `Invoice` and `LineItem` use `extra="forbid"`: an invented field raises instead of being dropped.
2. `line_items` is `None` for "could not tell" and `[]` only for an empty table.
3. `currency` is an ISO 4217 code; an ambiguous symbol like `$` gives `None`. No check against a currency list.
4. No arithmetic rule in the schema, so a wrong extraction can still be represented and scored.
5. The package is `document_extractor/` at the repo root; mypy runs in strict mode.
**Scope:** schema
**Why:** the schema must hold any extraction, right or wrong, so the scorer can measure it.
**Evidence:** [decisions-history.md](decisions-history.md), D18.

### D19. Sample labels and the dev/held-out split (active)
**Rule:**
1. Each sample is `samples/<set>/<name>.pdf` plus `<name>.expected.json`, an `Invoice` in JSON.
2. Splits are seeded random picks (seed 42), never chosen by difficulty.
3. Labels hold what the page prints. A printed figure with no schema field (rebate, shipping, withholding) is left out, so subtotal + tax
   can differ from total.
4. Currency is the ISO code a human reader would give from the symbol and address together. Dates are read in the sample country's format.
5. A line that states only an amount has null quantity and unit price.
6. Labels are drafted from the PDF text and cross-checked, not copied from a dataset's answer key. Sources and licences are in
   `samples/ATTRIBUTION.md`.
**Scope:** samples, labels
**Why:** labels must say what a careful reader of the page would answer.
**Changed by:** D30, D31
**Evidence:** [decisions-history.md](decisions-history.md), D19.

### D20. The arithmetic check is a warning, not a correctness test (active)
**Rule:** Subtotal + tax = total is checked by a separate function that reports a warning. It never marks an extraction wrong, and the
scorer compares fields to the labels only. No `adjustments` field.
**Scope:** arithmetic_check, scoring
**Why:** some samples print a rebate or shipping line the schema has no field for, so a correct extraction can fail the sum.
**Changes:** D9
**Evidence:** [decisions-history.md](decisions-history.md), D20.

### D21. Scorer design (active)
**Rule:**
1. Each header field is `correct`, `missing` (null where the label has a value) or `wrong` (a value that differs). Against a null label,
   null is correct and any value is wrong.
2. Seven header fields are scored: vendor name, invoice number, issue date, currency, subtotal, tax, total.
3. `Decimal` and `date` equality, exact strings for invoice number and currency, normalised text for vendor name (D12).
4. Results are counts of correct / missing / wrong per field and overall, never one blended percentage.
5. `score_invoice` and `score_dataset` are pure; the CLI feeds them.
**Scope:** scoring
**Why:** a blend would hide whether an extractor is missing values or inventing them (D11).
**Evidence:** [decisions-history.md](decisions-history.md), D21; `document_extractor/scoring.py`.

### D22. Arithmetic warning module (active)
**Rule:** `arithmetic_warning(invoice) -> str | None` in its own module, which the scorer never imports. It returns a message naming the
numbers that disagree, or `None`. Exact `Decimal` comparison, no tolerance. If subtotal, tax or total is null it returns `None`; a null tax is
never treated as zero. Only subtotal + tax = total; no line-sum check.
**Scope:** arithmetic_check, cli
**Why:** it needs no label, so the CLI can run it on any extraction. A tolerance would hide a one-cent misread.
**Rejected:** returning a bool, which does not say what to look at.
**Evidence:** [decisions-history.md](decisions-history.md), D22; `document_extractor/arithmetic_check.py`.

### D23. PDF reader interface (active)
**Rule:**
1. `read_pdf(pdf_path) -> PdfDocument`, a list of `PdfPage`, each with `width`, `height`, `text` (for the LLM) and `words` (for the rules
   extractor). Each `Word` has `text`, `x0`, `x1`, `top`, `bottom`. All frozen dataclasses of our own; no `pdfplumber` object leaves the module.
2. Coordinates are `pdfplumber`'s: points, origin top-left, `top` growing down.
3. Words, not `pdfplumber`'s lines, which join side-by-side columns.
4. A list of pages even for one-page invoices.
5. No words on any page raises `NoTextLayerError`.
**Scope:** pdf_reader
**Why:** an empty page would come back all null and be scored as missing, hiding the real cause (D2). Own types keep mypy strict.
**Changed by:** D32
**Evidence:** [decisions-history.md](decisions-history.md), D23; `document_extractor/pdf_reader.py`.

### D24. Rules extractor: labels, dates, amounts, currency, vendor (active)
**Rule:** Written from the 9 original dev samples only; no model.
1. Header fields only; `line_items` is `null`.
2. Words share a line when they overlap vertically by at least 60% of the shorter word's height. A gap over 12 pt starts a new segment
   (visual column).
3. Invoice number and issue date: a label ending in a colon, found anywhere in a line; the value is the rest of its segment or the next
   segment. `Due Date:` and `Due:` never count.
4. Subtotal, tax, total: the label must start a segment; the value is the first amount to its right on that line.
5. An amount needs exactly two decimals; the last `.` or `,` before them is the decimal point, other `.`, `,` and spaces are thousands
   separators.
6. Currency comes from the total's line: an ISO code wins, then `€`, `£`, a leading `R`. A bare `$` gives null.
7. Dates: dotted dates are day.month.year; month names are unambiguous; ambiguous slash dates give null.
8. Vendor name: the first segment from the top that is not a title or logo initials, cut before any label.
**Scope:** rules_extractor
**Why:** every threshold was measured on dev; where a rule could read a wrong value, it is narrowed to give null instead (D11).
**Open problem:** ambiguous slash dates (`09/03/2026`) give null. Candidates: a country signal from the address or phone prefix, or a Jev
resolver stage like D25's.
**Evidence:** [decisions-history.md](decisions-history.md), D24.

### D25. Jev currency resolver (active)
**Rule:**
1. A separate stage after the rules extractor (`currency_resolver.py`, with `jev.py`), so the rules extractor stays model-free.
2. It runs only when the rules currency is null and the page has a `$` amount.
3. One Jev `Choice` over USD, CAD, AUD, NZD, SGD, HKD, NAD, MXN or `unclear`, with the whole page text as state.
4. The answer is used only when it is a code with confidence at least 0.8.
5. A Jev failure leaves the currency null; extraction carries on.
6. `jev.py` is a trimmed copy of lead-bot's wrapper, not a cross-repo import.
**Scope:** currency_resolver, jev
**Why:** `$` is the one currency the page cannot settle by symbol; the clues are elsewhere on the page.
**Changes:** D16
**Evidence:** [decisions-history.md](decisions-history.md), D25 (live run setting the 0.8 threshold).

### D26. LLM extractor (active)
**Rule:**
1. Model `gpt-6-luna`, one setting so another model can be added.
2. The model fills its own schema, `LlmInvoice`: money as a string matching `^-?\d+\.\d{2}$`, currency matching `^[A-Z]{3}$`, and the
   issue date as three nullable integers (year, month, day). Code converts it to `Invoice`.
3. A missing date part, or parts that are not a real date, give a null `issue_date`.
4. Input is the `pdf_reader` page text, the same as the rules extractor.
5. The prompt is instructions only (D19's label conventions and D11), with no sample text.
6. Request: low reasoning effort, `max_output_tokens=16000` (D34.7), `store=False`.
7. An API error, refusal or incomplete reply raises `LlmExtractionError`; it never becomes guessed values.
**Scope:** llm_extractor
**Why:** the SDK turns a `Decimal` field into "number or any string", so formats are enforced as patterns. Asking for one date string made
the model copy the page's leading digits into the year.
**Rejected:** one date string with prompt examples, which steer away from the failure instead of removing it.
**Changes:** D10
**Changed by:** D28, D33, D34
**Evidence:** [decisions-history.md](decisions-history.md), D26 (live runs and the date diagnosis).

### D27. Null-source register (active)
**Rule:** Every code path that can leave a field null is listed in `docs/null-sources.md` with its trigger, reason and dev cost. A new path
gets an entry in the same commit.
**Scope:** process, all extractors, cli
**Why:** each cause of a null can then be studied for a fix.
**Evidence:** [decisions-history.md](decisions-history.md), D27; [null-sources.md](null-sources.md).

### D28. CLI (active)
**Rule:**
1. `extract <pdf>` prints one invoice as JSON; `score` runs one extractor over a sample set and prints the counts.
2. Run as `uv run document-extractor`, through a `[project.scripts]` entry point and a `uv_build` build system.
3. `argparse`; its untyped values are copied into typed variables at once.
4. `--extractor rules|rules-jev|llm`, default `rules`; `--set dev|heldout`, default `dev`.
5. `extract`: stdout is only the JSON; warnings and errors go to stderr. No text layer, a failed LLM call or a missing file prints an error
   and exits 1.
6. `score`: a failed extraction is scored as an all-null invoice and the failures are counted separately. It replaces the old live LLM
   check script.
7. Keys come from the environment only; a missing key exits 1 before any PDF is read.
8. Test seam: `main(argv, extractors=None) -> int`.
**Scope:** cli
**Why:** a failure must never look like an all-null invoice in `extract`, and `score` must finish the set.
**Rejected:** `click` and `typer`, dependencies that save little for two subcommands.
**Changes:** D26
**Evidence:** [decisions-history.md](decisions-history.md), D28 (first held-out run).

### D29. Comparison write-up (active)
**Rule:**
1. `docs/comparison.md` holds correct / missing / wrong per extractor, set and field, each miss traced to null-sources, cost and time per
   invoice, and the limits.
2. Extractors are ranked on accuracy only: wrong first, then missing. Cost and time are reported beside the ranking.
3. `score` measures wall time per invoice, LLM tokens and cost (an upper bound), and Jev calls, failures and tokens.
4. Results come from 3 runs of each billed extractor, at a frozen commit.
**Scope:** docs, cli, token_usage
**Why:** measured numbers, not estimates, back the verdict on a hybrid (D5).
**Changed by:** D34
**Evidence:** [decisions-history.md](decisions-history.md), D29; [comparison.md](comparison.md).

### D30. Wider sample set with real invoices (active)
**Rule:**
1. Real invoices are the owner's own received digital PDFs, kept with their labels in git-ignored `samples/private/<set>/`. Only aggregate
   scores reach the docs. `score --set X` reads `samples/X/` and `samples/private/X/`.
2. Synthetic additions: 25 more IEB v1 invoices and 20 Sinabis invoices, English only; multi-page allowed; credit notes, scans and
   dual-currency invoices stay out.
3. Split: synthetic 50/50 within each category; real invoices by template, so held-out templates are unseen. Dev 36 public + 2 private,
   held-out 22 public + 7 private.
4. A trade name printed alone is labelled as printed; a currency with no decimals is labelled as printed.
5. `score` prints a subtotal per source prefix (`a_`, `b_`, `c_`, `r_`).
6. The rules-extractor test is pinned to the 9 original dev invoices; results on the rest are measured by `score`, not asserted.
**Scope:** samples, labels, cli, tests
**Why:** 13 synthetic invoices from two generators could not show how the extractors handle real layouts.
**Changes:** D19
**Evidence:** [decisions-history.md](decisions-history.md), D30; [comparison.md](comparison.md) ("Wider set").

### D31. A vendor's legal name beats its brand (active)
**Rule:** When the page prints both a short brand and the full legal name, the `vendor_name` label is the legal name. One answer per field;
no "also accepted" list.
**Scope:** labels, scoring
**Why:** a legal name is what a supplier record or tax registration is matched against.
**Changes:** D19
**Evidence:** [decisions-history.md](decisions-history.md), D31.

### D32. NUL characters are repaired with pdfium (active)
**Rule:** `read_page` replaces each `\x00` character with the character pdfium finds at the same position, then builds `text` and `words`
with pdfplumber's own functions. Where pdfium has no printable character, the reader writes U+FFFD. The repair runs on any NUL from any PDF.
`pypdfium2` is a declared dependency, imported only in `pdf_reader`.
**Scope:** pdf_reader
**Why:** some PDFs map glyphs to U+0000, so pdfplumber copies a NUL where the page shows a hyphen. Pages without a NUL read exactly as before.
**Rejected:** switching the whole reader to pdfium, which would change every sample's text.
**Changes:** D14, D23
**Evidence:** [decisions-history.md](decisions-history.md), D32 (cause and held-out caveat); [comparison.md](comparison.md) ("After the
NUL repair").

### D33. The LLM prompt states the legal-name rule (active)
**Rule:** The prompt's vendor line asks for the registered name when the page prints both a brand and a fuller company name, the name as
printed otherwise, and never address parts. Its example suffixes are generic (Ltd, Inc, GmbH).
**Scope:** llm_extractor
**Why:** the model took the first name on the page. Suffixes from failing invoices would put held-out text in the prompt (D6).
**Changes:** D26
**Evidence:** [decisions-history.md](decisions-history.md), D33 (result and held-out caveat).

### D34. Line items (active)
**Rule:**
1. LLM only. The rules extractor stays at `line_items=None` as the baseline.
2. A line is a row in the item table with its own amount. Not lines: shipping, discount and tax rows in the totals block, a discount printed
   under an item, repeated headers, carried-forward and page-subtotal rows. Lines keep page order across pages.
3. Labels: a wrapped description is one string with single spaces; item codes and units of measure are left out; the description is
   everything else in that row's description cell. With several amounts, `line_total` is the amount before tax. With a row discount,
   `unit_price` is the printed rate and `line_total` the amount after discount. Zero-amount item rows are lines.
4. A percentage row has `quantity` = the printed base, null `unit_price`, and the amount as `line_total`. A foreign-currency row has null
   quantity and unit price and `line_total` in the invoice currency.
5. Scoring: lines pair by identical `line_total` first; inside a group of equal totals, lines with identical descriptions (after D12's
   normalising) pair first, then the rest in page order. Leftovers pair by identical description, k-th with k-th in page order. A null
   `line_total` never pairs by total; a null description never pairs by description. Lines that match neither way stay unpaired. Each
   pair's 4 fields are scored as header fields, descriptions after D12's normalising. Every field of an unpaired labelled line scores
   missing and every field of an unpaired predicted line scores wrong, null fields included; each unpaired predicted line is counted as
   invented. Line fields are a separate block in `score`, printed for the LLM only.
6. A null label skips the invoice in the line block (the count is printed); a null or `[]` prediction leaves every labelled line unpaired;
   `[]` is not allowed in labels.
7. One call returns header and lines. `line_total` uses the header money pattern; `quantity` and `unit_price` use `-?\d+(\.\d{1,4})?`.
   `max_output_tokens` is 16,000 (the documented maximum for `gpt-6-luna` is 128,000, checked 2026-11-03); a cut-off reply fails the
   whole invoice and partial JSON is never used. A cut-off is
   detected from the reply status before validation, reported as cut off, and metered.
8. Build order: labels, scorer (test-first), `score` output, LLM schema and prompt, then the billed runs:
   1. Header baseline: 3 LLM dev runs before any line-item code; a run with a failed extraction is repeated. The guard values are the
      highest header wrong count and the highest header missing count of the three.
   2. Baseline line run: 1 dev run with the first full prompt, checked against the guard values; if it exceeds either, the first fix
      round addresses the header.
   3. At most 3 fix rounds. A round is one committed change to the prompt or the field descriptions, plus one dev run. Progress means
      line wrong + missing went down and line wrong did not go up. A run whose only failures are API errors is repeated before it is
      judged. A round with no progress, a header wrong or missing count above its guard value, or a cut-off or schema failure is
      reverted and ends the loop.
   4. Final runs (D29.4): 3 dev runs, then 3 held-out runs, at the frozen commit (HEAD after the loop's last commit, clean tree, hash
      recorded before the first final run). No prompt or schema change after held-out is seen; a scorer bug may be fixed and all 6 runs
      repeated, marked as a re-run.
   5. Every run's counts and meter line go into the "Line items" section of `comparison.md`, with the spread of the 3 final dev runs
      and the remaining failures by cause.
**Scope:** labels, scoring, llm_extractor, cli
**Why:** line items are most of an invoice's data, and the header-only score says nothing about them.
**Rejected:** two calls (protects the header, but adds a merge step and meter changes).
**Changes:** D9, D12, D26, D29
**Not prompted:** conventions with no dev example stay out of the prompt (D6): a discount printed under an item, carried-forward and
page-subtotal rows, the before-tax amount on a row with several amounts, and zero-amount rows. Their labels still follow 2 and 3.
**Not built yet:** all 58 public invoices have line-item labels (the 25 IEB and 20 Sinabis invoices were labelled last); the 9 private ones
are deferred. Extraction, scoring and the `score` line block are built; the billed runs from 8.2 on are not done.
**Evidence:** [decisions-history.md](decisions-history.md), D34; [designs/line-items-brief.md](designs/line-items-brief.md);
[designs/line-items.md](designs/line-items.md).
