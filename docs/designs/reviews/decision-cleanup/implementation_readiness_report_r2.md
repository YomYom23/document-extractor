# Goldfish Review Report: Implementation Readiness, round 2

**Target:** `docs/designs/decision-cleanup.md` (lines 536-707, Detailed Implementation Plan; lines 1-535 read for definitions)
**Stage:** 9, Implementation Readiness Test (re-audit of the revised document)
**Reviewers:** `egm-implementation-readiness`, `egm-codebase-details`, `egm-style`
**Standard:** `resources/document_standards/implementation-readiness-standard.md` (all three lenses; the style persona names no default standard)

## Verdict

Not ready yet, but close. There are no Blockers. After deduplication there are 12 Majors and 19 Nits.

Commits 1, 2, 3 and 6 can mostly be carried out without guessing. Commits 4 and 5 (items 11 and 15-18) and the test in item 20 still leave choices to the implementer. Most of the paths, line numbers and counts the plan names check out against the repo (see "Verified correct" at the end).

The synthesizer re-checked two contested claims:
- `b_` files exist (`samples/dev/b_INV-2026-0068.pdf` and three others), but the Terms section never defines them.
- `line-drafts/` holds four `.py` files, and `[tool.mypy]` in `pyproject.toml` has `strict = true` with no `exclude`.

---

## Prioritized Findings (Blockers -> Major -> Nits)

### M1. `uv run mypy .` probably cannot pass while `line-drafts/` is in the working tree - Severity: Major
* **Reviewer Lens:** `egm-codebase-details`
* **Affected Scope:** Lines 538-540, 601, 694
* **Discrepancy Description:** The plan keeps `line-drafts/` local (line 601) and says every commit ends with mypy clean. The folder is hidden from git only by `.git/info/exclude`, not by `.gitignore`. It holds unannotated functions, for example `line-drafts/draft_ieb.py:34` `def number_spans(tokens: list[str], end: int):`. `pyproject.toml:39-40` turns on strict mode with no `exclude`, and mypy does not read git ignore files. So `mypy .` will probably report missing return types. This is inferred from the config; mypy was not run.
* **Rationale & Recommendation:** Choose one option and write it into the plan:
  - add `exclude = ["^line-drafts/"]` under `[tool.mypy]` in commit 2; or
  - change the check command to `uv run mypy document_extractor tests scripts`.

  Also confirm that `uv run ruff check .` skips the folder, or exclude it there too.

### M2. Item 8 does not name the round-2 review reports that already exist - Severity: Major
* **Reviewer Lens:** `egm-implementation-readiness`, `egm-codebase-details`, `egm-style`
* **Affected Scope:** Lines 587-599
* **Discrepancy Description:** `zoom_out_report_r2.md`, `comprehension_report_r2.md`, `critic_report_r2.md` and `intermediate_zoom_out_report_r2.md` are untracked in the repo root today, and this round's reports will join them. Item 8 lists only the round-1 files. Line 539 says each commit stages only the paths it names, so read strictly, the `_r2` files are left behind. "Any later review report of this design goes in the same folder" could mean reports written after commit 2, or reports that already exist when commit 2 is made. No naming rule stops reports from later rounds overwriting each other. (Codebase-details confirmed that `consolidated_review_report.md` uses same-folder links, so those links survive the move.)
* **Rationale & Recommendation:** List every report path that commit 2 moves to `docs/designs/reviews/decision-cleanup/`, including all `_r2` files and this round's `implementation_readiness_report_r2.md`. State the naming rule (an `_rN` suffix). Say in which commit reports written after commit 2 are added.

### M3. No source is given for "D21 to D23 state their settled rules", and the final status of some entries is not stated - Severity: Major
* **Reviewer Lens:** `egm-implementation-readiness`, `egm-style`
* **Affected Scope:** Lines 619-627 (relies on line 420)
* **Discrepancy Description:** The history entries D21-D23 (`decisions.md:101-125`) say "Recommended choices, pending your questions". The plan does not say where the settled answers are: in the code, in a later entry, or in chat. The implementer would have to invent the rule text. The plan also does not say whether D17 ends `active` or `retired`, or what is left of D13 once the "no commits" clause goes. Under the Zero-Decision Rule this is close to a Blocker.
* **Rationale & Recommendation:** Name the source of truth. For example: "the recommended choices, checked against `scoring.py`, `arithmetic_check.py` and `pdf_reader.py`; where the code differs, the code wins". Better still, give the one-line rule for each of D21, D22 and D23. List the intended status of all 34 entries, or at least D13 and D17.

### M4. The list of chains (which entries change which) is incomplete - Severity: Major
* **Reviewer Lens:** `egm-implementation-readiness`
* **Affected Scope:** Lines 619-627 (item 11, applying section 3)
* **Discrepancy Description:** The plan says D22, D28 and D30 change earlier entries without saying so, but never names the earlier entries. The explicit pairs in history are D20->D9, D25->D16, D26->D10, D31->D19, D32->D14, D32->D23, D33->D26 and D34->D9/D12. The three implicit targets are left to guesswork. Likely candidates are D30->D6/D19 and D28->D26. D22->D20 may not be a change at all, since D22 "implements D20". This is the very list the owner check depends on.
* **Rationale & Recommendation:** Add a table with every pair: later D, earlier D, and what changed. The owner check then confirms the list instead of having to work it out.

### M5. Which D cites count as "opaque" is left to the implementer - Severity: Major
* **Reviewer Lens:** `egm-implementation-readiness`, `egm-codebase-details`
* **Affected Scope:** Lines 652-667 (items 15-17, applying rule 3)
* **Discrepancy Description:** There are roughly 100-170 D tokens across about 25 scanned files, and the plan gives only three examples. For instance, two engineers could disagree on whether `llm_extractor.py:84` "Convert the model's answer into the shared `Invoice` (D26)" or line 120 is opaque. Item 17's "if any" pushes the same call onto `pyproject.toml:14` and `scripts/`, which may already read as explained.
* **Rationale & Recommendation:** Either list the cites to explain, with file:line and the new text, or state outright that the classification is a judgement call and that the owner reviews the commit 5 diff before the commit. That second option is a new owner check. Also say whether item 17 is expected to change anything.

### M6. The live-run link step in item 18 is unclear in scope and link form - Severity: Major
* **Reviewer Lens:** `egm-implementation-readiness`, `egm-codebase-details`, `egm-style`
* **Affected Scope:** Lines 668-673 (also the `**Evidence:**` links in item 11)
* **Discrepancy Description:** "Mentions of live runs ('D26 live run 2') link to the history file" does not say which mentions. `null-sources.md` mentions live runs at lines 9, 18, 46, 68, 93 and 103, and `comparison.md` has none, even though the Goals talk about links from comparison.md. No link form is chosen: heading anchor, plain file link or line link. History headings such as `### Live run 2, 2026-10-19 (after Q47; ...)` make anchors fragile. The new text for line 8-9 in the section 8 table says "(D26 live run 2, in history)" as plain text, which clashes with "link to". It is also unclear whether "link to" means "already link" or "become links".
* **Rationale & Recommendation:** List the lines to change and give the exact form, for example "a plain file link to `decisions-history.md`, with the heading named in words and no anchor". Use the same rule for the Evidence links in item 11.

### M7. The same stale "not extracted yet" text survives in two places - Severity: Major
* **Reviewer Lens:** `egm-implementation-readiness`, `egm-codebase-details`
* **Affected Scope:** Lines 555-560, 649-677 (section 8 stale-text table)
* **Discrepancy Description:** The plan rewrites `rules_extractor.py:313` because D34 keeps the rules extractor at null for good. Two places with the same claim are missed:
  - `docs/null-sources.md:26-27` (N3) still says "`line_items` always null ... not extracted yet; header fields come first and line items are not scored (D12, D24, D26)".
  - `document_extractor/README.md:52` still says "not extracted yet: both extractors return `line_items=None`". Item 2 changes only "in progress" to "paused".

  The restart search `git grep "D34 (paused)"` would also miss both.
* **Rationale & Recommendation:** Add both places to the stale-text table and to items 2 and 18, with exact replacement text. For example: "D34 (paused): the rules extractor stays at null for good; the LLM does not extract line items yet."

### M8. The cite test cannot be shown to fail, and the obvious negative test would trip its own scanner - Severity: Major
* **Reviewer Lens:** `egm-implementation-readiness`, `egm-codebase-details`
* **Affected Scope:** Lines 681-693 (item 20); lines 368-389 (scan list, index format)
* **Discrepancy Description:** The test runs only against the real repo, which is clean by construction. A `scanned_files()` that returns an empty list, a regex that never matches, or an index parser that skips lines would all pass. Nothing shows that check 1 reports `file:line: D42` (CUJ 4). `tests/test_decision_cites.py` is itself in the scan list, so a literal bad token in a fixture or docstring ("D42", "Q47") would make the test fail on itself. Several behaviours are also undecided:
  - what happens when git is missing, and which directory git runs from;
  - whether `decisions-index.md` may hold a heading or blank lines, and whether order is checked;
  - how the `tests/*.py` glob is matched (`fnmatch`'s `*` also matches `/`).
* **Rationale & Recommendation:**
  - Put each check's logic in a pure function that takes text and known IDs.
  - Add negative tests that build tokens at run time (`"D" + "42"`): unknown D, unknown N, any Q, an index line with the wrong status or title, a missing index line, an extra index line, and lowercase `d24` ignored.
  - Assert that the scan list is non-empty and includes `document_extractor/cli.py` and `docs/decisions.md`, and that there are 34 entries.
  - State that the test file must hold no literal invalid tokens.
  - Run git with `cwd=Path(__file__).parents[1]` and `check=True`, and fail if git is missing.
  - Give the exact index file layout and say whether order is checked.

### M9. "Q-to-D table" names two different tables - Severity: Major
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** Lines 613-617 (item 10); also lines 184, 327, 339, 344
* **Discrepancy Description:** Section 6 calls the 7-row live-cite map the "Q-to-D table" (line 327) and calls the per-D range table "the full table" (line 339). Item 10 asks for "the full Q-to-D table from section 6", which mixes the two names, so the implementer could paste the wrong table into history. Item 10 also leaves out the note required by line 344, that Q1-Q23 have no row.
* **Rationale & Recommendation:** Give the tables distinct names, for example "live-cite map" and "Q-range table", and use them consistently, including on line 184. Item 10 should say: "the Q-range table (one row per D from D24 to D34, plus the line saying Q1 to Q23 have no row)."

### M10. The commit 1 status line contradicts itself and commit 2 - Severity: Major
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** Lines 547-550 against lines 558-560
* **Discrepancy Description:** The new D34 line says "Status: paused ... the rest are in progress." That sentence calls the work both paused and in progress, and commit 2 then removes "in progress" from the READMEs as stale. "The rest" is also undefined.
* **Rationale & Recommendation:** Reword, for example: "Status: paused on 2026-10-29 until the decision-log cleanup is done. Line-item labels for the 25 IEB and 20 Sinabis invoices are committed; labels for the remaining invoices are unfinished drafts in the local, uncommitted `line-drafts/` folder."

### M11. Item 2's edits do not say which file gets which change - Severity: Major
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** Lines 555-560
* **Discrepancy Description:** "'line items (D34) are in progress' and '(D34 is in progress)' become 'paused'" does not say:
  - which phrase is in which file (implementation-readiness found them at `README.md:38-39` and in `document_extractor/README.md`);
  - whether the whole phrase becomes the single word "paused" or only "in progress" is replaced;
  - whether the clause about `document_extractor/README.md:52-54` is one of these two edits or a third.
* **Rationale & Recommendation:** Give the exact before and after text, with file:line, for each edit, and say "no other edits". Fold in the M7 fix for line 52.

### M12. The new ATTRIBUTION.md text uses the undefined `b_` prefix - Severity: Major
* **Reviewer Lens:** `egm-style` (repo check by synthesizer)
* **Affected Scope:** Line 417, applied by item 19 (line 677); Terms at lines 35-37
* **Discrepancy Description:** The replacement text says "The `a_`, `b_` and `c_` invoices are synthetic". The Terms section defines only `a_`, `c_` and `r_`. The `b_` files do exist (`samples/dev/b_INV-2026-0068.pdf`, `-0076`, `-0129`, `-0194`), but the design never says where they come from or whether they are synthetic.
* **Rationale & Recommendation:** Add `b_` to Terms with its source, and confirm it is synthetic before this text goes into `samples/ATTRIBUTION.md`.

---

### N1. Exact text is missing for two `D34 (paused)` comments - Severity: Nit
* **Reviewer Lens:** `egm-implementation-readiness`, `egm-codebase-details`, `egm-style`
* **Affected Scope:** Lines 655-656
* **Discrepancy Description:** `llm_extractor.py:100` (`line_items=None,  # header fields only (D26)`) and `scoring.py:10` (`# Header fields only; line items are scored later (D12).`) get only "`D34 (paused): ...`". The plan does not say whether the existing D26 and D12 cites are kept.
* **Rationale & Recommendation:** Add both lines to the stale-text table with their final wording.

### N2. The `rules_extractor.py:313` row says both "paused" and "for good" - Severity: Nit
* **Reviewer Lens:** `egm-implementation-readiness`
* **Affected Scope:** Lines 409, 655
* **Discrepancy Description:** Rule 4 reserves `D34 (paused)` for cites that D34 will change. This line describes permanent behaviour, so it would be a false hit in the restart search.
* **Rationale & Recommendation:** Use a plain `D34:` cite, or say on purpose that the false hit is accepted.

### N3. The stated source of D34's Q range is wrong - Severity: Nit
* **Reviewer Lens:** `egm-implementation-readiness`, `egm-codebase-details`
* **Affected Scope:** Lines 613-617, relying on lines 339-342
* **Discrepancy Description:** Section 6 says each range comes "from its heading". The D34 heading (`decisions.md:377`) says Q88-Q98, while the table correctly says Q88-Q105 (Q99-Q105 are in the body, at lines 396 and 403). An implementer might "correct" the table to Q98.
* **Rationale & Recommendation:** Say "from its heading, or for D34 also from its body".

### N4. It is unclear whether `null-sources.md` lines 8-9 are replaced whole - Severity: Nit
* **Reviewer Lens:** `egm-implementation-readiness`
* **Affected Scope:** Line 415
* **Discrepancy Description:** The "Becomes" text drops the sentence about the free rules run (56 correct, 7 missing, 0 wrong).
* **Rationale & Recommendation:** Say whether the whole lines are replaced or only the quoted fragments.

### N5. The arrows for moving untracked files read like `git mv` - Severity: Nit
* **Reviewer Lens:** `egm-implementation-readiness`, `egm-style`
* **Affected Scope:** Lines 589-598
* **Discrepancy Description:** `git mv` fails on untracked files. The design file itself is already in place.
* **Rationale & Recommendation:** Add "move with the shell, then `git add` the new path". Note that `docs/designs/decision-cleanup.md` only needs `git add`.

### N6. Item 13 does not say where the new `CLAUDE.md` lines go - Severity: Nit
* **Reviewer Lens:** `egm-implementation-readiness`, `egm-style`
* **Affected Scope:** Lines 635-638
* **Discrepancy Description:** "The README line stays" does not quote the line, and the order of the lines is not given. Today the file is one line: "Read @README.md ...".
* **Rationale & Recommendation:** Give the exact final content of the file.

### N7. The README link sentence in item 14 has no exact wording - Severity: Nit
* **Reviewer Lens:** `egm-implementation-readiness`
* **Affected Scope:** Lines 642-645
* **Discrepancy Description:** The wording is left free. Elsewhere the plan gives exact text in the stale-text table.
* **Rationale & Recommendation:** Give the exact sentence. Also quote the old string exactly as it appears; line 414 has a lowercase "the" where line 644 has "The" (style N9).

### N8. No baseline is stated for line numbers or for the behaviour check - Severity: Nit
* **Reviewer Lens:** `egm-implementation-readiness`, `egm-style`, `egm-codebase-details`
* **Affected Scope:** Lines 409-418, 559, 655-677, 695-699
* **Discrepancy Description:** Earlier edits move later line numbers. For example, `document_extractor/README.md` is edited in both commit 2 and commit 4. The AST check compares against "`main`". `main` and `cleanup` are both at 43969ce today, so this works now, but `main` could move.
* **Rationale & Recommendation:** After line 540, add "Line numbers refer to the files at 43969ce". Use that hash, or `git merge-base main HEAD`, as the AST baseline. List the changed `.py` files with `git diff --name-only <base>..HEAD -- '*.py'`, leaving out the new test file.

### N9. The httpx2 rationale names only one of the two test files that use it - Severity: Nit
* **Reviewer Lens:** `egm-codebase-details`
* **Affected Scope:** Lines 581-585, relying on lines 399-401
* **Discrepancy Description:** `tests/test_llm_extractor.py:5` also imports httpx2 and uses `httpx2.Client` and `MockTransport` at lines 167 and 265. The fix itself is unchanged.
* **Rationale & Recommendation:** Name both `tests/test_jev.py` and `tests/test_llm_extractor.py`.

### N10. Commit 5's file list does not mention the scanned `CLAUDE.md` files - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** Lines 649-650, against lines 368-376 and 565
* **Discrepancy Description:** The three `CLAUDE.md` files are scanned and committed "as they are" in item 3, but they are not in commit 5's list. Implementation-readiness found no Q cites outside the files the plan covers, so the risk is low. The plan should still say so.
* **Rationale & Recommendation:** Add "Items 15-19 list every scanned file that needs a change; no other scanned file needs one."

### N11. "Blueprints" is undefined jargon - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** Line 557
* **Rationale & Recommendation:** Use "Untracked docs", as item 3 does.

### N12. The claim that the drift report's findings are fixed cannot be checked as written - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** Lines 567-570
* **Discrepancy Description:** "All its findings are fixed and nothing links to it" gives no evidence, and the Goals ask for evidence.
* **Rationale & Recommendation:** Say where each finding was fixed, and give a check such as "`git grep DRIFT_REPORT` returns nothing". Note that the file is not part of the commit, as item 6 does.

### N13. "The frozen note with the date" is underspecified - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** Line 615, against line 182
* **Discrepancy Description:** Line 615 does not say which date to use. It also drops the "Do not edit below this line" text from line 182.
* **Rationale & Recommendation:** Say "the note from section 1, word for word, with the date of commit 3 and `decisions.md` as a relative link".

### N14. "Saying 25 IEB invoices" is terse - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** Lines 623-624
* **Rationale & Recommendation:** Reword to "states the IEB count as 25 (the history entry's 26 is wrong)".

### N15. "Owner check before the commit" is ambiguous about timing - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** Lines 627, 702
* **Discrepancy Description:** "Before commit 4" can be read as "before starting commit 4". That is impossible, because the file being checked is written in commit 4.
* **Rationale & Recommendation:** Reword to "after `decisions.md` is written and before commit 4 is made".

### N16. "In `.py` files only comments and docstrings change" can be read two ways - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** Line 650
* **Rationale & Recommendation:** Add a comma: "In `.py` files, only comments and docstrings change."

### N17. Items 15-19 are formatted differently from items 1-14 - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** Lines 652-677
* **Discrepancy Description:** Headings shorten paths after the first one (for example `currency_resolver.py`), and items 15-19 drop the "Proposed Changes" label. Line 666's "if any" hedges.
* **Rationale & Recommendation:** Use full paths and the same label in every item. Replace "if any" with an explicit list, or with "none today".

### N18. The same table goes by two names, and some wording is loose - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** Lines 649, 661-662, 688, 696-697, 703
* **Discrepancy Description:**
  - The plan says both "stale-text table" and "stale table".
  - "Pass at once" (line 688) is informal and could mean "immediately" or "together".
  - "Removes docstring expressions" is vague.
  - "Scratchpad" is undefined.
  - "TypeSafe" is undefined beyond the package name `typesafe-sdk`.
* **Rationale & Recommendation:**
  - Use one table name throughout.
  - Reword line 688 to "All four checks pass on first run; commits 4 and 5 removed every failing cite".
  - Describe the docstring step as "drops the first statement of each module, class and function body when it is a string constant".
  - Replace "scratchpad" with "a temporary directory outside the repo".
  - Write "the TypeSafe API (`typesafe-sdk`)".

### N19. The live-run link wording reads two ways - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** Lines 672-673
* **Discrepancy Description:** "Link to the history file" could mean the mentions already link there, or that they should become links. M6 covers the larger scope problem; this is only the wording.
* **Rationale & Recommendation:** Reword to "Each listed mention becomes a Markdown link to `docs/decisions-history.md`."

---

## Verified correct (by codebase-details and implementation-readiness)

- **Line numbers:** these match the repo:
  - `rules_extractor.py:313`, `llm_extractor.py:100` and `scoring.py:10`;
  - `tests/test_llm_extractor.py:36` and `tests/test_samples.py:49-50`;
  - `null-sources.md` lines 8-9, 50, 86, 106, 109 and 110;
  - `comparison.md` lines 5, 100 and 111;
  - `document_extractor/README.md:10-11` and `:52-54`, and `README.md:22-23` and `:38-39`;
  - `samples/ATTRIBUTION.md` lines 3, 23 and 30.
- **Q cites:** 37 lines (40 tokens) hold Q cites, and all are covered by the section 6 table. The heading ranges for D24-D33 match `decisions.md`.
- **No out-of-range cites:** no scanned file cites a D above 34. Every N cite matches an existing `### N<n>.` heading.
- **File coverage:** items 15-16 cover every code and test file that has a cite. `test_schema.py` and `test_scoring.py` have none.
- **httpx2:** version 2.13.1 is locked in `uv.lock`, and `[dependency-groups] dev` exists.
- **Files to remove:** `IDEA.md`, the drift report and `scripts/__pycache__/live_llm_check.cpython-313.pyc` all exist. Nothing outside the design links to `IDEA.md`.
- **Links:** only the two READMEs link to `docs/decisions.md`.
- **Baseline:** `main` and `cleanup` are both at 43969ce.
- **Commit 1 counts:** the 25 IEB and 20 Sinabis counts match commits cedda93 and 43969ce.
