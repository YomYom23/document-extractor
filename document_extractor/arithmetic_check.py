"""Warn when an invoice's subtotal + tax does not equal its total (D20, D22).

This is a hint for a human reader, never a correctness score: a correct
extraction of an invoice with a rebate or shipping line will not add up,
because the schema has no field for those. The scorer does not import this.
"""

from document_extractor.schema import Invoice


def arithmetic_warning(invoice: Invoice) -> str | None:
    """Return a message if subtotal + tax != total, otherwise None."""
    subtotal, tax, total = invoice.subtotal, invoice.tax, invoice.total
    # With any of the three unknown there is nothing to check. A missing tax
    # is not read as zero: that would be a guess (D11).
    if subtotal is None or tax is None or total is None:
        return None
    # Exact Decimal comparison, no tolerance: the page prints rounded figures,
    # so a correct extraction adds up to the cent, and a tolerance would hide
    # a real one-cent misread.
    if subtotal + tax == total:
        return None
    return (
        f"subtotal {subtotal} + tax {tax} = {subtotal + tax}, "
        f"but total is {total} (difference {total - (subtotal + tax)})"
    )
