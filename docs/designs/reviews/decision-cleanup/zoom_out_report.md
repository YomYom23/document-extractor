# Goldfish Review Report: Stage 5, Initial Zoom Out Review

**Target:** `C:\Users\Yomi\PycharmProjects\document-extractor\docs\designs\decision-cleanup.md` (lines 1-692)
**Reviewers:** `egm-zoom-out`, two independent instances (A and B)
**Standard:** `C:\Users\Yomi\.claude\plugins\cache\egm\egm\0.1.0\resources\document_standards\zoom-out-standard.md`

**Context check:** Both reviewers passed it. The goal is clear: make D cites readable on their own, and stop readers landing on rules that are out of date. The core approach is the right size: keep the D numbers, state one current rule per ID, and have a test reject unknown IDs. The findings below are about rules being spread out or written twice, scope creep, and places where the design argues against itself.

**Severity breakdown:** 0 Blockers, 4 Major, 7 Nits.

Note: the persona file is `agents/zoom_out.md`, not `zoom-out.md`.

---

## Prioritized Findings (Blockers -> Major -> Nits)

### 1. Amendment chains don't fix the problem the design names - Severity: Major
* **Reviewer Lens:** `zoom-out` (A and B)
* **Affected Scope:** Lines 227-245 (section 3), together with lines 27-32 (Problem), 56-58 (Goals) and 185-195 (section table)
* **Finding:** The Problem section names "the arithmetic rule is spread over six entries" as a main pain, but the design keeps all six entries. Lines 233-237 also leave it unclear which entry owns the rule text:
  * The older entry has "its Rule rewritten to the current rule".
  * The later entry "describes only what it added".
  
  Either the full rule is written twice (D9 and again in D20, D22 and D34), or the reader still builds the rule from the chain. The second is the same objection the design uses to reject Alternative A (lines 349-351), and it breaks the Goal of showing the current rule in one entry.
  
  The claim that "the IDs of a chain sit together" (line 240) is also false under the section table:
  * D9 is under Schema, while D20 and D22 are under Scoring.
  * D34 has its own section.
  * D25 (Extractors) amends D16 (Interface).
  * D26 amends D10 (Schema).
* **Suggested fix:** Pick one ownership model and state it. For example: the oldest entry in a chain holds the complete current rule, and each later entry holds only `Changes: Dx` plus its own Why and Evidence. Another option is a one-sentence "current rule" line at the top of each topic section that has a chain. Then either place each chain in one section, or delete the "sit together" claim. Work the arithmetic chain through as an example to show the Goal is met. Either test that every `Changes:` has a matching `Changed by:`, or keep only one direction, since both are kept by hand and nothing checks them.

### 2. Cite explanations are an unchecked third copy of every rule, which the design rejects elsewhere - Severity: Major
* **Reviewer Lens:** `zoom-out` (A Major, B Nit; merged at Major)
* **Affected Scope:** Lines 54-55, 86-87, 209, 286-288, 293-295, compared with Alternative E (397-406) and Alternative F (408-418)
* **Finding:** The design rejects Alternative E because explanations would be "a third copy of each rule ... with nothing to keep them in step". It rejects Alternative F because "a manual grep is the kind of step that drifted before". The chosen design then adds about 180 hand-written cite explanations. It does not check them, and keeps them current only by a manual `grep -rn "D12\b"` (286-288). The root problem is drift, and this is the largest new place for drift. The rejection reasons cut against the design itself.
* **Suggested fix:** Pick one:
  * (a) Make explanations checkable. For example, require the cite text to start with the entry heading, as in `D11 (Missing is null, never guessed)`, and have the cite test check it.
  * (b) Add explanations only where code needs local context.
  * (c) Keep the plan, but say explicitly that the drift control is line 294: explanations describe what *this code* does, which changes less often than the rule wording. Record the rest as an accepted risk, and soften the E and F rejections so they don't condemn the chosen approach.

### 3. Paused D34 work is written into the current-rules file as sub-IDs - Severity: Major
* **Reviewer Lens:** `zoom-out` (A and B)
* **Affected Scope:** Lines 83-84, 217-220, 534-535, 620-623
* **Finding:** The design pauses D34 but still writes the line-items brief's "settled points" as paused D34 sub-IDs. That is speculative work on an unbuilt feature, and the brief already expects N3 to be split and N1 widened. Each sub-ID adds:
  * a heading,
  * a session-loaded index line,
  * an item for the owner's single review in commit 4.
  
  The `rules_extractor.py:313` cite then depends on a sub-ID made only for this purpose. The brief is already committed (lines 498-504), so writing the sub-IDs keeps nothing that would otherwise be lost.
* **Suggested fix:** Give D34 one parent entry: status `paused`, a summary of what Q88-Q105 decided, and an Evidence link to `docs/designs/line-items-brief.md`. Add sub-IDs as the first step when D34 resumes. Point `rules_extractor.py:313` at `D34 (paused)`.

### 4. The held-out prompt-leak test is outside this design's scope - Severity: Major
* **Reviewer Lens:** `zoom-out` (A Major, B Nit; merged at Major)
* **Affected Scope:** Lines 63-66, 133-138, 320-324, 427-429, 576-583
* **Finding:** The test enforces a real README invariant, but it is new feature work riding along with a docs migration:
  * CUJ 5's trigger ("while folding label rules, a held-out vendor name is copied into `INSTRUCTIONS`") cannot happen here. No commit edits `INSTRUCTIONS`, and the Non-Goals rule out behaviour changes.
  * The plan puts new label-discovery code in `test_llm_extractor.py`. `tests/test_samples.py` already has `set_directories()`, `SAMPLES_DIRECTORY` and `PRIVATE_DIRECTORY`, which cover `samples/heldout` and `samples/private/heldout`.
  * A casefolded substring match on short or generic invoice numbers can fail when nothing has leaked.
* **Suggested fix:** Move the test to its own small change, or to the start of D34 prompt work. If it stays:
  * Make it a separate stated goal ("enforce the README held-out invariant before D34 edits the prompt").
  * Put it in `tests/test_samples.py` so it reuses the existing helpers.
  * Match whole words or values above a minimum length.

### 5. The two scan-scope descriptions disagree - Severity: Nit
* **Reviewer Lens:** `zoom-out` (A and B)
* **Affected Scope:** Lines 306-308 compared with 563-566
* **Finding:** Section 7 scans all of `docs/` except `decisions-history.md`. Item 15 also excludes `docs/designs/`. That exclusion is required: this design and the moved briefs contain Q tokens, so without it `test_no_q_cites` would fail after commit 5. Section 7 is the description a reader trusts.
* **Suggested fix:** Add the `docs/designs/` exclusion to section 7, with a clause saying why: design records are historical, like the history file.

### 6. The index is a hand-kept copy of the headings - Severity: Nit
* **Reviewer Lens:** `zoom-out` (A and B)
* **Affected Scope:** Lines 254-271, 313-315, 541-545
* **Finding:** `decisions-index.md` copies every heading and status by hand, and a test forces an exact match. Every heading or status change means editing two files and running the test to find the mismatch.
* **Suggested fix:** Have `test_index_matches_decisions` print the full expected index when it fails, so the fix is copy-paste, or generate the index with a small script. You could also drop the status column so less has to stay in step.

### 7. Commit 4 is one large rewrite with one review, and the Rollback note is wrong - Severity: Nit
* **Reviewer Lens:** `zoom-out` (B)
* **Affected Scope:** Lines 247-250, 528-539, 686-687; Rollback at 430-433
* **Finding:** In one commit, commit 4 writes:
  * every entry and sub-ID,
  * the index and the history header,
  * the Q-to-D table,
  * the tests and the README links.
  
  All of it goes through one owner read-through, so a mistake in a chain fold is hard to spot. The Rollback note says reverting commit 3 "leaves no `docs/decisions.md`". Once commit 4 exists, reverting commit 3 on its own would conflict instead.
* **Suggested fix:** Split commit 4 into (a) the new `decisions.md`, index and history header, reviewed with the fold table, and (b) the tests and README links. Rewrite the rollback sentence to say commits 3 and 4 revert together.

### 8. Alternative A is set up to lose, and the history file can still mislead searches - Severity: Nit
* **Reviewer Lens:** `zoom-out` (A)
* **Affected Scope:** Lines 341-356; history banner at 169-170
* **Finding:** Alternative A is defined as "no test" and rejected partly because nothing catches stale cites. The fairer simple alternative is to rewrite `decisions.md` in place, leave the old wording in git or behind a tag, and add the same test. With a separate history file whose headings match D for D, a grep for `D24` hits both files. The warning banner sits only at the top of the history file.
* **Suggested fix:** Compare against "rewrite in place + test", and say why a frozen history file is better than git history (stable link targets for live-run evidence is a fair reason). If the history file stays, label each heading, for example `## D24 (historical) ...`.

### 9. The `superseded by Dx` status has no use case - Severity: Nit
* **Reviewer Lens:** `zoom-out` (B)
* **Affected Scope:** Lines 210-212, compared with 238 and 284-285
* **Finding:** Section 3 says no ID becomes a stub, and dropped rules use `retired`. That leaves two ways to record an amendment (`Changed by:` and `superseded by`), and no case needs the second.
* **Suggested fix:** Name an entry that will actually be superseded, or drop the status and keep `active / paused / retired` plus `Changes` / `Changed by`.

### 10. The Detailed Implementation Plan has detail that will go stale - Severity: Nit
* **Reviewer Lens:** `zoom-out` (A; B disagreed, saying this detail belongs in the plan section)
* **Affected Scope:** Lines 437-668, especially 559-572 and 601-643
* **Finding:** Per-file cite counts ("6 Q cites, 13 D cites") go out of date as soon as anyone edits a comment, which is the drift this design is about. Helper names and regexes are less of a concern.
* **Suggested fix:** Replace the counts with "all Q cites in this folder". Keep the scan scope and the four checks.

### 11. Unrelated housekeeping is bundled in - Severity: Nit
* **Reviewer Lens:** `zoom-out` (A)
* **Affected Scope:** Lines 70-72, 326-337, commit 2 (454-506)
* **Finding:** Four changes have nothing to do with the decision system: deleting the drift report, deleting `IDEA.md`, adding the `httpx2` dev dependency, and fixing `ATTRIBUTION.md`. They are fine hygiene, but they make the design longer to review. Both reviewers agree the changes themselves are right.
* **Suggested fix:** Move them to a short "Housekeeping (unrelated)" section, or into a separate change.
