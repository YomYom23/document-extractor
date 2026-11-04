# Line items: extraction, scoring and the dev fix loop

*   **Author:** Yomi O Lebi
*   **Status:** Proposed
*   **Date:** 2026-11-03

--------------------------------------------------------------------------------

## Overview

document-extractor reads digital PDF invoices into one fixed schema and
measures each extractor against hand-written labels (D6, measure against a
labelled set; held-out stays unseen). Today only the header fields are
extracted and scored. The schema already has `line_items`, and D34 (line
items) fixes the rules for them, but nothing fills or scores that field:
every extractor returns `line_items=None` and the scorer compares header
fields only.

This design adds line items to the LLM extractor, in the same call as the
header (D34.7, one call for header and lines). It adds a line scorer that
pairs labelled rows with predicted rows, and a `score` output that shows only
the rows that went wrong and how they were paired. It also sets the process
for improving the prompt: one baseline run, at most three fix rounds, then a
frozen commit measured three times on dev and three times on held-out. That
process is recorded in D34.8 (the line-items build order).

This is a learning and portfolio project (D1). The aim is a measurement of
how well one model call reads invoice tables, plus a written account of what
still fails. It does not aim to reach a set accuracy.

## The Problem

Invoices carry most of their content in the item table, and the project
measures none of it. The header score says nothing about whether an
extractor can read the rows that make up the total.

Three things make line items harder to measure than header fields:

1.  **Rows must be paired before they can be compared.** A header field has
    one label and one prediction. A table has N labelled rows and M predicted
    rows, and the model may drop, merge, split or invent rows. A pairing rule
    based on position turns one dropped row into a run of wrong values on
    every later row. The score then measures the pairing rule, not the model.
2.  **One invoice dominates.** Of the 290 dev labelled rows, 110 (38%) come
    from one 8-page invoice. Any line-level number is mostly a number about
    that invoice.
3.  **Line changes move the header.** Header and lines share one call, so a
    prompt change made for lines can make the header worse, and a line-only
    score would not show it.

The proposed solution:

*   Extend the LLM call's output schema and prompt to return line items.
*   Pair rows in two passes: first by identical `line_total`, then by
    identical description after D12 normalising (casefold, collapsed
    whitespace). Inside a group of equal totals, rows with identical
    descriptions pair first and the rest pair in page order. Rows that match
    neither way stay unpaired, and every field of an unpaired row counts
    against the run.
*   Print, per invoice, only the pairs whose fields are not correct, with the
    pass that paired them, plus the unpaired rows and one count line.
*   Treat the first billed dev run as a baseline, then allow at most three
    fix rounds, each judged against the previous round and against a header
    baseline taken before any line change.

## Goals

*   **G1. Line extraction.** The LLM extractor returns `line_items` as a list
    of `LineItem` in the same call as the header. A reply cut off for length
    is reported as cut off, not as "did not fit the schema", and its tokens
    are metered.
*   **G2. Pairing by total, then description.** A pure function pairs
    labelled and predicted rows by identical `line_total` (inside a group of
    equal totals: identical description first, then page order), then the
    leftovers by identical normalised description. Every other row stays
    unpaired. It is covered by table-driven tests written before the code.
*   **G3. Line scores.** `score` reports line-field counts (correct, missing,
    wrong) as a block separate from the header counts, plus counts of
    invented rows and of labelled rows left unpaired.
*   **G4. Diagnostic output.** For the LLM extractor, each invoice gets the
    line output of Technical Plan section 4. For every extractor the header
    lines are unchanged, and rules and rules-jev output is unchanged as a
    whole.
*   **G5. Header guard, loop cap and final runs.** Stated in full once, in
    Technical Plan section 5.
*   **G6. Recorded rules.** D34.5 (pairing and scoring), D34.7 (one call,
    cap, cut-off) and D34.8 (build order and runs) are edited. Every step
    ends with pytest, ruff and mypy clean (D13).

## Non-Goals

*   **Line items from the rules or rules-jev extractors.** They keep
    returning `line_items=None` (D34.1, LLM only).
*   **A success threshold.** No line accuracy counts as "good enough". The
    loop ends on effort and progress, not on a score.
*   **An accepted-failures list.** Remaining failures are described by cause
    in the write-up, not approved one by one.
*   **Labels for the 9 private invoices.** Their line labels stay null and
    those invoices are skipped in the line block (D34.6, null labels skip the
    invoice).
*   **A second model call for line items.** Rejected in D34.7. Reopened only
    if the loop ends on a header-guard revert.
*   **Fuzzy description matching.** Descriptions pair only when equal after
    D12 normalising. Near-matches stay unpaired.
*   **Deferred reporting.** Per-source line subtotals, a count of invoices
    with no wrong line field, and any ranking that mixes header and line
    blocks.

## Open Questions

*   **Single-run noise.** Progress is judged on one dev run, so a noisy run
    can end the loop a round early. Accepted because the cap is three. The
    spread of the three final dev runs is reported, as the measure of that
    noise.
*   **The largest invoice decides progress.** The progress test is one sum
    over all invoices, so the 110-row invoice mostly decides it. Accepted; the
    summary also prints the line counts without that invoice, so a reader can
    see whether a round helped the rest. A per-invoice "nothing got worse"
    rule is not used: run noise across about 29 dev invoices would stop the
    loop at round 1.

## Risks

| Risk | Mitigation |
| --- | --- |
| A line prompt change makes the header worse | Header guard on wrong and missing counts (section 5, item 3) |
| The 110-row invoice is cut off at the token cap | Cap set to the documented maximum up to 16,000; cut-offs reported as such (section 1) |
| Run noise hides or fakes progress | Cap of 3 rounds; spread of 3 final dev runs reported |
| The prompt overfits dev | Prompt uses dev conventions only; 3 held-out runs at the frozen commit |
| An SDK upgrade breaks the schema helper | Pinned by the settings test in step 5.1 |

## Critical User Journeys (CUJs)

### CUJ 1: Read why an invoice's rows went wrong

*   **Given**: the line scorer and the line-item prompt are built, and
    `OPENAI_API_KEY` is in `.env`.
*   **When**: the owner runs
    `uv run --env-file .env document-extractor score --set dev --extractor llm`.
*   **Then**: each invoice prints its header lines exactly as today, then the
    line output of Technical Plan section 4. After all invoices, the header
    totals print as today, followed by a separate line-item block. The owner
    can tell a dropped row from a misread value without opening the PDF.

### CUJ 2: Run one fix round

*   **Given**: the header baseline (3 runs) and the baseline line run are
    recorded.
*   **When**: the owner commits one prompt change and runs dev once.
*   **Then**: from the summary blocks alone, the owner can tell whether the
    round passed the progress test and the header guard (Technical Plan
    section 5), and keeps or reverts the change.

### CUJ 3: Take the final measurement

*   **Given**: the loop has stopped and the frozen commit is recorded.
*   **When**: the owner runs dev 3 times and then held-out 3 times at that
    commit.
*   **Then**: the counts from all 6 runs go into `docs/comparison.md` with
    the commit hash, and the remaining failures are grouped by cause.

## Technical Plan (Architecture)

### Data flow

```text
 PDF --read_pdf--> page text --> LlmExtractor (one call, D34.7)
                                   |  output schema: LlmInvoice
                                   |    header fields (unchanged)
                                   |    line_items: list[LlmLineItem] | null
                                   v
                               to_invoice --> Invoice (header + line_items)
                                                   |
             label JSON --> Invoice (expected) ----+
                                                   v
                                   scoring.score_invoice   (header, unchanged)
                                   scoring.score_lines     (new)
                                     +- pair_lines -> list[LinePair]
                                     +- score each pair's 4 fields
                                     +- score unpaired rows (all fields count)
                                                   |
                                                   v
                cli.print_invoice_result (unchanged) + print_line_result (new, llm only)
                cli summary: header block (unchanged) + line block (new, llm only)
```

The scorer stays pure (D21, scorer design): it takes two `Invoice`s and
returns data. The CLI only formats what the scorer returns, so the printed
pairing is always the pairing that was scored.

### 1. Extraction (`llm_extractor.py`)

*   **Output schema.** A new `LlmLineItem` model with four fields, all
    required and nullable, no defaults (strict structured outputs need every
    field present):
    *   `description: str | None`
    *   `quantity: QuantityText | None`, pattern `^-?\d+(\.\d{1,4})?$` (D34.7)
    *   `unit_price: QuantityText | None`, same pattern
    *   `line_total: MoneyText | None`, the existing header money pattern

    `LlmInvoice` gains `line_items: list[LlmLineItem] | None`. Null means the
    model could not read the table; `[]` means the invoice has no item rows
    (D18, schema details).
*   **Conversion.** `to_invoice` converts each row's text to `Decimal` (never
    via float, D10) and keeps `None` and `[]` distinct. The inner `money`
    helper moves to module level so rows can use it.
*   **Prompt.** `INSTRUCTIONS` changes from "header fields" to "header fields
    and line items" and adds the line rules from D34.2 to D34.4 (what a line
    is, label conventions, percentage and foreign-currency rows) as plain
    instructions. No examples from any sample (D6). Each rule must have at
    least one dev invoice that shows it. A convention with no dev example is
    left out of the prompt; step 5.3 lists them and D34 records them as not
    prompted.

    Step 5.3 result (2026-11-03, dev page text and labels only):

    | Convention | Dev invoices that show it | Prompted |
    | --- | --- | --- |
    | Totals-block rows (shipping, discount, tax) are not lines (D34.2) | `a_clean-us-with-shipping`, `a_clean-us-trade-discount`, `c_0073141_000332` | yes |
    | Repeated headers are not lines; page order across pages (D34.2) | `a_multipage-2p-us-2`, `a_multipage-8p-na-10` | yes |
    | Discount printed under an item (D34.2) | none | no |
    | Carried-forward and page-subtotal rows (D34.2) | none | no |
    | Wrapped description joined (D34.3) | `c_0026691_201800431` | yes |
    | Item codes and units of measure left out (D34.3) | `c_0026691_201800431`, `c_0073141_000332` | yes |
    | Several amounts: `line_total` before tax (D34.3) | none | no |
    | Row discount: printed rate, amount after discount (D34.3) | `c_0026691_201800431`, `c_0073141_000332` | yes |
    | Zero-amount rows are lines (D34.3) | none | no |
    | Percentage row (D34.4) | `a_freight-carrier-za-3`, `a_tax-percentage-line-1`, `a_tax-percentage-line-2` | yes |
    | Foreign-currency row (D34.4) | `a_currency-multi-line-zar` | yes |
*   **Token cap.** `max_output_tokens` = 16,000: min(16,000, `gpt-6-luna`'s
    documented maximum of 128,000 output tokens, checked 2026-11-03 on
    OpenAI's model page). Written into D34.7.
*   **Cut-off replies.** Today a reply cut off mid-JSON fails validation
    inside `responses.parse()` and is reported as "reply did not fit the
    schema", and its tokens are not metered (`metered_llm` counts a call only
    when `last_usage` is set). The call moves to `responses.create`, so the
    status is read before the JSON is validated:
    1.  Request the same strict JSON schema `parse()` sends today (step 5.2).
    2.  Record `usage` for every reply that came back.
    3.  On `status == "incomplete"`, raise
        `LlmExtractionError(f"reply cut off: {reason}")`, with the reason from
        `incomplete_details.reason` as today (it can be `max_output_tokens`
        or `content_filter`).
    4.  If the last `message` output item has a `refusal` content item, or
        no `output_text` content, raise today's
        `"no parsed answer (refused or empty)"`.
    5.  Validate the text of that item's `output_text` content with
        `LlmInvoice.model_validate_json`, raising `"reply did not fit the
        schema: ..."` on `ValidationError`.

    Partial JSON is never used (D34.7).

### 2. Pairing (`scoring.py`)

```text
pair_lines(predicted: list[LineItem], expected: list[LineItem]) -> list[LinePair]

LinePair(label_index: int | None, predicted_index: int | None, pass_: PairPass | None)
PairPass = TOTAL | DESCRIPTION
```

1.  **Pass 1, by total.** Group the rows on each side by `line_total`. For
    each total present on both sides:
    1.  rows whose `normalise_text(description)` is identical pair first,
        k-th with k-th in page order;
    2.  the rows left in that group pair k-th with k-th in page order.

    Both sub-steps are labelled `total`. A null `line_total` never pairs
    here; a null description never pairs in sub-step 1.
2.  **Pass 2, by description.** Among the rows left, group by
    `normalise_text(description)` (the D12 casefold and collapsed
    whitespace). Rows pair k-th with k-th in page order. A null description
    never pairs.
3.  **The rest stay unpaired.** Each leftover labelled row becomes
    `LinePair(i, None, None)`; each leftover predicted row
    `LinePair(None, j, None)`.

The result lists every labelled row once and every predicted row once, in
this order: pairs and unpaired labelled rows by label index, then unpaired
predicted rows by predicted index. Indexes are 0-based in the data and
printed 1-based.

Page order inside a group of equal totals is a positional rule: if the model
reorders rows that share a total and differ in description, those rows pair
wrongly and their fields score wrong. The diff output shows such pairs with
`(total)` next to two different descriptions.

### 3. Line scoring (`scoring.py`)

*   `LINE_FIELDS = ("description", "quantity", "unit_price", "line_total")`.
*   Each pair's four fields are scored with the existing `score_field`;
    `description` uses `is_text=True` (D34.5). A pair made by pass 1 always
    has a correct `line_total`.
*   **Unpaired rows.** Every field of an unpaired labelled row scores MISSING,
    and every field of an unpaired predicted row scores WRONG, whatever the
    label value, null included. `score_field` is not used for unpaired rows,
    because it scores null against null as correct. An unpaired predicted row
    is also counted as invented.
*   **Null label or prediction (D34.6).** A null `line_items` label returns
    `None` (the invoice is skipped and counted as skipped). A null or `[]`
    prediction leaves every labelled row unpaired.
*   New per-invoice result `InvoiceLineScore`: the pairs and, for each pair,
    its field outcomes. Labelled, predicted, invented and unpaired-label
    counts are properties computed from the pairs. New `LineDatasetScore` and
    `score_line_dataset` add these up. The header `DatasetScore` and
    `score_dataset` do not change, so header numbers stay comparable with
    earlier runs.

### 4. Output (`cli.py`)

`print_invoice_result` stays as it is. For `--extractor llm` only,
`run_score` calls a new `print_line_result` after it for each invoice, and
prints the line block after the header summary. Rules and rules-jev output is
unchanged as a whole.

Per invoice, each line indented 32 spaces like the existing detail lines,
values printed with `!r` as `print_invoice_result` does:

```text
lines: {labelled} labelled, {predicted} predicted, {by_total} paired by total, {by_description} paired by description, {unpaired_labelled} labelled unpaired, {invented} invented
L{i}-P{j} ({pass}) {field} {outcome}: got {got!r}, label {label!r}
L{i} unpaired: {row!r}
P{j} invented: {row!r}
```

*   The count line comes first, then one line per field that is not correct
    in a pair, then unpaired labelled rows, then invented rows. `{row!r}` is
    the row's `model_dump()`.
*   A `None` or `[]` prediction, including a failed extraction, prints one
    line instead: `lines: no prediction ({None|[]}), {n} labelled unpaired`.
*   A null label prints: `lines: skipped, label null`.

Illustrative output (made-up invoices):

```text
a_example-multipage            all correct
                                lines: 4 labelled, 4 predicted, 2 paired by total, 1 paired by description, 1 labelled unpaired, 1 invented
                                L2-P2 (total) description wrong: got 'Widget A -', label 'Widget A - blue'
                                L3-P3 (description) line_total wrong: got Decimal('12.50'), label Decimal('125.00')
                                L4 unpaired: {'description': 'Freight', 'quantity': None, 'unit_price': None, 'line_total': Decimal('9.00')}
                                P4 invented: {'description': None, 'quantity': None, 'unit_price': None, 'line_total': Decimal('9.50')}
b_example-long                 FAILED: reply cut off: max_output_tokens
b_example-long                 {'vendor_name': 'missing', ...}
                                lines: no prediction (None), 6 labelled unpaired
r_example-private              all correct
                                lines: skipped, label null
```

After the header summary, the line block:

```text
line items
{format_counts("lines overall", ...)}
{format_counts(field, ...)}            one line per LINE_FIELDS name
invented {n}
labelled unpaired {n}
largest invoice: {name}, {n} labelled rows
{format_counts("lines excl. top", ...)}
skipped {n} invoices (label null)
```

Time and the meter line still print last (D29, comparison write-up). Private
invoices print the same way on the terminal only; their rows are never copied
into a committed file (D30.1).

### 5. Process (D34.8, docs only)

This is the one full statement of the loop; the Goals, CUJs and
implementation steps refer to it.

1.  **Header baseline.** 3 billed LLM dev runs at the step 1 commit, before
    any line-item code. A run with a failed extraction is repeated. The guard
    values are the highest header wrong count and the highest header missing
    count of the three runs.
2.  **Baseline line run.** 1 dev run with the first full prompt. It is
    checked against the guard values; if it exceeds either, the first fix
    round addresses the header before line accuracy.
3.  **Fix rounds, at most 3.** A round is one committed change to
    `INSTRUCTIONS` or to the field descriptions of `LlmLineItem` or
    `LlmInvoice`, plus one dev run. Progress means line wrong + missing went
    down and line wrong did not go up. A run whose only failed extractions
    are API errors (`OpenAI call failed`) is repeated before it is judged; a
    cut-off or schema failure counts against the round. A round is reverted,
    and the loop ends, when it shows no progress, when its header wrong or
    header missing count exceeds its guard value, or when it has a cut-off or
    schema failure.
4.  **Final runs.** The frozen commit is the last commit kept by the loop,
    with a clean working tree, recorded by hash. At it: 3 dev runs, then 3
    held-out runs. Nothing in the prompt or schema changes after held-out is
    seen. A scorer bug found afterwards may be fixed and all 6 runs repeated,
    marked as a re-run; a prompt or schema change may not.
5.  **Record.** Each run's counts and meter line go into the "Line items"
    section of `docs/comparison.md`; the final counts, the spread of the 3
    final dev runs and the remaining failures by cause go there too.

## Alternatives Considered

### Alternative A: Second pass by page order (D34.5 as written)

*   **Pros**: Every row on the shorter side gets a partner, so few rows are
    unpaired. Simple to explain and to code.
*   **Cons**: One dropped row shifts every later leftover onto its neighbour,
    and each shifted pair scores up to four wrong fields. Those wrong values
    come from the pairing rule, not from the model, and a prompt fix cannot
    remove them.
*   **Reason for Rejection**: It makes the wrong count, the number that
    matters most (D11, missing is null, never guessed), depend on the scorer.
    Page order is kept only as the last tie-break inside a group of equal
    totals, where the totals already agree.

### Alternative B: Page-order pairs marked "unverified"

*   **Pros**: Keeps Alternative A's coverage and tells the reader which pairs
    to distrust.
*   **Cons**: The marked pairs are still counted, so the totals still contain
    the cascade. A label on the output does not fix the number.
*   **Reason for Rejection**: Chosen briefly during the brainstorm, then
    replaced by description pairing, which does not create the wrong values
    in the first place.

### Alternative C: Fuzzy or best-fit matching

Pair rows by text similarity (edit distance, token overlap) or solve an
assignment problem over a similarity score.

*   **Pros**: Pairs rows whose description differs by a dash, an accent or a
    wrapped tail, so fewer rows end up as one missing plus one invented.
*   **Cons**: Needs a similarity threshold with no principled value. Pairings
    change when the threshold changes. Harder to test and to explain in the
    output.
*   **Reason for Rejection**: The cost of exact matching (a near-miss scores
    as missing plus invented) is visible in the diff output, where both rows
    print. A wrong similarity pairing would not be visible.

### Alternative D: A second model call for line items

*   **Pros**: Line prompt changes cannot move the header. Each call has its
    own token budget, so the large invoice is less likely to be cut off.
*   **Cons**: Twice the calls, a merge step, and meter changes. Two prompts
    to keep in step with the label rules.
*   **Reason for Rejection**: Rejected in D34.7. If the loop ends on a
    header-guard revert, two calls become the next design to consider.

### Alternative E: "Expected to fail" with an edge-case stop rule

The earlier framing: the first run fails by design, and the loop stops when
every remaining failure is a listed, accepted edge case.

*   **Pros**: Forces every remaining failure to be explained.
*   **Cons**: "Fail", "edge case", "rare" and "recurring" had no measurable
    meaning. Description mismatches recur, so they could never be accepted,
    and the loop had no way to end except success.
*   **Reason for Rejection**: Replaced by the baseline framing and a round
    cap. Remaining failures are still explained, by cause, in the write-up.

### Alternative F: Stop at a success threshold

*   **Pros**: A clear target and a clear "done".
*   **Cons**: There is no basis for a number before a baseline exists. A
    number picked now would be arbitrary, and one picked after seeing dev
    results would be tuned to them.
*   **Reason for Rejection**: Deferred. The loop ends on effort and progress.
    A threshold can be set later from the baseline and final numbers.

### Alternative G: Keep `responses.parse()` and infer cut-offs

Treat a `ValidationError` as a cut-off, or, more precisely, treat a Pydantic
`json_invalid` error (truncated JSON) as a cut-off and any other error as a
schema failure.

*   **Pros**: No change to how the call is made; the `json_invalid` variant is
    a few lines in the existing `ValidationError` branch.
*   **Cons**: The cause is inferred from the JSON, not read from the API
    status: invalid JSON for any other reason is labelled a cut-off. Token
    usage is still not recorded, so the meter undercounts the most expensive
    calls.
*   **Reason for Rejection**: The cause of a failure decides whether the fix
    is a larger token cap or a prompt change, and the cost report must count
    every billed call.

### Alternative H: Summary counts only, no per-row output

*   **Pros**: Short output, no new formatting code.
*   **Cons**: A dropped row and a misread value give similar counts. Telling
    them apart would mean opening each PDF.
*   **Reason for Rejection**: The per-row diff is the cheapest way to see why
    a round failed, which is what the fix rounds need.

--------------------------------------------------------------------------------

## Non-Functional Requirements

*   **Cost.** The last header-only run cost $0.0101 for 67 calls (dev and
    held-out); line replies are longer, so expect several times that per
    run. The plan makes at most 3 (header baseline) + 1 (line baseline) + 3
    (rounds) + 3 (final dev) + 3 (final held-out) = 13 billed runs, plus any
    repeats for API errors. Each run's meter line is recorded.
*   **Privacy.** Private invoices (D30, wider sample set) are scored on the
    terminal only. Committed docs carry their counts, never their rows.
*   **Held-out isolation (D6).** A test checks that no held-out label
    description of 3 or more words appears in the prompt (step 5.1).
*   **Rollback.** Each code step is its own commit. Reverting step 5 restores
    header-only extraction; header scoring is unchanged throughout.

--------------------------------------------------------------------------------

## Detailed Implementation Plan

Nine steps, in order. Steps 1, 3, 4, 5 and 9 commit code or decision docs;
steps 2, 6, 7 and 8 are billed runs whose commits edit `docs/comparison.md`
only (step 7 also commits each round's prompt change). Each commit ends with
`uv run pytest`, `uv run ruff check .`, `uv run ruff format --check .` and
`uv run mypy .` clean (D13). Billed runs happen only when the owner asks for
them.

### Step 1. Record the rules and the design (docs only)

#### 1.1 `docs/decisions.md` (Modify)

*   **Type / Scope**: decision record.
*   **Proposed Changes**:
    *   **D34.5** rewritten: "Lines pair by identical `line_total` first;
        inside a group of equal totals, rows with identical descriptions
        (after D12's normalising) pair first, then the rest in page order.
        Leftovers pair by identical description, k-th with k-th in page
        order. A null key never pairs. Rows that match neither way stay
        unpaired. Each pair's 4 fields are scored as header fields,
        descriptions after D12's normalising. Every field of an unpaired
        labelled line scores missing and every field of an unpaired predicted
        line scores wrong, null fields included; each unpaired predicted line
        is counted as invented. Line fields are a separate block in `score`,
        printed for the LLM only."
    *   **D34.7**: "a cut-off reply fails the whole invoice" gains "and is
        detected from the reply status before validation, reported as cut
        off, and metered." The cap figure stays "about 16,000" until step 5.
    *   **D34.8** replaced by the build order (scorer test-first, CLI, LLM
        schema and prompt) and the five items of Technical Plan section 5,
        written for line items, with the final runs citing D29.4 (results
        from 3 runs at a frozen commit).
    *   **D34** `Changes` gains D29; **D29** `Changed by` gains D34: line-item
        runs are recorded under D34.8 in a "Line items" section.
    *   **D34** `Evidence` gains this design.
*   **Why**: the code cites these rules; they must exist first.

#### 1.2 `docs/designs/line-items.md` (Create)

*   This design, committed with the decision edits so D34's Evidence link
    resolves.

#### 1.3 `docs/designs/line-items-brief.md` (Modify)

*   **Proposed Changes**: a note under the title: "Superseded by
    [line-items.md](line-items.md) on 2026-11-03; its open items are resolved
    there." Body not edited.
*   **Why**: two briefs with conflicting open items would mislead a reader.

### Step 2. Header baseline (run)

*   Technical Plan section 5, item 1, at the step 1 commit.
*   **`docs/comparison.md` (Modify)**: new section "Line items (D34)" with a
    sub-section "Header baseline": the commit, the three header count lines,
    the failed-extraction count, the meter lines, and the two guard values.

### Step 3. Pairing and line scoring, test-first

#### 3.1 `tests/test_scoring.py` (Modify)

*   **Type / Scope**: unit tests, written before 3.2.
*   **Proposed Changes**: one parametrised `test_pair_lines` over a case
    table; each case gives the labelled rows, the predicted rows and the
    expected `(label_index, predicted_index, pass_)` list (rows written as
    `(description, line_total)`, other fields null):
    *   identical lists `[(a,1),(b,2)]` / `[(a,1),(b,2)]`:
        `(0,0,total),(1,1,total)`;
    *   a dropped middle row `[(a,1),(b,2),(c,3)]` / `[(a,1),(c,3)]`:
        `(0,0,total),(1,None,None),(2,1,total)`;
    *   a misread total, same description `[(a,1)]` / `[(a,9)]`:
        `(0,0,description)`;
    *   a misread total, different description `[(a,1)]` / `[(x,9)]`:
        `(0,None,None),(None,0,None)`;
    *   equal totals in page order `[(a,5),(b,5)]` / `[(a,5),(b,5)]`:
        `(0,0,total),(1,1,total)`;
    *   equal totals reordered `[(a,5),(b,5)]` / `[(b,5),(a,5)]`:
        `(0,1,total),(1,0,total)`;
    *   equal totals, descriptions differ `[(a,5),(b,5)]` / `[(x,5),(y,5)]`:
        `(0,0,total),(1,1,total)`;
    *   a dropped first duplicate `[(a,5),(b,5)]` / `[(b,5)]`:
        `(0,None,None),(1,0,total)`;
    *   a wrong total equal to another row's total `[(a,1),(b,2)]` /
        `[(a,2),(b,2)]`: `(0,0,description),(1,1,total)`;
    *   null totals and null descriptions never pair on that key;
    *   descriptions equal after normalising (case, spaces) pair;
    *   negative (credit) totals pair like any other;
    *   in every case, each labelled and each predicted index appears exactly
        once, in the documented order.

    Tests for `score_lines`: `test_paired_fields_are_scored_like_header_fields`;
    `test_every_field_of_an_unpaired_labelled_row_is_missing` (including null
    label fields); `test_every_field_of_an_invented_row_is_wrong` (including
    an all-null row, also counted as invented);
    `test_a_null_label_skips_the_invoice`;
    `test_a_null_or_empty_prediction_leaves_every_label_unpaired`. Tests for
    `score_line_dataset`: `test_line_dataset_sums_invoices_and_skips`.
    Existing header tests are not changed.

#### 3.2 `document_extractor/scoring.py` (Modify)

*   **Type / Scope**: pure scorer.
*   **Proposed Changes**:
    *   `LINE_FIELDS = ("description", "quantity", "unit_price",
        "line_total")`.
    *   `class PairPass(StrEnum)`: `TOTAL = "total"`, `DESCRIPTION =
        "description"`.
    *   `@dataclass(frozen=True) class LinePair`: `label_index: int | None`,
        `predicted_index: int | None`, `pass_: PairPass | None`.
    *   `pair_lines(predicted: list[LineItem], expected: list[LineItem]) ->
        list[LinePair]`, as in Technical Plan section 2.
    *   `@dataclass(frozen=True) class ScoredPair`: `pair: LinePair`,
        `outcomes: dict[str, Outcome]` (all four fields).
    *   `@dataclass(frozen=True) class InvoiceLineScore`: `pairs:
        list[ScoredPair]`, with properties `labelled`, `predicted`,
        `by_total`, `by_description`, `unpaired_labels`, `invented`.
    *   `score_lines(predicted: Invoice, expected: Invoice) ->
        InvoiceLineScore | None`.
    *   `@dataclass class LineDatasetScore`: `invoice_count: int = 0`,
        `skipped_count: int = 0`, `per_field: dict[str, Counter[Outcome]]`
        (default one empty `Counter` per `LINE_FIELDS` name), `overall:
        Counter[Outcome]`, `invented: int = 0`, `unpaired_labels: int = 0`,
        `largest_name: str | None = None`, `largest_labelled: int = 0`,
        `overall_without_largest: Counter[Outcome]`.
    *   `score_line_dataset(results: Iterable[tuple[str, Invoice, Invoice]])
        -> LineDatasetScore` (name, predicted, expected).
    *   The comment on `HEADER_FIELDS` changes from "header fields only until
        line-item scoring is built" to "header fields; line fields are
        `LINE_FIELDS`, scored as a separate block (D34.5)". The module
        docstring adds one sentence on line pairing.
*   **Why**: G2 and G3. Kept in `scoring.py` because pairing is part of
    scoring and must stay pure (D21).

### Step 4. Line output in `score`

#### 4.1 `tests/test_cli.py` (Modify)

*   **Proposed Changes**:
    *   `test_rules_score_output_is_unchanged`: pins the full `score` output
        for the rules extractor on the existing CLI test samples as a literal
        string, written before 4.2, so it shows no line output and no change
        to the header lines.
    *   Tests for `print_line_result`, one per string in Technical Plan
        section 4: the count line; a failing field line with pass, outcome
        and got/label; an unpaired labelled row; an invented row; the "no
        prediction" line for `None` and for `[]`; the "skipped, label null"
        line; row numbers are 1-based.
    *   `test_line_summary_block`: the block's lines in order, including the
        largest invoice and "lines excl. top", and that time and the meter
        line still print last.

#### 4.2 `document_extractor/cli.py` (Modify)

*   **Proposed Changes**:
    *   `print_line_result(predicted: Invoice, expected: Invoice) -> None`,
        formatting `score_lines`' result as in Technical Plan section 4.
    *   `format_line_summary(score: LineDatasetScore) -> list[str]`, reusing
        `format_counts`.
    *   `run_score` calls `print_line_result` after `print_invoice_result`,
        and prints the line summary after the per-field header lines and
        before the time line, only when `extractor_name == "llm"`. It
        collects `(name, predicted, expected)` for `score_line_dataset`; no
        second extraction.
*   **Why**: G4. `print_invoice_result` and `format_counts` are not changed.

### Step 5. Extraction: schema, prompt, cap, cut-off

#### 5.0 Token cap (before the tests)

*   Read `gpt-6-luna`'s documented maximum output tokens. Set the cap to
    min(16,000, that maximum) and write the number into Technical Plan
    section 1 and D34.7.

#### 5.1 `tests/test_llm_extractor.py` (Modify)

*   **Proposed Changes**:
    *   `ACME_JSON` gains `"line_items": null`. A new fixture
        `ACME_WITH_LINES_JSON` carries two rows.
    *   `test_money_strings_become_exact_decimals`: its `line_items is None`
        assert becomes a check that the answer's line items convert; the D34
        comment is removed.
    *   `invoice_dated` and every other `LlmInvoice(...)` builder pass
        `line_items=None`.
    *   New: `test_rows_become_exact_decimals` (from `ACME_WITH_LINES_JSON`);
        `test_none_and_empty_line_items_stay_distinct`;
        `test_quantity_text_allows_one_to_four_decimals` (5 decimals or a
        thousands separator fails validation).
    *   `test_sends_the_page_and_settings_and_parses_the_answer` asserts
        `max_output_tokens` equals the step 5.0 cap (was 4000), that
        `text.format` has `name == "LlmInvoice"` and `strict is True`, and
        that its schema has `line_items`.
    *   `test_a_reply_cut_off_mid_json_is_a_failure` passes `usage=USAGE`
        and also asserts the message is `reply cut off: max_output_tokens`
        and that `last_usage` is set.
    *   New: `test_a_complete_reply_that_breaks_the_schema_is_a_failure`
        ("did not fit the schema").
    *   `test_a_refusal_is_a_failure_not_an_empty_invoice` and
        `test_a_refused_reply_still_reports_its_billed_usage` stay and must
        pass unchanged.
    *   New: `test_no_heldout_label_description_appears_in_the_instructions`:
        no description of 3 or more words from
        `samples/heldout/*.expected.json` appears, after D12 normalising, in
        normalised `INSTRUCTIONS`.

#### 5.2 `document_extractor/llm_extractor.py` (Modify)

*   **Proposed Changes**:
    *   Module docstring: "header fields" becomes "header fields and line
        items".
    *   `QuantityText = Annotated[str, StringConstraints(pattern=r"^-?\d+(\.\d{1,4})?$")]`.
    *   `class LlmLineItem(BaseModel)`, `extra="forbid"`, fields
        `description: str | None`, `quantity: QuantityText | None`,
        `unit_price: QuantityText | None`, `line_total: MoneyText | None`,
        each with a short `Field(description=...)`, no defaults.
    *   `LlmInvoice.line_items: list[LlmLineItem] | None`.
    *   `money()` moved to module level as `decimal_from_text`; `to_invoice`
        builds `LineItem`s with it; `line_items=None` hard-coding removed.
    *   `INSTRUCTIONS`: first line becomes "You extract header fields and
        line items from the text of one invoice."; a new `line_items` block
        states the D34.2 to D34.4 conventions that step 5.3 found on dev, and
        that `[]` means no item rows while null means the table could not be
        read.
    *   `max_output_tokens` set to the step 5.0 cap, with the comment citing
        D34.7.
    *   `TEXT_FORMAT = type_to_text_format_param(LlmInvoice)`, built once at
        import, from `openai.lib._parsing._responses`. It is the helper
        `parse()` uses, so the request schema is unchanged; it gives
        `{"type": "json_schema", "strict": True, "name": "LlmInvoice",
        "schema": ...}`. The module is private to the SDK, so an upgrade can
        move it; the settings test catches that.
    *   `extract_from_text` calls `responses.create(..., text={"format":
        TEXT_FORMAT})` and follows the five steps in Technical Plan section 1.
        The other request settings (`reasoning`, `store`, `instructions`)
        are unchanged.
*   **Docs in the same commit** (D27, null-source register: N edits land with
    the code that adds the null path):
    *   `docs/decisions.md`: D26 (LLM extractor) cap figure updated to the
        step 5.0 cap; D34 gains a "Not prompted" line listing the
        conventions from step 5.3.
    *   `docs/null-sources.md`: N1 (the LLM call fails) says a cut-off reply
        is reported as cut off and that `line_items` is null with the other
        fields; N3 (`line_items` always null) narrows to the rules
        extractors; N18 (the model returns null) extends to `line_items` and
        each row field.
*   **Why**: G1. The status must be read before validation to tell a
    cut-off from a schema break and to meter every billed reply.

#### 5.3 Convention check (no file of its own)

*   Before writing the `line_items` block, list each D34.3/D34.4 convention
    against the dev labels that show it, by reading dev label JSON only.
    Conventions with no dev example are left out of the prompt and go into
    D34's "Not prompted" line.

### Step 6. Baseline line run (run)

*   Technical Plan section 5, item 2. Record in the "Line items" section,
    sub-section "Baseline": commit, header counts against the guard values,
    line summary block, failed extractions, meter line.

### Step 7. Fix rounds (at most 3)

*   Technical Plan section 5, item 3.
*   Recorded in a "Fix rounds" sub-section: round number, commit, what
    changed and why (citing invoices and rows from the run output), line
    counts, header wrong and missing counts against the guard values, failed
    extractions, progress yes/no.
*   A reverted round is undone with `git revert`, not by rewriting history.

### Step 8. Final runs

*   Technical Plan section 5, item 4; held-out runs use `--set heldout`.
*   Recorded in a "Final" sub-section: the frozen commit's hash, all 6 runs'
    header and line counts, the spread of the 3 dev runs, meter lines.

### Step 9. Write-up and doc updates

#### 9.1 `docs/comparison.md` (Modify)

*   **Proposed Changes**: a "Verdict" update line for line items; under
    "Line items", "Remaining failures by cause" (public invoices row by row,
    private invoices as counts per cause), and a note that the prompt was
    tuned on dev only, so a gap between dev and held-out is expected. The
    sentence saying line items are not measured is replaced.

#### 9.2 `docs/null-sources.md` (Modify, only if needed)

*   A new N entry if step 7 added a deliberate null path (for example a rule
    telling the model to leave a field null).

#### 9.3 `README.md` (Modify)

*   **Proposed Changes**: overview says header fields and line items; the
    "only header fields so far" invariant becomes "the LLM extracts line
    items; the rules extractors do not (D34)".

#### 9.4 `document_extractor/README.md` (Modify)

*   **Proposed Changes**: interface lists `LlmLineItem`,
    `decimal_from_text`, `pair_lines`, `score_lines`, `score_line_dataset`,
    `LinePair`, `ScoredPair`, `PairPass`, `InvoiceLineScore`,
    `LineDatasetScore`, `LINE_FIELDS`, `print_line_result`; the line-items
    invariant is rewritten; a new invariant: `score` prints exactly the
    pairing it scored.

#### 9.5 `docs/decisions.md` (Modify)

*   **Proposed Changes**: D34's "Not built yet" note is removed; D34's
    Evidence points at the comparison sections.

### Files not changed

*   `document_extractor/schema.py`: `LineItem` and `Invoice.line_items`
    already exist.
*   `document_extractor/rules_extractor.py`, `currency_resolver.py`:
    keep `line_items=None` (D34.1).
*   `samples/`: labels are already written; not changed.
*   `tests/test_samples.py`: already rejects `[]` labels.
*   `docs/decisions-index.md`: no new decision, and D34's title is unchanged.
*   `docs/decisions-history.md`: frozen.

### Verification Plan

*   **Unit tests**: `uv run pytest`; existing tests pass, except those that
    steps 4.1 and 5.1 change on purpose, plus the new pairing, scoring, CLI
    and extractor tests.
*   **Static analysis**: `uv run ruff check .`, `uv run ruff format --check
    .`, `uv run mypy .` (strict).
*   **Rules output unchanged**: `test_rules_score_output_is_unchanged` in
    step 4.1.
*   **Held-out isolation**: the guard test in step 5.1.
*   **Live**: steps 2, 6, 7 and 8, recorded in `docs/comparison.md`.

--------------------------------------------------------------------------------

*Drafted with EGM*
