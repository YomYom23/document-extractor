# Consolidated review: decision-cleanup.md

*   **Target:** `docs/designs/decision-cleanup.md` (692 lines; feature spec
    1-436, implementation plan 437-692)
*   **Date:** 2026-10-30
*   **Mode:** consolidated, all five stages, no edits between stages

## Verdict

Not ready to implement. Every stage agrees the core is sound: keep the D
numbers, freeze the old log with `git mv`, write one current entry per ID,
and have a test reject unknown IDs. The problems sit in the extra machinery
around that core and in details the plan leaves to the implementer.

| Stage | Report | Blocker | Major | Nit |
| --- | --- | --- | --- | --- |
| 5 Initial zoom out | [zoom_out_report.md](zoom_out_report.md) | 0 | 4 | 7 |
| 6 Comprehension | [comprehension_report.md](comprehension_report.md) | 4 | 9 | 10 |
| 7 Critic | [critic_report.md](critic_report.md) | 1 | 12 | 12 |
| 8 Intermediate zoom out | [intermediate_zoom_out_report.md](intermediate_zoom_out_report.md) | 2 | 4 | 2 |
| 9 Implementation readiness | [implementation_readiness_report.md](implementation_readiness_report.md) | 1 | 11 | 13 |

After merging duplicates: **3 Blockers, 10 Majors, a set of Nits.** Three of
the items below reopen choices the owner already made; they are marked
**Owner decision**.

## 🔴 Blockers

### C1. Commit 5 ends with a failing test

`test_no_q_cites` is added in commit 5 and "now passes", but the Q cites in
`docs/null-sources.md` (lines 50, 86, 106, 109, 110) and `docs/comparison.md`
(5, 100, 111) are only rewritten in commit 6. Breaks D13 (every change ends
with pytest, ruff and mypy clean).

*   **Fix:** reorder so the tests come last. Rewriting cites does not need the
    new `decisions.md`, so: cleanup → `git mv` → current rules and index →
    every Q rewrite and explanation (code and docs together) → the cite test.
    This also fixes the wrong rollback claim (C10).

### C2. The cite test's scan list is contradictory and too broad

Technical Plan section 7 scans all of `docs/`; item 15 excludes
`docs/designs/`. This design and the briefs contain Q tokens and example IDs
(D35, D24.3), so the section 7 version can never pass. "Every README.md and
CLAUDE.md" has no root, so it would also scan `.venv/` and `.pytest_cache/`.

*   **Fix:** define the scan once, in section 7, as an include list of
    tracked files (`git ls-files`) under `document_extractor/`, `tests/`,
    `scripts/`, the named live docs (`docs/decisions.md`,
    `docs/decisions-index.md`, `docs/null-sources.md`, `docs/comparison.md`),
    the three READMEs, the three `CLAUDE.md` files and `pyproject.toml`.
    Everything else is out by default. Item 15 then points to section 7.

### C3. Sub-IDs (D24.n, D34.n) are used but never defined

The Q-to-D table has one row per D, so Q cites cannot be mapped to sub-IDs.
The sub-IDs are never listed; item 22 still says `D34.n`. Every paused D34
sub-ID also writes rules for unbuilt work into the current-rules file, and
item 22 cites one as a rule in force today.

*   **Owner decision** (reopens brief decision 2, "sub-IDs where needed"):
    *   **Drop sub-IDs.** Every Q maps to its parent D. D24 stays one entry
        with its rules as a short list; D34 is one `paused` entry linking to
        the line-items brief. Stage 8 says this alone removes about a third of
        the findings.
    *   **Keep sub-IDs** and list them in the design: each sub-ID, its title,
        and its Q range, before implementation starts.

## 🟡 Majors

### C4. Who owns the full current rule in an amendment chain

Reviewers say option B (every ID keeps its own current rule) does not say
whether an amended entry repeats the later change, so either the rule is
written twice or the reader still pieces it together. The claim that "the
IDs of a chain sit together" is false under the topic table: D9 is under
Schema, D20 and D22 under Scoring. The owner check's "fold table" belongs to
the rejected folding option. Stage 8 recommends switching to "oldest ID owns
the full rule".

*   **Owner decision** (reopens the choice of B on 2026-10-30):
    *   **Keep B, tightened:** each entry states only its own part, never the
        later change; "Changed by" is the only link; drop the "sit together"
        claim or move chain members into one section; replace the fold table
        with a list of chains and their IDs.
    *   **Switch to oldest owns:** the oldest ID holds the full current rule,
        later IDs become pointers, and cites to them move. This is option A,
        which you rejected for large entries and less specific cites.

### C5. Short versions of each rule can still drift

Up to five copies of each rule: Rule text, heading, index line, cite
explanation, README invariant. About 180 hand-written explanations are
checked by nothing, which is the reason the design gives for rejecting
Alternatives E and F. "Where needed" and "if opaque" leave the implementer
to decide which cites get explanations.

*   **Owner decision:**
    *   **Heading is the short form.** A cite explanation, where present, is
        the heading text, and the test checks it. Fewer words per cite, no
        drift.
    *   **Free-text explanations, risk accepted.** Keep them as now and record
        the drift in a Risks section, with the manual reread step from
        section 5.

### C6. The held-out prompt test is out of scope and too weak

No commit touches `INSTRUCTIONS`, so the leak test does not belong here.
Whole-value matching misses fragments such as "S.R.L.", the kind of leak D33
recorded. It does not say substring or whole word, or what happens with no
labels.

*   **Fix:** move it to the D34 work, written against the first prompt change,
    reusing the label helpers in `tests/test_samples.py`. Record the gap as
    accepted until then.

### C7. Parsing formats are not defined

The heading pattern, Status values, sub-ID headings and index-line format are
described by example only. The index file and the test must agree on them.
Status lists also disagree: `paused` is missing from the Goals, `superseded`
has no use case under option B, and sub-IDs have no Status line.

*   **Fix:** one short "Formats" subsection in section 2: the heading pattern
    `### D<n>. <title>`, the closed set of statuses (`active`, `paused`,
    `retired`), and the index line `D<n>  <status>  <title>`. Drop
    `superseded` unless C4 switches option.

### C8. Stale text: values missing, some sites missed

The plan names stale facts but not their replacements (the IEB count, the D34
Q range, the new null-sources numbers). Missed sites:
`tests/test_llm_extractor.py:36`, `document_extractor/README.md:52-54`,
`tests/test_samples.py:49-50`. Item 17 quotes the package README as "point
here"; it says "point there". Item 12's "D34 Q range" fix would put Q tokens
into the new `decisions.md`, and "D35 onward" would fail the cite test.

*   **Fix:** give each stale item its correct value in the plan; add the three
    missed sites; write the D34 heading without Q numbers; write "new
    decisions get the next free number" instead of "D35".

### C9. The Q-to-D rewrite has no rules for edge cases

Many cites already read like "(D25, Q32)", so a plain rewrite gives
"(D25, D25)". Nothing covers gaps or overlaps in the Q ranges. The Q-cite
count is given as about 31, about 34 and 37 in different places.

*   **Fix:** rule: drop a Q cite whose D is already cited on the same line.
    List the full Q-to-D table in the design (it is small), state the count
    once as 37, and remove per-file counts from the plan.

### C10. The rollback claim is wrong

Reverting single commits causes conflicts or failing tests, the opposite of
what the Non-Functional Requirements section says.

*   **Fix:** replace it with "roll back by reverting the branch, or the
    commits in reverse order". C1's reorder makes this true.

### C11. Missing Risks section; terms a new reader cannot follow

The feature-spec standard requires Risks and Mitigations. The Problem
section uses the bare D numbers it calls useless. Undefined terms: owner,
grilling questions, N IDs, held-out, IEB, Sinabis, the drift report (which
this design deletes), the YAGNI reviewer, TypeSafe, EGM.

*   **Fix:** add a Risks section (folding errors, explanation drift, D34
    restart); explain every D number in the Problem section; a short glossary
    or one-line definitions at first use.

### C12. Housekeeping and untracked files

The cleanup bundles unrelated housekeeping. The five review reports in the
repo root are not covered, and the plan never says to stage only named
paths.

*   **Fix:** say each commit stages named paths only (never `git add -A`);
    list the review reports (delete after the design is updated, or move to
    `docs/designs/reviews/`).

### C13. The "behaviour unchanged" check cannot show what it claims

`git diff --stat` cannot show changes are comment-only, and it would also
flag the new README and CLAUDE.md prose.

*   **Fix:** compare the code with comments and docstrings stripped, for
    example by checking that `ast.dump` of each changed module is unchanged
    between `main` and the branch, or state that the check is a manual diff
    read.

## 🟢 Nits

*   Index length given as 40 to 60 lines in one place and about 50 in
    another.
*   Alternative A is set up to lose; the reason for a separate history file
    (stable evidence links) is never stated.
*   Alternative D does not follow the template of the others.
*   The diagram has gaps; the "Open problems" table row has no IDs.
*   The `CLAUDE.md` chat rule cannot be enforced; say so.
*   History headings will also turn up in searches for a D number.
*   The header date is 2026-10-29; the design was finished 2026-10-30.
*   The `httpx2` reason names only `test_jev.py`.
*   Finding the "D34 (paused)" cites later is not described (a search for
    `D34 (paused)` is enough; say so).

## What checks out

Every per-file Q and D count, every named line number, the stale comment at
`rules_extractor.py:313`, the N1 to N20 headings, the topic table covering D1
to D34 once each, and the commit 2 inputs (`httpx2` lock, `IDEA.md`, the
`.pyc`) match the repo.

## Suggested order of fixes

1.  Settle the three owner decisions: C3 (sub-IDs), C4 (who owns the rule),
    C5 (short form).
2.  C2 and C7: one scan definition and one formats subsection.
3.  C1 and C10: reorder the commits, test last, fix the rollback text.
4.  C6 and C12: move the held-out test out, deal with untracked files.
5.  C8, C9, C11, C13, then the Nits.

## Traceability

| Item | Stage 5 | Stage 6 | Stage 7 | Stage 8 | Stage 9 |
| --- | --- | --- | --- | --- | --- |
| C1 Commit 5 fails | | Blocker 1 | M9 | Reorder (Major) | Blocker |
| C2 Scan list | Nit (scope) | Blockers 2, 3 | B1 | Blocker 2 | Major (scan) |
| C3 Sub-IDs | Major 3 | Blocker 4 | M7 | Blocker 1 | Major (sub-IDs) |
| C4 Rule owner | Major 1 | Major (chains, fold table) | M5, M6, M10 | Major (owner) | |
| C5 Short forms | Major 2, Nit (index) | | M2 | Major (copies) | Major (subjective) |
| C6 Held-out test | Major 4 | Major (leak test) | M8 | Major (split) | |
| C7 Formats | Nit (superseded) | Major (formats, statuses) | M4 | Blocker 2 | Major (formats) |
| C8 Stale text | | Major (values) | | | Majors (values, missed sites, item 12) |
| C9 Q rewrite | Nit (counts) | Major (gaps), Nit (counts) | M3 | Nit (counts) | Major (duplicates) |
| C10 Rollback | Nit | Major | M9 | Reorder (Major) | |
| C11 Risks, terms | | Major (terms) | M1, M11, M12 | Nit (straw man) | |
| C12 Housekeeping | Nit | Nit | Nit | Major (split) | Major (untracked) |
| C13 Behaviour check | | Nit | | | Major |
