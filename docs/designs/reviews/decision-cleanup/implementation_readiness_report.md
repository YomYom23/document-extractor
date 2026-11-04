# Goldfish Review Report: Stage 9, Implementation Readiness Test

**Target:** `docs/designs/decision-cleanup.md` (lines 437-692, Detailed Implementation Plan)
**Reviewers:** `egm-implementation-readiness`, `egm-codebase-details`, `egm-style`
**Standard:** `resources/document_standards/implementation-readiness-standard.md`

**Verdict: not ready.** There is 1 Blocker, 11 Major findings and 13 Nits. The Blocker is that commit 5 can't end with pytest passing. Most of the Major findings are places where the implementer would have to make a choice the plan should already have made (the Zero-Decision Rule).

## What checked out against the repo

Two reviewers checked these independently and found them correct:

- **Cite counts.** Every per-file Q and D count in items 18-31 matches the repo. This covers cli 6Q/13D, currency_resolver 3/9, llm_extractor 2/16, pdf_reader 1/7, rules_extractor 1/10, arithmetic/jev/schema/scoring/token_usage 2/2/4/5/1, the test-file Q counts 8/1/1/3/1/1/1, test_arithmetic_check 1D, live_currency_check 3D, scripts/README 2D, null-sources 5Q, and comparison.md Q on lines 5, 100 and 111.
- **Line references.** These are all where the plan says: `llm_extractor.py:100`, `rules_extractor.py:313`, the `scoring.py:10` `HEADER_FIELDS` comment, the `pyproject.toml:14` D28 comment, and `INSTRUCTIONS` at `llm_extractor.py:29`.
- **Commit 2 inputs.**
  - `IDEA.md` and the stale `.pyc` exist.
  - httpx2 2.13.1 is locked (`uv.lock:413-425`) and missing from the dev group (`pyproject.toml:27-32`).
  - Both README "in progress" strings exist, and so do both links to `decisions.md`.
- **Stale facts named in item 12 are real.**
  - IEB count: 26 at `decisions.md:380`, 25 at `:409`.
  - "pending your questions": `:102`, `:114`, `:124`.
  - `scripts.live_llm_check`: `:214`, `:237`.
- **Existing cites are valid.** No scanned file has a D token above D34 today, and every N cite names an existing heading. So `test_cited_decisions_exist` and `test_cited_null_sources_exist` can pass at commit 4.
- **The held-out prompt test can pass.** No held-out vendor_name or invoice_number appears in the current `INSTRUCTIONS`, so item 16's test can pass at commit 4.

---

## Prioritized Findings (Blockers -> Major -> Nits)

### 1. Commit 5 fails its own new test - Severity: Blocker
* **Reviewer Lens:** `egm-implementation-readiness`, `egm-codebase-details`
* **Affected Scope:** Lines 563-566, 573-574, 645-647, 649-661
* **Discrepancy Description:** Item 27 adds `test_no_q_cites` in commit 5 and says it "now passes". But item 15 has the test scan `docs/`, and the Q cites in `docs/null-sources.md` and `docs/comparison.md` aren't rewritten until commit 6 (items 28-29). So commit 5 ends with pytest failing, which breaks the rule that every commit ends clean (line 439-440).
  * `docs/null-sources.md:50, 86, 106, 109, 110` cite Q26, Q32 and Q47.
  * `docs/comparison.md:5, 100, 111` cite Q62, Q47 and Q62.
* **Rationale & Recommendation:** Do one of these:
  * Move the Q rewrites from items 28 and 29 into commit 5.
  * Or add `test_no_q_cites` in commit 6, after the docs are rewritten.

### 2. D24/D34 sub-IDs and the Q-to-sub-ID mapping are never defined - Severity: Major
* **Reviewer Lens:** `egm-implementation-readiness`, `egm-codebase-details`, `egm-style`
* **Affected Scope:** Lines 528-539 (item 12), 596, 620-622 (item 22)
* **Discrepancy Description:** Item 12 says "Sub-IDs for D24 and D34" but never lists them, their headings, or which Qs they absorb. Item 11's Q-to-D table has "one row per D", so it can't answer which Q maps to which sub-ID. Yet commit 5 rewrites Qs "to its D or sub-ID". Item 22 uses a literal placeholder, `# D34.n`. These cites would need a sub-ID choice:
  * `rules_extractor.py:189` "(D24, Q26)"
  * `docs/null-sources.md:50`
  * `tests/test_rules_extractor.py:57`
  * the D34 "rules stay at null" rule (`decisions.md:378`)
* **Rationale & Recommendation:** Add a table of every sub-ID with its exact heading, its status, the Qs it absorbs and the cites it replaces. Replace `D34.n` with the real ID. Or state that Q cites under D24 and D34 map to the parent ID.

### 3. The Q-to-D rewrite produces duplicate IDs - Severity: Major
* **Reviewer Lens:** `egm-codebase-details`
* **Affected Scope:** Lines 596, 601-647
* **Discrepancy Description:** Most Q cites sit next to their own D, for example "(D25, Q32)" or "(D29, Q59)". A plain rewrite gives "(D25, D25)", and the plan doesn't say what to do instead. Examples:
  * `currency_resolver.py:23, 38, 63`
  * `cli.py:271`
  * `tests/test_jev.py:84`
  * `tests/test_llm_extractor.py:237`
  * `tests/test_pdf_reader.py:168`
  * `pdf_reader.py:25`
  * `llm_extractor.py:20, 107`
  * `docs/null-sources.md:86, 106, 109`
* **Rationale & Recommendation:** State the rule: "If the cite already names the target D, delete the Q token. Otherwise replace it."

### 4. The parsing formats the test depends on are not specified - Severity: Major
* **Reviewer Lens:** `egm-implementation-readiness`, `egm-codebase-details`
* **Affected Scope:** Lines 555-572 (item 15)
* **Discrepancy Description:** `decision_ids()`, `null_source_ids()` and `test_index_matches_decisions` depend on formats the plan never defines:
  * which heading levels count;
  * whether the heading text includes the `D11. ` prefix;
  * how Status is read out of `**Status:** active · **Scope:** ...`;
  * how non-ID headings such as "Open problems" are skipped;
  * how an index line splits into fields, given that "superseded by D9" contains spaces.

  The index file and the test have to agree on all of these.
* **Rationale & Recommendation:** Give the exact grammar. For example:
  * heading: `^#{3,4} (D\d+(?:\.\d+)?)\. (.+)$`, with the heading text excluding the `Dn. ` prefix;
  * index line: `^(\S+)  (.+?)  (.+)$`, with exactly two spaces between fields;
  * status: `\*\*Status:\*\* ([^·]+?)\s*(·|$)`;
  * the same kind of rule for `### N1. ...` headings.

### 5. Item 12 can put tokens into the new decisions.md that item 15 rejects - Severity: Major
* **Reviewer Lens:** `egm-implementation-readiness`, `egm-codebase-details`
* **Affected Scope:** Lines 528-539
* **Discrepancy Description:** Two parts of item 12 conflict with the commit 4 tests:
  * Item 12 says the new file corrects "the D34 Q range". That would write Q tokens into a file that `test_no_q_cites` scans.
  * Technical Plan section 5 (line 283) has the opening lines state the change rule with "(D35 onward)". D35 has no heading, so `test_cited_decisions_exist` would fail in commit 4.
* **Rationale & Recommendation:**
  * Say that the Q-range correction (Q88 to Q105) goes only into the history file's Q-to-D table.
  * Say that the new `decisions.md` contains no Q tokens.
  * Give the opening lines word for word, using "the next unused D number" instead of a literal unassigned ID.

### 6. Stale facts are named but the correct values are not given - Severity: Major
* **Reviewer Lens:** `egm-style`, `egm-implementation-readiness`
* **Affected Scope:** Lines 535-538
* **Discrepancy Description:** The plan names the stale facts but not what replaces them:
  * "25 vs 26 IEB count" doesn't say which number is right.
  * "the D34 Q range" doesn't give the range.
  * "pending your questions" doesn't say what replaces it.
* **Rationale & Recommendation:** Write each correction out, with the file it goes into. For example:
  * "The IEB count is 25 (commit cedda93)."
  * "D34 covers Q88 to Q105 (history Q-to-D table only)."
  * "D21 to D23 drop 'pending your questions'."
  * "D26's run command for the deleted script is removed."

### 7. The null-sources "current numbers" are undefined - Severity: Major
* **Reviewer Lens:** all three
* **Affected Scope:** Lines 651-656 (item 28)
* **Discrepancy Description:** The plan doesn't say which numbers to use, or which run or commit they come from. Every N entry's "Dev cost" was measured on the original 9 dev invoices (`docs/null-sources.md:8-9`). If only the opening line changes, those figures no longer match it. Today dev has 36 public plus 2 private invoices, and held-out was run on 2026-10-19 (`decisions.md:266-277`).
* **Rationale & Recommendation:** Give the exact replacement sentence for lines 8-9. For example: "Dev cost figures are measured on the 9 original dev invoices. Held-out was first run on 2026-10-19; see comparison.md." Also say whether the per-N figures are re-measured.

### 8. Some D34-affected and stale "header only" text is missed or misquoted - Severity: Major
* **Reviewer Lens:** `egm-implementation-readiness`, `egm-codebase-details`
* **Affected Scope:** Lines 456-466, 585-592, 611-635 (items 3, 17, 20, 23, 24)
* **Discrepancy Description:**
  * **Not listed as D34-affected.** Only `llm_extractor.py:100` and `scoring.py`'s `HEADER_FIELDS` are named. These lines are not:
    * `tests/test_llm_extractor.py:36` ("header fields only (D26)");
    * `document_extractor/README.md:52-54` ("not extracted yet");
    * `docs/null-sources.md:27` (N3, "not extracted yet").
  * **Stale comment.** `tests/test_samples.py:49-50` says labels "are header-only (line_items null)". All 58 public labels now have `line_items`.
  * **Misquote.** Item 17 quotes "point here", but `document_extractor/README.md:10-11` says "point there".
  * **Unclear.** The plan doesn't say whether `D34 (paused)` replaces the existing D26/D12 cite or is added next to it. Section 3 says "no D cite moves".
* **Rationale & Recommendation:** List every D34-affected line with its exact new comment. Add the test_samples comment fix. Quote both README strings exactly.

### 9. Scanned-file list picks up venv and tool-cache READMEs - Severity: Major
* **Reviewer Lens:** `egm-implementation-readiness` (Major), `egm-codebase-details` (Nit)
* **Affected Scope:** Lines 563-566
* **Discrepancy Description:** "every `README.md` and `CLAUDE.md`" also matches `.pytest_cache/README.md` and several READMEs under `.venv/Lib/site-packages/`. Whether the test passes would then depend on third-party text and on the local environment. None of these files holds a matching token today, so this is a latent risk rather than a current failure. The reviewers disagreed on severity; it is kept at Major because the outcome depends on the environment.
* **Rationale & Recommendation:** Name the six files explicitly (the three READMEs and the three CLAUDE.md files), or build the list from `git ls-files`.

### 10. Behaviour-unchanged check can't show what it claims - Severity: Major
* **Reviewer Lens:** all three
* **Affected Scope:** Lines 680-683
* **Discrepancy Description:** The check has two problems:
  * `git diff main --stat` shows only file names and line counts, so it can't show that the changes are comment-only.
  * Scoping it to `document_extractor` also picks up `document_extractor/README.md` and `CLAUDE.md`, which are prose added in commit 2. So the check can't pass as written.
* **Rationale & Recommendation:** Use `git diff main -- 'document_extractor/*.py' 'scripts/*.py' pyproject.toml` and check every changed line. Optionally make it mechanical, for example with `git diff -U0` and checking that every changed line is a comment.

### 11. Untracked root reports and staging method not addressed - Severity: Major
* **Reviewer Lens:** `egm-implementation-readiness` (Major), `egm-codebase-details` (Nit)
* **Affected Scope:** Lines 454-506 (commit 2)
* **Discrepancy Description:** `comprehension_report.md`, `critic_report.md`, `intermediate_zoom_out_report.md` and `zoom_out_report.md` are untracked at the repo root, and the plan says nothing about them. `line-drafts/` is excluded only through `.git/info/exclude`, not `.gitignore`. A careless `git add .` would commit the reports.
* **Rationale & Recommendation:** Decide what happens to each report: delete it, or move it to `docs/designs/`. State that each commit stages only the paths it names.

### 12. Subjective tests decide which cites get explanations - Severity: Major
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** Lines 627-628, 633-635, 639, 643, 669-672
* **Discrepancy Description:** The plan uses "where needed", "if opaque", "it already reads well" and "if they are opaque". These are judgments, so two implementers would edit different cites. Line 596-597 already gives an objective test.
* **Rationale & Recommendation:** Use "a cite whose number is its whole content" everywhere. For item 26, quote the current comment and write "No change".

### 13. "Comments only" heading is false for commit 5; test list contradicts itself - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** Lines 567-574, 594-599
* **Discrepancy Description:** Two contradictions:
  * Line 569 lists `test_no_q_cites` among the tests created in commit 4, but line 574 says it's added in commit 5.
  * Commit 5's heading says "(comments only)", but item 27 adds a test function in that commit.
* **Rationale & Recommendation:**
  * Remove `test_no_q_cites` from line 569.
  * Change the claim to "In `document_extractor/` and `scripts/`, only comments and docstrings change."
  * Rename the heading to match whatever finding 1 decides.

### 14. Item 8/9 heading says "Add" but files are moved; links claim - Severity: Nit
* **Reviewer Lens:** `egm-style`, `egm-implementation-readiness`
* **Affected Scope:** Lines 498-506
* **Discrepancy Description:** The files are moved and renamed, but the heading says "(Add)" and the old-to-new mapping is only implied. "Any link to them is updated" has no targets, because no tracked file links to `concepts_brief*.md`.
* **Rationale & Recommendation:** Write "`concepts_brief.md` -> `docs/designs/decision-cleanup-brief.md` (Move)" and do the same for the line-items brief. Say "no links exist".

### 15. Two different exclusion lists for the scan - Severity: Nit
* **Reviewer Lens:** all three
* **Affected Scope:** Line 565 vs Technical Plan section 7 (lines 306-308)
* **Discrepancy Description:** Item 15 excludes `docs/designs/`, but section 7 doesn't. The design and the moved briefs contain Q tokens, so item 15's list is the right one.
* **Rationale & Recommendation:** Change section 7 to match item 15.

### 16. httpx2 is imported by two tests, and no command is given - Severity: Nit
* **Reviewer Lens:** `egm-implementation-readiness`, `egm-codebase-details`
* **Affected Scope:** Lines 485-491
* **Discrepancy Description:** `tests/test_llm_extractor.py:5` also imports httpx2, not just `tests/test_jev.py:9`.
* **Rationale & Recommendation:** Name both files. Give the command: `uv add --dev "httpx2>=2.13.1"`.

### 17. Held-out test details and helper reuse - Severity: Nit
* **Reviewer Lens:** `egm-implementation-readiness`, `egm-codebase-details`
* **Affected Scope:** Lines 576-583
* **Discrepancy Description:** The plan doesn't say how paths are anchored, or whether "appear in" means substring. It also restates the public-plus-private directory logic that already exists in `set_directories` (`tests/test_samples.py:15-16`) and in `sample_directories` (`document_extractor/cli.py:44-53`).
* **Rationale & Recommendation:** Reuse one of the existing helpers. State substring matching on casefolded text.

### 18. Fixed line number and placeholder in commit 5 - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** Lines 611, 620-621
* **Discrepancy Description:** "line 100" moves as comments are added earlier in the same file. `D34.n` is a placeholder (see finding 2).
* **Rationale & Recommendation:** Anchor the edit to the code ("the `line_items=None` argument in the `Invoice(...)` call"), not to a line number.

### 19. Fold table contradicts section 3 - Severity: Nit
* **Reviewer Lens:** `egm-implementation-readiness`, `egm-style`
* **Affected Scope:** Lines 686-687
* **Discrepancy Description:** Section 3 chose "every ID keeps its own entry", so there is nothing to fold. The table at 686-687 is also in a commit message that doesn't exist yet.
* **Rationale & Recommendation:** Redefine it as a chain table (ID, Changes, Changed by, current Rule) in the draft commit message.

### 20. Item 31 check is meaningless - Severity: Nit
* **Reviewer Lens:** `egm-implementation-readiness`, `egm-style`
* **Affected Scope:** Lines 669-672
* **Discrepancy Description:** Item 31 says "Checked against the new D numbers", but D numbers don't change.
* **Rationale & Recommendation:** State a concrete check, or drop the item.

### 21. Commit 1 status line is inaccurate and vague - Severity: Nit
* **Reviewer Lens:** `egm-codebase-details`, `egm-style`
* **Affected Scope:** Lines 445-452
* **Discrepancy Description:** All 58 public labels already have line items, including the 4 `b_` labels. Only the 9 git-ignored `r_` labels remain, and those are never committed. "Status:" also doesn't use the bold field format from section 2.
* **Rationale & Recommendation:** Write "**Status:** paused 2026-10-29. Public labels committed; the 9 private real-invoice labels are in progress."

### 22. mypy may check `line-drafts/` scripts - Severity: Nit
* **Reviewer Lens:** `egm-codebase-details`
* **Affected Scope:** Lines 439-440, 506
* **Discrepancy Description:** `line-drafts/` holds `.py` scripts. `uv run mypy .` doesn't read git excludes, so it may type-check them and break "each commit ends clean".
* **Rationale & Recommendation:** Confirm that mypy is clean today. If it isn't, add a `[tool.mypy]` exclude.

### 23. Unverifiable claims in commit 2 - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** Lines 471-472, 477
* **Discrepancy Description:** Two claims are made without evidence:
  * "All its findings are fixed": the stale text is only fixed in commits 4 and 6.
  * "nothing links to it" has no evidence.
* **Rationale & Recommendation:**
  * Write "fixed in commits 4 and 6, or listed in section 8".
  * Write "`grep -rn IDEA.md` matches only this design."

### 24. Imprecise wording - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** Lines 515-516, 553, 588-592
* **Discrepancy Description:** "briefly broken" is vague. "The existing README line stays" and "The decisions links now describe" don't give exact text.
* **Rationale & Recommendation:** Write "broken between commit 3 and commit 4". Quote the exact sentences that are kept and the ones that replace them.

### 25. "TypeSafe" undefined; Q-count totals disagree - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** Line 688; lines 603-660 vs 39 and 347
* **Discrepancy Description:** "TypeSafe" is never introduced in the design. The per-file Q counts add up to 37, but the overview says "about 31" and Alternative A says "about 34".
* **Rationale & Recommendation:** Define TypeSafe or link to the README. Make the totals agree, or say what each number counts.
