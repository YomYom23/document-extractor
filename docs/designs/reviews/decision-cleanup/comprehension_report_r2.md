# Goldfish Review Report: Comprehension Test (Stage 6, re-audit)

**Target:** `docs/designs/decision-cleanup.md` (FeatureRange lines 1-535, DetailedRange lines 536-707)
**Standard:** `re-implementation-standard.md`
**Reviewers:** `egm-comprehension`, run as two independent instances. A read the document from start to end. B read the DetailedRange first.

**Summary:** 0 Blockers, 6 Majors, 14 Nits.

Both readers described the plan back correctly: six commits that are reviewed by the owner, a frozen history file, a new rules log with one entry per D, an index, Q cites rewritten as D cites, and a cite test. No program behaviour changes. They also confirmed these points against the repository:
- The topic table covers D1 to D34, each once.
- Every live Q cite is in the Q-to-D table.
- No file cites a D above D34 or an N above N20.
- `pyproject.toml` has only one cite (D28).
- The line numbers in the stale-text table match the files.

The findings below are the places where a newcomer still has to guess.

## Prioritized Findings (Blockers -> Major -> Nits)

### 1. The full list of chain links is not given - Severity: Major
* **Reviewer Lens:** `egm-comprehension` (A and B)
* **Affected Scope:** Lines 45-50, 256-266, 272, 281-284, 627
* **Discrepancy Description:** Commit 4 puts `Changes:` and `Changed by:` lines in every chain entry. The owner check reviews "the chain list". But only one pair is shown (D9 and D20).
  * Readers can rebuild most pairs from the old log: D20 changes D9, D25 changes D16, D26 changes D10, D31 changes D19, D32 changes D14 and D23, D33 changes D26, and D34 changes D9 and D12.
  * D22, D28 and D30 are said to change earlier entries "without saying it". Their targets are never named.
  * The Problem list (line 49) leaves out D14, D23 and D26, which are also changed later.
  * It is unclear whether a paused entry takes part in chains. D9 gets `Changed by: D20, D34` (line 272), but D34 is paused. Should D9's Rule reflect a paused change? Does the one-line D34 entry carry `Changes: D9, D12`?
* **Rationale & Recommendation:** The person doing the work should not have to make these design choices alone. Add a table to section 3 with every pair: later D, earlier D, and one line on what changed. Include D22, D28 and D30. State whether paused entries take part in chain links.

### 2. The stale N3 text in `null-sources.md` is not in the stale-text table - Severity: Major
* **Reviewer Lens:** `egm-comprehension` (A)
* **Affected Scope:** Lines 405-421 (section 8 table). Goal at line 87.
* **Discrepancy Description:** `docs/null-sources.md:27` (N3) says line items are "not extracted yet; header fields come first and line items are not scored (D12, D24, D26)". This is the same stale claim the table already fixes in `rules_extractor.py:313` and the READMEs. The goal says the stale text in section 8 is corrected, so this line would stay wrong.
* **Rationale & Recommendation:** Add a row. For example, `null-sources.md:27` becomes "D34 (paused): the rules extractor stays at null; the LLM does not extract line items yet". Or say that N3 is left alone on purpose until D34 restarts.

### 3. The `null-sources.md:8-9` row does not say how much text is replaced - Severity: Major
* **Reviewer Lens:** `egm-comprehension` (A)
* **Affected Scope:** Line 415
* **Discrepancy Description:** Lines 8-9 also contain "Rules extractor numbers are from a free run on 2026-10-19 (56 correct, 7 missing, 0 wrong)". The "Becomes" text leaves this sentence out. A reader cannot tell whether to delete it or to swap only the two quoted fragments.
* **Rationale & Recommendation:** Give the full new text of lines 8-9. Or say "replace only the quoted fragments; keep the rules-extractor sentence".

### 4. "The settled rule" for D21 to D23 is not defined - Severity: Major
* **Reviewer Lens:** `egm-comprehension` (B)
* **Affected Scope:** Lines 420 and 624-625
* **Discrepancy Description:** In the history file, D21 to D23 are "recommended choices, pending your questions". The design says the new entries state "the settled rule". It does not say where that rule comes from. It could be the recommended choice, what the code does today, or something decided somewhere else.
* **Rationale & Recommendation:** Name the source. For example: "the recommended choices as built in `scoring.py`, `arithmetic_check.py` and `pdf_reader.py`". Also list any choice that ended up different from the recommendation.

### 5. The layout of the index file is not exact enough to write the test - Severity: Major
* **Reviewer Lens:** `egm-comprehension` (A and B)
* **Affected Scope:** Lines 288-298, 389-390, 629-631, 686
* **Discrepancy Description:** Check 4 needs "exactly one line per entry, no other numbers". This leaves four questions open:
  * Can the file have a title, intro text or blank lines?
  * What does "no other numbers" mean? It could mean no line for a missing D, or no D tokens on lines that are not index lines.
  * How is a line split when the title contains spaces?
  * "About 50 lines" does not fit 34 entries plus "the next free number".
* **Rationale & Recommendation:** Say that the file holds only index lines, or name the lines the test skips. Give the line pattern as a regex, for example `^D(\d+)  (active|paused|retired)  (.+)$`. Define "no other numbers". Fix or drop the line count.

### 6. The content of "Open problems" is not given - Severity: Major
* **Reviewer Lens:** `egm-comprehension` (A and B)
* **Affected Scope:** Lines 208-210
* **Discrepancy Description:** The section gives only one example: ambiguous slash dates (D24). It does not say where the full list comes from, so the person doing the work has to choose what belongs there.
* **Rationale & Recommendation:** List the items. Or give a rule for finding them, for example: "every `### Open problem` section in the history file, plus any open or deferred item in D21 to D23".

### 7. The Q ranges do not all come "from its heading" - Severity: Nit
* **Reviewer Lens:** `egm-comprehension` (A and B)
* **Affected Scope:** Lines 339-342
* **Discrepancy Description:** The D34 heading says Q88 to Q98. Q99 to Q105 appear only in the body. In the same way, Q47 in D26 comes from an amendment subheading.
* **Rationale & Recommendation:** Change the text to "from its heading and body".

### 8. The count of 37 Q cites does not match the files - Severity: Nit
* **Reviewer Lens:** `egm-comprehension` (A)
* **Affected Scope:** Lines 57 and 448
* **Discrepancy Description:** Reader A counted 40 Q tokens on 38 lines. Some lines carry two, for example "(Q51, Q54)".
* **Rationale & Recommendation:** Say whether the number counts tokens or lines, and correct it.

### 9. The ATTRIBUTION wording slips past the D34 grep - Severity: Nit
* **Reviewer Lens:** `egm-comprehension` (A)
* **Affected Scope:** Line 418. Lines 322 and 436.
* **Discrepancy Description:** The new text "(D34, paused)" does not use the "D34 (paused):" form. So `git grep "D34 (paused)"` misses it. `samples/ATTRIBUTION.md` is not scanned by the test either.
* **Rationale & Recommendation:** Use "D34 (paused): labels include line items". Or say that ATTRIBUTION.md is left out of the grep on purpose.

### 10. Two comments have no exact new text - Severity: Nit
* **Reviewer Lens:** `egm-comprehension` (A and B)
* **Affected Scope:** Lines 655-656
* **Discrepancy Description:** `llm_extractor.py:100` and the `HEADER_FIELDS` comment at `scoring.py:10` ("line items are scored later (D12)") are to become "D34 (paused): ...". The table gives exact text for the matching lines elsewhere, but not for these two.
* **Rationale & Recommendation:** Add both to the section 8 table with their exact new text.

### 11. Some terms are not defined - Severity: Nit
* **Reviewer Lens:** `egm-comprehension` (A and B)
* **Affected Scope:** Lines 33-37, 60, 77, 81-82, 98, 107, 186, 399-401, 415, 417, 703, 707
* **Discrepancy Description:** These terms are used without a definition:
  * the `b_` prefix (InvoiceBenchmark). Terms defines only `a_`, `c_` and `r_`.
  * Jev, TypeSafe and `typesafe-sdk`
  * `httpx2`
  * "dev set", "live run", "drift check" and "frozen-commit hash"
  * "67 invoices" (the design never shows how 67 adds up)
  * "EGM"
* **Rationale & Recommendation:** Add a one-line Terms entry for each, or a link to where it is explained.

### 12. "The README line stays" is unclear - Severity: Nit
* **Reviewer Lens:** `egm-comprehension` (A and B)
* **Affected Scope:** Lines 637-638
* **Discrepancy Description:** It is not clear which line is meant. It is probably the existing `Read @README.md` line in CLAUDE.md.
* **Rationale & Recommendation:** Name the line.

### 13. The cite test scans its own file - Severity: Nit
* **Reviewer Lens:** `egm-comprehension` (A and B)
* **Affected Scope:** Lines 371 and 686
* **Discrepancy Description:** `tests/*.py` includes `tests/test_decision_cites.py`. Example tokens in its docstrings or test data, such as "D42" from CUJ 4 or "Q1", would make the test fail.
* **Rationale & Recommendation:** Add a rule that the test file holds no literal D, N or Q tokens, or leave the file out of the scan.

### 14. Rewrite rule 2 gives awkward text when a Q is used as a name - Severity: Nit
* **Reviewer Lens:** `egm-comprehension` (A and B)
* **Affected Scope:** Lines 348-350
* **Discrepancy Description:** `tests/test_llm_extractor.py:65` says "D11 and the Q47 amendment". Applied literally, rule 2 turns this into "D11 and the D26 amendment".
* **Rationale & Recommendation:** Add a note: a Q used as a name ("the Q47 amendment", "since Q47") is rewritten in words, as the `null-sources.md:110` row already does.

### 15. The "same commit" rule blocks changes that touch no code - Severity: Nit
* **Reviewer Lens:** `egm-comprehension` (A)
* **Affected Scope:** Line 307
* **Discrepancy Description:** The rule says every change to decisions.md goes in the same commit as the code it affects. A change that affects no code would have no allowed commit.
* **Rationale & Recommendation:** Add "(or alone, if no code is affected)".

### 16. The owner check does not say it covers whether each Rule is correct - Severity: Nit
* **Reviewer Lens:** `egm-comprehension` (A)
* **Affected Scope:** Lines 240-254 and 281-284
* **Discrepancy Description:** For most of the 34 entries, the design says nothing about what the new Rule should say. The owner check covers only overlap between chained entries. The Risks section (around line 426) suggests the owner also checks each Rule against history, but section 3 does not say so.
* **Rationale & Recommendation:** Say in section 3 that the owner checks each Rule against the history, not only the chains.

### 17. The date and position of the frozen note are unclear - Severity: Nit
* **Reviewer Lens:** `egm-comprehension` (B)
* **Affected Scope:** Lines 182 and 615-616
* **Discrepancy Description:** The note's date could be the date of commit 4 or the date of the move. "At the top" could mean above or below the existing `# ` title.
* **Rationale & Recommendation:** Say which date to use and exactly where the note goes.

### 18. The test helpers' error behaviour is not stated - Severity: Nit
* **Reviewer Lens:** `egm-comprehension` (B)
* **Affected Scope:** Lines 684-687
* **Discrepancy Description:**
  * `decision_entries()` does not say what happens when an entry has no `**Status:**` line, or has a status outside the three allowed values.
  * `scanned_files()` does not say which directory runs `git ls-files`, or how patterns are matched. Python's `fnmatch` lets `*` match `/`, so `tests/*.py` would also match files in subfolders.
* **Rationale & Recommendation:** State that both cases fail the test. Run from the repo root, found from the test file's path. Say how patterns are matched.

### 19. The behaviour check compares against a moving `main` - Severity: Nit
* **Reviewer Lens:** `egm-comprehension` (B)
* **Affected Scope:** Lines 695-699
* **Discrepancy Description:** `main` equals `cleanup` today (43969ce), but `main` can move. "The scratchpad" is not defined.
* **Rationale & Recommendation:** Compare against the commit before commit 1, given by its hash. Define or drop "the scratchpad".

### 20. The "clean checks" claim does not mention broken links - Severity: Nit
* **Reviewer Lens:** `egm-comprehension` (B)
* **Affected Scope:** Lines 538-540 and 609
* **Discrepancy Description:** After commit 3, the README links point at a file that no longer exists. The design accepts this. But "pytest, ruff and mypy clean" does not say that broken links are allowed in the meantime.
* **Rationale & Recommendation:** Say in the commit preamble that links are broken between commit 3 and commit 4.
