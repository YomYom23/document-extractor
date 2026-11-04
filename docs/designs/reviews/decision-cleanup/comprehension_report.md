# Goldfish Review Report - Stage 6 (Comprehension Test)

**Target:** `docs/designs/decision-cleanup.md` (FeatureRange lines 1-436, DetailedRange lines 437-692)
**Standard:** re-implementation-standard.md
**Reviewers:** `egm-comprehension`, two separate runs (A and B), with duplicate findings merged.

Summary: 4 Blockers, 9 Majors and 10 Nits.

## What the reviewers understood

Both readers understood the plan the same way:

- D34 (line items) is paused.
- Some unused files are deleted, and the untracked docs are committed.
- The current `docs/decisions.md` is moved with `git mv` to `docs/decisions-history.md` and frozen. A note at its top and a Q-to-D table are added.
- A new `docs/decisions.md` is written. It has one entry per D ID showing the rule as it stands today, grouped by topic, with sub-IDs for D24 and D34.
- A new `docs/decisions-index.md` is imported by `CLAUDE.md`.
- Every Q cite becomes a D cite, and bare D cites get a short explanation.
- `tests/test_decision_cites.py` and a held-out leak test are added.
- The work is done in six commits. Runtime behaviour does not change.

The high-level picture is clear. The gaps are in the exact rules an implementer needs to rebuild the work.

## Prioritized Findings (Blockers -> Major -> Nits)

### 1. `test_no_q_cites` cannot pass in commit 5 - Severity: Blocker
* **Reviewer Lens:** `egm-comprehension` (A; checked by the synthesizer)
* **Affected Scope:** Lines 304-312, 573-574, 645-647, 651-661
* **Finding:** Item 27 adds `test_no_q_cites` in commit 5 and says it "now passes". The test scans `docs/`. But `docs/null-sources.md` (5 Q cites) and `docs/comparison.md` (3 Q cites) are only rewritten in commit 6, items 28-29. So commit 5 ends with a failing test. That breaks the rule that every commit ends clean (line 73, line 439, and D13).
* **Suggested fix:** Either move the Q rewrites in `null-sources.md` and `comparison.md` into commit 5, or add `test_no_q_cites` in commit 6. Then correct line 647.

### 2. The two ranges give different scan scopes for the cite test - Severity: Blocker
* **Reviewer Lens:** `egm-comprehension` (A, B)
* **Affected Scope:** Lines 304-308 vs 563-566
* **Finding:** The two sections list different files to scan:
  * Section 7 scans all of `docs/` except `decisions-history.md`.
  * Item 15 also leaves out `docs/designs/`, limits the scan to `*.py` and `*.md`, and never scans `line-drafts/` or `__pycache__`.

  This design file and the two moved briefs contain Q tokens (Q24, Q47, Q99-Q105) and IDs that do not exist yet (D35, D24.3). If the Section 7 scope is followed, the test can never pass.
* **Suggested fix:** Use one scan list, the same in both places. Say why `docs/designs/` is left out: design records are historical, like the history file.

### 3. "Every README.md and CLAUDE.md" has no root or exclusions - Severity: Blocker
* **Reviewer Lens:** `egm-comprehension` (B)
* **Affected Scope:** Lines 307, 565
* **Finding:** The repo has a `.venv/`. A recursive search for `README.md` would pick up third-party package READMEs, which are full of tokens like `D2` and `N1`. The test would fail for reasons that have nothing to do with this project.
* **Suggested fix:** Either list the exact files (root, `document_extractor/` and `scripts/` READMEs and CLAUDE.md files), or say "recursive from the repo root, skipping `.venv`, `.git`, `samples`, `line-drafts` and `__pycache__`".

### 4. Q cites cannot be mapped to sub-IDs, and the sub-IDs are never listed - Severity: Blocker
* **Reviewer Lens:** `egm-comprehension` (A, B)
* **Affected Scope:** Lines 170-173, 217-225, 292, 523-539, 596, 620-621
* **Finding:** The design says to replace each Q with "its D (or D sub-ID)" from the Q-to-D table, but the mapping cannot be done from the document:
  * The table has one row per D and no sub-ID column.
  * The table is written into the frozen history file.
  * The sub-IDs for D24 and D34 are never listed. Only D24.3 appears, as an example.
  * It is not said which points of the line-items brief count as "settled".
  * Item 22 uses a placeholder, `D34.n`.

  For example, there is no way to tell which D24.n replaces Q26 in `rules_extractor.py:189`. Two implementers would produce different files and cites.
* **Suggested fix:** Pick one of two options:
  * State that Q cites always map to the parent D.
  * List the planned sub-IDs with their heading text, and give a Q-to-sub-ID mapping. Keep it in `decisions.md` if the history file must stay frozen.

  Replace `D34.n` with the real ID. Alternatively, state plainly that the entry text is written at implementation time and approved by the owner.

### 5. Heading and index formats cannot be parsed reliably - Severity: Major
* **Reviewer Lens:** `egm-comprehension` (A, B)
* **Affected Scope:** Lines 199-207, 254-266, 304-305, 313-315, 544-545, 559-562, 569-570
* **Finding:** Several details the test depends on are not defined:
  * Which token in a heading is the ID. A heading that also mentions another ID, such as "(amends D9)", would register D9 by mistake.
  * Whether "heading text copied exactly" includes the "D11." prefix and its period.
  * How Status is read out of `**Status:** active · **Scope:** ...`.
  * How fields are separated in an index line. A status can contain spaces ("superseded by D20"), so splitting on spaces does not work.
  * Whether `####` sub-ID headings have their own Status line.
  * Whether the "Open problems" and topic headings count.
  * The heading pattern for N IDs in `null-sources.md`.
* **Suggested fix:** Give an exact grammar, for example:
  * Heading: `^#{3,4} (D\d+(?:\.\d+)?)\. (.+)$`. The ID is group 1 and the text is group 2. Other tokens in a heading are ignored.
  * Status: the text after `**Status:** `, up to ` · ` or the end of the line.
  * Index line: a fixed delimiter, such as a tab or two or more spaces, giving exactly three fields.
  * N headings: `^### (N\d+)\.`.

### 6. The amendment chains are never listed, and the "fold table" contradicts the chosen approach - Severity: Major
* **Reviewer Lens:** `egm-comprehension` (B; A noted the late definition)
* **Affected Scope:** Lines 27-32, 227-250, 686-687
* **Finding:** The document names the decisions that amend others (D20, D25, D26, D31-D34, plus D22, D28 and D30, which amend without saying so). It also names the decisions that were amended (D9, D10, D12, D16, D19). It never says which amends which, except for D9. So an implementer would have to rebuild the Changes / Changed by links from the history, which is a design choice the document should make.

  The owner check also asks for a "fold table" giving "the new entry they became". Folding is the approach Section 3 rejects. It is also unclear how the owner reviews a commit message "before the commit is made", and whether "the commit" means commit 4.
* **Suggested fix:**
  * Add a table listing each amending decision and the IDs it changes.
  * Rename "fold table" to "chain table": each chain, its Changes / Changed by links, and the rewritten Rule.
  * Say that the owner reviews it before commit 4, and where they see it.

### 7. D34 sub-ID status is inconsistent - Severity: Major
* **Reviewer Lens:** `egm-comprehension` (B)
* **Affected Scope:** Lines 220, 535, 620-623
* **Finding:** All sub-IDs from the line-items brief get status `paused`. But item 22 cites a D34 sub-ID for "the rules extractor stays at null for line items" as a rule in force today, and calls it stale text rather than a paused cite.
* **Suggested fix:** Say which D34 sub-IDs are `active` (for example the null rule) and which are `paused`.

### 8. The rollback statement looks wrong - Severity: Major
* **Reviewer Lens:** `egm-comprehension` (A, B)
* **Affected Scope:** Lines 430-433
* **Finding:** The statement does not match what `git revert` would do:
  * "Reverting commit 3 without commit 4 leaves no `docs/decisions.md`" is backwards. Reverting commit 3 restores the old file, and after commit 4 it would conflict with the new file.
  * Reverting commit 4 removes the cite test, so "the cite test would fail" cannot happen.
  * Reverting commit 4 after commit 5 conflicts, because commit 5 edits `test_decision_cites.py`.
* **Suggested fix:** State which reverts are safe, which must be done together (for example 3+4, or 4+5), and what each one leaves behind.

### 9. N IDs are used before they are defined - Severity: Major
* **Reviewer Lens:** `egm-comprehension` (A, B)
* **Affected Scope:** Lines 63, 148, 267, 311, 551, 561-562
* **Finding:** "D or N ID" appears in the Goals with no explanation. Only line 311 hints that N IDs are headings in `null-sources.md`, and the reader is never told what that file is.
* **Suggested fix:** Add one sentence to the Overview, for example: "N1-N20 are the entries in `docs/null-sources.md`, the list of reasons a field can come back null (D27)."

### 10. The stale facts are named but their correct values are not - Severity: Major
* **Reviewer Lens:** `egm-comprehension` (A, B)
* **Affected Scope:** Lines 33-38, 334-337, 535-537, 653-655
* **Finding:** Several corrections are named without the value to correct them to:
  * "The 25 vs 26 IEB count": which number is right?
  * "The D34 Q range": what should it say?
  * D21 to D23's "pending your questions".
  * "The current numbers" for `null-sources.md`.
  * "`test_samples.py` is checked for the same stale counts".

  An implementer cannot write the corrected text from the document.
* **Suggested fix:** Give the correct value for each, or name its source, such as a section of `comparison.md` or the number of files in a sample folder.

### 11. The held-out leak test is not fully specified - Severity: Major
* **Reviewer Lens:** `egm-comprehension` (A, B)
* **Affected Scope:** Lines 320-324, 579-583
* **Finding:** Several details are missing:
  * Whether "compared casefolded" means a substring match or a whole-word match. A short invoice number such as "1" would match ordinary prompt text.
  * Where `INSTRUCTIONS` lives (`document_extractor/llm_extractor.py:29`).
  * That `vendor_name` and `invoice_number` are top-level keys of the label JSON.
  * What happens when `samples/heldout/` has no labels.
* **Suggested fix:** Specify:
  * substring or whole word, with a minimum length if one is needed;
  * the import path for `INSTRUCTIONS`;
  * the JSON keys;
  * the behaviour when the folder is empty (fail, or skip).

### 12. The Q-to-D table rule is incomplete - Severity: Major
* **Reviewer Lens:** `egm-comprehension` (B)
* **Affected Scope:** Lines 171-173, 523-526
* **Finding:** The table is built "from Q ranges in headings and inline (Qn) marks". The document does not say what to do with a Q that appears in no range, or in two.
* **Suggested fix:** Require every Q cited in the scanned files to appear in exactly one row, and say how gaps and overlaps are resolved.

### 13. Project terms are not defined - Severity: Major
* **Reviewer Lens:** `egm-comprehension` (A, B)
* **Affected Scope:** First uses at lines 18-19, 34-43, 59, 65, 220, 412, 449-450, 688, 692
* **Finding:** These terms are used with no definition or link:
  * "the owner"
  * "grilling questions"
  * "the drift report" (it can only be identified from line 328)
  * "held-out", and the difference between the dev and held-out sets
  * the "r_" invoices
  * IEB and Sinabis
  * "live-run log" and "frozen-commit hash"
  * "the line-items brief" (the file is only named in item 9)
  * "the YAGNI reviewer"
  * Jev, TypeSafe and EGM
  * the CLAUDE.md `@`-import mechanism
* **Suggested fix:** Add a short glossary, or a one-clause definition or link at each first use.

### 14. Q cite counts disagree - Severity: Nit
* **Reviewer Lens:** `egm-comprehension` (A, B)
* **Affected Scope:** Lines 39, 347, 603-639
* **Finding:** Line 39 says "about 31" and line 347 says "about 34". The per-file counts in the DetailedRange add up to 37, which matches a grep. It is also not said whether the counts are lines or tokens: `test_cli.py` has 8 Q lines but 10 Q tokens.
* **Suggested fix:** Use one number everywhere and say whether it counts lines or tokens.

### 15. The httpx2 reason names only one test file - Severity: Nit
* **Reviewer Lens:** `egm-comprehension` (A, B)
* **Affected Scope:** Lines 330-331, 488-489
* **Finding:** Only `tests/test_jev.py` is named, but `tests/test_llm_extractor.py` also imports `httpx2`.
* **Suggested fix:** Name both files.

### 16. The brief move and link updates are vague - Severity: Nit
* **Reviewer Lens:** `egm-comprehension` (A, B)
* **Affected Scope:** Lines 332, 501-504
* **Finding:** The FeatureRange only says the briefs are committed. The move into `docs/designs/` appears only in item 9, and "any link to them is updated" does not say which files link to them.
* **Suggested fix:** Mention the move in Section 8, and name the files that link to the briefs (or say none do).

### 17. One untracked file is not covered - Severity: Nit
* **Reviewer Lens:** `egm-comprehension` (A)
* **Affected Scope:** Section 8 and commit 2 (no single line)
* **Finding:** `zoom_out_report.md` is untracked at the repo root and contains a Q token. The design does not say whether to keep, commit or delete it.
* **Suggested fix:** Say which.

### 18. The Status values disagree, and the entry template is incomplete - Severity: Nit
* **Reviewer Lens:** `egm-comprehension` (A)
* **Affected Scope:** Line 57 vs line 210; lines 199-207 vs 233-237
* **Finding:** The Goals list three status values, but Section 2 adds a fourth, `paused`. The entry template leaves out the Changes / Changed by lines and does not show where they go.
* **Suggested fix:** Make the two status lists the same, and add the Changes / Changed by lines to the template.

### 19. Token matching details are only in the DetailedRange - Severity: Nit
* **Reviewer Lens:** `egm-comprehension` (A, B)
* **Affected Scope:** Lines 310-312, 567-572
* **Finding:** The test names and regexes appear only in item 15. It is not said whether matching is case-sensitive; evidence anchors such as `#d11-...` are lowercase. It is also not said whether the test file's own docstrings and examples must avoid Q tokens.
* **Suggested fix:** Add one line to Section 7 saying matching is case-sensitive, and that the test file is scanned too.

### 20. Example IDs could leak into scanned files - Severity: Nit
* **Reviewer Lens:** `egm-comprehension` (B)
* **Affected Scope:** Line 283
* **Finding:** Wording like "the next ID (D35 onward)" is fine in this excluded design. If the same wording is copied into the opening lines of `decisions.md` or into a CLAUDE.md, the cite test fails.
* **Suggested fix:** Warn writers not to put example IDs in scanned files, or use a placeholder such as `Dx`.

### 21. The behaviour check uses the wrong command - Severity: Nit
* **Reviewer Lens:** `egm-comprehension` (B)
* **Affected Scope:** Lines 680-683
* **Finding:** `git diff --stat` only shows which files changed. It cannot show that the changes are comment-only.
* **Suggested fix:** Rely on reviewing the `-w` diff, or on a comparison of the code with comments stripped (by token or by syntax tree).

### 22. Finding the paused cites later is not described - Severity: Nit
* **Reviewer Lens:** `egm-comprehension` (B)
* **Affected Scope:** Lines 266-268, 296-298
* **Finding:** The `# D34 (paused): ...` cites are to get their real explanation when D34 lands, but the design does not say how to find them then.
* **Suggested fix:** Say they are found by searching for the string "D34 (paused)".

### 23. The owner check timing is ambiguous - Severity: Nit
* **Reviewer Lens:** `egm-comprehension` (B)
* **Affected Scope:** Lines 247-250, 686-687
* **Finding:** Section 3 says the owner reviews "before the commit is made". The Verification section says "before commit 4". They only agree if "the commit" means commit 4.
* **Suggested fix:** Say "before commit 4" in both places. This is covered by the fix in finding 6.
