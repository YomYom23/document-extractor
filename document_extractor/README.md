# document_extractor

## Overview

The package that turns a digital PDF invoice into an `Invoice` and scores it
against a hand-written label. It holds three extractors that share one
signature, `extract(pdf_path) -> Invoice` (D5): rules only, rules plus the Jev
currency resolver, and an OpenAI model. The CLI wires them to the samples and
prints the scores. The rules behind each choice are in
[docs/decisions.md](../docs/decisions.md), and the D numbers in the code point
there; the old log, with live runs and diagnoses, is
[docs/decisions-history.md](../docs/decisions-history.md).

## Interface

- `schema.py`: `Invoice` and `LineItem`, the Pydantic contract between the
  extractors, the labels and the scorer. Every field is nullable.
- `pdf_reader.py`: `read_pdf(path) -> PdfDocument` with frozen `PdfPage` and
  `Word` dataclasses (reading-order text plus positioned words);
  `NoTextLayerError`; `repair_nul_characters`, `read_with_pdfium`.
- `rules_extractor.py`: `extract(pdf_path) -> Invoice`, plus its helpers
  `parse_amount`, `parse_date`, `build_lines`, `find_labelled_value`,
  `find_labelled_amount`, `detect_currency`, `find_vendor_name`.
- `currency_resolver.py`: `resolve_currency`, `currency_from_answer`,
  `extract_with_currency_resolver(pdf_path, ask)`, `CURRENCY_QUESTION`,
  `MIN_CONFIDENCE`, and the `AskJev` callable type.
- `jev.py`: `Jev.ask(state, questions)` and `JevError`. The only module that
  calls TypeSafe.
- `llm_extractor.py`: `LlmExtractor.extract` / `extract_from_text`,
  `LlmInvoice`, `LlmLineItem`, `TEXT_FORMAT`, `to_invoice`,
  `decimal_from_text`, `issue_date_from_parts`, `LlmExtractionError`,
  `DEFAULT_MODEL` and its per-million-token prices.
- `scoring.py`: `score_invoice`, `score_field`, `score_dataset`,
  `DatasetScore`, `Outcome` (`correct`, `missing`, `wrong`), `HEADER_FIELDS`;
  for line items `pair_lines`, `LinePair`, `PairPass`, `score_lines`,
  `ScoredPair`, `InvoiceLineScore`, `score_line_dataset`, `LineDatasetScore`,
  `LINE_FIELDS`.
- `arithmetic_check.py`: `arithmetic_warning(invoice) -> str | None`.
- `token_usage.py`: `TokenUsage`, one token-count shape for both vendors.
- `cli.py`: `main(argv, extractors) -> int`, the `document-extractor` command
  with `extract <pdf>` and `score --set dev|heldout`, each taking
  `--extractor rules|rules-jev|llm`. `CallMeter`, `metered_ask` and
  `metered_llm` count billed calls and tokens; `format_meter` prints them.
  `print_line_result` and `format_line_summary` print the line block.

## Invariants

- Money is `Decimal`, never `float`, and must match to the cent (D10).
- A field the page does not show is `None`, never a guess. A wrong value is
  worse than a missing one (D11). `line_items` `None` means "could not tell";
  `[]` means "no items" (D18).
- `Invoice` and `LineItem` use `extra="forbid"`. The schema does not check
  that subtotal + tax == total; `arithmetic_warning` does, as a hint only, and
  the scorer does not import it (D20, D22).
- Only `pdf_reader.py` imports a PDF library, only `jev.py` builds a
  `TypeSafeClient` and calls Jev (other modules import only the `Choice` and
  `ChoiceAnswer` types), and only `llm_extractor.py` imports OpenAI.
- Only the LLM extracts line items, in the same call as the header; the rules
  extractors return `line_items=None` as the baseline (D34.1). The scorer pairs and scores line items as a separate
  block (`score_lines`, D34.5). `score --extractor llm` prints it per invoice
  and after the header counts; rules and rules-jev output is unchanged.
- Line pairing uses identical totals and identical descriptions only, with
  page order as the tie-break inside a group of equal totals. Every field of
  an unpaired row counts against the run (D34.5).
- `score` prints exactly the pairing it scored: `print_line_result` and the
  line block both come from `score_lines`, never a second pairing.
- The rules extractor never calls a model. The resolver never overrides a
  currency the rules found, and only runs when the page has a bare `$` (D25).
- A Jev failure leaves the currency `None`. An LLM failure raises
  `LlmExtractionError`; `score` counts it as a failed extraction and scores
  the invoice as all-null (D26). A cut-off reply is read from the status
  before the JSON is validated, so it is reported as cut off and its tokens
  are metered; partial JSON is never used (D34.7).
- The LLM prompt contains instructions only, no examples from the samples, and
  held-out text never reaches it (D6). Held-out is scored only when asked for
  with `--set heldout`.
- Only `vendor_name` is compared loosely (casefold, collapsed whitespace).
  Invoice number and currency are identifiers and compared exactly (D12).
- Time, tokens and cost are reported after the counts and never ranked (D29).

## Side Effects

- Reads PDFs from disk (pdfplumber and pdfium open each file; the pdfium
  handle is closed explicitly).
- `score` reads `samples/<set>/` and the git-ignored `samples/private/<set>/`
  and their `*.expected.json` labels.
- `rules-jev` makes billed calls to TypeSafe (`TYPESAFE_API_KEY`); `llm` makes
  billed calls to OpenAI (`OPENAI_API_KEY`, `store=False`). The CLI checks the
  key before reading any PDF.
- `cli.py` prints JSON to stdout and warnings and errors to stderr.

## Verification

- Run: `uv run pytest`, `uv run ruff check .` and `uv run mypy .` (all three
  clean, D13). Tests fake every network call.
