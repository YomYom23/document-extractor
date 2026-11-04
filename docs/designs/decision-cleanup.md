# Repo cleanup and a current-rules decision system

*   **Author:** Yomi O Lebi
*   **Status:** Proposed (revised after two review rounds)
*   **Date:** 2026-10-30

--------------------------------------------------------------------------------

## Overview

document-extractor records every design decision in `docs/decisions.md`, an
append-only log of 34 entries (D1 to D34) across 413 lines. Code, tests and
docs cite it about 180 times by D or Q number. This design removes the few
files the repo no longer uses and replaces the log with two files: a frozen
history file that keeps every original entry, and a new `docs/decisions.md`
that holds only the rule each decision stands for today, still keyed by the
same D numbers. Opaque cites in the code gain a short explanation, and a
test fails when a cite points at a decision that does not exist. The
line-items work (D34) waits until this is done. The only readers are the
owner (Yomi) and Claude.

### Terms

*   **D number**: an entry in the decision log, D1 to D34. New decisions take
    the next free number.
*   **Q number**: a question from a grilling session, the question-and-answer
    sessions in which decisions were made. Each D heading or body names the Q
    numbers it settled (for example D24 settled Q24 to Q31). No list of the
    questions exists.
*   **N number**: an entry in `docs/null-sources.md`, N1 to N20, one per place
    the code can return null.
*   **Cite**: a D, Q or N number written in code, tests or docs.
*   **Chain**: an earlier decision and a later one that changed it, such as
    D9 (schema fields) and D20 (the arithmetic check is a warning only).
*   **Held-out**: the sample set kept for the final comparison only; its text
    must never shape a rule or the LLM prompt.
*   **Sample sources**: three public sources of synthetic invoices, the
    Invoice Extraction Benchmark (IEB, `a_` files), InvoiceBenchmark (`b_`)
    and Sinabis (`c_`); and the owner's real invoices (`r_`), kept in the
    git-ignored `samples/private/`.
*   **Jev, TypeSafe**: Jev is the currency-answering service the
    `rules-jev` extractor calls, through the TypeSafe SDK.
*   **Live run**: a billed run of an extractor against real APIs, recorded in
    the log with its date and results.

## The Problem

A bare "D24" in a comment, a test or a chat message tells the reader nothing.
Finding out what it means takes three steps: open the log, find the entry, and
read it. That is the pain the owner reported. Three things make it worse:

1.  **The entry you find may be out of date.** When a later decision changes an
    earlier one, the later entry says "amends Dx", but the earlier entry is
    never updated. For example, D9 (the schema fields) reads as if the
    arithmetic check were part of correctness, but D20 later made it a warning
    only, and nothing in D9 says so. Six more earlier entries have the same
    problem, and D28 and D30 change earlier entries without saying so at all.
2.  **Some text is already wrong.** `rules_extractor.py:313` and
    `null-sources.md` N3 say line items are "not extracted yet", as if
    temporary, but D34 (line items) fixed the rules extractor at null for
    good. `null-sources.md` says held-out has never been run.
    `samples/ATTRIBUTION.md` opens with "All invoices are synthetic", which
    its own `r_` section contradicts. D26 (the LLM extractor) gives a run
    command for a script that D28 (the CLI) deleted.
3.  **Q numbers point at nothing.** 37 lines cite Q numbers. The only way to
    decode one is to find the D whose Q range contains it.

Nothing checks any of this. A drift check run on 2026-10-28 found the new
READMEs out of date within a day of writing them.

The solution keeps the D numbers, because commit messages, `comparison.md`
and `null-sources.md` depend on them. It moves today's log unchanged into a
history file, writes one current rule per D in a new `decisions.md`, rewrites
every Q cite as its D, explains opaque cites, and adds a test that keeps
cites and rules in step.

## Goals

*   A reader who meets a D number in the code learns what the rule means for
    that code from the comment itself, without opening another file.
*   A reader who opens `docs/decisions.md` at any D sees the rule as it stands
    today and its status (`active` or `retired`). A rule that a later decision
    changed says so and names it.
*   Nothing is lost. Every original entry, live-run log, diagnosis and
    frozen-commit hash survives in `docs/decisions-history.md`, moved with
    `git mv` so `git log --follow` still works.
*   No Q cites remain outside the history file.
*   `uv run pytest` fails when a scanned file cites a D or N number that does
    not exist, cites any Q number, or when the index does not match the
    entry headings.
*   Claude loads the index (one line per entry, 34 lines today) at the start
    of every session through `CLAUDE.md`.
*   Unused files are removed, each with evidence: the 2026-10-28 drift
    report, `IDEA.md` and a stale `.pyc`.
*   Stale text is corrected (section 8).
*   Each commit ends with pytest, ruff and mypy clean (D13, project hygiene).

## Non-Goals

*   Renumbering, renaming or reusing D numbers.
*   Sub-numbers such as D24.1. A D that holds several rules lists them in one
    entry.
*   Writing up the Q questions from chat history.
*   One file per decision.
*   Any change to how the extractors, scorer or CLI behave. Code changes are
    comments and docstrings only.
*   Building line items (D34). D34's rules are recorded; the build waits.
*   A test that held-out labels never reach the LLM prompt. No commit here
    touches the prompt; the test belongs with the first D34 prompt change.
    Until then the gap is accepted.
*   Changes to sample PDFs or labels.
*   A test that a cite's explanation matches its rule, or that every rule is
    cited somewhere.
*   Removing `scripts/live_currency_check.py`, `dotenv_key.py`,
    `currency_snippets.json`, the `min_confidence` and `model` parameters, or
    `PdfPage.width` / `height`. All are kept on purpose.
*   Committing `line-drafts/`. It stays local until D34 labelling is done.

## Open Questions

*   None open.

## Critical User Journeys (CUJs)

### CUJ 1: Reading a cite in the code

*   **Given**: The migration is done. `llm_extractor.py` has
    `issue_date_from_parts` with a cite in its docstring.
*   **When**: The owner or Claude reads it.
*   **Then**: It reads like
    `D26: date asked as year/month/day; a missing part gives null`.
    The rule is clear without opening `docs/decisions.md`. For more, D26 in
    `docs/decisions.md` gives the current rule, its reason and a link to the
    evidence.

### CUJ 2: Claude refers to a decision in chat

*   **Given**: A new Claude session. `CLAUDE.md` imports the index.
*   **When**: Claude needs to point at a decision while answering.
*   **Then**: Claude writes the number with a short explanation, for example
    "D11 (missing is null, never guessed)", never a bare "D11". This is an
    instruction to Claude; no test can enforce it.

### CUJ 3: A later decision changes an existing rule

*   **Given**: The owner decides something that changes D12 (scoring rules).
*   **When**: The decision is written down.
*   **Then**: D12's entry is edited in place in the same commit as the code
    it affects. No new number is created. The index line changes only if the
    title or status changed. Cites whose explanation is now wrong are fixed
    in the same commit, and the tests pass. The commit message and
    `git log` record what changed.

### CUJ 4: A cite goes stale

*   **Given**: Code cites D24, and a typo later turns it into D42.
*   **When**: `uv run pytest` runs.
*   **Then**: The cite test fails with `file:line: D42`.

## Technical Plan (Architecture)

### The pieces and how they connect

```text
  scanned files: code, tests, scripts, READMEs, CLAUDE.md, live docs
  "D26: date asked as year/month/day; a missing part gives null"
        |
        | cite D / N numbers
        v
  docs/decisions.md ------ headings copied into ------> docs/decisions-index.md
  (current rules, in number order)                        (one line per entry)
        |                                                       |
        | "Evidence:" links                                     | imported by
        v                                                       v
  docs/decisions-history.md (frozen; full Q table)        CLAUDE.md (repo root)
  docs/comparison.md, docs/null-sources.md (N1..N20)

  tests/test_decision_cites.py checks: every cited D and N exists,
  no Q appears, and the index equals the headings.
```

### 1. The history file

`docs/decisions.md` is moved to `docs/decisions-history.md` with `git mv`, in a
commit that changes nothing else, so git records it as a rename. The next
commit adds, directly under the history file's `# Decision log` title and
touching nothing below:

*   A line: "Frozen on YYYY-MM-DD (the date of that commit). The current rules
    are in decisions.md. Do not edit below this line."
*   The **full Q table** (section 6).

The test never scans the history file. Its old wording, live runs, diagnoses
and frozen-commit hashes stay where they are, and evidence links point at it.

### 2. The current-rules file

A new `docs/decisions.md`. It opens with three lines: what the file is, that
history lives in `decisions-history.md`, and that a changed rule is edited in
place (section 5). Entries follow in number order, D1 to D34. There are no
topic sections; the index gives the overview.

#### Formats

These are exact, because the test and the index depend on them.

*   **Entry heading**: `### D<n>. <title> (<status>)`, where status is
    exactly `active` or `retired`. The title is one line and readable on its
    own.
*   **Index file**: a first line `# Decision index`, a blank line, then one
    line per entry, in number order, each equal to that entry's heading with
    the leading `### ` removed. No other lines.
*   Nothing else in `decisions.md` starts with `### D`.

Each entry has this shape:

```markdown
### D11. Missing is null, never guessed (active)
**Rule:** A field the page does not show is null. A wrong value is worse
than a missing one, so when unsure, return null.
**Scope:** all extractors, scorer
**Why:** one to three sentences.
**Evidence:** link to the history entry, and to comparison.md where relevant.
```

Optional lines, only when they apply: `**Rejected:**` (alternatives, one line
each), `**Changed by:**`, `**Changes:**`, `**Not built yet:**` and
`**Open problem:**`.

*   **Rule** states only this decision's own rule (section 3).
*   **A D with several rules** (D24 holds about eight) lists them as a short
    numbered list under Rule. A cite names the rule in words, for example
    `D24: ambiguous slash dates give null`.
*   **D34** is an `active` entry with its settled rules (from Q88 to Q105 in
    history and the four points settled in `docs/designs/line-items-brief.md`)
    and one line: `**Not built yet:** line items are labelled for the 25 IEB
    and 20 Sinabis invoices; extraction and scoring wait (paused on
    2026-10-29).`
*   **Open problems** sit in their own entry as `**Open problem:**`, for
    example ambiguous slash dates under D24. `git grep -n "Open problem"`
    lists them all.
*   **Process rules** (D1, D4, D13, D17, D27) have no code to cite them and
    need not be cited anywhere.

#### Where each entry's text comes from

1.  The latest wording for that D in history, with every later change to it
    applied.
2.  Where history has only a recommendation ("pending your questions", as in
    D21 to D23), the code as it stands is the source: the entry states what
    the code does.
3.  Facts that history gets wrong are corrected while writing (D34's IEB
    count is 25, not 26; D26 has no run command).
4.  Content that is finished and no longer guides work is dropped: D17's
    build order and D13's "no commits" clause. D17 has nothing left and
    becomes `retired` with a one-line reason. D13 stays `active` with its
    remaining rule (each change ends with pytest, ruff and mypy clean).

### 3. Chains: each entry states only its own rule

*   Each entry's Rule states **only that decision's own rule, as it stands
    today**. It never repeats a later decision's change, and never shows old
    wording; that stays in history.
*   The earlier entry gets `**Changed by:** D20`; the later one gets
    `**Changes:** D9`. The two lines are the only place a chain is written.
*   No entry becomes a pointer, and no D cite moves. Only Q cites are
    rewritten.

The chains, from history:

| Later | Changes | What changed |
| --- | --- | --- |
| D20 | D9 | the arithmetic check is a warning, not a correctness test |
| D25 | D16 | a sixth part, the Jev currency resolver |
| D26 | D10 | the LLM gets its own schema, mapped to `Invoice` |
| D28 | D26 | the live LLM check script is replaced by `score` |
| D30 | D19 | the sample set grows and adds real invoices |
| D31 | D19 | a vendor's legal name beats its brand |
| D32 | D14, D23 | NUL characters are repaired with pdfium |
| D33 | D26 | the prompt states the legal-name rule |
| D34 | D9, D12 | line items are labelled and, when built, scored |

While writing, any further change found in history is added to this table
and to the owner check list. D22 implements D20 and changes nothing, so it
is not a chain.

Example: D9 lists the schema fields and ends `Changed by: D20, D34`. D20 says
the arithmetic check (subtotal + tax = total) is a warning only, never a
reason to mark a field wrong, and ends `Changes: D9`.

Chosen on 2026-10-30 over folding a chain into its oldest entry and over
newest-wins (Alternative D).

**Owner check.** Claude writes the whole new file, then gives the owner a
review list: every entry's number, title and one-line Rule, with each chain
pair marked. The owner checks that each Rule matches the code and that no
two linked entries state the same rule, before the commit is made.

### 4. The index and the chat rule

`docs/decisions-index.md` follows the format in section 2, for example:

```text
# Decision index

D11. Missing is null, never guessed (active)
D17. Build order (retired)
D24. Rules extractor: labels, dates, amounts, currency, vendor (active)
```

Because each line equals its heading and the test checks that, the index
cannot drift from `decisions.md`.

The root `CLAUDE.md` imports it with `@docs/decisions-index.md` and gains one
rule: when Claude mentions a D or N number in chat, it adds a few words
saying what it is. Only the index is imported, not the full file, so it stays
small enough to load every session.

### 5. Changing a decision later

*   **A change to an existing rule** edits that entry in place, in the same
    commit as the code it affects. It never gets a new number, so the chain
    table in section 3 never grows after the migration.
*   **A new rule** gets the next free number.
*   **A rule dropped entirely** keeps its heading, with status `retired` and a
    one-line reason.
*   **A decision with no code change** (a process rule, a label convention)
    is committed on its own, with the entry and any docs it affects.
*   **After any Rule change**, search for the number (for example
    `git grep -n "D12\b"`) and reread each cite's explanation. The test checks
    that numbers exist, not that explanations still match.
*   History is never edited after the freeze.

### 6. Cites in code and docs

**Live Q table.** Every Q cite in the scanned files maps to one D:

| Q | D |
| --- | --- |
| Q26 | D24 |
| Q32, Q33, Q34 | D25 |
| Q39, Q47 | D26 |
| Q51, Q53, Q54, Q55, Q56 | D28 |
| Q59, Q60, Q62 | D29 |
| Q75, Q76 | D30 |
| Q81 | D32 |

**Full Q table**, written into history: one row per D that names Q numbers,
taken from its heading and body: D24: Q24 to Q31; D25: Q32 to Q38; D26: Q39
to Q47 (Q47 is in the body); D28: Q48 to Q56; D29: Q57 to Q63; D30: Q64 to
Q76; D31: Q77; D32: Q78 to Q83; D33: Q84 to Q87; D34: Q88 to Q105 (the
heading says Q98; the body continues to Q105). The ranges do not overlap. D1
to D23 recorded no Q ranges, so Q1 to Q23 have no row; the table says so.

**Rewrite rules.**

1.  A Q whose D is already cited in the same parentheses or sentence is
    deleted: `(D25, Q32)` becomes `(D25)`.
2.  A Q used as a name is reworded: "the Q47 amendment" becomes "the D26
    date change".
3.  Any other Q becomes its D: `(Q55)` becomes `(D28)`.
4.  A cite is **opaque** when the comment or docstring sentence holding it
    says nothing besides the numbers: a bare number or number list, or a
    phrase like "(decisions D14, D23, D32)". An opaque cite gets a short
    explanation in free words: `D<n>: what this code does because of the
    rule`. Today's opaque cites:
    *   `document_extractor/llm_extractor.py:20` (`# D26, Q39` on
        `DEFAULT_MODEL`)
    *   `document_extractor/pdf_reader.py:1` ("decisions D14, D23, D32")
    *   `document_extractor/scoring.py:1` ("decisions D11, D12, D21")

    Any other cite already sits in a sentence that says what it means and is
    left as it is.
5.  Comments that describe line items as temporary or header-only are
    rewritten to say what the code does now and cite D34, for example
    `# D34: line items not extracted yet; scoring is header fields only`.
6.  Edits are by hand. Labels under `samples/` are never touched; "Q1 2026"
    and "D16 (16mm)" appear in them as data.

### 7. The cite test

**`tests/test_decision_cites.py`**, no network, no new dependency.

**Files it scans** (defined here only), found with `pathlib` globs from the
repo root:

*   `document_extractor/*.py`, `tests/*.py`, `scripts/*.py`, except
    `tests/test_decision_cites.py` itself
*   `README.md`, `document_extractor/README.md`, `scripts/README.md`
*   `CLAUDE.md`, `document_extractor/CLAUDE.md`, `scripts/CLAUDE.md`
*   `docs/decisions.md`, `docs/decisions-index.md`, `docs/null-sources.md`,
    `docs/comparison.md`
*   `pyproject.toml`

`.venv/`, caches, `samples/`, `line-drafts/`, `docs/decisions-history.md`
and `docs/designs/` are never scanned, because nothing in the list matches
them. A new file is scanned as soon as it exists, tracked or not.

**Checks**, each failure reported as `file:line: token`:

1.  `test_cited_decisions_exist`: every `\bD\d+\b` token names an entry
    heading in `decisions.md`.
2.  `test_cited_null_sources_exist`: every `\bN\d+\b` token names an
    `### N<n>.` heading in `null-sources.md`.
3.  `test_no_q_cites`: no `\bQ\d+\b` token appears.
4.  `test_index_matches_decisions`: the index file is exactly the title
    line, a blank line, and the entry headings without `### `, in order.

Tokens are case-sensitive (`D`, `N`, `Q` upper case only).

**Proving the checks can fail.** Each check's matching function is also
tested on small strings: a known number passes, an unknown one is reported,
a Q is reported, a mismatched index line is reported. The test strings are
built at run time (for example `"D" + "999"`) so the test file itself holds
no literal bad token.

### 8. Cleanup and stale text

*   **Removed**: `2026-10-28_DRIFT_REPORT.md` (untracked), `IDEA.md`
    (tracked, one line, unreferenced), and the git-ignored
    `scripts/__pycache__/live_llm_check.cpython-313.pyc`.
*   **`line-drafts/`** moves from `.git/info/exclude` into `.gitignore`, so
    its private and held-out renders cannot be committed by mistake, and is
    added to `[tool.mypy] exclude`. Today `uv run mypy .` fails with 5 errors
    in `line-drafts/draft_ieb.py` (checked 2026-10-30), so without this no
    commit can end clean.
*   **`httpx2`** added to the dev dependencies, because `tests/test_jev.py`
    and `tests/test_llm_extractor.py` import it directly; today it arrives
    only through `openai` and `typesafe-sdk`.
*   **Committed**: the three READMEs, the three `CLAUDE.md` files, both briefs
    (moved to `docs/designs/`), this design, and every review report of it
    (moved to `docs/designs/reviews/decision-cleanup/`). `line-drafts/` stays
    local.

**Stale text rule.** Before the cite commit, run over the scanned files:

```sh
git grep -n -i -E "not extracted yet|header[- ]fields? only|header-only|only header fields|scored later|in progress|never been run|all invoices are synthetic|Q[0-9]+" -- document_extractor tests scripts README.md "*/README.md" CLAUDE.md docs/null-sources.md docs/comparison.md samples/ATTRIBUTION.md
```

Every hit is fixed in that commit. The table below gives the known hits and
their new text; anything else the search finds is fixed the same way.

| Where | Now says | Becomes |
| --- | --- | --- |
| `rules_extractor.py:313` | `# not extracted yet (D24)` | `# D34: the rules extractor never extracts line items` |
| `llm_extractor.py:100` | `# header fields only (D26)` | `# D34: line items not extracted yet` |
| `scoring.py:10` | `# Header fields only; line items are scored later (D12).` | `# D34: header fields only until line-item scoring is built.` |
| `tests/test_llm_extractor.py:36` | `# header fields only (D26)` | `# D34: line items not extracted yet` |
| `tests/test_samples.py:49-50` | labels added in D30 are header-only | a label's `line_items` is null (not labelled yet) or a list; an empty list would claim "no lines" (D18) |
| `README.md:38-39` | line items (D34) are in progress | line items (D34) are decided but not built yet |
| `document_extractor/README.md:52-54` | line items not extracted yet (D34 is in progress) | line items are not extracted yet and the scorer compares `HEADER_FIELDS` only (D34, not built yet) |
| `README.md:22-23`, `document_extractor/README.md:10-11` | "the D and Q numbers in the code point here/there" | "the D numbers in the code point here/there", with links to the rules, index and history |
| `null-sources.md:8-9` | "measured on the 9 dev invoices. Rules extractor numbers are from a free run on 2026-10-19 (56 correct, 7 missing, 0 wrong); LLM numbers are from D26 live run 2. Held-out has never been run (D6)." | "measured on the 9 dev invoices of 2026-10-19: rules extractor numbers from a free run that day (56 correct, 7 missing, 0 wrong), LLM numbers from D26 live run 2 (in history). Current results for all 67 invoices are in comparison.md. Held-out was first run on 2026-10-19 (D28)." |
| `null-sources.md:27` (N3) | not extracted yet; header fields come first and line items are not scored (D12, D24, D26) | the rules extractor never extracts line items; the LLM will, once D34 is built; until then line items are not scored (D34) |
| `null-sources.md:110` | "since Q47. Before Q47..." | "since the D26 date change. Before it..." |
| `samples/ATTRIBUTION.md:3` | "All invoices are synthetic." | "The `a_`, `b_` and `c_` invoices are synthetic; the `r_` invoices are real and not distributed (see below)." |
| `samples/ATTRIBUTION.md:23, 30` | labels are header-only | labels include line items (D34) |

Links to live-run evidence: in `null-sources.md` and `comparison.md`, each
mention of a named live run ("D26 live run 2", "held-out run") gets a
Markdown link to the matching heading in `decisions-history.md`, for example
`[D26 live run 2](decisions-history.md#live-run-2-2026-10-19-...)`, using the
anchor GitHub generates for that heading.

## Risks and Mitigations

*   **A rule is rewritten wrongly when moving to the new file.** Mitigation:
    history keeps the original; the owner check covers every entry.
*   **Cite explanations drift from their rules.** Explanations are free text
    and no test checks them. Accepted: an explanation describes the code
    beside it, and the section 5 search-and-reread step covers rule changes.
    The test still catches a wrong or missing number.
*   **Two linked entries state the same rule.** Mitigation: the owner check
    looks for exactly this; chains never grow after the migration.
*   **Private renders in `line-drafts/` are committed.** Mitigation: it moves
    into `.gitignore`, and every commit stages named paths only.
*   **Held-out text reaches the prompt before a test exists.** Accepted until
    the first D34 prompt change, which adds the test.

## Alternatives Considered

### Alternative A: Keep one `decisions.md` and fix it in place

Add a one-line index of current rules at the top of today's log, an
"Amended by Dx" line under each amended entry, a D plus explanation in place
of every Q cite, and a `CLAUDE.md` rule. No new files.

*   **Pros**: Smallest change: 37 Q edits and a few explanations. No file
    moves, so no links break. The cite test could still be added.
*   **Cons**: The current rule is stated whole only in its index line; the
    entry below still shows old wording that reads as current. Live-run logs
    and diagnoses stay mixed in with rules.
*   **Reason for Rejection**: It speeds up the lookup but leaves out-of-date
    entries, which is the larger part of the problem.

### Alternative B: Name-based IDs (`docs/rules.md` keyed by names)

Replace D numbers with names such as `null.never-guess`, with a
D/Q-to-name table in history.

*   **Pros**: The ID explains itself.
*   **Cons**: Every one of about 180 cites is rewritten. Commit messages
    ("D34 step 1"), `comparison.md` and `null-sources.md` would need the
    mapping table for ever, and `git log --grep=D30` would stop matching new
    work. Names go stale when a rule's meaning shifts.
*   **Reason for Rejection**: The most churn and broken traceability, for a
    gain a short explanation beside a D number already gives.

### Alternative C: One file per decision

*   **Pros**: A common convention; each file can be linked directly.
*   **Cons**: 34 files for two readers; the index still has to exist.
*   **Reason for Rejection**: More files to keep in step, with no benefit at
    this size.

### Alternative D: Fold each chain into its oldest entry, or let the newest win

*   **Pros**: Folding gives one place to read a topic. Newest-wins matches how
    the log was written.
*   **Cons**: Folding makes large entries and less specific cites
    (`arithmetic_check.py` would cite D9, not D22). Newest-wins moves cites to
    old numbers forward, and the newest entry grows with every change.
*   **Reason for Rejection**: Each entry stating only its own rule fixes the
    out-of-date entries without moving any D cite.

### Alternative E: Explanations at every cite, no rules-file change

*   **Pros**: Fixes the "what does D24 mean" moment in code directly.
*   **Cons**: The explanations would summarise entries that are already out
    of date.
*   **Reason for Rejection**: Explanations are part of the chosen design, but
    only on top of a file that states each current rule once.

### Alternative F: Cite explanations must equal the entry heading

*   **Pros**: Explanations can never drift; the test can check them.
*   **Cons**: Generic comments. A title describes the whole rule, not what
    one line of code does; D24's title covers eight rules and would say
    nothing about slash dates above the date parser.
*   **Reason for Rejection**: Specific wording is what points a reader at the
    right rule when one D holds several.

### Alternative G: Linked new numbers for later changes

Allow a changed rule to get a new number, with `Changes:` / `Changed by:`
lines, and test that both sides of each pair exist.

*   **Pros**: Each change keeps its own reasons in the current file.
*   **Cons**: Chains grow with every change, which is how the old log became
    hard to read; the "new number or edit in place" choice is a judgement
    call each time.
*   **Reason for Rejection**: Editing in place keeps one current text per
    rule; `git log` keeps the reasons.

### Alternative H: Topic sections in `decisions.md`

*   **Pros**: Related entries sit near each other.
*   **Cons**: Status and title live apart from the index, which makes the
    index check fragile; an "Open problems" section needs its own rules.
*   **Reason for Rejection**: Number order with the status in the heading
    makes the index a plain copy of the headings.

### Alternative I: A grep instead of the cite test

*   **Pros**: No test code.
*   **Cons**: Only runs when someone remembers. The project already ends
    every change with pytest (D13).
*   **Reason for Rejection**: The test is one small file and runs where the
    checks already run.

--------------------------------------------------------------------------------

## Non-Functional Requirements

*   **Privacy**: `line-drafts/` holds renders of private and held-out
    invoices; it is git-ignored and never committed. Each commit stages named
    paths only; `git add -A` and `git add .` are never used.
*   **Behaviour**: No commit changes what the extractors, scorer or CLI
    return (checked as described in the Verification Plan).
*   **Rollback**: Revert the whole branch, or revert commits newest first.
    Reverting a single middle commit is not supported: later commits depend
    on earlier ones.

--------------------------------------------------------------------------------

## Detailed Implementation Plan

Five commits on the `cleanup` branch, in this order. Each ends with
`uv run pytest`, `uv run ruff check .` and `uv run mypy .` clean, stages only
the paths it names, and is made only after the owner's go-ahead. Line
numbers below are as of commit `43969ce`. Between commits 2 and 3 the README
links to `docs/decisions.md` point at a missing file; nothing tests links.

### Commit 1: Cleanup and untracked docs

#### 1. `.gitignore`, `.git/info/exclude`, `pyproject.toml` (Modify)

*   Add `line-drafts/` to `.gitignore`; remove it from `.git/info/exclude`
    (local, not committed).
*   In `pyproject.toml`: add `exclude = ["^line-drafts/"]` under
    `[tool.mypy]`, and `httpx2>=2.13.1` (the version already locked) to
    `[dependency-groups] dev`. Run `uv lock`; commit `uv.lock`.
*   Check: `uv run mypy .` reports no errors.

#### 2. `README.md`, `document_extractor/README.md`, `scripts/README.md`, `CLAUDE.md`, `document_extractor/CLAUDE.md`, `scripts/CLAUDE.md` (Add)

*   Committed as they are. Their stale lines are fixed in commit 4 with the
    rest.

#### 3. Removed files (Delete)

*   `2026-10-28_DRIFT_REPORT.md`: delete (untracked).
*   `IDEA.md`: `git rm`.
*   `scripts/__pycache__/live_llm_check.cpython-313.pyc`: delete locally;
    git ignores it.

#### 4. `docs/designs/` (Add)

Untracked files are moved with plain `mv` (not `git mv`), then added:

*   `concepts_brief.md` → `docs/designs/decision-cleanup-brief.md`.
*   `concepts_brief_line_items.md` → `docs/designs/line-items-brief.md`.
*   `docs/designs/decision-cleanup.md` (this design).
*   Every review report of this design in the repo root (`*_report.md`,
    `*_report_r2.md`, `consolidated_review_report*.md`) →
    `docs/designs/reviews/decision-cleanup/`. Their links to each other keep
    working, since they stay in one folder. Later reports of this design go
    to the same folder.

### Commit 2: Move the log to history

#### 5. `docs/decisions.md` → `docs/decisions-history.md` (Move)

*   `git mv` only, so git records a rename.

### Commit 3: Current rules and index

#### 6. `docs/decisions-history.md` (Modify)

*   Under the title only: the frozen line with the commit's date and the full
    Q table (section 6), including the note that Q1 to Q23 have no row.

#### 7. `docs/decisions.md` (Create)

*   Written to section 2 (formats, sources) and section 3 (chains). Uses no Q
    numbers and no D number above D34.
*   **Owner check** before the commit, using the review list from section 3.

#### 8. `docs/decisions-index.md` (Create)

*   Section 2's index format: `# Decision index`, a blank line, then each
    heading without `### `.

#### 9. `CLAUDE.md` (Modify)

*   Add a line `@docs/decisions-index.md` and the rule "When you mention a D
    or N number in chat, add a few words saying what it is, for example 'D11
    (missing is null, never guessed)'." The existing line "Read @README.md
    before working in this directory..." stays first.

#### 10. `README.md`, `document_extractor/README.md` (Modify)

*   The decisions links describe `docs/decisions.md` as the current rules,
    with history in `docs/decisions-history.md` and the index in
    `docs/decisions-index.md`.

### Commit 4: Rewrite cites and stale text

Record the starting commit first: `BASE=$(git rev-parse HEAD)`. Then run the
stale text search (section 8) and apply section 6's rewrite rules and
section 8's table. In `.py` files only comments and docstrings change.

#### 11. Code: `document_extractor/cli.py`, `currency_resolver.py`, `llm_extractor.py`, `pdf_reader.py`, `rules_extractor.py`, `scoring.py` (Modify)

*   Q cites rewritten; the three opaque cites explained; the stale lines in
    the section 8 table.

#### 12. Tests: `tests/test_cli.py`, `test_currency_resolver.py`, `test_jev.py`, `test_llm_extractor.py`, `test_pdf_reader.py`, `test_rules_extractor.py`, `test_samples.py` (Modify)

*   Q cites rewritten (rule 2 for "the Q47 amendment" in
    `test_llm_extractor.py:65`); stale lines per the table.

#### 13. Docs: `README.md`, `document_extractor/README.md`, `docs/null-sources.md`, `docs/comparison.md`, `samples/ATTRIBUTION.md` (Modify)

*   Stale lines per the table; Q cites rewritten (null-sources lines 50, 86,
    106, 109, 110; comparison lines 5, 100, 111); live-run mentions linked to
    history.

#### 14. Any other file the stale text search finds (Modify)

*   Fixed the same way and named in the commit message.

### Commit 5: The cite test

#### 15. `tests/test_decision_cites.py` (Create)

*   Section 7 exactly: the scan list, the four checks with `file:line: token`
    failures, and the small-string tests that prove each check can fail.
    All checks pass at once, because commits 3 and 4 did the work.

### Verification Plan

*   **Unit tests**: `uv run pytest`, which from commit 5 includes
    `tests/test_decision_cites.py`.
*   **Static analysis**: `uv run ruff check .` and `uv run mypy .`.
*   **Behaviour unchanged**: after commit 4, a one-off script in the
    scratchpad (not committed) parses each changed `.py` file at `$BASE` and
    at `HEAD` with `ast`, removes docstring expressions, and checks that
    `ast.dump` is identical. Comments are not in the syntax tree, so equal
    dumps mean only comments and docstrings changed.
*   **History kept**: `git log --follow docs/decisions-history.md` shows
    commits from before the move.
*   **Owner check**: done before commit 3.
*   **No live calls**: nothing in this plan calls OpenAI or TypeSafe.

--------------------------------------------------------------------------------

*Drafted with EGM*
