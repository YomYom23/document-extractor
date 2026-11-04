# Goldfish Review Report: Zoom Out, Round 2

**Target:** `docs/designs/decision-cleanup.md` (lines 1-707)
**Stage:** 5, Initial Zoom Out Review (re-audit of the revised design)
**Reviewers:** `egm-zoom-out`, run as two separate instances (A and B)
**Standard:** `zoom-out-standard.md`

## Verdict

The design passes the zoom-out check. It goes after the root cause: old entries go out of date because later decisions never update them. Its fix is to write each rule once, as it stands today, and to say at each cite what the rule means. It keeps D numbers and uses the pytest habit the project already has. Both reviewers found it in proportion to the problem.

Findings: **0 Blockers, 1 Major, 8 Nits.**

### Claims checked against the repo (all confirmed)

- There are 37 Q cites across 14 live files, and the section 6 table covers each one.
- No scanned file cites a D above D34 or an N above N20, so the cite test can pass on its first run.
- `docs/null-sources.md` has exactly 20 N headings.
- `pyproject.toml:14` cites D28.
- `tests/test_jev.py` imports `httpx2` directly.
- `rules_extractor.py:313` reads `line_items=None,  # not extracted yet (D24)`.
- Only `README.md:22` and `document_extractor/README.md:10` link to `docs/decisions.md`.

## Prioritized Findings (Blockers -> Major -> Nits)

### 1. The `Changed by:` / `Changes:` back-links are never checked - Severity: Major
* **Reviewer Lens:** `egm-zoom-out` (B)
* **Affected Scope:** Lines 141-145 (CUJ 3), 256-266, 305-321, 382-390 (test checks)
* **Discrepancy Description:** The original bug was a later decision changing an earlier one while the earlier entry said nothing (Problem item 1; D22, D28 and D30). The design fixes this with a pair of links, `Changes:` on the new entry and `Changed by:` on the old one. Line 265 says these links are "the only place the relationship is written." But none of the four test checks in section 7 looks at them. CUJ 3 and section 5 rely on the owner remembering to add the back-link, and remembering is the habit that already failed. If someone adds `Changes: D12` and forgets `Changed by:` on D12, the out-of-date-entry problem comes back and no test catches it. Meanwhile the test does check smaller things, such as whether the index matches the headings.
* **Rationale & Recommendation:** Add a fifth check to `tests/test_decision_cites.py`. If entry Dy has `**Changes:** Dx`, then Dx's `**Changed by:**` must list Dy, and the other way round. It parses the same file the test already reads and needs no new format. If the owner decides not to add the check, list the risk under Risks and Mitigations ("a back-link is forgotten and the old entry reads as current again") so it is a known, accepted gap.

### 2. The full Q-to-D table repeats the headings and gets D34's range wrong - Severity: Nit
* **Reviewer Lens:** `egm-zoom-out` (A, B)
* **Affected Scope:** Lines 339-344 (and the matching step at 615-616)
* **Discrepancy Description:** Each D24-D34 heading in the old log already names its Q range, and the whole old log becomes the history file. So the full table restates headings that sit further down the same file. Only the 7-row table of live cites (lines 329-337) is needed for the migration. The table also has a small error. Line 339 says the ranges come "from its heading", but the D34 heading (`decisions.md:377`) says Q88 to Q98, while the table gives Q88 to Q105. Q99-Q105 appear only in the D34 body.
* **Rationale & Recommendation:** Keep only the 7-row live table and add one sentence: "Each heading below names the Q numbers it settled; Q1-Q23 were never recorded." If the full table stays, say why it is worth having (for example, decoding Q numbers in old commit messages), and change the D34 source wording to "heading and body".

### 3. Committing six review reports goes against the cleanup goal and adds noise to searches - Severity: Nit
* **Reviewer Lens:** `egm-zoom-out` (A, B)
* **Affected Scope:** Lines 402-404, 593-599; compare lines 567-570
* **Discrepancy Description:** The drift report is deleted because "all its findings are fixed and nothing links to it." Six review reports about earlier drafts, whose findings are also fixed, are kept for good, and line 599 sends every future report to the same folder. They cite things that will not exist (D35, D24.3, old line numbers). The test does not scan them, so it is safe. But the manual `git grep -n "D12\b"` step in section 5, and any reader searching for a D number, will hit them. They will also go stale, which is the problem this design sets out to remove.
* **Rationale & Recommendation:** Use one rule for both cases. Either do not commit the reports (keep the design and the briefs), or commit only `consolidated_review_report.md` and drop line 599. If they stay, narrow the section 5 search, for example `git grep -n "D12\b" -- ':!docs/designs'`.

### 4. Commit 1 edits a file that is frozen two commits later - Severity: Nit
* **Reviewer Lens:** `egm-zoom-out` (A, B)
* **Affected Scope:** Lines 542-551
* **Discrepancy Description:** Commit 1 adds a "paused" line to the old log, and commit 3 freezes that log as history. The paused status is already recorded in the new D34 entry (`Status: paused`, line 247) and in the index. This costs one commit and one owner go-ahead for information that is already recorded.
* **Rationale & Recommendation:** Drop commit 1. Put the pause date and label progress (25 IEB, 20 Sinabis) in the new D34 entry's summary, or in the frozen note added with the history file. Otherwise, say why history needs its own copy.

### 5. Commit 6 names helper functions - Severity: Nit
* **Reviewer Lens:** `egm-zoom-out` (A, B)
* **Affected Scope:** Lines 683-688
* **Discrepancy Description:** The design lists `decision_entries()`, `null_source_ids()`, `index_lines()` and `scanned_files()` and how each one parses. The standard flags helper-level detail as too low for a design. Section 7 already defines the contract that matters: the files scanned, the checks and the failure format.
* **Rationale & Recommendation:** Replace the list with "Implements section 7" and leave the internal structure to the implementer.

### 6. A goal protects links that do not exist yet - Severity: Nit
* **Reviewer Lens:** `egm-zoom-out` (A)
* **Affected Scope:** Lines 76-79
* **Discrepancy Description:** The goal says "Links from comparison.md to live-run evidence keep a fixed target there." `docs/comparison.md` has no such links today. The live-run mentions are in `null-sources.md`, and item 18 adds those links for the first time. The goal reads as if it protects links that already exist.
* **Rationale & Recommendation:** Reword it to: "Evidence links added from the new entries and from null-sources.md point at a fixed target in the history file."

### 7. The entry shape has more required fields than it needs - Severity: Nit
* **Reviewer Lens:** `egm-zoom-out` (B)
* **Affected Scope:** Lines 225-238
* **Discrepancy Description:** All 34 entries carry Rule, Status, Scope, Why, Rejected and Evidence. `Rejected` repeats the history entry that `Evidence` already links to, and `Scope` often repeats the title. Every extra field is more to write in commit 4, more for the owner to check, and more text that can go stale.
* **Rationale & Recommendation:** Make `Rejected` optional, used only where a rejected option is likely to come up again. Consider dropping `Scope` when the title already names the module.

### 8. Grouping by topic is extra upkeep - Severity: Nit
* **Reviewer Lens:** `egm-zoom-out` (B). Instance A reviewed the grouping and accepted it.
* **Affected Scope:** Lines 197-206, 220-223
* **Discrepancy Description:** Each new D has to be given a topic, and the file is no longer in number order. The index already lists entries by number, so topic headings add little at 34 entries.
* **Rationale & Recommendation:** Either order entries by number, or add one line saying why topics are worth the upkeep. This is optional, since the reviewers disagreed.

### 9. Smaller scope notes (N-number check, httpx2 fix) - Severity: Nit
* **Reviewer Lens:** `egm-zoom-out` (A)
* **Affected Scope:** Lines 81-82, 386-387 (N check); 97-98, 397-401, 581-585 (httpx2)
* **Discrepancy Description:** The problem statement never reports N cites as broken, so the N check is mild extra scope, though it costs little. The `httpx2` dev dependency fix is correct and disclosed in Non-Goals, but it has nothing to do with decisions.
* **Rationale & Recommendation:** Add one sentence on why the N check is there (N cites sit beside D cites in the code and can have the same typos). Optionally put the `httpx2` fix in its own commit so reverting the decision work cannot undo it. Instance B accepted both as they are.

## Checked and accepted (no action)

- Keeping D numbers rather than names (Alternative B), and using a test rather than a grep (Alternative G).
- The separate `decisions-index.md`. It is justified because an `@` import loads the whole file.
- The "Open problems" section, the `D34 (paused)` marker, the include-list scan of tracked files, the one-off AST check that code behaviour is unchanged, the rollback note, the rule against `git add -A`, and the non-goal on held-out data.
