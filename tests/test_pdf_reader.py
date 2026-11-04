from pathlib import Path

import pdfplumber
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


# Your own Stripe invoice; git-ignored (D30), so a fresh clone skips this test.
STRIPE_SAMPLE = SAMPLES_DIRECTORY / "private" / "heldout" / "r_stripe-9B5AC24F-0001.pdf"


@pytest.mark.skipif(not STRIPE_SAMPLE.exists(), reason="private sample absent")
def test_nul_characters_in_the_text_layer_are_repaired() -> None:
    page = read_pdf(STRIPE_SAMPLE).pages[0]
    # The file's ToUnicode table maps these glyphs to U+0000 (D32); the
    # page itself draws a hyphen, a plus and a minus.
    assert "\x00" not in page.text
    assert "9B5AC24F-0001" in page.text
    assert "+1 888-493-2343" in page.text
    assert "-$40.00" in page.text
    assert "9B5AC24F-0001" in [word.text for word in page.words]


@pytest.mark.parametrize(
    "pdf_path",
    sorted(SAMPLES_DIRECTORY.glob("*/*.pdf")),
    ids=lambda path: path.stem,
)
def test_pages_without_nul_read_exactly_as_pdfplumber_reads_them(
    pdf_path: Path,
) -> None:
    # The NUL repair rebuilds text and words itself (D32); on a page with
    # no NUL that must equal pdfplumber's own calls, character for character.
    document = read_pdf(pdf_path)
    with pdfplumber.open(pdf_path) as pdf:
        for our_page, pdfplumber_page in zip(document.pages, pdf.pages, strict=True):
            assert our_page.text == pdfplumber_page.extract_text()
            assert [word.text for word in our_page.words] == [
                raw_word["text"] for raw_word in pdfplumber_page.extract_words()
            ]


def write_pdf_with_broken_glyph(pdf_path: Path) -> None:
    """One line "AB?C" in Helvetica whose ToUnicode table maps the third
    glyph to U+0000, so neither pdfplumber nor pdfium can name it (D32)."""
    to_unicode = (
        b"/CIDInit /ProcSet findresource begin 12 dict begin begincmap"
        b" /CMapName /Broken def 1 begincodespacerange <00> <FF> endcodespacerange"
        b" 1 beginbfchar <2D> <0000> endbfchar"
        b" endcmap CMapName currentdict /CMap defineresource pop end end"
    )
    # Glyph codes 41 42 2D 43: "A", "B", a hyphen with a real width (so
    # pdfium finds it by position) but a broken mapping, then "C".
    page_content = b"BT /F1 24 Tf 100 700 Td <41422D43> Tj ET"
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        (
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792]"
            b" /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>"
        ),
        # Explicit widths for codes 45 ("-") to 67 ("C"): without them
        # pdfplumber gives the broken glyph zero width, and the repair has
        # no box to look in.
        (
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /ToUnicode 6 0 R"
            b" /FirstChar 45 /LastChar 67 /Widths [" + b"600 " * 23 + b"] >>"
        ),
        b"<< /Length %d >>\nstream\n" % len(page_content)
        + page_content
        + b"\nendstream",
        b"<< /Length %d >>\nstream\n" % len(to_unicode) + to_unicode + b"\nendstream",
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


def test_a_nul_nothing_can_repair_becomes_the_unknown_character_mark(
    tmp_path: Path,
) -> None:
    broken_pdf = tmp_path / "broken.pdf"
    write_pdf_with_broken_glyph(broken_pdf)
    page = read_pdf(broken_pdf).pages[0]
    # U+FFFD, not NUL and not whatever placeholder pdfium uses (D32).
    assert page.text == "AB\ufffdC"
    assert [word.text for word in page.words] == ["AB\ufffdC"]
