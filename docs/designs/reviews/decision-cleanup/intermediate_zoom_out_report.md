# Goldfish Review Report: Stage 8 (Intermediate Zoom Out)

**Target:** `C:\Users\Yomi\PycharmProjects\document-extractor\docs\designs\decision-cleanup.md` (`1-692`)

**Reviewers:** `egm-zoom-out`, run twice independently (instances A and B). Persona: `C:\Users\Yomi\.claude\plugins\cache\egm\egm\0.1.0\agents\zoom_out.md`. Standard: `C:\Users\Yomi\.claude\plugins\cache\egm\egm\0.1.0\resources\document_standards\zoom-out-standard.md`.

**Context:** Stage 5 `zoom_out_report.md`, Stage 6 `comprehension_report.md`, Stage 7 `critic_report.md`. The target has not changed since those reports were written.

**Totals:** 2 Blockers, 4 Majors, 2 Nits.

## Overall diagnosis

The goal is still right, and so is the shape of the core design:

- keep the D numbers,
- freeze the old log,
- write one current entry for each ID,
- have a test that rejects unknown IDs.

Both instances agree that most of the roughly 60 findings from Stages 5-7 are not separate defects. They come from a handful of mechanisms built on top of that core:

1. sub-IDs,
2. an amendment model with too many parts,
3. a cite-test scope written as a blocklist over the whole repo,
4. a commit order that adds tests before the content is clean,
5. several hand-kept short forms of each rule, none of them canonical,
6. unrelated work bundled into the same design.

Fixing findings 1-3 below removes every Blocker from Stages 6 and 7. All the findings together remove or shrink about two thirds of the earlier findings. None of them changes the core approach.

## Prioritized Findings (Blockers -> Major -> Nits)

### 1. Sub-IDs turn a mechanical migration into an open-ended content job - Severity: Blocker
* **Reviewer Lens:** `egm-zoom-out` (A and B agree. A rated this Blocker; B rated it Major. Blocker is kept because it is the root of a Stage 6 Blocker.)
* **Affected Scope:** Lines 148, 217-225, 260, 266, 292, 310, 534-535, 571, 620-623; also 67.
* **Discrepancy Description:** The design runs two migrations at once.
  - **Format migration:** frozen history plus current rules, keyed by the same IDs. This part is mechanical and well specified.
  - **Content migration:** split D24 and D34 into sub-IDs, map each Q to a sub-ID, and turn the brief's "settled points" into D34 sub-IDs.

  The content migration needs information the document does not contain: the list of sub-IDs, a Q-to-sub-ID mapping, which brief points count as settled, a status for each sub-ID, and a real ID in place of the "D34.n" placeholder. Without sub-IDs, every Q maps to its parent D using the Q ranges already in the D headings (for example "D24 ... grilling Q24 to Q31"). The sub-IDs also add nothing the cite explanation doesn't already give: all 8 D24 cites sit in `rules_extractor.py`, and "D24: ambiguous slash dates give null" is as specific as "D24.3". The D34 sub-IDs are speculative work on a paused feature whose brief is being committed anyway.
* **Subsumes:**
  - Stage 5: #3
  - Stage 6: #4 (Blocker), #7, #12, #20, and part of #5
  - Stage 7: M7, N1, N10, and part of M4
* **Rationale & Recommendation:**
  - Add a Non-Goal: "No sub-IDs in this change. Every Q cite maps to its parent D."
  - D24 becomes one entry whose Rule is a short bulleted list.
  - D34 becomes one entry with status paused and an Evidence link to `docs/designs/line-items-brief.md`. `rules_extractor.py:313` becomes `# D34 (paused): the rules extractor never extracts line items; they stay null`.
  - Record a trigger for adding sub-IDs later, for example "when D34 resumes, or when one cite needs to point at a single bullet".
  - The test regex and the heading grammar shrink to `D\d+`.

### 2. The cite test is a blocklist over the whole repo, and its contract is written twice - Severity: Blocker
* **Reviewer Lens:** `egm-zoom-out` (A rated this Blocker, B rated it Major. Blocker is kept because it is the shared root of three Stage 6 Blockers and the Stage 7 Blocker.)
* **Affected Scope:** Lines 199-216, 254-266, 302-318, 535-537, 555-574.
* **Discrepancy Description:** The scan scope is described twice and built as "scan everything, then exclude". Meanwhile the design adds historical text full of Q tokens and future-D tokens into the scanned trees: this design, the two moved briefs, and the untracked review reports. Every disagreement about scope, the `.venv` pickup, the self-scan and the example-ID leaks follows from that one choice. A second problem has the same cause. The parts the test parses (heading grammar, Status line, index line format) are never given as one exact contract. The editorial content, by contrast, is over-specified in places.
* **Subsumes:**
  - Stage 5: #5
  - Stage 6: #2 (Blocker), #3 (Blocker), #5, #19
  - Stage 7: B1, N2, N7
* **Rationale & Recommendation:** Add one short "Contract" block to Section 7, written once and referenced everywhere else. It should give:
  - **Scan set:** an allowlist of tracked files only (`git ls-files`) under `document_extractor/`, `tests/` and `scripts/`, plus a named list of live docs: `docs/decisions.md`, `docs/decisions-index.md`, `docs/null-sources.md`, `docs/comparison.md`, the README.md and CLAUDE.md files, and `pyproject.toml`. Designs, briefs, history and reports are then out of scope by construction. `.venv`, `__pycache__` and untracked reports never enter the scan.
  - **Heading regex:** for example `^### (D\d+)\. (.+)$`, with the ID in group 1.
  - **Status:** on its own line under each heading.
  - **Index line format:** a fixed delimiter.
  - **N heading regex.**
  - **One sentence:** "Entry wording and corrected facts are written at implementation and approved in the owner review." This settles the editorial gaps (Stage 6 #10, the open parts of #4) without listing every value in the design.

### 3. The commit order adds tests before the content they check is clean - Severity: Major
* **Reviewer Lens:** `egm-zoom-out` (A and B agree.)
* **Affected Scope:** Lines 427-441, 508-593, 645-661.
* **Discrepancy Description:** Six commits; a `git mv` followed by recreating the same path; a test split across commits 4 and 5; doc Q cites fixed only in commit 6. Together these cause the red commit 5, README links that break for a moment in commit 3, one oversized review, and a rollback claim that cannot hold. The order isn't necessary. The D numbers never change (and with finding 1 there are no sub-IDs), so cite rewrites don't depend on the new `decisions.md` and can come first.
* **Subsumes:**
  - Stage 5: #7
  - Stage 6: #1 (Blocker), #8
  - Stage 7: M9, and the timing part of M5
* **Rationale & Recommendation:** Five commits, each clean on arrival:
  1. Pause D34 (plus housekeeping, if it isn't split out under finding 6).
  2. Rewrite every Q cite in code, tests and docs to its parent D, and add any needed explanations. This commit touches comments and docs only.
  3. `git mv` the log to `docs/decisions-history.md` as a pure rename, then add the frozen note and the Q-to-D table.
  4. The new `decisions.md`, the index, and the README and CLAUDE.md link updates. The owner reviews the chain table before this commit.
  5. `tests/test_decision_cites.py`, complete, passing on arrival.

  Replace the rollback paragraph with "revert from the newest commit backward". Instance A put the cite rewrites after the new file. Either order works as long as the test lands last; B's order (above) is simpler because step 2 has no dependencies.

### 4. The amendment model has five parts because it never says who owns the current rule - Severity: Major
* **Reviewer Lens:** `egm-zoom-out` (A folded this into its sub-ID Blocker. B raised it separately.)
* **Affected Scope:** Lines 56-58, 117-124, 210-212, 227-250, 273-288, 387-395.
* **Discrepancy Description:** Earlier stages flagged these pieces one at a time. Together they form one subsystem:
  - two-way Changes / Changed by links,
  - a `superseded by` status that no case uses,
  - a judgement call on when a change "deserves its own record",
  - a "fold table" left over from the rejected folding option,
  - a claim that chain IDs "sit together", which the section table contradicts.

  The root cause: the design never says which entry in a chain holds the full current rule. After the freeze, git log already records edits, as the design says itself at line 278. So new IDs for later amendments add little.
* **Subsumes:**
  - Stage 5: #1, #9
  - Stage 6: #6, #18, #23
  - Stage 7: M4, M5, M6, M10, N3
* **Rationale & Recommendation:** Replace Section 3 and the bullets at lines 280-285 with two rules.
  - **Migration:** in each existing chain, the oldest ID's Rule states the whole current rule. Each later ID keeps only "Changes: Dx", its own Why and its Evidence, so existing cites still land on the specific reason.
  - **After the freeze:** change a rule by editing it in place. Create a new ID only for a new rule. Retire a dropped rule.

  Then:
  - Drop "Changed by" and `superseded by`. The statuses become active, paused and retired.
  - Replace the fold table with a chain table (chain, owning ID, rewritten Rule).
  - Work one chain (D9 -> D20 -> D22 -> D34) as the example.

  CUJ 3 then becomes one sentence.

### 5. No single short form of each rule is canonical, so the design repeats the drift it rejects in Alternatives E and F - Severity: Major
* **Reviewer Lens:** `egm-zoom-out` (A and B. A rated this Major. B split it into two Nits: the index copy and the overstated explanation workload. They are merged here.)
* **Affected Scope:** Lines 17-18, 54-55, 67-69, 150-155, 209, 252-271, 286-295, 313-315, 397-418, 541-553.
* **Discrepancy Description:** Each rule ends up with up to five hand-kept short forms:
  - the Rule text,
  - the heading,
  - the index line,
  - a free-text explanation at each cite,
  - the README "Invariants" lists, which already restate current rules with D numbers and already load every session through CLAUDE.md.

  Only the link between heading and index is checked. That is the drift risk the design uses to reject Alternatives E and F. The Overview also overstates the work: most cites under `document_extractor/` already end a sentence that explains the code (for example "wrong is worse than missing (D11)"). The truly opaque ones are few: module docstrings and lines such as `DEFAULT_MODEL = ...  # D26, Q39`.
* **Subsumes:**
  - Stage 5: #2, #6
  - Stage 6: part of #5
  - Stage 7: M2, N1, N9, and the explanation-drift part of M1
* **Rationale & Recommendation:** Pick one of two options.
  - **(a) Make the heading the canonical short form.** Cites take the form `D11 (Missing is null, never guessed)`, optionally followed by `: <local note>`, and the test checks the text in brackets against the heading. Generate the index from the headings, or have the test print the expected index when it fails. Drop the status column from the index. The CLAUDE.md chat rule becomes "use the index heading text", which can be checked.
  - **(b) Keep free-text explanations.** Narrow the Goal to "cites whose comment doesn't already say what the code does gain one". State that explanations describe this code's behaviour, not the rule's wording. Record the remaining drift as an accepted risk, and soften the E and F rejections so they don't condemn the chosen design.

  Either way, add one line saying the README invariants are module contracts that cite D numbers, are not restatements of rules, and are outside the test. This is the main design choice left for the owner.

### 6. Housekeeping and the held-out prompt test are bundled into a decision-system design - Severity: Major
* **Reviewer Lens:** `egm-zoom-out` (A and B agree.)
* **Affected Scope:** Title and lines 1-19, 63-66, 70-72, 77-91, 133-138, 320-337, 422-433, 454-506, 576-583, 649-672.
* **Discrepancy Description:** The design bundles four separate changes:
  - the decision system,
  - housekeeping: the drift report, IDEA.md, .pyc files, httpx2, committing the untracked docs, moving the briefs,
  - stale-text fixes,
  - a new held-out prompt-leak test.

  About half of the Stage 6 and Stage 7 findings sit outside the decision system. The held-out test has no trigger here, because no commit edits `INSTRUCTIONS`, and its own CUJ 5 cannot happen under this design's Non-Goals. It also rebuilds sample discovery that `tests/test_samples.py` already provides (`SAMPLES_DIRECTORY`, `PRIVATE_DIRECTORY`, `set_directories`). The bundling also makes the Non-Goal list and the Behaviour NFR list disagree.
* **Subsumes:**
  - Stage 5: #4, #11
  - Stage 6: #10 (the non-decision facts), #11, #15, #16, #17
  - Stage 7: M8, N6, N7, and the held-out part of M1
* **Rationale & Recommendation:**
  - Move housekeeping, and the stale-text fixes that don't touch D entries, into a separate short change or a lightly reviewed appendix.
  - Defer the held-out test to the first D34 prompt change, and add it to `tests/test_samples.py` using the existing helpers.
  - Drop CUJ 5.

  The design then matches its title, and its NFR becomes "comments, docs and one new test only".

### 7. Alternative A is a straw man, and the case for the history file is never made - Severity: Nit
* **Reviewer Lens:** `egm-zoom-out` (A)
* **Affected Scope:** Lines 169-176, 341-356.
* **Discrepancy Description:** The fair minimal alternative is never compared: rewrite `decisions.md` in place, keep the old text in git (a tag), and add the same test. The frozen history file is probably the better choice, because live-run evidence needs stable link targets. But the design never says so.
* **Subsumes:** Stage 5 #8.
* **Rationale & Recommendation:** Restate Alternative A as "rewrite in place plus test". Give the stable-evidence-links reason for choosing the history file. Note that the allowlist from finding 2 already keeps the history file out of the test.

### 8. Hard-coded per-file cite counts cause the count disagreement and will go stale - Severity: Nit
* **Reviewer Lens:** `egm-zoom-out` (A and B)
* **Affected Scope:** Lines 33-39, 347, 600-643.
* **Discrepancy Description:** The per-file Q counts in the plan are why the reports disagree about the Q count. They are also a small example of the drift the design is fighting.
* **Subsumes:**
  - Stage 5: #10
  - Stage 6: #14
  - Stage 7: M3
* **Rationale & Recommendation:** In the plan, replace the counts with "all Q cites in this folder". Give one checked total, in the Problem section only.

## Local fixes still outstanding (not structural)

These still need an edit, but no design change:

- **Undefined terms:** N IDs, grilling questions, owner, held-out (Stage 6 #9, #13; Stage 7 M12).
- **Bare D numbers in the design itself:** Stage 7 M11. Finding 5(a)'s cite format fixes this if it is applied to the document.
- **A short Risks section:** Stage 7 M1. After the fixes above, three risks remain: meaning drift in the rewrite, unchecked evidence anchors, and the context cost of the index.
- **The behaviour check command:** Stage 6 #21.
- **Finding the paused cites later:** search for "D34 (paused)" (Stage 6 #22).
- **Missing D14, D23 and D26 in the Problem list:** Stage 7 N8.
- **Diagram, wording, dates and wrap fixes:** Stage 7 N4, N5, N11, N12.

## Suggested order of fixes

1. Findings 1 and 2. Together they clear every Stage 6 and Stage 7 Blocker.
2. Finding 3. This follows almost automatically from 1 and 2.
3. Finding 6. This shrinks the document before anything is rewritten.
4. Finding 4.
5. Finding 5. This is the one real choice for the owner: canonical heading cites, or free text with an accepted drift risk.
6. The Nits and the local fixes.

Deferrable without hurting the goal: sub-IDs, the held-out prompt test, the housekeeping, and an index generator.
