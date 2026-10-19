from collections import Counter
from pathlib import Path

import pytest

from document_extractor.schema import Invoice

SAMPLES_DIRECTORY = Path(__file__).parent.parent / "samples"
SAMPLE_SETS = ("dev", "heldout")
# Your own invoices are git-ignored (D30, Q75), so a fresh clone has none;
# the checks below cover them only where they exist.
PRIVATE_DIRECTORY = SAMPLES_DIRECTORY / "private"


def set_directories(sample_set: str) -> list[Path]:
    return [SAMPLES_DIRECTORY / sample_set, PRIVATE_DIRECTORY / sample_set]


def all_label_paths() -> list[Path]:
    return sorted(
        path
        for sample_set in SAMPLE_SETS
        for directory in set_directories(sample_set)
        for path in directory.glob("*.expected.json")
    )


def test_expected_public_split_sizes() -> None:
    counts = Counter(
        path.parent.name
        for path in all_label_paths()
        if PRIVATE_DIRECTORY not in path.parents
    )
    # D30: the old 13 are all dev; plus 13 IEB + 10 Sinabis in dev and
    # 12 IEB + 10 Sinabis in held-out.
    assert counts == {"dev": 36, "heldout": 22}


@pytest.mark.parametrize("label_path", all_label_paths(), ids=lambda path: path.stem)
def test_label_parses_and_has_a_matching_pdf(label_path: Path) -> None:
    invoice = Invoice.model_validate_json(label_path.read_text(encoding="utf-8"))
    pdf_path = label_path.with_name(
        label_path.name.removesuffix(".expected.json") + ".pdf"
    )
    assert pdf_path.exists()
    # A label with nothing in it would score every extractor as "correct" by returning nothing.
    assert invoice.vendor_name is not None
    assert invoice.total is not None
    # Labels added in D30 are header-only (line_items null); an empty list
    # would instead claim "the invoice has no lines" (D18).
    assert invoice.line_items != []


@pytest.mark.parametrize("sample_set", SAMPLE_SETS)
def test_every_pdf_has_a_label(sample_set: str) -> None:
    for directory in set_directories(sample_set):
        for pdf_path in directory.glob("*.pdf"):
            label_path = pdf_path.with_name(pdf_path.stem + ".expected.json")
            assert label_path.exists(), f"{pdf_path.name} has no label"


def test_no_invoice_appears_in_both_sets() -> None:
    names = {
        sample_set: {
            path.name.removesuffix(".expected.json")
            for directory in set_directories(sample_set)
            for path in directory.glob("*.expected.json")
        }
        for sample_set in SAMPLE_SETS
    }
    assert names["dev"].isdisjoint(names["heldout"])
