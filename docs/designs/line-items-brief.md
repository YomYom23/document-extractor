# Line-item extraction (D34, LLM only)

> Superseded by [line-items.md](line-items.md) on 2026-11-03; its open items
> are resolved there. The body below is not edited.

* **Author:** Yomi O Lebi
* **Date:** 2026-10-28

## Overview

The extractors read only the seven header fields today. `LineItem` already
exists in the schema, and the 58 public labels already hold 468 lines (290 dev,
178 held-out), but both extractors return `line_items=None` and the scorer
ignores lines. This work makes the LLM extractor return line items in the same
OpenAI call as the header and adds a separate line block to `score`. The rules
extractor stays at `None` as the baseline. The design is D34 in
`docs/decisions.md`; this brief records what six independent reviewers found
missing or risky in it before it is built.

Success thresholds and the line-item labels for the 9 private real invoices are
deliberately left for later.

## Analysis

### Blockers

All three are now resolved; see Key Decisions 1 to 4.

1. **The output cap will cut off the largest invoices and take their headers
   with them.** `llm_extractor.py:154` caps output at 4000 tokens, and
   reasoning counts against it. One line costs about 35 to 45 tokens as JSON,
   so the 110-line dev invoice (`a_multipage-8p-na-10`) needs 4,000 to 5,000
   tokens before any reasoning. A cut-off reply fails validation, raises
   `LlmExtractionError`, and `score` counts the whole invoice, header
   included, as missing. Because header and lines share one call, a line
   problem becomes a header loss. The failed call is also not metered (D29).
   Fix before the billed run: raise the cap (for example 16k, checked against
   the model's documented maximum), update the pinned test, record the
   largest invoice's output tokens, and state that partial JSON is never used.

2. **The scorer has no rule for a null or empty line list.** D34's pairing
   rule covers only "both sides are lists". `score` also reads
   `samples/private/`, whose 9 labels have no line items. Applying the header
   rule ("label null, any value is wrong") would count every line the model
   finds on a real invoice as wrong. Proposed rule:

   | Label | Prediction | Outcome |
   | --- | --- | --- |
   | `None` | anything | Not labelled: skip the invoice in the line block and print how many were skipped. |
   | list | `None` | Every labelled line is unpaired, so it counts missing. |
   | list | `[]` | Same as `None`. |
   | `[]` | anything | Not allowed in labels (`test_samples.py:51` already enforces this). |

   `decisions.md:379` also says all 67 invoices are labelled, which is not
   true yet.

3. **It is unclear how null fields in an unpaired labelled line count.** D34
   says all 4 fields count missing, but under D21 a null label met by a null
   prediction is correct. 27 label values are null (amount-only rows,
   percentage rows, foreign-currency rows). Pick one: treat an unpaired line as
   an all-null prediction (consistent with D21), or count only the non-null
   label fields.

### Scoring meaning

- **The pairing rule is not exact enough to write tests from.** Pin down:
  "identical total" means `Decimal` equality; null totals never pair in the
  first pass; the k-th duplicate pairs with the k-th; the second pass zips the
  leftovers in list order. Note that a pair made by total has a correct
  `line_total` by construction, which inflates that field's count.
- **The second pass can cascade.** If the model drops one row and misreads a
  later total, every later pair shifts by one. Reviewers disagree on the fix.
  The lower-cost option is to keep D34 as written and let the per-line output
  show cascades; the alternative is to pair in the second pass only when
  descriptions also match.
- **The line block has no fixed total.** Invented lines add "wrong" outcomes,
  so correct + missing + wrong varies by extractor, and an invented all-null
  line adds nothing at all. Print line counts beside the field counts:
  labelled, predicted, paired by total, paired by order, unpaired on each side.
- **Exact description matching will dominate "wrong".** A wrapped tail or a
  dash counts as much as a wrong amount. 19 InvoiceBench descriptions contain
  em dashes or non-ASCII letters. Keep D12's matching unchanged, report the 4
  fields separately, and treat wrong numbers as the safety figure.
- **One invoice carries about a third of each set.** The 110-line invoice is
  38% of dev lines; one 61-line invoice is 34% of held-out. Show the line
  block per source and add "invoices with zero wrong line fields".
- **Ranking across blocks is undecided.** D29 ranks by wrong, then missing.
  Say whether the header verdict stands and lines are ranked separately.

### One call or two

D34 chose one call but records no rejected alternative. Two calls would keep
the header call byte-identical, so a line failure could not null the header and
header movement could not be blamed on the prompt. Cost does not decide it
(under $0.01 a run). The reviewers recommend keeping one call, recording two
calls as the rejected option, fixing the token cap first, and running the
billed check 3 times (about $0.05) so header movement can be told from noise.

### Schema and prompt

- Add `LlmLineItem` (4 required nullable fields, `extra="forbid"`) with
  anchored patterns shared with `MoneyText`. `to_invoice` keeps `None` and
  `[]` apart and reuses one module-level `money()`.
- The prompt must say when to return null versus `[]`, list the rows that are
  not lines (shipping, discount and tax rows in the totals block,
  carried-forward rows, page subtotals, repeated headers), and give the
  percentage-row and foreign-currency-row rules. Without them the model will
  put 22.5 in `unit_price` or the foreign amount in `line_total`.
- D6 risk: some conventions were found on held-out invoices (Q98, Q101,
  Q105). Prompt wording must be generic and checked to contain no sample
  text, with a held-out caveat like D32 and D33.

### Output and debugging

`print_invoice_result` is header-only, so without line output an extractor
error, a label error and a pairing error look the same. Per invoice, print a
one-line summary and got versus label for each non-correct pair and unpaired
line. Control volume (the rules row is all missing; the 110-line invoice is
long). Print the line block after the header block and keep header output
byte-identical so past results stay comparable.

### Code and docs

- Keep `score_invoice`, `HEADER_FIELDS`, `overall` and `per_field` unchanged.
  Add pure `pair_lines` and `score_line_items` functions with table-driven
  tests, and new `DatasetScore` fields for the line block.
- Tests that will break: `test_llm_extractor.py:36` and `:90`
  (`line_items is None`) and `test_nulls_stay_null`.
- Docs to update in the same commits: `null-sources.md` (split N3, widen N1),
  both READMEs, `comparison.md`, `ATTRIBUTION.md`, the `INSTRUCTIONS` first
  line and module docstrings.
- D34 heading says Q88 to Q98 but uses up to Q105, lists D9 as amended
  (nothing changes there), and omits D21, D24, D26, D30 and D22's deferred
  line-sum check. Line 380 says 26 IEB invoices; line 409 says 25.

## Goals vs. Non-Goals

* **In-Scope Goals:**
  * A test-first `pair_lines` / `score_line_items` that follows D34 exactly,
    including null and `[]` on both sides.
  * A separate line block in `score` (overall, per source, per field, line
    counts, invoices skipped), with header output unchanged.
  * Per-invoice line diagnostics with volume control.
  * `LlmLineItem` in the same call, with a token cap checked on the 110-line
    invoice.
  * Generic prompt rules for what a line is, sourced only from dev.
  * A billed run on dev, then held-out once, recorded in D34 and
    `comparison.md` with header changes listed field by field.
  * Doc and test updates in the same commits, including label guard tests
    (patterns match the API formats; lines sum to the subtotal with listed
    exceptions).
* **Out-of-Scope Non-Goals:**
  * Line items in the rules extractor.
  * Fuzzy, Unicode-folded or tolerance-based matching, or optimal assignment.
  * A line-sum arithmetic warning (D22 stays deferred).
  * Credit notes and negative-total invoices beyond a synthetic test.
  * A two-call design, unless the token cap or header stability forces it.
  * Changes to `pdf_reader` or the header fields.
  * Success thresholds and the 9 private labels (deferred by choice).

## Key Decisions & Staging for Next Steps

### Resolved (2026-10-28, following the reviewers' suggestions)

1. **Token cap and truncation.** Raise `max_output_tokens` from 4000 to
   about 16,000 before the billed run, after checking `gpt-6-luna`'s
   documented maximum output (still to confirm). Update the pinned test.
   A cut-off reply fails the whole invoice; partial JSON is never used.
   Record the 110-line invoice's output tokens in the run. Widen N1 in
   `null-sources.md` to cover line items.
2. **One call, recorded.** Keep header and lines in one call (Q93). Record
   two calls as the rejected alternative: it would protect the header, but
   costs a second model, a merge step and meter changes. Run the billed dev
   check 3 times (about $0.05) so header movement can be told from noise.
3. **Null and empty line lists.** The scorer follows the table under
   Blocker 2: a null label skips the invoice in the line block (and the
   count of skipped invoices is printed); a null or `[]` prediction against
   a labelled list makes every labelled line unpaired; `[]` is not allowed
   in labels. These four cases are the first scorer tests. Amend
   `decisions.md:379` to say the 58 public invoices are labelled and the 9
   private ones are deferred.
4. **Null fields on an unpaired labelled line.** Treat an unpaired labelled
   line as if the prediction were all null, so a null label field counts
   correct and a non-null one counts missing. This keeps D21's rule and
   amends D34's "counts its 4 fields missing".

### Still to decide in `/egm-draft`

5. The exact pairing steps with a worked example, and whether the second
   pass stays pure list order.
6. How line counts and invented lines are reported.
7. The prompt text for line conventions, and its D6 check.
8. The CLI line-block layout, diagnostics and volume control.
9. The ranking rule across header and line blocks.
10. Scorer and `DatasetScore` names.
11. Acceptance criteria per build step and the billed-run protocol.
12. D34 fixes: heading Q range, amends list, 25 versus 26.

Open, deferred by choice: the line-item success threshold, the acceptable
header loss ("at or near 468 / 1 / 0" is not testable as written), and the 9
private labels, so the first result covers 58 invoices, not 67.
