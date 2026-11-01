"""Read a digital PDF into plain Python objects.

This is the only module that imports a PDF library (D14: pdfplumber, and pdfium
for the NUL repair of D32). Everything after it sees our own frozen dataclasses
(D23), so the libraries can be swapped by changing this file.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pdfplumber
import pypdfium2  # type: ignore[import-untyped]  # ships no type hints
from pdfplumber.page import Page
from pdfplumber.utils.text import chars_to_textmap, extract_words


class NoTextLayerError(Exception):
    """The PDF has no extractable text, for example a scan (D2)."""


# What a broken ToUnicode table turns a glyph into (D32).
NUL_CHARACTER = "\x00"
# Unicode's own "unknown character" mark, written where no repair is possible
# (D32): visible in any viewer, where a NUL hides.
UNREADABLE_CHARACTER = "\ufffd"


# Frozen: a page is a fact read from the file; no later stage should edit it.
@dataclass(frozen=True)
class Word:
    text: str
    # Points (1/72 inch) from the page's top-left corner. `top` and `bottom`
    # grow DOWN the page, so a bigger `top` means lower on the page.
    x0: float  # left edge
    x1: float  # right edge
    top: float
    bottom: float


@dataclass(frozen=True)
class PdfPage:
    width: float
    height: float
    # Reading-order text, for the LLM extractor. Side-by-side columns are
    # merged into one line here, which is why `words` exists too.
    text: str
    # Positioned words, for the rules extractor ("the number right of Total").
    words: tuple[Word, ...]


@dataclass(frozen=True)
class PdfDocument:
    pages: tuple[PdfPage, ...]


def read_pdf(pdf_path: Path) -> PdfDocument:
    # `with` closes the file even if extraction raises halfway through.
    with pdfplumber.open(pdf_path) as pdf:
        # pdfium opens the same file a second time; it is only asked about
        # characters pdfplumber read as NUL (D32).
        pdfium_document = pypdfium2.PdfDocument(pdf_path)
        try:
            pages = tuple(
                # pdfplumber numbers pages from 1, pdfium indexes from 0.
                read_page(page, pdfium_document[page.page_number - 1])
                for page in pdf.pages
            )
        finally:
            # Releases the file handle; Windows cannot move or delete a
            # file that is still open.
            pdfium_document.close()
    # Checked over the whole document, not per page: a blank back page on an
    # otherwise digital invoice is normal. Zero words anywhere means a scan,
    # which would otherwise come back all-null and be scored as "missing".
    if not any(page.words for page in pages):
        raise NoTextLayerError(f"{pdf_path} has no text layer; is it a scan?")
    return PdfDocument(pages=pages)


def read_page(page: Page, pdfium_page: Any) -> PdfPage:
    characters = repair_nul_characters(page.chars, pdfium_page)
    words = tuple(
        Word(
            # pdfplumber types each word as dict[str, Any], and Any switches
            # mypy off; str()/float() make the types real at this boundary.
            text=str(raw_word["text"]),
            x0=float(raw_word["x0"]),
            x1=float(raw_word["x1"]),
            top=float(raw_word["top"]),
            bottom=float(raw_word["bottom"]),
        )
        # pdfplumber returns each word as a dict; copying the five fields we
        # use into `Word` keeps its other keys from leaking out of this module.
        # The same call `Page.extract_words()` makes, but on the repaired
        # characters, so a page without NULs gives exactly what it did.
        for raw_word in extract_words(characters)
    )
    # Mirrors `Page.extract_text()` (pdfplumber 0.11.10, page.py), which
    # passes the page's box and size along with its characters.
    text = chars_to_textmap(
        characters,
        layout_bbox=page.bbox,
        layout_width=page.width,
        layout_height=page.height,
    ).as_string
    return PdfPage(
        width=float(page.width),
        height=float(page.height),
        text=text,
        words=words,
    )


def repair_nul_characters(
    characters: list[dict[str, Any]], pdfium_page: Any
) -> list[dict[str, Any]]:
    """Replace each NUL with the character pdfium reads at that spot (D32).

    Some PDFs map glyphs to U+0000 in their ToUnicode table, so pdfplumber
    returns NUL where the page draws `-`, `(` or `+`. pdfium recovers them.
    """
    if not any(character["text"] == NUL_CHARACTER for character in characters):
        # The usual case: no NUL, so pdfium's text page is never built.
        return characters
    pdfium_text_page = pdfium_page.get_textpage()
    try:
        return [
            # A copy with only `text` changed; pdfplumber's own dict is left
            # as it was, since the page object caches it.
            {**character, "text": read_with_pdfium(character, pdfium_text_page)}
            if character["text"] == NUL_CHARACTER
            else character
            for character in characters
        ]
    finally:
        pdfium_text_page.close()


def read_with_pdfium(character: dict[str, Any], pdfium_text_page: Any) -> str:
    # pdfplumber's y0/y1 are measured up from the page's bottom edge, the
    # same direction as pdfium's coordinates; `top` would be the wrong way.
    centre_x = (character["x0"] + character["x1"]) / 2
    centre_y = (character["y0"] + character["y1"]) / 2
    # Horizontally, under half a character width, so the neighbour on either
    # side is not picked.
    horizontal_tolerance = (character["x1"] - character["x0"]) / 4
    # Vertically, half the character's height: pdfium boxes only the ink,
    # and a hyphen's ink sits well above the centre of pdfplumber's
    # full-height box (D32).
    vertical_tolerance = (character["y1"] - character["y0"]) / 2
    index = pdfium_text_page.get_index(
        centre_x, centre_y, horizontal_tolerance, vertical_tolerance
    )
    if index is None:
        return UNREADABLE_CHARACTER
    pdfium_character = str(pdfium_text_page.get_text_range(index, 1))
    # When pdfium cannot name a glyph either it returns U+FFFE, a Unicode
    # non-character; it could also return NUL or nothing. None of those is a
    # repair, and `isprintable()` is False for all of them.
    if len(pdfium_character) != 1 or not pdfium_character.isprintable():
        return UNREADABLE_CHARACTER
    return pdfium_character
