# Goldfish Review Report: Stage 8, Intermediate Zoom Out (round 2)

**Target:** `docs/designs/decision-cleanup.md` (lines 1-707)
**Reviewers:** `egm-zoom-out`, run as two independent instances (A and B)
**Context:** the round-2 reports from Stages 5, 6 and 7 (`zoom_out_report_r2.md`, `comprehension_report_r2.md`, `critic_report_r2.md`). The target has not been edited since those reports were written.

## Verdict

The design passes at altitude. 0 Blockers, 4 Majors, 4 Nits.

The goal and the root cause are right, and the core plan is in proportion:
- keep the D numbers
- freeze the old log as history
- write one current rule per D
- explain every cite
- add one pytest check

Stages 5-7 raised about 50 findings. Most of them do not need separate fixes, because they come from four structural choices. Changing those four removes or absorbs about 20 earlier findings, and the design gets shorter.

Both instances found M1, M2 and the stale-text part of M2 on their own, and both found N1. M3 and M4 came from one instance only. They are rated Major because each removes several findings at once.

Report names used below: **ZO** = zoom_out_report_r2, **CO** = comprehension_report_r2, **CR** = critic_report_r2. Numbers refer to the findings in those reports.

---

## Prioritized Findings

### M1. "Paused" mixes up "D34 is decided" with "D34 is built" - Severity: Major
* **Reviewer Lens:** `zoom-out` (A and B, found independently)
* **Affected Scope:** lines 74, 99-100, 218-219, 247-249, 294, 322-323, 358-360, 409-418, 434-436, 542-560, 622-623, 655-656
* **Finding:** The design makes D34 a two-line `paused` entry and says its "full rules are written when D34 restarts" (line 249). But the history (`docs/decisions.md:377-413`) shows D34 as settled through Q88-Q105:
  * what counts as a line
  * how lines are scored and matched
  * the LLM number formats
  * the label conventions

  45 committed labels (25 IEB and 20 Sinabis) already follow those conventions. The build work is paused. The decision is not. Treating D34 as undecided forces four special mechanisms:
  * a third status value
  * a `D34 (paused):` cite form with its own grep
  * a stub entry
  * commit 1, which edits a file that commit 3 then freezes

  It also leaves the new `decisions.md` with no current rule for conventions that committed data already obeys, which goes against the Goal at lines 73-75. Some of the "paused" markers are also wrong. For example, `rules_extractor.py:313` stays at null for line items for good (Q88: LLM only), so the restart grep would return lines that never need to change.
* **Absorbs:** CR #3 (chain links to the paused D34 undefined), CO #1 (the paused-chain half), CO #9 (ATTRIBUTION wording slips past the grep), CO #10 and CR #6 (no exact text for the "D34 (paused)" comments), ZO #4 (commit 1 edits a file frozen later), and the D34 risk at lines 434-436.
* **Suggested fix:**
  * Write D34 from the history like every other entry: status `active`, a numbered summary of its settled rules (as D24 gets), and `Changes: D9, D12`.
  * Record the build state as a fact, not a status. Add one line, either under the Rule or in Open problems: "Not built yet: labels done for IEB and Sinabis; scorer and LLM work paused 2026-10-29."
  * Reduce the statuses to `active | retired`.
  * Drop rule 4, the `D34 (paused)` marker and commit 1.
  * Code comments say what the code does now, e.g. `D34: rules extractor never extracts line items (LLM only)`. Add "not built yet" only where the code really is unbuilt (`llm_extractor.py:100`, and the `HEADER_FIELDS` comment in `scoring.py`).
  * The non-goal at lines 99-100 still holds: no D34 work beyond writing its entry.

### M2. The design lists migration content item by item instead of giving one rule for where content comes from - Severity: Major
* **Reviewer Lens:** `zoom-out` (A and B, found independently)
* **Affected Scope:** lines 87, 208-210, 240-254, 256-284, 405-421, 425-427, 619-627, 647-677
* **Finding:** The format is specified very exactly: headings, the index line, regex tokens and helper names. What the 34 rewritten Rules must say, and what counts as stale text, is handled by lists with exceptions. Every gap in a list then becomes a finding, and each review round finds another one. Two examples:
  * Line 87 makes the stale-text table in section 8 the complete list. No hand-written table can be shown to be complete.
  * The owner check (lines 281-284) covers only the chains, so most entries get no review against their history.

  The Risks mitigation at lines 425-427 claims more than section 3 actually promises. Claude writes the content and the owner reviews it, so the design only needs a rule for where content comes from and a review that covers every entry.
* **Absorbs:** CO #1 (full chain list, mostly), CO #2 (N3 text at `null-sources.md:27` missing), CO #3 (how much of `null-sources.md:8-9` is replaced), CO #4 (where the D21-D23 settled rule comes from), CO #6 (what goes in Open problems), CO #14 (a Q used as a name), CO #16 (owner check covers only chains), CR #6 (stale-text table incomplete), CR #8 (where the rules figures come from), CR #13 (path style).
* **Suggested fix:** Add four sentences to section 2 and section 8:
  1. "Each Rule states what the history decided, corrected to what the code, labels and prompt do today. Every place where they differ goes on a list for the owner." This settles D21-D23 (the code built the recommended choices) and D12 (line items are not scored yet; D34 changes that).
  2. "Open problems = every `### Open problem` section in the history (today, one under D24), plus the D34 build state."
  3. "Every live claim about line items states D34's current state. Every count and held-out claim matches `comparison.md`. No Q remains. While rewriting each cite in commit 5, check the sentence around it against the new Rule." Name the search that drives this, e.g. `git grep -nE "not extracted|in progress|header.only|header fields only|never been run|scored later"`.
  4. "Before commit 4, Claude produces one review list for the owner: every entry's one-line Rule, every link pair (including the targets of D22, D28 and D30 that line 50 promises), the difference list, and the open problems. The owner checks every entry, not only the chains."

  Mark the section 8 table "examples, not exhaustive". Keep exact replacement text only where there is no cite to anchor it: `ATTRIBUTION.md:3`, the README "D and Q numbers" lines, and `null-sources.md:8-9` (say "replace only the quoted fragments"). Do not add a full chain table to the design. The review list built from the file is that table.

### M3. Topic grouping plus a separate Status line make the index format and check 4 fragile - Severity: Major
* **Reviewer Lens:** `zoom-out` (A; B agreed on number ordering as a Nit)
* **Affected Scope:** lines 197-206, 212-223, 288-298, 389-390, 684-686
* **Finding:** Entries are grouped by topic, so they are not in number order, and the status sits on its own line under the title. As a result, the index needs a new line format with two-space fields and its own regex, built by joining two parsed sources and re-sorting them. Several precision and rendering findings come from that format. The consecutive `**Field:**` lines also run together into one paragraph in any Markdown preview.
* **Absorbs:** CO #5 (index layout not exact), CO #18 (missing or invalid Status line), CR #7 ("about 50 lines"; it is about 34), CR #10 ("no other numbers" ambiguous), CR #16 (renders as a run-on paragraph), ZO #8 (topic upkeep), ZO #5 in part.
* **Suggested fix:**
  * Order `decisions.md` by number.
  * Put the status in the heading: `### D11. Missing is null, never guessed (active)`.
  * Build the index from those heading lines as list items, in file order.
  * Check 4 becomes an exact string comparison: the index lines without `- ` equal the `### D` headings without `### `, in order.
  * Write the remaining fields as a bullet list.
  * If topics are still wanted, add a short "see also" table at the top that the test ignores.

### M4. Allowing new linked entries forever brings back the drift the design exists to fix - Severity: Major
* **Reviewer Lens:** `zoom-out` (A; B instead asked for a back-link symmetry check)
* **Affected Scope:** lines 141-145, 264-266, 305-321
* **Finding:** The `Changes:` / `Changed by:` links are needed to migrate the existing log. But section 5 keeps open, for good, the choice between editing an entry in place and opening a new linked D. The test for choosing ("worth keeping on their own") is subjective and is worded two ways. Every new chain also needs a hand-kept back-link that no test checks. That is the failure the design was written to stop.
* **Absorbs:** CR #5 (subjective new-D vs edit-in-place rule), ZO #1 (back-links never checked), CR #18 in part ("chain" and "amend" undefined).
* **Suggested fix:** Pick one of these:
  * **(a), preferred as the simpler option:** after the migration, a change to an existing rule always edits that entry in place. The reasons go in its Why, and git log keeps the history. A new D is only for a new rule and never carries `Changes:`. The migrated chains become a fixed set that the owner checks once, and CUJ 3 shrinks to "edit D12 in place".
  * **(b):** keep both options, but add a back-link symmetry check to the existing test (about ten lines, in a file it already parses). With M1 adopted, D34 needs no exception.

---

### N1. `git ls-files` adds nothing to an explicit include list - Severity: Nit
* **Reviewer Lens:** `zoom-out` (A and B)
* **Affected Scope:** lines 368-380, 686-687
* **Finding:** The include list already contains only fixed paths and one-level globs under named folders, so `.venv/`, `samples/` and `line-drafts/` can never match. Going through git adds three problems:
  * a subprocess
  * a choice of working directory
  * untracked new files escape the check in the commit that creates them
* **Absorbs:** CR #2 (which should be a Nit, not a Major, since the next commit catches it), and the `git ls-files` and fnmatch half of CO #18.
* **Suggested fix:** Glob the include list with non-recursive `pathlib` globs from the repo root, found from the test file's path. Drop the "tracked" wording.

### N2. Migration aids and side work are being stored in permanent files - Severity: Nit
* **Reviewer Lens:** `zoom-out` (A and B; they split on the Q-to-D table)
* **Affected Scope:** lines 85-86, 179-184, 339-344, 396-404, 553-601, 615-616
* **Finding:** Commit 2 bundles housekeeping that has nothing to do with the decision system: httpx2, deleted files, committing the READMEs, and six review reports. Committing the reports goes against the reason given for deleting the drift report, and line 599 sends future reports to the same folder.
* **Absorbs:** ZO #3, ZO #9, CR #12 (second httpx2 importer).
* **Suggested fix:**
  * Commit at most `consolidated_review_report.md` and drop line 599.
  * Name both files that import httpx2, including `tests/test_llm_extractor.py`.
  * Add `line-drafts/` to `.gitignore` in commit 2 (CR #4). Today it covers only `samples/private/`.
  * On the full Q-to-D table in history (ZO #2, CO #7, CR #11), the two instances disagreed:
    * A: keep the table in the design only.
    * B: keep it in history, because recent commit messages (c6aec15, 1a587e9) cite Q numbers.

    Either is fine. Whichever you choose, fix the D34 source wording to "heading and body".

### N3. Helper names and optional fields - Severity: Nit
* **Reviewer Lens:** `zoom-out` (A and B)
* **Affected Scope:** lines 216-238, 683-688
* **Finding:** The helper function names are implementation detail (ZO #5) and invite questions about error behaviour (CO #18). The `Rejected` field is required even where nothing was rejected (ZO #7).
* **Suggested fix:** Replace the helper list with "implements section 7". Make `Rejected` optional.

### N4. Many Stage 6 and Stage 7 polish findings are not worth a revision round - Severity: Nit
* **Reviewer Lens:** `zoom-out` (A and B)
* **Affected Scope:** whole document
* **Finding:** The design becomes an archive once it is implemented, and its two readers (the owner and Claude) know the repo.
  * **Leave these:** CR #13, #14, #15, #17, #19-#27; CO #8, #11, #17, #19. CO #20 is already handled at lines 608-609.
  * **Fix only the factual errors:**
    * CR #1: there are three public sample sources, including `b_`. This is a one-word Nit, not a Major.
    * CR #12: httpx2 has a second importer, and the comparison.md goal describes links that do not exist yet.
    * CO #3 and CR #8: covered by M2.
    * CO #14: covered by M2.
  * CO #13 and CR #9 (the cite test scans its own file) need one clause at most: "the test file contains no literal D/N/Q example tokens".
  * Pinning the AST comparison to a fixed commit hash costs one word. Do it if convenient.

---

## Net effect

Adopting M1-M4 and N1-N2 removes from the design:
* the third status
* the `D34 (paused)` cite form
* commit 1
* the index field format
* the subjective numbering rule
* the git subprocess

About 20 earlier findings are absorbed, and the design gets shorter. Nothing found here is a Blocker.
