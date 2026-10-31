# Consolidated review, round 2: decision-cleanup.md

*   **Target:** `docs/designs/decision-cleanup.md` (707 lines; feature spec
    1-535, implementation plan 536-707), revised after round 1
*   **Date:** 2026-10-30
*   **Mode:** consolidated, all five stages, no edits between stages. This is
    the one re-audit EGM allows; findings left open after it are recorded as
    accepted trade-offs.

## Verdict

Close, not ready. **No Blockers in any stage**, down from 3 in round 1. All
round-1 blockers are confirmed fixed: the test is last, the scan list is
defined once, and every Q has its D. What remains is in two groups:

*   **Three structural choices** (Stage 8) that, if changed, remove about 20
    findings at once and shorten the design. Two of them touch decisions the
    owner made, so they are owner decisions.
*   **Concrete gaps** in commits 4 and 5, where the implementer would still
    have to guess.

| Stage | Report | Blocker | Major | Nit |
| --- | --- | --- | --- | --- |
| 5 Initial zoom out | [zoom_out_report_r2.md](zoom_out_report_r2.md) | 0 | 1 | 8 |
| 6 Comprehension | [comprehension_report_r2.md](comprehension_report_r2.md) | 0 | 6 | 14 |
| 7 Critic | [critic_report_r2.md](critic_report_r2.md) | 0 | 5 | 22 |
| 8 Intermediate zoom out | [intermediate_zoom_out_report_r2.md](intermediate_zoom_out_report_r2.md) | 0 | 4 | 4 |
| 9 Implementation readiness | [implementation_readiness_report_r2.md](implementation_readiness_report_r2.md) | 0 | 12 | 19 |

After merging: **0 Blockers, 9 Majors (three of them owner decisions), and
Nits.**

## 🟡 Majors: owner decisions

### R1. Is D34 "paused" or "active, not built yet"?

D34's decisions are settled (Q88 to Q105) and 45 committed labels already
follow them. Only the building is paused. Marking the decision `paused`
forces a third status, the `D34 (paused)` cite form, a stub entry, commit 1
(which edits a file that commit 3 freezes, and whose text says both "paused"
and "in progress"), and an open question about whether a paused entry can
appear in `Changes:` / `Changed by:` (D34 already changes D9 and D12).

*   **Active, not built yet (Stage 8's recommendation).** D34 is a normal
    `active` entry with its rules, plus one line: "Not built yet; work paused
    on 2026-10-29." Statuses shrink to `active` and `retired`. Commit 1 is
    dropped. Cites say `D34: line items not extracted yet`.
*   **Keep paused (current design).** Then the design must say a paused entry
    takes part in chains, and fix commit 1's wording.

### R2. Can a later change still get its own linked D number?

Section 5 allows a rule change to get a new number with `Changes:` /
`Changed by:`. Nothing tests that both sides of a pair exist, and that is the
only place the link is written (Stage 5's one Major). The test for "new
number or edit in place" is also a judgement call, worded differently in CUJ
3 and section 5.

*   **Always edit in place after the migration (Stage 8).** New numbers only
    for new rules. Links exist only for the chains written during the
    migration, so they never grow.
*   **Keep both options and test the links.** Add a fifth check: every
    `Changes: Dx` has a matching `Changed by:` on Dx, and the reverse.

### R3. Topic sections, or number order?

Topic sections plus a separate Status line make the index check fragile (the
heading, status and index are in three places) and give a list of open
problems with no rule for what goes in it.

*   **Number order, status in the heading (Stage 8).** Heading
    `### D11. Missing is null, never guessed (active)`; the index is the list
    of headings copied exactly; check 4 compares them. No topic sections; the
    index shows the whole list in 34 lines.
*   **Keep topic sections.** Then define the index format exactly (title line,
    blank lines, how to split a line) and say what belongs in Open problems.

## 🟡 Majors: fixes

### R4. mypy fails today because of `line-drafts/`

Confirmed by running `uv run mypy .` on 2026-10-30: 5 errors, all in
`line-drafts/draft_ieb.py`. `pyproject.toml` has `strict = true` and no
exclude, and `line-drafts/` stays in the working tree. Every commit's "mypy
clean" rule fails until this is fixed.

*   **Fix:** add `line-drafts/` to `.gitignore` (it holds private and
    held-out renders, Stage 7 Major) and to `[tool.mypy] exclude` in the
    cleanup commit.

### R5. Content is listed item by item, so each round finds a missing row

Missed stale text this round: `docs/null-sources.md:26-27` (N3 "not
extracted yet"), `document_extractor/README.md:52`, `README.md:38`,
`llm_extractor.py:100` and `scoring.py:10` (no exact new text). The
null-sources replacement drops the separate source of the rules figures.

*   **Fix:** one rule instead of a growing list: before commit 5, run
    `git grep -n -i -E "not extracted yet|header[- ]only|in progress|Q[0-9]+"`
    over the scanned files and fix every hit. Keep the table as examples.

### R6. Where the new Rule text comes from

D21 to D23 say "state their settled rules", but history only has pending
recommendations. D13 and D17 are not said to end up active or retired. D22,
D28 and D30 change earlier entries, but which entries is never named.

*   **Fix:** a source rule: each Rule is the latest wording in history, with
    every later change applied, checked against the code. Where history only
    has a recommendation, the code is the source. List every chain pair in the
    design (D20→D9, D22→D20, D25→D24, D26→D24, D28→?, D30→D19, D31→D19,
    D32→D14 and D23, D33→D26, D34→D9 and D12; fill in from history while
    writing). The owner check covers every entry, not only chains.

### R7. The cite test cannot be shown to fail, and misses new files

No negative cases; it scans its own file (a literal "D42" in a test case
would fail it); plain `git ls-files` skips files not yet added.

*   **Fix:** use path globs over the include list instead of `git ls-files`
    (Stage 8), skip `tests/test_decision_cites.py` itself, and test the
    matching helpers on small strings in the test file, built so they hold no
    literal bad token.

### R8. Opaque cites still left to judgement

About 100 to 170 D cites; "opaque" decides which get explanations.

*   **Fix:** make it mechanical: a cite is opaque when the comment or
    docstring sentence holding it has no other words than the number,
    `decisions`, or other numbers. List the opaque ones in the plan (a
    `git grep` finds them).

### R9. Untracked files, round-2 reports and small factual errors

*   The round-2 reports are not in item 8. Arrows read like `git mv`, which
    fails on untracked files.
*   `b_` (InvoiceBenchmark) is a third public source; Terms says two.
*   `httpx2` is imported by two test files, not one.
*   "Q-to-D table" names two different tables.
*   The D34 Q range comes from its heading and body, not the heading alone.
*   The behaviour check compares against `main`, which can move.

*   **Fix:** commit only the two consolidated reports (round 1 and round 2)
    and delete the stage reports, or keep all; use plain moves for untracked
    files; correct the facts; call the tables "live Q table" and "full Q
    table"; compare against a fixed commit hash.

## 🟢 Nits worth fixing

*   Index length: about 34 lines, not about 50.
*   Make `Rejected` optional in the entry shape.
*   Drop helper function names from commit 6.
*   Alternative F's reason is only a date; give the reason.
*   The goal about `comparison.md` links refers to links that do not exist
    yet.
*   Define "chain" in Terms.

The remaining style Nits (path styles, cross-reference wording, placeholders
that vanish when rendered) are accepted as they are.

## What checks out

The 37 Q cites and their mapping, the topic table, the amendment headings,
every quoted stale line, the httpx2 lock version, the file removals and most
line numbers match the repo.

## Suggested order

1.  Owner decisions R1, R2, R3.
2.  R4 (mypy), since it blocks every commit.
3.  R5, R6, R7, R8.
4.  R9 and the Nits.
