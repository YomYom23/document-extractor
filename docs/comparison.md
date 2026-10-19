# Comparison: rules vs rules + Jev vs LLM

Step 8 (D17, D29). All runs are at commit `b488ce4`, on 2026-10-19, with
`uv run --env-file .env document-extractor score --extractor <name> --set <dev|heldout>`.
The extractors were frozen for these runs (D29, Q62).

## Verdict

**The LLM extractor is the most accurate: 91 of 91 header fields correct, in all three runs, with no wrong values.**
Rules + Jev comes second (84 correct, 7 missing) and rules alone third (82 correct, 9 missing). Neither rules row ever produced a wrong value.

**A hybrid is not justified by these numbers (D5).** A hybrid that runs the rules first and asks the LLM only for the fields they leave null
could, at best, match the LLM's 91 of 91 on this set. It cannot beat it. Its only gains would be cost and time, which do not count in the
ranking (D29). Revisit if a larger set shows the LLM giving wrong values on fields the rules get right; nothing like that happened here.

## Accuracy

Ranked on accuracy only: wrong values first, then missing ones (D11). 13 invoices (9 dev, 4 held-out), 7 header fields each, 91 fields.

| Rank | Extractor | Correct | Missing | Wrong | Runs |
| --- | --- | --- | --- | --- | --- |
| 1 | llm | 91 | 0 | 0 | 3, identical counts |
| 2 | rules-jev | 84 | 7 | 0 | 3, identical |
| 3 | rules | 82 | 9 | 0 | 1 (no model, so no run-to-run change) |

Split by set:

| Extractor | Dev (63 fields) | Held-out (28 fields) |
| --- | --- | --- |
| llm | 63 / 0 / 0 | 28 / 0 / 0 |
| rules-jev | 58 / 5 / 0 | 26 / 2 / 0 |
| rules | 56 / 7 / 0 | 26 / 2 / 0 |

(correct / missing / wrong)

The rules were written from dev and scored the same share on held-out (93%) as on dev (89% rules, 92% rules-jev), so they did not
overfit visibly. Held-out is only 4 invoices, though, so that comparison carries little weight.

### Every miss, traced to its cause

Causes are numbered as in `docs/null-sources.md`.

| Invoice | Set | Field | rules | rules-jev | Cause |
| --- | --- | --- | --- | --- | --- |
| a_clean-fr-right-header | dev | issue_date | missing | missing | N6: `09/03/2026`, day/month order ambiguous |
| a_clean-us-clean-simple | dev | issue_date | missing | missing | N6: same |
| a_clean-us-clean-simple | dev | currency | missing | correct | N11: bare `$`; Jev answered USD |
| a_currency-nad-bare-dollar | dev | currency | missing | correct | N11: bare `$`; Jev answered NAD |
| b_INV-2026-0129 | dev | subtotal | missing | missing | N7: label inside a sentence |
| b_INV-2026-0129 | dev | total | missing | missing | N7: same |
| b_INV-2026-0129 | dev | currency | missing | missing | N10: no total line to read it from |
| a_clean-zm-banner | held-out | issue_date | missing | missing | N5: `18-Mar-2025` is not a known format |
| a_clean-zm-banner | held-out | currency | missing | missing | N12: kwacha printed as `K`; Jev not asked (N14, no `$`) |

The LLM missed none of these, including the ambiguous `09/03/2026` dates. It read them as the invoice's country reads them (D19).

### Per field (all 13 invoices)

| Field | rules | rules-jev | llm |
| --- | --- | --- | --- |
| vendor_name | 13 / 0 / 0 | 13 / 0 / 0 | 13 / 0 / 0 |
| invoice_number | 13 / 0 / 0 | 13 / 0 / 0 | 13 / 0 / 0 |
| issue_date | 10 / 3 / 0 | 10 / 3 / 0 | 13 / 0 / 0 |
| currency | 9 / 4 / 0 | 11 / 2 / 0 | 13 / 0 / 0 |
| subtotal | 12 / 1 / 0 | 12 / 1 / 0 | 13 / 0 / 0 |
| tax | 13 / 0 / 0 | 13 / 0 / 0 | 13 / 0 / 0 |
| total | 12 / 1 / 0 | 12 / 1 / 0 | 13 / 0 / 0 |

## Cost and time (reported, not ranked)

Measured by `score` (D29). Time is wall-clock per invoice on this PC, including reading the PDF.

| Extractor | Time per invoice | Cost per invoice | Calls |
| --- | --- | --- | --- |
| rules | 0.05 s | $0 | none |
| rules-jev | 0.12 s on average; each Jev call adds about 0.4 s | Jev tokens: about 810 input + 87 output per call; not priced (D29) | Jev only on the 2 invoices with a `$` amount |
| llm | 2.4 s on average (1.8 to 3.9 s) | $0.00013 (about 870 input + 75 to 111 output tokens) | one OpenAI call per invoice |

All 39 LLM calls together cost $0.0051, an upper bound since cached input was not discounted. At that rate 10,000 invoices would cost about
$1.30, so cost would not decide between the extractors at any scale this project has in view. Time might: the LLM is about 50 times slower
than the rules.

The output token count changed between runs on the same invoices (dev: 744 to 1,001 tokens per run), so the model's reasoning varies from call
to call. Its answers did not.

## What changed on the way

- **LLM dates (D26).** The first LLM run had 9 of 63 dev fields **wrong**, not missing: every `issue_date` got a year built from the printed
  day and month (`30.04.2026` became 3004-04-30). In this whole project that is the only time any extractor gave a wrong value: the dangerous
  failure D11 ranks worst. The cause was asking for one `YYYY-MM-DD` string; asking for year, month and day as three numbers fixed it (Q47).
  The fix was found on dev before any held-out run, and held-out then confirmed it (4 of 4 dates, 3 runs).
- **Jev threshold (D25).** It stays at 0.8, set from 13 snippet and invoice cases. Both dev `$` invoices cleared it in all three runs.

## Limits

- **Small set.** 13 invoices. One wrong value on one invoice would change the ranking, and 0 wrong in 91 fields does not mean the LLM's
  wrong-value rate is zero.
- **Synthetic layouts.** All samples are synthetic and come from two generators (D19). Real supplier invoices vary more: scans, multiple
  pages, credit notes and dual currencies are all out of scope.
- **Held-out has now been used.** Fixing what it exposed (N5 `18-Mar-2025`, N12 `K`) would tune the rules to it. Any later change needs new
  held-out samples to be measured fairly (Q62).
- **Three runs.** Enough to see that the LLM's answers were stable here, not to estimate how often it is wrong.
- **Header fields only.** Line items were not extracted or scored (D12).
