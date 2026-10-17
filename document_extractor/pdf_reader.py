"""Read a digital PDF into plain Python objects (decisions D14, D23).

This is the only module that imports pdfplumber. Everything after it sees our
own frozen dataclasses, so the library can be swapped by changing this file.
"""

from dataclasses import dataclass
from pathlib import Path

import pdfplumber
from pdfplumber.page import Page


class NoTextLayerError(Exception):
    """The PDF has no extractable text, for example a scan (D2)."""


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
        pages = tuple(read_page(page) for page in pdf.pages)
    # Checked over the whole document, not per page: a blank back page on an
    # otherwise digital invoice is normal. Zero words anywhere means a scan,
    # which would otherwise come back all-null and be scored as "missing".
    if not any(page.words for page in pages):
        raise NoTextLayerError(f"{pdf_path} has no text layer; is it a scan?")
    return PdfDocument(pages=pages)


def read_page(page: Page) -> PdfPage:
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
        for raw_word in page.extract_words()
    )
    return PdfPage(
        width=float(page.width),
        height=float(page.height),
        text=page.extract_text(),
        words=words,
    )
