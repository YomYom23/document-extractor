# Goldfish Review Report (Stage 7 Critic Review, re-audit r2)

**Target:** `docs/designs/decision-cleanup.md` (lines 1-535, FeatureRange; lines 536-707 are the implementation plan and were read for context only)

**Reviewers:** egm-design (persona `agents/design_critic.md`), egm-structural, egm-style
**Standard:** `resources/document_standards/feature-spec-standard.md` (all three lenses; egm-style's persona names no default standard)

**Summary:** 0 Blockers, 5 Majors, 22 Nits (after deduplication).

All three lenses found that the document has every section the standard requires and that those sections have real content. The headings nest correctly, and the code blocks and tables are well formed. The design lens checked these against the repository and found them correct: the 37 Q cites, the D1-D34 topic table, the amendment headings, and the stale-text quotes.

---

## Prioritized Findings (Blockers -> Major -> Nits)

### Blockers

None.

### Majors

### 1. Terms list says two public sample sources; there are three - Severity: Major
* **Reviewer Lens:** `egm-structural`, `egm-style`, `egm-design` (all three)
* **Affected Scope:** Lines 35-37 (Terms: "IEB, Sinabis"); conflicts with line 417
* **Finding:** The glossary calls IEB and Sinabis "the two public sources of synthetic invoices (`a_` and `c_` files)". `samples/ATTRIBUTION.md` (lines 13-17) and `samples/dev/b_*.pdf` show a third public source: InvoiceBenchmark (`b_`, MIT licence). Line 417 of the design itself names the `b_` invoices. So the glossary is wrong, and `b_` is used later without a definition.
* **Suggested fix:** Change it to "IEB (`a_`), InvoiceBenchmark (`b_`) and Sinabis (`c_`): the three public sources of synthetic invoices". If only IEB and Sinabis matter here, keep that scope but don't call them the only sources.

### 2. New files escape the cite test in the commit that creates them - Severity: Major
* **Reviewer Lens:** `egm-design`
* **Affected Scope:** Lines 81-82 (Goal), 368-380 (section 7, files it scans)
* **Finding:** `scanned_files` uses plain `git ls-files`, which lists only tracked files. The workflow runs pytest before it stages named paths. So a new module, test or doc with a bad D, N or Q cite is not scanned in the run that is meant to clear it. The bad cite is caught only one commit later. That weakens the Goal "`uv run pytest` fails when a scanned file cites...".
* **Suggested fix:** Use `git ls-files --cached --others --exclude-standard`, then apply the include patterns. The patterns are explicit, so untracked clutter (root report files, `line-drafts/`) still won't match. State this in section 7.

### 3. Chain links to the paused D34 are undefined - Severity: Major
* **Reviewer Lens:** `egm-design`
* **Affected Scope:** Lines 99-100, 247-249, 264-274, 281 (section 3 and the owner check)
* **Finding:** The example gives D9 `Changed by: D20, D34`, but D34 is `paused`, and its rules are written "when D34 restarts". In the history, D34 already settles line-item scoring (pair by `line_total`, then by page order; Q91, Q92, Q96). That replaces D12's "scored as a set matched by line total". D34 also overrides the "line items later" / "null until scored" wording in D21, D22, D24, D26 and D30. And 45 committed labels (25 IEB, 20 Sinabis) already follow D34's Q99-Q105 conventions. The design never says three things:
  - whether a paused entry may appear in `Changes:` / `Changed by:`;
  - what D12's Rule says about line-item scoring while D34 is paused;
  - whether D21, D22, D24, D26 and D30 get `Changed by: D34`.

  Section 3 lists only D34's explicit amends, so the owner check will miss these implicit ones.
* **Suggested fix:** Add a rule to section 3. For example: "a paused entry may carry `Changes:`; each earlier Rule keeps only what is in force now and notes 'line-item part: see D34 (paused)'". List D21, D22, D24, D26 and D30 as implicit chain members of D34. Also have the D34 entry's Evidence link to the history D34 entry, not only to `line-items-brief.md`. The settled label conventions exist only in the history.

### 4. `line-drafts/` holds private and held-out renders but is not git-ignored - Severity: Major
* **Reviewer Lens:** `egm-design`
* **Affected Scope:** Line 110; lines 524-526 (NFR privacy); Risks section (lines 423+)
* **Finding:** `.gitignore` covers `samples/private/` but not `line-drafts/`. The privacy NFR depends only on process ("stages named paths only; `git add -A` ... never used"). One slip, or a later session that doesn't know the rule, would commit renders of real invoices and leak held-out content. The Risks section does not list this risk.
* **Suggested fix:** Add `line-drafts/` to `.gitignore` in commit 2, the same way `samples/private/` is handled. Keep the named-paths rule as a second line of defence, and add the risk to Risks and Mitigations.

### 5. The test for "new D number vs edit in place" is subjective and worded two ways - Severity: Major
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** Line 142 (CUJ 3) and lines 311-314 (section 5)
* **Finding:** CUJ 3 says "if the change deserves its own record". Section 5 says "whose reasons are worth keeping on their own". This rule controls numbering, and two readers could apply it differently.
* **Suggested fix:** State one concrete test in section 5. For example: "a new number when the change came from a separate grilling session or reverses the rule's outcome; otherwise edit in place". Have CUJ 3 point to section 5 instead of rewording the rule.

### Nits

### 6. Stale-text table is incomplete although line 87 treats it as the full list - Severity: Nit
* **Reviewer Lens:** `egm-structural`, `egm-design`
* **Affected Scope:** Lines 405-421 (section 8 table); line 87; section 6 rule 4 (lines 358-360)
* **Finding:** The table leaves out four places:
  - `document_extractor/llm_extractor.py:100` (`line_items=None,  # header fields only (D26)`);
  - `document_extractor/scoring.py:10` (the `HEADER_FIELDS` comment, "line items are scored later (D12)");
  - `README.md:38` ("line items (D34) are ... in progress").

  The implementation plan covers some of these, but the feature section does not.
* **Suggested fix:** Add those rows, or say the table lists examples and rule 4 covers the rest.

### 7. Index size "about 50 lines" does not match one line per entry - Severity: Nit
* **Reviewer Lens:** `egm-style` (rated Major), `egm-design` (rated Nit)
* **Affected Scope:** Lines 83-84, 288-289; affects the size argument at lines 302-303
* **Finding:** There are 34 entries (D1-D34) at one line each, so the index is about 34 lines, not about 50.
* **Suggested fix:** Say "34 lines, one per entry, plus one per new decision".

### 8. `null-sources.md` replacement text drops where the rules figures come from - Severity: Nit
* **Reviewer Lens:** `egm-design`
* **Affected Scope:** Line 415
* **Finding:** Today the rules figures (56/7/0) come from a free run on 2026-10-19, and only the LLM figures come from D26 live run 2. The new text credits all dev cost figures to D26 live run 2.
* **Suggested fix:** "Rules figures are from a free run on 2026-10-19; LLM figures are from D26 live run 2 (in history)."

### 9. Cite test scans its own file - Severity: Nit
* **Reviewer Lens:** `egm-design`
* **Affected Scope:** Lines 149-151, 368-372
* **Finding:** The pattern `tests/*.py` includes `tests/test_decision_cites.py`. A docstring or test-data example such as "D42" (the CUJ 4 example) or "Q47" would make the suite fail.
* **Suggested fix:** State that the test file uses no D, N or Q tokens in its docstrings or data, or exclude the file explicitly.

### 10. Check 4 "no other numbers" is ambiguous - Severity: Nit
* **Reviewer Lens:** `egm-design`
* **Affected Scope:** Line 390
* **Finding:** It could mean "no index line for a number that has no entry". It could also mean "no D tokens anywhere in a line". Under the second reading, a title like "(implements D20)" would fail.
* **Suggested fix:** Say "no line for a number that has no entry". If titles must not contain D tokens, say so in the Formats list.

### 11. Q-range source contradicts itself for D34 - Severity: Nit
* **Reviewer Lens:** `egm-design`
* **Affected Scope:** Lines 339-344
* **Finding:** The text says each row takes "the Q range from its heading", then gives D34 as Q88-Q105. The D34 heading says Q88-Q98; Q99-Q105 appear only in the body.
* **Suggested fix:** Say ranges come from the heading, extended by Q numbers used in the body (D34: Q99-Q105).

### 12. Two small claims do not match the repo - Severity: Nit
* **Reviewer Lens:** `egm-design`
* **Affected Scope:** Lines 78-79; lines 399-401
* **Finding:** Two claims don't match the repo:
  - The Goal "Links from `comparison.md` to live-run evidence keep a fixed target" reads as if the links already exist. Today `comparison.md` has no links to `decisions.md`.
  - The `httpx2` reason names only `tests/test_jev.py`, but `tests/test_llm_extractor.py` imports `httpx2` too.
* **Suggested fix:** Reword the Goal as links that this work creates. Name both test files in the `httpx2` reason.

### 13. Path style in the stale-text table is inconsistent - Severity: Nit
* **Reviewer Lens:** `egm-structural`
* **Affected Scope:** Lines 409-418; also lines 51, 53
* **Finding:** Some paths have no directory (`rules_extractor.py:313`, `null-sources.md:8-9`). Others are full repo paths.
* **Suggested fix:** Use repo-relative paths throughout, for example `document_extractor/rules_extractor.py:313` and `docs/null-sources.md:8-9`.

### 14. `<date>` placeholder will vanish when rendered - Severity: Nit
* **Reviewer Lens:** `egm-structural`
* **Affected Scope:** Line 182
* **Finding:** `Frozen on <date>. ...` is plain prose, so a Markdown renderer treats `<date>` as an HTML tag and hides it. Every other placeholder in the document is in backticks.
* **Suggested fix:** Put the note in backticks, or write "Frozen on YYYY-MM-DD".

### 15. Mixed subsection styles in the Technical Plan - Severity: Nit
* **Reviewer Lens:** `egm-structural`
* **Affected Scope:** Line 212 (`#### Formats`) versus lines 281, 327, 346, 368, 382 (bold run-in labels)
* **Finding:** Section 2 uses an H4 heading. Sections 3, 6 and 7 split into the same kind of sub-part with bold labels instead.
* **Suggested fix:** Pick one convention and use it everywhere.

### 16. Entry and index formats render as run-on paragraphs - Severity: Nit
* **Reviewer Lens:** `egm-structural`
* **Affected Scope:** Lines 216-238, 288-295
* **Finding:** The fields of each entry, and the lines of the index, are consecutive lines with no blank lines or list markers. GitHub and IDE previews will merge them into one paragraph and collapse the "two spaces between fields".
* **Suggested fix:** Say these files are meant to be read raw, or change the format: blank lines between fields, a trailing backslash on each line, or a fenced `text` block for the index. Keep section 7 check 4 consistent with whichever you choose.

### 17. Cross-reference wording varies - Severity: Nit
* **Reviewer Lens:** `egm-structural`, `egm-style`
* **Affected Scope:** Lines 87, 141, 194, 281, 318, 349
* **Finding:** The document uses "Technical Plan section 8", "Section 5's rule" and "section 5" for the same kind of reference. CUJ 3 also points to section 5 before the reader gets there.
* **Suggested fix:** Use one form everywhere, for example "Technical Plan §5".

### 18. "Chain" / "amend" / "change" used without a definition - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** Lines 141, 256, 281, 427, 445
* **Finding:** The design mixes "amend", "chain" and "change", but the actual field names are `Changes` and `Changed by`. "Chain" is never defined.
* **Suggested fix:** Add "Chain" to Terms (entries linked by Changes / Changed by). Use "change" throughout, and keep "amend" only when quoting the old log.

### 19. Bare D-number lists repeat the problem the design describes - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** Lines 49-50, 199-206 (prose), 258-259
* **Finding:** Lists like "D10, D12, D16 and D19" give a fresh reader no idea what each entry is.
* **Suggested fix:** Add a two-to-four-word gloss after each number in prose, for example "D12 (scoring rules)".

### 20. Vague counts and quantities - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** Line 14 ("the few files"); line 244 ("about eight") vs line 507 ("eight rules"); line 448 ("a few dozen explanations"); line 476 ("A common convention")
* **Finding:** These are approximate or unsupported where exact figures exist or a source is needed.
* **Suggested fix:**
  - Line 14: "three unused files (listed in section 8)".
  - Lines 244 and 507: use the exact count in both places.
  - Line 448: give the real number of opaque cites, or drop the count.
  - Line 476: "the ADR convention (one file per record)", or drop the phrase.

### 21. Subjective or opinion wording stated as fact - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** Lines 41-43 ("tells the reader nothing", "That is the pain the owner reported"), 125 ("The rule is clear"), 216 ("readable on its own"), 242 ("are short"), 430-431 ("the costly error"), 455 ("the larger part of the problem"), 514 ("enough for two readers, in one reviewer's view")
* **Finding:** These are judgments with no measure, or are conversational in tone.
* **Suggested fix:**
  - Lines 41-43: "A bare 'D24' does not say what the rule is ... The owner reported this as the main cost."
  - Line 125: "The comment states the rule."
  - Lines 216 and 242: use the template's own measures ("one to three sentences", "one line per alternative").
  - Lines 430-431: "The test still catches a wrong or missing number."
  - Line 455: point to Problem item 1 instead of calling it the larger part.
  - Line 514: "adequate for a two-reader project".

### 22. "All are kept on purpose" gives no reason - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** Lines 107-109
* **Finding:** The claim cannot be checked.
* **Suggested fix:** Give a one-clause reason for each item, or point to where the reasons are recorded.

### 23. "Grilling session" is jargon, with a singular/plural slip - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** Lines 26-29 (Terms: Q number)
* **Finding:** "Grilling session" is an in-house term. The sentence also switches from "a grilling session" to "the question-and-answer sessions".
* **Suggested fix:** "a question asked in a design Q&A session (a 'grilling session') where decisions were made".

### 24. Rejection reasons for folding and newest-wins are written twice - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** Lines 276-279 vs lines 483-491 (Alternative D)
* **Finding:** The same reasons appear in almost the same words in both places.
* **Suggested fix:** Keep them only in Alternative D. Replace lines 276-279 with "Chosen on 2026-10-30; see Alternative D."

### 25. Alternative F's "Reason for Rejection" is a date, not a reason - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** Lines 509-510
* **Finding:** The standard asks for specific, documented reasons. This field gives only a decision date and the option chosen.
* **Suggested fix:** "Rejected because a title cannot describe what one line of code does (see Cons); drift is accepted as a risk. Decided 2026-10-30."

### 26. Redundant phrase - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** Lines 186-188
* **Finding:** "one fixed target that never changes" says the same thing twice.
* **Suggested fix:** "gives evidence links a fixed target".

### 27. Minor wording - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** Lines 465, 469, 141, 318
* **Finding:** A few phrases read awkwardly:
  - "for ever" (line 465);
  - "for a gain a short explanation beside a D number already gives" (line 469);
  - "Rule" is capitalised as a field name in running prose (lines 141 and 318).
* **Suggested fix:**
  - Line 465: "permanently".
  - Line 469: "when a short explanation beside the D number gives the same benefit".
  - Lines 141 and 318: format the field name as `**Rule:**`.

---

**Out-of-range note (not a finding):** Line 528 (NFR "Behaviour") points to "the Verification Plan", which is an H3 under the implementation plan (line 690). The reference resolves correctly.
