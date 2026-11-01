# Comparison: rules vs rules + Jev vs LLM

Step 8 (D17, D29). All runs are at commit `b488ce4`, on 2026-10-19, with
`uv run --env-file .env document-extractor score --extractor <name> --set <dev|heldout>`.
The extractors were frozen for these runs (D29).

## Verdict

**Update, wider set (D30):** on 67 invoices including 9 real ones, the LLM still ranks first, but it is no longer error-free: 7 wrong values in
469 fields. All 7 trace to defects in the PDF's text layer or to which printed vendor name counts (see "Wider set" below). Rules alone now rank
above rules + Jev by one wrong value: Jev gave its first wrong currency.

**Update, NUL repair (D32):** with the reader's text-layer repair, the LLM re-run gives 466 / 0 / 3, and 63 / 0 / 0 on the real invoices. The 4
Stripe invoice numbers are now right. The 3 left are one garbled text layer and two brand names (D31). Rules are unchanged (see the end of this file).

**Update, legal-name prompt (D33):** with the vendor-name rule stated in the prompt, the LLM gives 468 correct, 1 missing, 0 wrong
(see "After the legal-name prompt" at the end of this file).

**Original 13-invoice comparison, below this section's update:** the LLM extractor is the most accurate: 91 of 91 header fields correct, in all three runs, with no wrong values.
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
  failure D11 ranks worst. The cause was asking for one `YYYY-MM-DD` string; asking for year, month and day as three numbers fixed it (D26).
  The fix was found on dev before any held-out run, and held-out then confirmed it (4 of 4 dates, 3 runs).
- **Jev threshold (D25).** It stays at 0.8, set from 13 snippet and invoice cases. Both dev `$` invoices cleared it in all three runs.

## Limits

- **Small set.** 13 invoices. One wrong value on one invoice would change the ranking, and 0 wrong in 91 fields does not mean the LLM's
  wrong-value rate is zero.
- **Synthetic layouts.** All samples are synthetic and come from two generators (D19). Real supplier invoices vary more: scans, multiple
  pages, credit notes and dual currencies are all out of scope.
- **Held-out has now been used.** Fixing what it exposed (N5 `18-Mar-2025`, N12 `K`) would tune the rules to it. Any later change needs new
  held-out samples to be measured fairly (D29).
- **Three runs.** Enough to see that the LLM's answers were stable here, not to estimate how often it is wrong.
- **Header fields only.** Line items were not extracted or scored (D34, not built yet).

## Wider set (D30), 2026-10-19

Commit `6d36091`, one run per extractor, `score --set dev` and `--set heldout`. 67 invoices, 469 header fields: 13 original, 25 more IEB, 20 Sinabis
(a second layout engine) and 9 real invoices received by the project owner (Stripe-hosted, IONOS, Lucid; git-ignored, so only these totals are
published). 67 billed LLM calls ($0.0100, $0.00015 per invoice), 29 Jev calls, 0 failed calls.

| Rank | Extractor | Correct | Missing | Wrong | Real invoices only (63 fields) |
| --- | --- | --- | --- | --- | --- |
| 1 | llm | 462 | 0 | 7 | 59 / 0 / 4 |
| 2 | rules | 295 | 151 | 23 | 27 / 28 / 8 |
| 3 | rules-jev | 322 | 123 | 24 | 36 / 19 / 8 |

Ranked on wrong values first (D11, D29): rules + Jev fills 28 more fields than rules alone, 27 of them correctly; the one wrong value ranks it last.

By set (correct / missing / wrong):

| Extractor | Dev (38 invoices, 266 fields) | Held-out (29 invoices, 203 fields) |
| --- | --- | --- |
| llm | 265 / 0 / 1 | 197 / 0 / 6 |
| rules-jev | 197 / 61 / 8 | 125 / 62 / 16 |
| rules | 185 / 74 / 7 | 110 / 77 / 16 |

### Every LLM wrong value

| Invoice | Field | Got | Label | Cause |
| --- | --- | --- | --- | --- |
| 4 Stripe invoices (real) | invoice_number | `C7F92D63\x000001` | `C7F92D63-0001` | Text layer holds `\x00` where the page shows `-`; the model copied it |
| a_currency-multi-line-nad | vendor_name | `…(Pty) LtTdAX` | `…(Pty) Ltd` | Text layer interleaves the name with the overlapping "TAX INVOICE" |
| c_0026691 (Romania) | vendor_name | `Dunărea Montaj` | `Dunărea Montaj Electric S.R.L.` | Page prints a short brand at the top and the legal name lower down |
| c_0119854 (India) | vendor_name | `MM Painters` | `Mumbai Master Painters Pvt Ltd` | Same |

The two remaining Stripe invoices read correctly. No wrong date, currency or amount from the LLM.

### What the rules got wrong on unseen layouts

- **Vendor name (19 wrong):** the first segment that is not a title is often a phone number, an address, a logo abbreviation (`VDMElect`,
  `Toscana Assic.`) or, on every Stripe invoice, the `Invoice number …` line, because that label has no colon (D24).
- **Amounts (4 wrong):** a tax rate read as the tax (`Tax (7.25%)` gave 7.25); `Total excl. tax` and `Total excluding tax` read as the total;
  `Tax - Arizona 8.7% on $20.00 $1.74` read as 20.00. Each is a label starting a segment, followed by a number that is not the amount.
- **Missing:** mostly labels without colons (`Invoice number`, `Date of issue`), date formats the parser does not know, and currency symbols
  it does not know (null-sources N4, N5, N12).

### Jev's first wrong answer

`c_0108653` is a Mexican seller (Monterrey address, `+52` phone) billing a US customer in `$`; the label, from the dataset's manifest, is USD.
Jev answered MXN with confidence at or above the 0.8 threshold. It is the same seller-country-versus-customer-country judgement as D25's two
low-confidence cases, but this time the confidence was high. Across the wider set Jev was asked 29 times: 27 currencies filled correctly, 1 wrong,
1 left null.

### Brand versus legal name (settled, D31)

Two of the LLM's wrong values were a convention gap, not a misreading: the page prints both a short brand and the legal name, and D19 only said
"the seller's name as printed". D31 settles it: the label is the legal name, so these 2 stay wrong and the LLM's count stays at 7.

## After the NUL repair (D32), 2026-10-19

Commit `51d2d9d`. The reader now replaces each `\x00` the text layer holds with the character pdfium reads at the same spot (D32). LLM re-run,
one run, both sets: 67 billed calls, 66,953 input + 6,232 output tokens, $0.0098; 0 failed extractions.

| Extractor | Correct | Missing | Wrong | Real invoices only (63 fields) | Dev | Held-out |
| --- | --- | --- | --- | --- | --- | --- |
| llm | 466 | 0 | 3 | 63 / 0 / 0 | 265 / 0 / 1 | 201 / 0 / 2 |
| rules | 295 | 151 | 23 | unchanged | 185 / 74 / 7 | 110 / 77 / 16 |

The LLM's 3 wrong values: `…(Pty) LtTdAX` (the text layer interleaves the name with "TAX INVOICE"), `Dunărea Montaj`, and `MM Painters Mumbai`
(the brand; this run appended the city, the last run did not). Rules did not move, because they never found the Stripe invoice numbers.
`rules-jev` was not re-run (Jev calls are billed); its figures above are from before the repair.

Caveat: the Stripe invoices are in held-out, and the defect was found by reading their failures. The fix is justified by the file defect, not by
the score, but held-out is no longer a clean measure of it (D32).

## After the legal-name prompt (D33), 2026-10-19

Commit `0a8b3a2`. The prompt's vendor line now asks for the registered name when the page prints both a brand and a fuller company name, and
never for address parts (D33). LLM re-run, one run, both sets: 67 billed calls, 71,040 input + 5,961 output tokens, $0.0101; 0 failed extractions.

| Extractor | Correct | Missing | Wrong | Real invoices only (63 fields) | Dev | Held-out |
| --- | --- | --- | --- | --- | --- | --- |
| llm | 468 | 1 | 0 | 63 / 0 / 0 | 265 / 1 / 0 | 203 / 0 / 0 |

- Both brand cases are fixed: `Dunărea Montaj Electric S.R.L.` and `Mumbai Master Painters Pvt Ltd`.
- `…(Pty) LtTdAX` came back as `…(Pty) Ltd`, though the text layer did not change; one run cannot say whether the prompt or variation did it.
- New missing value: `c_0108653`'s currency is null (was USD, correct): a Mexican seller billing a US customer in `$`, the case Jev got wrong.
  The currency instruction did not change, and null is what it asks for when the page is unclear. One run cannot attribute it.
