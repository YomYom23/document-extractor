import re
from pathlib import Path

REPO = Path(__file__).parent.parent
DECISIONS = REPO / "docs" / "decisions.md"
INDEX = REPO / "docs" / "decisions-index.md"
NULL_SOURCES = REPO / "docs" / "null-sources.md"

# The files whose D, N and Q cites are checked. The history file, the designs
# and the sample labels are never scanned: nothing here matches them.
SCANNED_GLOBS = ("document_extractor/*.py", "tests/*.py", "scripts/*.py")
SCANNED_FILES = (
    "README.md",
    "BLUEPRINT.md",
    "document_extractor/README.md",
    "scripts/README.md",
    "CLAUDE.md",
    "document_extractor/CLAUDE.md",
    "scripts/CLAUDE.md",
    "docs/decisions.md",
    "docs/decisions-index.md",
    "docs/null-sources.md",
    "docs/comparison.md",
    "pyproject.toml",
)

DECISION_TOKEN = re.compile(r"\bD\d+\b")
NULL_SOURCE_TOKEN = re.compile(r"\bN\d+\b")
QUESTION_TOKEN = re.compile(r"\bQ\d+\b")
DECISION_HEADING = re.compile(r"^### (D\d+)\. .+ \((?:active|retired)\)$")
NULL_SOURCE_HEADING = re.compile(r"^### (N\d+)\.")
INDEX_TITLE = "# Decision index"


def scanned_paths() -> list[Path]:
    globbed = [path for pattern in SCANNED_GLOBS for path in REPO.glob(pattern)]
    named = [REPO / name for name in SCANNED_FILES if (REPO / name).exists()]
    return sorted(path for path in globbed + named if path != Path(__file__))


def read_lines(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8").splitlines()


def decision_headings(lines: list[str]) -> list[str]:
    return [line for line in lines if line.startswith("### D")]


def heading_ids(lines: list[str], heading: re.Pattern[str]) -> set[str]:
    return {match[1] for line in lines if (match := heading.match(line))}


def unknown_tokens(
    name: str, lines: list[str], token: re.Pattern[str], known: set[str]
) -> list[str]:
    """`file:line: token` for each token not in `known` (pass an empty set to
    report every token)."""
    return [
        f"{name}:{number}: {found}"
        for number, line in enumerate(lines, start=1)
        for found in token.findall(line)
        if found not in known
    ]


def index_mismatches(index_lines: list[str], headings: list[str]) -> list[str]:
    expected = [INDEX_TITLE, ""] + [
        heading.removeprefix("### ") for heading in headings
    ]
    problems = [
        f"decisions-index.md:{number}: {got!r} != {want!r}"
        for number, (got, want) in enumerate(zip(index_lines, expected), start=1)
        if got != want
    ]
    if len(index_lines) != len(expected):
        problems.append(
            f"decisions-index.md: {len(index_lines)} lines, expected {len(expected)}"
        )
    return problems


def scan(token: re.Pattern[str], known: set[str]) -> list[str]:
    return [
        problem
        for path in scanned_paths()
        for problem in unknown_tokens(
            path.relative_to(REPO).as_posix(), read_lines(path), token, known
        )
    ]


def test_cited_decisions_exist() -> None:
    known = heading_ids(read_lines(DECISIONS), DECISION_HEADING)
    assert scan(DECISION_TOKEN, known) == []


def test_cited_null_sources_exist() -> None:
    known = heading_ids(read_lines(NULL_SOURCES), NULL_SOURCE_HEADING)
    assert scan(NULL_SOURCE_TOKEN, known) == []


def test_no_q_cites() -> None:
    # Q numbers live only in decisions-history.md, which maps each to its D.
    assert scan(QUESTION_TOKEN, set()) == []


def test_index_matches_decisions() -> None:
    headings = decision_headings(read_lines(DECISIONS))
    assert all(DECISION_HEADING.match(heading) for heading in headings)
    assert index_mismatches(read_lines(INDEX), headings) == []


# --- each check can fail ------------------------------------------------------
# Bad tokens are built at run time so this file holds none for the scan to find.

UNKNOWN_DECISION = "D" + "999"
QUESTION = "Q" + "47"


def test_unknown_decision_is_reported() -> None:
    lines = ["# D11: missing is null", f"# {UNKNOWN_DECISION}: no such rule"]
    assert unknown_tokens("x.py", lines, DECISION_TOKEN, {"D11"}) == [
        f"x.py:2: {UNKNOWN_DECISION}"
    ]


def test_unknown_null_source_is_reported() -> None:
    unknown = "N" + "99"
    lines = [f"see N3 and {unknown}"]
    assert unknown_tokens("x.md", lines, NULL_SOURCE_TOKEN, {"N3"}) == [
        f"x.md:1: {unknown}"
    ]


def test_question_is_reported() -> None:
    lines = ["(D26)", f"(D26, {QUESTION})"]
    assert unknown_tokens("x.py", lines, QUESTION_TOKEN, set()) == [
        f"x.py:2: {QUESTION}"
    ]


def test_lower_case_and_embedded_tokens_are_ignored() -> None:
    lines = ["an anchor like #live-run-after-q47", "a part named XD11 or D11a"]
    assert unknown_tokens("x.md", lines, DECISION_TOKEN, set()) == []
    assert unknown_tokens("x.md", lines, QUESTION_TOKEN, set()) == []


def test_mismatched_index_line_is_reported() -> None:
    headings = ["### D1. Purpose (active)", "### D2. Input (active)"]
    index = [INDEX_TITLE, "", "D1. Purpose (active)", "D2. Input (retired)"]
    assert index_mismatches(index, headings) == [
        "decisions-index.md:4: 'D2. Input (retired)' != 'D2. Input (active)'"
    ]


def test_missing_index_line_is_reported() -> None:
    headings = ["### D1. Purpose (active)", "### D2. Input (active)"]
    index = [INDEX_TITLE, "", "D1. Purpose (active)"]
    assert index_mismatches(index, headings) == [
        "decisions-index.md: 3 lines, expected 4"
    ]
