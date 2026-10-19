# Null sources

Every place in the application that can leave a field `null`, why it does, and what it has cost so far. It exists so each cause can be
looked at later for a fix. A `null` is always on purpose (D11: wrong is worse than missing), so every entry is a trade-off, not a bug.

Rule (D27): any new code path that can produce a `null` gets an entry here in the same commit.

"Dev cost" is measured on the 9 dev invoices. Rules extractor numbers are from a free run on 2026-10-19 (56 correct, 7 missing, 0 wrong);
LLM numbers are from D26 live run 2. Held-out has never been run (D6).

## Whole invoice

### N1. LLM call fails (`llm_extractor.py`, `LlmExtractor.extract_from_text`)
- Fields: all seven. Raises `LlmExtractionError`; `scripts/live_llm_check.py` then scores an empty `Invoice()`.
- Triggers: any OpenAI `APIError` (timeout, connection, 4xx, 5xx), a reply cut off at `max_output_tokens`, a refusal, a reply that fails `LlmInvoice` validation.
- Why null: a failed call has no answer to use, and filling in values would be a guess (D26).
- Dev cost: 0 failed calls in live runs 1 and 2.

### N2. No text layer (`pdf_reader.py`, `read_pdf`)
- Fields: none directly. Raises `NoTextLayerError` instead, so a scan is reported as a scan, not as seven missing fields (D23).
- Listed because whoever catches it (the CLI, step 7) decides whether it becomes an all-null invoice or an error.

## Line items

### N3. `line_items` always null (`rules_extractor.extract`, `llm_extractor.to_invoice`)
- Why null: not extracted yet; header fields come first and line items are not scored (D12, D24, D26).

## Rules extractor (`rules_extractor.py`)

### N4. Label not found: invoice number, issue date (`find_labelled_value`)
- The label must be `Invoice No:`, `Invoice Number:`, `Invoice #:` or `Date:`, with the colon. `Invoice No. 123`, `Invoice Date 30.04.2026` (no colon),
  `Issued:` or `Bill date:` give `null`. `Due Date:` is excluded on purpose.
- Why: the colon makes a match in the middle of a line safe (D24). Each label variant came from the dev samples only.
- Dev cost: 0.

### N5. Date text that is not a date the parser knows (`parse_date`)
- Known formats: `30.04.2026`, `12 February 2026`, slash dates with a 4-digit year. Anything else gives `null`: ISO `2026-04-30`, `April 30, 2026`,
  `30 Apr 2026` (short month names), `30-04-2026`, two-digit years, a month word that is not an English month name.
- A date-shaped string that is not a real day (`31.02.2026`) also gives `null`.
- Dev cost: 0 (every dev date is in a known format).

### N6. Ambiguous slash date (`parse_date`)
- `09/03/2026`: both parts are 12 or under, so it is 9 March (most countries) or 3 September (US). Returns `null`.
- Why: the order cannot be told from the date alone; guessing could be wrong (D11). Open problem in D24, with candidate fixes listed there.
- Dev cost: 2 (`a_clean-fr-right-header`, `a_clean-us-clean-simple`). The LLM read both correctly in live run 2.

### N7. Amount label not at the start of a segment (`find_labelled_amount`)
- Fields: subtotal, tax, total. A label inside a sentence ("The subtotal including VAT is EUR 196,147.20") is not used.
- Why: matching anywhere in a line read that sentence as the tax too, a wrong value (D24, Q26).
- Dev cost: 2 (`b_INV-2026-0129` subtotal and total). The LLM read both from the sentences.

### N8. Tax label not in the list (`TAX_LABEL`)
- Known: `Tax`, `Sales Tax`, `VAT`, `MwSt`, `TVA`, `BTW`. `GST`, `HST`, `IVA`, `IGST` and others give a `null` tax.
- Dev cost: 0. The LLM prompt names GST; the rules do not.

### N9. Amount not in the expected shape (`parse_amount`, `find_first_amount`)
- An amount must end in a separator plus exactly two digits. `1,000`, `1500`, `JPY 1500` and three-decimal currencies give `null`.
- Why: the two-decimal requirement is what stops `VAT No: 4334037646` being read as the tax (D24).
- Dev cost: 0. Any zero-decimal currency (JPY) would lose every amount.

### N10. Currency read only from the total's line (`extract`, `detect_currency`)
- No total found means no currency, even if the page prints the currency elsewhere.
- Dev cost: 1 (`b_INV-2026-0129`, which has no total line; D24).

### N11. Bare `$` (`detect_currency`)
- `$` is USD, CAD, AUD, NZD, NAD, MXN, ... so the rules return `null` and the Jev resolver (D25) gets a chance.
- Dev cost for rules alone: 2 (`a_clean-us-clean-simple`, `a_currency-nad-bare-dollar`). Jev resolved both in the D25 live run.

### N12. Currency not recognised (`detect_currency`)
- Only these codes count when printed: EUR, USD, GBP, ZAR, CHF, CAD, AUD, NZD, JPY, SEK, NOK, DKK. Only these symbols: `€`, `£`, `R` before a digit.
  `INR`, `PLN`, `¥`, `₹`, `kr`, `Fr.`, `R$` and others give `null`.
- Why: a known list means an unknown code is missing, never a made-up currency (D24).
- Dev cost: 0.

### N13. No vendor candidate (`find_vendor_name`)
- `null` only if every segment on the page is a title (`INVOICE`, `TAX INVOICE`), logo initials (3 capitals or fewer) or empty.
- Dev cost: 0. The more likely failure here is a wrong name, not a missing one.

## Jev currency resolver (`currency_resolver.py`, `jev.py`)

Runs only after N10 to N12 have left the currency `null`. Each path below keeps it `null`.

### N14. No `$` straight before a number (`resolve_currency`, `DOLLAR_AMOUNT`)
- The resolver skips the invoice. `12,00 $` (symbol after the amount, as in French Canadian invoices) does not match, so it stays `null`.
- Why: Jev is asked only about the bare-dollar problem; other lost currencies are a total-finding problem (D25, Q32).

### N15. Jev call fails (`Jev.ask` raises `JevError`)
- Any `TypeSafeError`, or a reply missing the `Choice` answer.
- Why: an outage shows up as a missing field, never a crash or a guess (D25).

### N16. Jev says `unclear` or is under 0.8 confident (`currency_from_answer`)
- Why: the threshold set from the D25 live run. At 0.8 one of 13 cases (US seller, Canadian customer, 0.73) stayed `null`.

### N17. Currency outside Jev's list
- Jev can only answer USD, CAD, AUD, NZD, SGD, HKD, NAD, MXN or `unclear`. Any other `$` currency (TWD, BRL `R$`, ...) can at best be `unclear`.

## LLM extractor (`llm_extractor.py`)

### N18. The model returns null
- The prompt asks for `null` when: the field is not printed; the date's day/month order cannot be told; the currency is unclear from symbol and addresses;
  no separate tax amount is printed. The model can also return `null` for reasons it does not state.
- Dev cost: 0 in live run 2.

### N19. Partial date (`issue_date_from_parts`)
- Any of `issue_year`, `issue_month`, `issue_day` null gives a `null` date; a missing part is never filled in (D26, Q47).

### N20. Impossible date (`issue_date_from_parts`)
- Month 30, 30 February, day 0: `date()` raises, the date becomes `null` and the other fields are kept (D26, Q47).
- Dev cost: 0 since Q47. Before Q47 the one-string date was wrong, not null, on all 9.
