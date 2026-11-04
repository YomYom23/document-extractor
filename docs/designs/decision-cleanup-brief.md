# Repo cleanup and a current-rules decision system

* **Author:** Yomi O Lebi
* **Date:** 2026-10-29

## Overview

Building has become hard to manage, mostly because of how decisions are kept.
`docs/decisions.md` is one 413-line append-only log (D1 to D34). Code, tests
and docs cite it about 180 times by D or Q number, and a bare "D24" in a
comment or in chat means stopping to find and read the entry. This work pauses
the line-items work (D34), removes what the repo no longer uses, and replaces
the log with a system where each decision's current rule lives in one place
and is readable in one line wherever it is cited. The only readers are you and
Claude.

## Analysis

### The real problem: the current rule is unreliable, not just slow to find

- **Amendments only point backwards.** D20, D25, D26, D31, D32, D33 and D34
  each say "amends Dx", but the amended entry never says "amended by". A
  reader following a cite to D9, D10, D12, D16 or D19 sees an out-of-date
  rule and gets no warning. Some amendments are not even marked (D22, D28,
  D30). The arithmetic rule is spread over six entries across about 360
  lines; the vendor-name rule over four.
- **Some text is already wrong.** Examples:
  - `rules_extractor.py:313` says line items are "not extracted yet (D24)",
    but D34 froze the rules extractor at null for good.
  - `null-sources.md:8-9` says "9 dev invoices" and "held-out has never been
    run". Both are out of date.
  - `samples/ATTRIBUTION.md:3` says all invoices are synthetic; the `r_`
    invoices are real.
  - D26 gives `scripts.live_llm_check` as a run command, but D28 deleted
    that script.
  - D21, D22 and D23 still say "pending your questions".
  - The D34 heading says Q88 to Q98, but the body runs to Q105, and it gives
    26 IEB invoices in one place and 25 in another.
- **Q numbers point at nothing.** About 31 Q cites in code have no entry
  anywhere. Each Q does map to exactly one D through the Q ranges in the D
  headings (D24 holds Q24 to Q31, and so on), so they can be rewritten
  mechanically.
- **One D is not one rule.** D24 alone holds about eight rules. Several
  entries mix rules with live-run logs and results that repeat
  `comparison.md`. Open problems sit inside rules. Process rules (D1, D4,
  D13, D17, D27) have no code to point at.
- **The same rule is written in two places.** The Invariants section of
  `document_extractor/README.md` restates about ten decisions. A one-line
  summary at every cite site would make a third copy, and copies drift.

### The pain is narrower than the numbers suggest

Many cites already read well, for example "wrong is worse than missing (D11)"
at `currency_resolver.py:80`. Only a few dozen are opaque, where the number is
the whole content: `# D26, Q39` beside `DEFAULT_MODEL`, "(Q55)" in `cli.py:42`,
and docstrings like "decisions D14, D23, D32". The rest of the pain comes from
chat, where Claude writes a bare "D24".

### Migration risks

- **Keep D numbers.** Commit messages ("D34 step 1"), `comparison.md` and
  `null-sources.md` rely on them, and `git log --grep=D30` should keep
  working. Renumbering or switching to name-based IDs throws that away.
- **Do not lose reasons.** Live runs, diagnoses and open problems exist only
  in `decisions.md`. Move it with `git mv` to a frozen history file before
  writing the new one, so nothing is deleted.
- **Do not search-and-replace blindly.** "Q1 2026" appears in a dev label,
  and a held-out label matches `D` plus digits. Limit rewrites to code,
  tests, scripts, docs, READMEs and `pyproject.toml`.
- **There is a third ID scheme.** `null-sources.md` defines N1 to N20, cited
  from `comparison.md` and `decisions.md`.
- **Many files are untracked.** The READMEs, the CLAUDE.md files, both
  briefs and the drift report are not in git. Decide each one before anyone
  runs `git add -A`.

### Noticing staleness

Nothing reads the docs today, so a removed ID fails silently. Five of six
reviewers want a pytest that checks every cited D exists in the rules file and
no Q appears outside the history file. The YAGNI reviewer thinks a grep is
enough for two readers. The drift report found doc drift within a day of
writing, which argues for the test.

### The held-out rule is spread out and partly unenforced

It appears in D6, D19, D29, D32, D33 and D34, with caveats that held-out is
"no longer clean" for two changes. Tests enforce the set split and the dev
default. Nothing enforces "held-out text never reaches the prompt"; it is only
a comment. Folding label rules into the new file is exactly when held-out
wording could slip into `INSTRUCTIONS`.

### Cleanup: less to remove than expected

The reviewers found no dead functions, constants or dependencies. All 67 PDFs
pair with labels, every `.gitignore` entry is used, and `token_usage.py` is
used.

**Safe to remove:**

| Item | Evidence |
| --- | --- |
| `2026-10-28_DRIFT_REPORT.md` | One-off; all its findings are fixed; nothing links to it. |
| `IDEA.md` | One line ("application that extracts structured fields"); nothing references it. |
| `scripts/__pycache__/live_llm_check.cpython-313.pyc` | Leftover of the script D28 deleted; git-ignored, local tidying only. |

**You decide:**

| Item | Why it is not provably unused |
| --- | --- |
| `scripts/live_currency_check.py`, `dotenv_key.py`, `samples/currency_snippets.json` | The run is done, but it is the evidence for `MIN_CONFIDENCE` and D28 chose to keep it. Reviewers recommend keeping. |
| `resolve_currency(min_confidence=...)`, `LlmExtractor(model=...)` | Never passed by callers; kept as test seams and for swapping models (D26). Reviewers recommend keeping. |
| `PdfPage.width` / `height` | Only a test reads them. |
| `line-drafts/` | Throwaway D34 drafting scripts, text dumps and renders, including renders of private and held-out invoices. Ignored only via `.git/info/exclude`. Deleting cannot be undone. Keep while D34 is paused, or delete once labelling is finished. |
| Finished one-off content in `decisions.md` | D17's build order, D13's "no commits" clause, the deleted-script note. Move to history, do not delete. |

Also noticed: tests import `httpx2` directly but it is not a declared
dependency; it arrives through `openai` and `typesafe-sdk`.

### Timing against D34

D34 is paused in the middle of labelling, and it will itself change several
"header only" comments. Glossing those now means touching them twice. Either
gloss everything now and accept the second touch, or leave the D34-affected
cites until D34 lands.

## Candidate designs

**Design 1: minimal, in place.** Keep `decisions.md`. Add a one-line index of
current rules at the top, "Amended by Dx" under each amended entry, D-plus-a-
gloss in place of every Q cite, and a rule in `CLAUDE.md`. No new files, no
test. Lowest cost (about 34 Q edits and a few dozen glosses), but the current
rule still lives in a chain, history and rules stay mixed, and nothing
catches staleness.

**Design 2: current rules keyed by the existing D numbers, plus frozen
history (recommended by the reviewers; chosen 2026-10-29).**
- `git mv docs/decisions.md docs/decisions-history.md`, frozen, with a
  Q-to-D table and the old wording.
- A new `docs/decisions.md` holds only current rules, still keyed D1 to D34.
  Each amendment chain is folded into the oldest ID, which lists the IDs it
  absorbed. New decisions get D35 onward.
- Each entry has: the rule in one stand-alone sentence, a status (active,
  superseded by Dx, retired), scope, why, rejected alternatives, and a link
  to evidence in `comparison.md` or history.
- Sections by topic, plus Process and Open problems. Sub-IDs (D24.1, D24.2)
  only where one D holds several rules.
- `CLAUDE.md` imports a short index (about 40 to 60 lines).
- Cites read like `# D26: date asked as year/month/day; a missing part gives null`.
- A pytest checks every cited ID exists and no Q remains.

It keeps commit and git-log traceability, gives one current text per rule,
keeps history apart, and makes staleness fail the tests. The cost is a
one-off, hand-written fold of each amendment chain, which you should check.

**Design 3: name-based IDs.** A `docs/rules.md` keyed by names such as
`null.never-guess`, about 50 to 70 of them, with a D/Q-to-name table in
history. The ID itself explains the rule, but every one of about 180 cites is
rewritten and commit messages need the mapping table for ever. Most churn for
two readers.

Design 1's index can be the first slice of Design 2 if you want the smallest
step first.

## Goals vs. Non-Goals

* **In-Scope Goals:**
  * Cleanup in its own commits, with evidence for each removal.
  * A current-rules file with one text per rule and forward-pointing
    amendments, with the stale text above corrected while folding.
  * A frozen history file made with `git mv`, holding old wording, live
    runs, diagnoses, frozen-commit hashes and the Q-to-D table.
  * Every cite reads as "Dn: what this code does because of the rule". No
    Q cites outside history.
  * A short index loaded for Claude, and a `CLAUDE.md` rule that Claude
    always explains a D number in chat.
  * A pytest for cite existence and no Q cites, scanning only code, tests,
    scripts and docs.
  * Fixing links and stale text in the READMEs, `null-sources.md`,
    `comparison.md`, `ATTRIBUTION.md` and `test_samples.py`.
* **Out-of-Scope Non-Goals:**
  * Renumbering or reusing D IDs.
  * Writing up the Q questions from chat history.
  * One file per decision.
  * Any change to code behaviour in the migration commits.
  * Line-items (D34) work beyond a "paused" status line.
  * Changes to sample data.
  * Checking that a cite's summary matches the rule word for word.

## Key Decisions & Staging for Next Steps

All decided on 2026-10-29, following the reviewers' recommendations:

1. **Design 2.** Frozen history file made with `git mv`; a new current-rules
   `docs/decisions.md` keyed by the existing D numbers; a short index imported
   by `CLAUDE.md`; glossed cites; the cite-existence test. Designs 1 and 3 are
   dropped. Every folded amendment chain (for example the arithmetic rule over
   six entries) is checked by you before the history file is frozen.
2. **Sub-IDs only where needed.** D24 and D34 get sub-IDs (D24.1, D24.2, ...);
   every other D stays one entry.
3. **N1 to N20 are covered by the cite test.** `null-sources.md` keeps its
   layout; the test checks that every cited N exists there.
4. **No "every rule is cited" test.** It would mean marking each process rule,
   which costs more than it saves for two readers.
5. **Held-out prompt test.** A small pytest checks that no held-out vendor
   name or invoice number appears in the LLM `INSTRUCTIONS`.
6. **D34-affected cites wait.** They are marked "D34, paused" now and get
   their real gloss when D34 lands, so each is rewritten once.
7. **Untracked files.** Commit the three READMEs, the three `CLAUDE.md` files,
   `concepts_brief.md` and `concepts_brief_line_items.md`. Delete
   `2026-10-28_DRIFT_REPORT.md`. Keep `line-drafts/` local, out of git, until
   D34 labelling is finished.
8. **Line-items brief decisions fold into D34's sub-IDs**, not new D numbers.
9. **Keep** `scripts/live_currency_check.py`, `dotenv_key.py`,
   `currency_snippets.json`, `resolve_currency(min_confidence=...)` and
   `LlmExtractor(model=...)`. Also **keep** `PdfPage.width` / `height`: page
   positions may matter for line-item table columns in D34.

Also in the cleanup: delete `IDEA.md` and the stale
`scripts/__pycache__/live_llm_check.cpython-313.pyc`, and declare `httpx2` as
a dev dependency because the tests import it directly.

Commit order, each ending with pytest, ruff and mypy clean:

1. Mark D34 paused.
2. Cleanup (the removals above, `httpx2`, commit the READMEs and CLAUDE.md
   files).
3. `git mv docs/decisions.md docs/decisions-history.md`.
4. New rules file, the index, the cite test and the held-out prompt test.
5. Rewrite Q cites and add glosses, folder by folder (comments only).
6. Fix links and stale docs (READMEs, `null-sources.md`, `comparison.md`,
   `ATTRIBUTION.md`, `test_samples.py`).
