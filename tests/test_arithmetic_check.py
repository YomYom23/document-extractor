from decimal import Decimal
from pathlib import Path

import pytest

from document_extractor.arithmetic_check import arithmetic_warning
from document_extractor.schema import Invoice

SAMPLES_DIRECTORY = Path(__file__).parent.parent / "samples"

# These two print a rebate the schema has no field for, so their correct
# labels do not add up (D20). The check must flag them anyway.
REBATE_SAMPLES = ("dev/b_INV-2026-0068", "dev/b_INV-2026-0194")


def load_label(sample: str) -> Invoice:
    label_path = SAMPLES_DIRECTORY / f"{sample}.expected.json"
    return Invoice.model_validate_json(label_path.read_text(encoding="utf-8"))


@pytest.mark.parametrize("sample", REBATE_SAMPLES)
def test_rebate_samples_get_a_warning(sample: str) -> None:
    assert arithmetic_warning(load_label(sample)) is not None


def test_numbers_that_add_up_get_no_warning() -> None:
    invoice = Invoice(
        subtotal=Decimal("346.50"), tax=Decimal("25.99"), total=Decimal("372.49")
    )
    assert arithmetic_warning(invoice) is None


def test_null_tax_is_not_read_as_zero() -> None:
    # 100 + 0 would equal the total; a None tax must skip the check instead.
    invoice = Invoice(subtotal=Decimal("100.00"), tax=None, total=Decimal("100.00"))
    assert arithmetic_warning(invoice) is None
    assert arithmetic_warning(load_label("dev/b_INV-2026-0129")) is None


def test_one_cent_off_is_flagged() -> None:
    invoice = Invoice(
        subtotal=Decimal("346.50"), tax=Decimal("25.99"), total=Decimal("372.50")
    )
    assert arithmetic_warning(invoice) is not None


def test_message_names_the_sum_the_total_and_the_gap() -> None:
    invoice = Invoice(
        subtotal=Decimal("100.00"), tax=Decimal("8.00"), total=Decimal("107.00")
    )
    message = arithmetic_warning(invoice)
    assert message is not None
    assert "108.00" in message
    assert "107.00" in message
    assert "-1.00" in message
