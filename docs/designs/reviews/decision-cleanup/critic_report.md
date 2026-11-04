# Goldfish Review Report (Stage 7, Critic Review)

**Target:** `C:\Users\Yomi\PycharmProjects\document-extractor\docs\designs\decision-cleanup.md` (lines 1-436; lines 437-692, the implementation plan, were read only for context)

**Reviewers:** `egm-design`, `egm-structural`, `egm-style`
**Standard:** `C:\Users\Yomi\.claude\plugins\cache\egm\egm\0.1.0\resources\document_standards\feature-spec-standard.md`. The design and structural reviewers were told to use it. The style persona names no default standard, so the style reviewer used it as well.

**Totals after deduplication:** 1 Blocker, 12 Major, 12 Nit.

The reviewers also checked these claims against the repo and found them correct:
- `rules_extractor.py:313` reads "not extracted yet (D24)".
- `null-sources.md` has headings N1 to N20.
- `null-sources.md:9` says the held-out set has never been run.
- `ATTRIBUTION.md:3` says all invoices are synthetic.
- The D26 run command points at a script that D28 deleted.
- The topic table (lines 185-195) lists each of D1 to D34 exactly once.
- The list of seven amending entries is correct.

---

## Blocker

### B1. As written, the cite test would fail on this design and on the moved briefs
- **Reviewer lens:** `egm-design`. `egm-structural` and `egm-style` raised the same point as a Major.
- **Lines:** 302-318 (Section 7) and 63-64 (Goals)
- **Finding:**
  - Section 7 scans all of `docs/` except `decisions-history.md`, and that includes `docs/designs/`.
  - This design contains tokens the test rejects:
    - Q tokens such as Q24, Q31, Q47, Q99, Q105 (lines 172-173) and Q1 (line 300).
    - IDs that do not exist, such as D35 and D24.3 (lines 77, 122, 128, 260).
  - The two briefs being moved into `docs/designs/` contain more Q tokens. So `test_no_q_cites` would fail.
  - The plan (line 565) quietly leaves out `docs/designs/`, so the spec and the plan disagree.
  - "Every `README.md` and `CLAUDE.md`" has no root folder and no exclusions. `.venv/` holds third-party READMEs today (mypy typeshed, openai), and those can contain tokens like D2 or N1.
- **Suggested fix:** Make Section 7 the one place that defines the scan list, and make the plan match it. Do one of these:
  - Scan only tracked files, for example from `git ls-files`.
  - Or list fixed paths plus the README and CLAUDE files in the repo itself.

  Then state the exclusions outright: `docs/designs/`, `docs/decisions-history.md`, `samples/`, `.venv/` and `__pycache__`. Give the reason too: designs and briefs are historical records, like the history file.

---

## Major

### M1. No Risks and Mitigations section
- **Reviewer lens:** `egm-design`, `egm-structural`, `egm-style`. Structural rated this Blocker-or-Major.
- **Lines:** whole document. Risks are scattered across 286-288, 424-426 and 430-433.
- **Finding:** The standard says a spec must state its constraints, how it can fail, and how each failure is handled. The design has Non-Functional Requirements, but no risks section. These risks are stated nowhere, or only in passing:
  - Wrong Q-to-D mappings.
  - Claude changing a rule's meaning while rewriting about 34 entries, with only one owner review to catch it.
  - The regex matching tokens that are not decisions, such as "Q1 2026" or "N1".
  - Explanations next to cites drifting away from their rule (see M2).
  - Evidence links into `decisions-history.md#...` anchors, and links from `comparison.md` and `null-sources.md`. Nothing checks these, so they break silently.
  - The index loaded into `CLAUDE.md` growing, which costs context in every session.
  - The CLAUDE.md rule "always explain a D number" cannot be tested.
- **Suggested fix:** Add a `## Risks & Mitigations` H2. List each risk with its mitigation, or mark it as an accepted gap, and move the scattered items into it. For the anchor links, either have the test resolve anchors or record it as an accepted gap.

### M2. The chosen design adds unchecked explanations, which is the reason it gives for rejecting other options
- **Reviewer lens:** `egm-design`
- **Lines:** 54-55, 86-87 and 286-288, against 397-418 (Alternatives E and F)
- **Finding:**
  - Alternative E is rejected as "a third copy of each rule ... with nothing to keep them in step".
  - Alternative F is rejected because a manual grep is "the kind of step that drifted before".
  - Yet the chosen design adds about 180 rule summaries in comments that nothing checks. It keeps them in step with a manual grep after each Rule change, and a Non-Goal rules out any automated check.
- **Suggested fix:** Pick one of these:
  - Accept the gap openly and record it as a risk, with the reasoning (two readers, the cost of a check).
  - Add a cheap guard. For example, when a Rule changes, the test lists every cite of that ID for review.
  - Keep the explanations short and tied to what the code does, not restated rules, so they need to change less often.

### M3. The Q-cite count disagrees with itself and with the repo
- **Reviewer lens:** `egm-structural`, `egm-style`, `egm-design` (design rated it a Nit)
- **Lines:** 39 and 347-348
- **Finding:** Line 39 says "about 31" Q cites. Alternative A says "about 34 Q edits". A repo search, and the plan's own per-file counts, both find 37:
  - 13 in code
  - 16 in tests
  - 5 in `null-sources.md`
  - 3 in `comparison.md`
- **Suggested fix:** Use one checked figure everywhere, and say what it covers: code, tests and docs, excluding the history file and designs.

### M4. The status values are inconsistent, and "superseded" is never defined
- **Reviewer lens:** `egm-structural`, `egm-style`, `egm-design`
- **Lines:** 57, 210-212, 217-220, 238 and 313-315
- **Finding:**
  - The Goal (line 57) lists three statuses. Line 210 adds a fourth, `paused`.
  - Section 3 says "No ID becomes a stub" and handles every amendment with `Changed by` / `Changes`. Nothing says when `superseded by Dx` would apply instead.
  - The `####` sub-ID entries are never given a Status line. Check 4 needs every ID, sub-IDs included, to have a status that matches the index.
- **Suggested fix:**
  - List all four statuses in the Goal.
  - Define `superseded by Dx` in one sentence and say how it differs from `Changed by`, or drop it.
  - State that each sub-ID carries its own `**Status:**` line.

### M5. The owner check uses a "fold table" left over from the rejected folding option
- **Reviewer lens:** `egm-design`, `egm-style`
- **Lines:** 247-250
- **Finding:**
  - The check asks for a table of "the source IDs and the new entry they became". But the chosen design folds nothing: every ID keeps its own entry.
  - This review is the only safeguard against meaning errors in the rewrite, and as written it has nothing concrete to check against.
  - The order of steps is also unclear. "Claude writes the whole new file in one commit" comes before "the owner reviews ... before the commit is made".
- **Suggested fix:**
  - Replace the fold table with a per-entry table: ID, old history wording or a link to it, new Rule, and the `Changes` / `Changed by` lines it gains.
  - Put the steps in order: Claude writes the file, the owner reviews it with the table, then the commit is made.

### M6. It is unclear what an amended entry's Rule contains
- **Reviewer lens:** `egm-design`
- **Lines:** 227-241. This also affects CUJ 3.
- **Finding:** The earlier entry's Rule is "rewritten to the current rule", and the later entry "describes only what it added". So does D9's Rule repeat D20's and D34's changes, or not?
  - If it does, the same rule lives in two places, which is the duplication the design is trying to remove.
  - If it does not, D9 is not "the rule as it stands today" (line 57).
- **Suggested fix:** State one rule. For example: the earlier entry states the whole current rule, and the later entry states only its change and points back. Then work one real chain end to end (D9 → D20 → D22 → D34) to show the result.

### M7. Q numbers cannot be mapped to sub-IDs, and the sub-IDs are never listed
- **Reviewer lens:** `egm-design`
- **Lines:** 169-173, 217-220 and 290-292
- **Finding:**
  - Section 6 says a Q cite becomes "its D (or D sub-ID)" from the Q-to-D table. But the table is one row per D or per Q range, so it cannot give a sub-ID.
  - For example, `rules_extractor.py:189` cites "D24, Q26", and nothing says which D24.n that becomes.
  - The sub-IDs under D24 and D34 are never listed. Two people doing this work would produce different results.
- **Suggested fix:** Either have the Q table map each Q to its final ID, sub-ID included, or list the D24.n and D34.n sub-IDs with the Q numbers each one takes in.

### M8. The held-out prompt test guards against less than CUJ 5 suggests
- **Reviewer lens:** `egm-design`
- **Lines:** 65-66, 133-138 and 320-324
- **Finding:**
  - The test only catches a whole held-out `vendor_name` or `invoice_number` appearing in a prompt.
  - The real leaks so far were fragments. D33 records that "S.R.L." and "Pvt Ltd" came from held-out invoices.
  - `samples/private/heldout/` is checked only where it exists, so a clean clone checks only the public labels.
  - The change the CUJ describes (folding label rules into `INSTRUCTIONS`) is one this design forbids under "no behaviour change" (lines 80-82).
- **Suggested fix:** State the test's limits, and say it is there for when D34 resumes. Then either widen it (distinctive name tokens without generic suffixes, and line descriptions once D34 labels exist) or call it a smoke check rather than a guarantee.

### M9. The rollback claim does not hold for this commit sequence
- **Reviewer lens:** `egm-design`. `egm-structural` and `egm-style` rated it a Nit.
- **Lines:** 427-433
- **Finding:**
  - Reverting commit 3 (the `git mv`) after commit 4 has created a new `docs/decisions.md` causes a conflict. It does not "leave no `docs/decisions.md`".
  - Reverting commit 4 alone after commit 5 also conflicts.
  - Reverting commit 6 alone brings back Q cites in the docs while `test_no_q_cites` exists, so the tests fail.
  - From the plan, for context: `test_no_q_cites` lands in commit 5, but the doc Q cites are only removed in commit 6. So commit 5 is not clean, which contradicts line 73.
  - "Commit 3" and "commit 4" are only defined in the plan.
  - Commits 4 and 5 are not "small".
- **Suggested fix:**
  - Rewrite the claim as "revert in reverse order", or "revert as one unit from commit 4 onward".
  - Name commits by what they do, or link to the plan section.
  - In the plan, remove the doc Q cites before or with `test_no_q_cites`.

### M10. There is no test for when a change gets its own ID
- **Reviewer lens:** `egm-style`
- **Lines:** 121-122 and 281-282
- **Finding:** "If the change deserves its own record" and "worth recording on its own" are judgement calls with no rule behind them. Different Claude sessions will decide differently.
- **Suggested fix:** State a rule. For example: a new ID when the change came from a separate discussion or adds or removes behaviour; an edit in place when it only rewords or narrows.

### M11. The document uses the bare D numbers it says are useless
- **Reviewer lens:** `egm-style`
- **Lines:** 23, 28-38, 229-230 and 414
- **Finding:** Line 23 says a bare "D24" "tells the reader nothing". The Problem section then lists D9, D10, D12, D16, D19, D22, D26, D28, D30 and D34 without explaining them, and line 414 says just "(D13)".
- **Suggested fix:** Give each D number a short explanation the first time it appears, following the same rule CUJ 2 sets for Claude. For example: "D13 (every change ends with pytest, ruff and mypy)".

### M12. Terms and references a new reader cannot follow
- **Reviewer lens:** `egm-style`, `egm-structural`
- **Lines:** 40, 43-44, 63, 84, 148, 220, 267 and 412
- **Finding:**
  - "N ID" is used from line 63 on, but is only shown to mean the headings in `null-sources.md` in Section 7.
  - "grilling questions" (line 40) is never explained.
  - "The drift report" (line 43) is the evidence for the problem, but Section 8 deletes that file.
  - "the line-items brief" (lines 84 and 220) has no path.
  - "the YAGNI reviewer's preference" (line 412) refers to a review the reader has never seen. It also says who preferred the option, not what the option gains.
- **Suggested fix:**
  - Define N IDs the first time they appear.
  - Explain or drop "grilling questions".
  - State the drift report's finding directly, for example how many facts were wrong after how long, so the claim survives the file being deleted.
  - Give the brief's new path, `docs/designs/line-items-brief.md`.
  - Rewrite line 412 as what the option gains, for example "No test code to maintain; proportionate for two readers."

---

## Nit

### N1. The index length is given two ways, with no limit
- **Lens:** structural, style, design
- **Lines:** 67 and 266
- **Finding:** Line 67 says "about 40 to 60 lines" and line 266 says "about 50 lines". Nothing says what happens as D34 sub-IDs are added.
- **Fix:** Use one figure, say whether sub-IDs count toward it, and set a soft limit. For example, sub-IDs collapse into the parent line once the limit is passed.

### N2. The Status line and the index format are hard to parse
- **Lens:** structural
- **Lines:** 199-207, 258-262 and 313-315
- **Finding:** Status and Scope share one line. The index is space-separated, but "superseded by D35" contains spaces, so the columns are ambiguous. Line 254 says "one line per ID", but the example includes sub-IDs.
- **Fix:** Put Status on its own line. Define the index line format exactly. Write "per ID and sub-ID".

### N3. Alternative D breaks the template and repeats Section 3
- **Lens:** structural, style
- **Lines:** 242-245 and 387-395
- **Finding:** Alternative D lacks the Pros, Cons and Reason bullets the other alternatives have, and its reasoning repeats Section 3.
- **Fix:** Use the same bullets as the other alternatives, and keep the reasoning in one place with a pointer from the other.

### N4. The diagram is unclear, and the claims next to it overstate
- **Lens:** structural, style
- **Lines:** 144-160 and 264-265
- **Finding:**
  - `comparison.md` and `null-sources.md` hang off the history box with no arrow.
  - `null-sources.md` is a source of N IDs that the test reads, and the diagram does not show that.
  - "checks every arrow that carries an ID" is not true: Evidence anchors and the @-import are not checked.
  - "the index cannot drift" is only true while the test runs.
- **Fix:** Give `null-sources.md` its own box with its arrows. Write "checks the cite and index arrows" and "the test fails if the index drifts".

### N5. The "Open problems" row has no IDs in it
- **Lens:** structural, style
- **Lines:** 195
- **Finding:** The row puts prose in the "IDs" column.
- **Fix:** Rename the column to "Contents", or move the row into a note below the table.

### N6. The Non-Goal and the NFR list different sets of changed things
- **Lens:** structural, style
- **Lines:** 80-82 and 427-429
- **Finding:** Neither list mentions everything that changes: removing `IDEA.md`, `uv.lock`, the CLAUDE.md files and the moved briefs.
- **Fix:** Use one complete list in both places.

### N7. The cleanup list is incomplete
- **Lens:** structural, style
- **Lines:** 70-71, 88-90 and 328-337
- **Finding:**
  - The untracked `comprehension_report.md` and `zoom_out_report.md` in the repo root contain Q tokens, and the design neither removes them nor keeps them.
  - "both briefs" and "the three READMEs" are never named.
  - Nothing says what happens if `test_samples.py` turns out to have stale counts.
  - "All are kept on purpose" gives no reasons.
- **Fix:** Decide the fate of the two reports. Name the files. State the action for stale counts. Add a short reason for each item kept.

### N8. The list of entries showing an old rule is incomplete
- **Lens:** design
- **Lines:** 27-32
- **Finding:** The list leaves out D14 and D23 (amended by D32) and D26 (amended by D33).
- **Fix:** List them all, or say "for example".

### N9. The chat rule is written as a goal nothing can check
- **Lens:** design
- **Lines:** 67-69 and 266-268
- **Finding:** "Always explains a D number in chat" is stated as a goal, but nothing can enforce or measure it.
- **Fix:** Phrase it as a CLAUDE.md instruction, not a measurable outcome.

### N10. Notation is inconsistent
- **Lens:** style
- **Lines:** 148, 172 and 310
- **Finding:** Sub-IDs are written "D.n" in one place and "D<n>.<m>" in another. "One row per D" does not match the examples, which are one row per Q range or single Q.
- **Fix:** Use one form for sub-IDs, and write "one row per Q range or single Q".

### N11. Wording problems
- **Lens:** style
- **Lines:** 104, 175 and 293-295
- **Finding:**
  - Line 175 says the history file is "never cited by the test". `decisions.md` does link to it; the test just does not scan it.
  - "The comment reads like" (line 104) is vague.
  - "Cites that already read well" (lines 293-295) is subjective.
- **Fix:**
  - Line 175: "The cite test does not scan the history file."
  - Line 104: "The comment is, for example,".
  - Lines 293-295: "Cites whose sentence already states the rule".

### N12. Small housekeeping
- **Lens:** style
- **Lines:** 5, 93-95, 123 and 266
- **Finding:**
  - The header date, 2026-10-29, is earlier than the "Chosen 2026-10-30" recorded in the body.
  - "None open." could just be "None."
  - Lines 123 and 266 break the roughly 80-column wrap used elsewhere.
- **Fix:** Update the date or add a "Last updated" line. Trim the wording. Rewrap the two lines.
