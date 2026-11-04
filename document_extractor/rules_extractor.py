"""Extract invoice header fields with hand-written rules, no model (D5, D24)."""

import re
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from itertools import pairwise
from pathlib import Path

from document_extractor.pdf_reader import PdfPage, Word, read_pdf
from document_extractor.schema import Invoice

# --- Amounts and dates ------------------------------------------------------

# One printed amount, such as "1.151,18", "13,680.00" or "1 440.12".
AMOUNT_PATTERN = re.compile(
    r"""
    (?P<integer_part>
        \d{1,3}(?P<thousands>[.,\ ])\d{3}(?:(?P=thousands)\d{3})*  # grouped: 1.151 / 375,905
        | \d+                                                    # ungrouped: 346
    )
    (?P<decimal>[.,])
    (?P<cents>\d{2})
    """,
    re.VERBOSE,
)


def parse_amount(printed: str) -> Decimal | None:
    """Read one printed amount, or None if it is not one (D24).

    The separator before the last two digits is the decimal point; any other
    `.`, `,` or space is a thousands separator. Deciding per amount, not per
    country, handles European and English formats on the same page.
    """
    # fullmatch, not search: "4334037646" must not match its last digits.
    match = AMOUNT_PATTERN.fullmatch(printed)
    if match is None:
        return None
    # "1.151.18" would otherwise read as 1151.18: one symbol cannot be both
    # the thousands separator and the decimal point.
    if match["thousands"] == match["decimal"]:
        return None
    digits = re.sub(r"[.,\ ]", "", match["integer_part"])
    return Decimal(f"{digits}.{match['cents']}")


# Own table instead of strptime's %B, which reads month names in the
# machine's locale and could stop recognising "July" on another computer.
MONTH_NUMBERS = {
    name: number
    for number, name in enumerate(
        [
            "january",
            "february",
            "march",
            "april",
            "may",
            "june",
            "july",
            "august",
            "september",
            "october",
            "november",
            "december",
        ],
        start=1,
    )
}
DOTTED_DATE = re.compile(r"(\d{1,2})\.(\d{1,2})\.(\d{4})")
SLASH_DATE = re.compile(r"(\d{1,2})/(\d{1,2})/(\d{4})")
MONTH_NAME_DATE = re.compile(r"(\d{1,2}) ([A-Za-z]+) (\d{4})")


def parse_date(printed: str) -> date | None:
    """Read one printed date, or None if it is not one or is ambiguous (D24)."""
    if match := DOTTED_DATE.fullmatch(printed):
        # Dotted dates are day.month.year in every country that uses them.
        day, month, year = (int(part) for part in match.groups())
    elif match := MONTH_NAME_DATE.fullmatch(printed):
        month_number = MONTH_NUMBERS.get(match[2].casefold())
        if month_number is None:
            return None  # right shape, but the middle word is not a month
        day, month, year = int(match[1]), month_number, int(match[3])
    elif match := SLASH_DATE.fullmatch(printed):
        first, second, year = (int(part) for part in match.groups())
        if first > 12:
            day, month = first, second  # 13/06/2025: 13 must be the day
        elif second > 12:
            day, month = second, first  # 06/13/2025
        else:
            # 09/03/2026 is 9 March in France and 3 September in the US.
            # Guessing could be wrong, and wrong is worse than missing (D11).
            # Open problem, see D24.
            return None
    else:
        return None
    try:
        return date(year, month, day)
    except ValueError:
        return None  # a date-shaped string that is not a real day: 31.02.2026


# --- Lines and segments (D24) -----------------------------------------------

# Measured on the dev samples: words on one line overlap vertically by at
# least 71% of the shorter one's height, words on different lines by at most
# 48%. 60% sits between, and scales with font size unlike a fixed point gap.
SAME_LINE_MIN_OVERLAP = 0.6
# Measured: spaces between words are at most 5.4 pt, gaps between visual
# columns at least 24.1 pt. 12 pt separates the two with room on each side.
COLUMN_GAP_POINTS = 12.0


@dataclass(frozen=True)
class Segment:
    """One visual column's worth of text on a line, e.g. "Invoice Number:"."""

    text: str


# A line is its segments from left to right.
Line = list[Segment]


def vertical_overlap_share(first: Word, second: Word) -> float:
    overlap = min(first.bottom, second.bottom) - max(first.top, second.top)
    shorter_height = min(first.bottom - first.top, second.bottom - second.top)
    return overlap / shorter_height


def build_lines(page: PdfPage) -> list[Line]:
    """Group words into lines (top to bottom), each cut into segments."""
    word_lines: list[list[Word]] = []
    for word in sorted(page.words, key=lambda word: word.top):
        # Compare with the line's first word: comparing with the last one
        # could let a line creep downwards one slightly lower word at a time.
        if (
            word_lines
            and vertical_overlap_share(word_lines[-1][0], word) >= SAME_LINE_MIN_OVERLAP
        ):
            word_lines[-1].append(word)
        else:
            word_lines.append([word])

    lines: list[Line] = []
    for word_line in word_lines:
        word_line.sort(key=lambda word: word.x0)  # left to right
        segment_words: list[list[Word]] = [[word_line[0]]]
        for previous_word, word in pairwise(word_line):  # (w1,w2), (w2,w3)...
            if word.x0 - previous_word.x1 > COLUMN_GAP_POINTS:
                segment_words.append([word])  # a column gap: new segment
            else:
                segment_words[-1].append(word)
        lines.append(
            [Segment(" ".join(word.text for word in words)) for words in segment_words]
        )
    return lines


# --- Labelled identifiers and dates -----------------------------------------

# Allowed anywhere in a segment: the b_ samples have no columns, so the label
# sits mid-line ("Stark Industries Europe Ltd Invoice No: INV-2026-0068").
# The colon is what makes a mid-line match safe.
INVOICE_NUMBER_LABEL = re.compile(r"\bInvoice (?:No|Number|#):", re.IGNORECASE)
# The lookbehind rejects "Due Date:", which is not the issue date.
ISSUE_DATE_LABEL = re.compile(r"(?<!Due )\bDate:", re.IGNORECASE)


def find_labelled_value(lines: list[Line], label: re.Pattern[str]) -> str | None:
    """The text after the first match of `label`, or the next segment's text
    when the label ends its segment ("Date:" || "30.04.2026")."""
    for line in lines:
        for index, segment in enumerate(line):
            match = label.search(segment.text)
            if match is None:
                continue
            value = segment.text[match.end() :].strip()
            if not value and index + 1 < len(line):
                value = line[index + 1].text
            if value:
                return value
    return None


# --- Labelled amounts -------------------------------------------------------

# Must START a segment (D24). Anywhere in a line would read 0129's
# "The subtotal including VAT is EUR 196,147.20" as the tax too.
# `\b` ends the label at a word boundary, so "Totals" is not "Total"; and
# since the label must start the segment, "Subtotal" never matches "total".
SUBTOTAL_LABEL = re.compile(r"subtotal\b", re.IGNORECASE)
TAX_LABEL = re.compile(r"(?:sales tax|tax|vat|mwst|tva|btw)\b", re.IGNORECASE)
TOTAL_LABEL = re.compile(r"total\b", re.IGNORECASE)

# An amount inside running text. The lookbehind stops a match from starting
# in the middle of a longer number. The lookahead stops it ending inside one:
# without the `[.,]\d` part, "13.07" would be read out of the date 13.07.2025.
AMOUNT_IN_TEXT = re.compile(
    r"(?<![\d.,])(?:" + AMOUNT_PATTERN.pattern + r")(?![\d]|[.,]\d)", re.VERBOSE
)


def find_first_amount(text: str) -> Decimal | None:
    for match in AMOUNT_IN_TEXT.finditer(text):
        # The search pattern is looser than parse_amount (it does not check
        # that the two separators differ), so every candidate is re-checked.
        amount = parse_amount(match.group(0))
        if amount is not None:
            return amount
    return None


@dataclass(frozen=True)
class LabelledAmount:
    amount: Decimal
    # The text the amount was found in; the currency is read from it.
    surrounding_text: str


def find_labelled_amount(
    lines: list[Line], label: re.Pattern[str]
) -> LabelledAmount | None:
    """The first amount right of a segment-starting `label`, on its line."""
    for line in lines:
        for index, segment in enumerate(line):
            match = label.match(segment.text)  # match(): only at the start
            if match is None:
                continue
            # The amount is often its own column: "MwSt 19%" || "1.070,21 €".
            text_to_the_right = " ".join(
                [segment.text[match.end() :]]
                + [later_segment.text for later_segment in line[index + 1 :]]
            )
            amount = find_first_amount(text_to_the_right)
            # No amount (e.g. "VAT No: 4334037646"): keep looking further down.
            if amount is not None:
                return LabelledAmount(amount, text_to_the_right)
    return None


# --- Currency ---------------------------------------------------------------

# A known list, not "any three capitals": an unknown code then gives None
# (missing) instead of a made-up currency (wrong).
ISO_CURRENCY_CODES = frozenset(
    {"EUR", "USD", "GBP", "ZAR", "CHF", "CAD", "AUD", "NZD", "JPY", "SEK", "NOK", "DKK"}
)
THREE_CAPITALS = re.compile(r"\b[A-Z]{3}\b")
# "R" counts only straight before a digit ("R11 739.28"), so "R$" (Brazil)
# and words starting with R are not read as rand.
RAND_PREFIX = re.compile(r"(?<![A-Za-z])R(?=\d)")


def detect_currency(amount_text: str) -> str | None:
    # finditer, not findall: findall is typed as list[Any], which mypy rejects.
    for match in THREE_CAPITALS.finditer(amount_text):
        if match.group(0) in ISO_CURRENCY_CODES:
            return match.group(0)  # a printed code beats any symbol
    if "€" in amount_text:
        return "EUR"
    if "£" in amount_text:
        return "GBP"
    if RAND_PREFIX.search(amount_text):
        return "ZAR"
    # A bare "$" is USD, CAD, AUD, NZD, NAD... The Jev resolver decides (D25).
    return None


# --- Vendor name ------------------------------------------------------------

TITLES = frozenset({"invoice", "tax invoice"})
LOGO_INITIALS = re.compile(r"[A-Z]{1,3}")


def find_vendor_name(lines: list[Line]) -> str | None:
    """The first segment from the top that is not a title or logo initials,
    cut before an invoice-number label sharing its line."""
    for line in lines:
        for segment in line:
            label = INVOICE_NUMBER_LABEL.search(segment.text)
            text = (segment.text[: label.start()] if label else segment.text).strip()
            if not text or text.casefold() in TITLES or LOGO_INITIALS.fullmatch(text):
                continue
            return text
    return None


# --- The extractor ----------------------------------------------------------


def extract(pdf_path: Path) -> Invoice:
    """Read the header fields of a digital PDF invoice with rules (D5, D24)."""
    lines = [line for page in read_pdf(pdf_path).pages for line in build_lines(page)]

    invoice_number_text = find_labelled_value(lines, INVOICE_NUMBER_LABEL)
    issue_date_text = find_labelled_value(lines, ISSUE_DATE_LABEL)
    subtotal = find_labelled_amount(lines, SUBTOTAL_LABEL)
    tax = find_labelled_amount(lines, TAX_LABEL)
    total = find_labelled_amount(lines, TOTAL_LABEL)

    return Invoice(
        vendor_name=find_vendor_name(lines),
        # The number is one token: "INV-2026-0068", not any text after it.
        invoice_number=invoice_number_text.split()[0] if invoice_number_text else None,
        issue_date=parse_date(issue_date_text) if issue_date_text else None,
        # Read from the total's line: the amount the currency matters most for.
        currency=detect_currency(total.surrounding_text) if total else None,
        subtotal=subtotal.amount if subtotal else None,
        tax=tax.amount if tax else None,
        total=total.amount if total else None,
        line_items=None,  # D34: the rules extractor never extracts line items
    )
