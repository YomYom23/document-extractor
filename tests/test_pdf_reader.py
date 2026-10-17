from pathlib import Path

import pytest

from document_extractor.pdf_reader import NoTextLayerError, PdfPage, Word, read_pdf

SAMPLES_DIRECTORY = Path(__file__).parent.parent / "samples"
US_SAMPLE = SAMPLES_DIRECTORY / "dev" / "a_clean-us-clean-simple.pdf"


def find_word(page: PdfPage, text: str) -> Word:
    matches = [word for word in page.words if word.text == text]
    assert len(matches) == 1, f"expected one {text!r}, found {len(matches)}"
    return matches[0]


def test_reads_one_us_letter_page() -> None:
    document = read_pdf(US_SAMPLE)
    assert len(document.pages) == 1
    page = document.pages[0]
    # US Letter is 8.5 x 11 inches at 72 points per inch.
    assert (page.width, page.height) == (612, 792)


def test_total_amount_sits_right_of_its_label_on_the_same_line() -> None:
    page = read_pdf(US_SAMPLE).pages[0]
    label = find_word(page, "TOTAL")
    amount = find_word(page, "$372.49")
    # Values measured on this sample with pdfplumber 0.11.10 (D23).
    assert label.top == pytest.approx(302.7, abs=0.1)
    assert amount.top == pytest.approx(label.top)
    assert amount.x0 > label.x1
    # top grows down the page: the subtotal line is above the total line.
    assert find_word(page, "Subtotal").top < label.top


def write_blank_pdf(pdf_path: Path) -> None:
    """A valid one-page PDF with no text, standing in for a scan (D2)."""
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>",
    ]
    content = b"%PDF-1.4\n"
    # The cross-reference table must give each object's exact byte offset.
    offsets = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(content))
        content += b"%d 0 obj\n" % number + body + b"\nendobj\n"
    xref_offset = len(content)
    content += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objects) + 1)
    content += b"".join(b"%010d 00000 n \n" % offset for offset in offsets)
    content += b"trailer\n<< /Size %d /Root 1 0 R >>\n" % (len(objects) + 1)
    content += b"startxref\n%d\n%%%%EOF\n" % xref_offset
    pdf_path.write_bytes(content)


def test_pdf_without_text_raises(tmp_path: Path) -> None:
    blank_pdf = tmp_path / "blank.pdf"
    write_blank_pdf(blank_pdf)
    with pytest.raises(NoTextLayerError):
        read_pdf(blank_pdf)


@pytest.mark.parametrize(
    "pdf_path",
    sorted(SAMPLES_DIRECTORY.glob("*/*.pdf")),
    ids=lambda path: path.stem,
)
def test_every_sample_has_text_and_words(pdf_path: Path) -> None:
    page = read_pdf(pdf_path).pages[0]
    assert page.words
    assert page.text.strip()


def test_text_keeps_reading_order_for_the_llm() -> None:
    page = read_pdf(US_SAMPLE).pages[0]
    assert "TOTAL $372.49" in page.text.splitlines()
