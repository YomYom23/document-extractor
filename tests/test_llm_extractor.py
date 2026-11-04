import json
from datetime import date
from decimal import Decimal
from pathlib import Path

import httpx2
import pytest
from openai import OpenAI
from pydantic import ValidationError

from document_extractor.llm_extractor import (
    INSTRUCTIONS,
    TEXT_FORMAT,
    LlmExtractionError,
    LlmExtractor,
    LlmInvoice,
    LlmLineItem,
    to_invoice,
)
from document_extractor.schema import LineItem
from document_extractor.scoring import normalise_text
from document_extractor.token_usage import TokenUsage

HELDOUT_DIRECTORY = Path(__file__).parent.parent / "samples" / "heldout"


def test_money_strings_become_exact_decimals() -> None:
    llm_invoice = LlmInvoice(
        vendor_name="Acme Industrial Supply Co",
        invoice_number="ACM-100145",
        issue_year=2024,
        issue_month=3,
        issue_day=12,
        currency="USD",
        subtotal="346.50",
        tax="25.99",
        total="372.49",
        line_items=None,
    )
    invoice = to_invoice(llm_invoice)
    assert invoice.total == Decimal("372.49")
    assert invoice.subtotal == Decimal("346.50")
    assert invoice.vendor_name == "Acme Industrial Supply Co"
    assert invoice.issue_date == date(2024, 3, 12)
    assert invoice.line_items is None


def invoice_dated(year: int | None, month: int | None, day: int | None) -> LlmInvoice:
    """An answer where only the three date numbers matter."""
    return LlmInvoice(
        vendor_name=None,
        invoice_number=None,
        issue_year=year,
        issue_month=month,
        issue_day=day,
        currency=None,
        subtotal=None,
        tax=None,
        total=None,
        line_items=None,
    )


def invoice_with_lines(line_items: list[LlmLineItem] | None) -> LlmInvoice:
    return invoice_dated(None, None, None).model_copy(update={"line_items": line_items})


def test_rows_become_exact_decimals() -> None:
    rows = [
        LlmLineItem(
            description="Hydraulic hose, per metre",
            quantity="15",
            unit_price="84.6050",
            line_total="1269.08",
        ),
        # A percentage row: the base as quantity, no unit price (D34.4).
        LlmLineItem(
            description="Fuel surcharge",
            quantity="-34978.05",
            unit_price=None,
            line_total="-7870.06",
        ),
    ]
    assert to_invoice(invoice_with_lines(rows)).line_items == [
        LineItem(
            description="Hydraulic hose, per metre",
            quantity=Decimal(15),
            unit_price=Decimal("84.6050"),
            line_total=Decimal("1269.08"),
        ),
        LineItem(
            description="Fuel surcharge",
            quantity=Decimal("-34978.05"),
            unit_price=None,
            line_total=Decimal("-7870.06"),
        ),
    ]


def test_none_and_empty_line_items_stay_distinct() -> None:
    # Null is "could not read the table"; [] is "no item rows" (D18).
    assert to_invoice(invoice_with_lines(None)).line_items is None
    assert to_invoice(invoice_with_lines([])).line_items == []


@pytest.mark.parametrize("printed", ["1", "2.5", "0.1250", "-3", "77867.7"])
def test_quantity_text_allows_up_to_four_decimals(printed: str) -> None:
    LlmLineItem(description=None, quantity=printed, unit_price=printed, line_total=None)


@pytest.mark.parametrize("printed", ["1.23456", "1,000", "1.", ".5", "2 pcs"])
def test_quantity_text_rejects_other_shapes(printed: str) -> None:
    with pytest.raises(ValidationError):
        LlmLineItem(
            description=None, quantity=printed, unit_price=None, line_total=None
        )


def test_the_three_date_numbers_become_one_date() -> None:
    assert to_invoice(invoice_dated(2026, 4, 30)).issue_date == date(2026, 4, 30)


@pytest.mark.parametrize(
    ("year", "month", "day"),
    [(None, 4, 30), (2026, None, 30), (2026, 4, None)],
)
def test_a_partial_date_is_null_not_completed(
    year: int | None, month: int | None, day: int | None
) -> None:
    # D11 and the D26 date change: never fill in a missing part by guessing.
    assert to_invoice(invoice_dated(year, month, day)).issue_date is None


@pytest.mark.parametrize(
    ("year", "month", "day"),
    [(2026, 30, 4), (2026, 2, 30), (2026, 0, 1), (2026, 4, 0)],
)
def test_an_impossible_date_is_null_not_an_error(
    year: int, month: int, day: int
) -> None:
    # The other fields are still good, so the date scores as missing (D26).
    assert to_invoice(invoice_dated(year, month, day)).issue_date is None


def test_nulls_stay_null() -> None:
    llm_invoice = invoice_dated(None, None, None)
    assert to_invoice(llm_invoice).model_dump() == {
        "vendor_name": None,
        "invoice_number": None,
        "issue_date": None,
        "currency": None,
        "subtotal": None,
        "tax": None,
        "total": None,
        "line_items": None,
    }


@pytest.mark.parametrize("printed", ["$12,731.44", "12731.4", "12.731,44"])
def test_money_must_be_plain_two_decimal_text(printed: str) -> None:
    # The same pattern the API enforces while the model writes (D26), so a
    # reply that slipped past it would still be rejected here.
    with pytest.raises(ValidationError):
        LlmInvoice(
            vendor_name=None,
            invoice_number=None,
            issue_year=None,
            issue_month=None,
            issue_day=None,
            currency=None,
            subtotal=None,
            tax=None,
            total=printed,
            line_items=None,
        )


def heldout_descriptions() -> list[str]:
    descriptions = []
    for label_path in HELDOUT_DIRECTORY.glob("*.expected.json"):
        label = json.loads(label_path.read_text(encoding="utf-8"))
        for row in label.get("line_items") or []:
            text = normalise_text(row["description"] or "")
            if len(text.split()) >= 3:
                descriptions.append(text)
    return descriptions


def test_no_heldout_label_description_appears_in_the_prompt_or_schema() -> None:
    # Held-out text must never reach the model (D6). Field descriptions are
    # sent inside the schema, so they are checked as well as the instructions.
    sent_text = normalise_text(INSTRUCTIONS + " " + json.dumps(TEXT_FORMAT["schema"]))
    descriptions = heldout_descriptions()
    assert descriptions  # the guard checks something
    # A count, not the list: a failure must not print held-out text.
    leaked = sum(description in sent_text for description in descriptions)
    assert leaked == 0


# --- Contract tests: the real OpenAI SDK, only the HTTP layer faked ----------

ACME_JSON = (
    '{"vendor_name": "Acme Industrial Supply Co", "invoice_number": "ACM-100145",'
    ' "issue_year": 2024, "issue_month": 3, "issue_day": 12,'
    ' "currency": "USD", "subtotal": "346.50",'
    ' "tax": "25.99", "total": "372.49", "line_items": null}'
)
ACME_WITH_LINES_JSON = ACME_JSON.replace(
    '"line_items": null',
    '"line_items": ['
    '{"description": "Hex bolts M8", "quantity": "100", "unit_price": "1.4650",'
    ' "line_total": "146.50"},'
    '{"description": "Freight", "quantity": null, "unit_price": null,'
    ' "line_total": "200.00"}]',
)


def response_body(
    content: list[dict[str, object]],
    status: str = "completed",
    incomplete_reason: str | None = None,
    usage: dict[str, object] | None = None,
) -> dict[str, object]:
    """The smallest Responses API body the SDK parses."""
    return {
        "id": "resp_test",
        "object": "response",
        "created_at": 1760000000,
        "model": "gpt-6-luna",
        "status": status,
        "incomplete_details": (
            {"reason": incomplete_reason} if incomplete_reason else None
        ),
        "output": [
            {
                "type": "message",
                "id": "msg_test",
                "role": "assistant",
                "status": status,
                "content": content,
            }
        ],
        "parallel_tool_calls": True,
        "tool_choice": "auto",
        "tools": [],
        "usage": usage,
    }


def text_content(text: str) -> list[dict[str, object]]:
    return [{"type": "output_text", "text": text, "annotations": []}]


def extractor_answering(
    status_code: int, body: object, sent: list[httpx2.Request]
) -> LlmExtractor:
    def handle(request: httpx2.Request) -> httpx2.Response:
        sent.append(request)
        return httpx2.Response(status_code, json=body)

    client = OpenAI(
        api_key="test-key",
        http_client=httpx2.Client(transport=httpx2.MockTransport(handle)),
        max_retries=0,  # the HTTP 500 test should fail at once, not back off
    )
    return LlmExtractor(client)


def test_sends_the_page_and_settings_and_parses_the_answer() -> None:
    sent: list[httpx2.Request] = []
    extractor = extractor_answering(200, response_body(text_content(ACME_JSON)), sent)

    invoice = extractor.extract_from_text("Acme Industrial Supply Co ... TOTAL $372.49")

    assert invoice.total == Decimal("372.49")
    assert invoice.currency == "USD"
    assert invoice.issue_date == date(2024, 3, 12)
    request_body = json.loads(sent[0].content)
    assert request_body["model"] == "gpt-6-luna"
    assert request_body["input"] == "Acme Industrial Supply Co ... TOTAL $372.49"
    assert request_body["reasoning"] == {"effort": "low"}
    # Room for the largest invoice's rows plus reasoning (D34.7).
    assert request_body["max_output_tokens"] == 16000
    assert request_body["store"] is False
    sent_format = request_body["text"]["format"]
    assert sent_format["type"] == "json_schema"
    assert sent_format["name"] == "LlmInvoice"
    assert sent_format["strict"] is True
    assert "line_items" in sent_format["schema"]["properties"]
    total_schema = sent_format["schema"]["properties"]["total"]["anyOf"][0]
    assert total_schema["pattern"] == r"^-?\d+\.\d{2}$"
    # One "YYYY-MM-DD" string made the model copy the page's leading digits
    # into the year (D26 diagnosis); the date goes out as three integers.
    properties = sent_format["schema"]["properties"]
    assert "issue_date" not in properties
    for part in ("issue_year", "issue_month", "issue_day"):
        assert properties[part]["anyOf"][0]["type"] == "integer"


def test_a_refusal_is_a_failure_not_an_empty_invoice() -> None:
    refusal: list[dict[str, object]] = [
        {"type": "refusal", "refusal": "I can't help with that."}
    ]
    with pytest.raises(LlmExtractionError):
        extractor_answering(200, response_body(refusal), []).extract_from_text("x")


def test_the_answer_rows_reach_the_invoice() -> None:
    body = response_body(text_content(ACME_WITH_LINES_JSON))
    invoice = extractor_answering(200, body, []).extract_from_text("x")

    assert invoice.line_items == [
        LineItem(
            description="Hex bolts M8",
            quantity=Decimal(100),
            unit_price=Decimal("1.4650"),
            line_total=Decimal("146.50"),
        ),
        LineItem(
            description="Freight",
            quantity=None,
            unit_price=None,
            line_total=Decimal("200.00"),
        ),
    ]


def test_a_reply_cut_off_mid_json_is_a_failure() -> None:
    body = response_body(
        text_content(ACME_JSON[:40]),
        status="incomplete",
        incomplete_reason="max_output_tokens",
        usage=USAGE,
    )
    extractor = extractor_answering(200, body, [])
    # Read from the status before the JSON is validated, so it is reported as
    # cut off, not as a schema break, and its billed tokens are kept (D34.7).
    with pytest.raises(LlmExtractionError, match="^reply cut off: max_output_tokens$"):
        extractor.extract_from_text("x")
    assert extractor.last_usage == TokenUsage(input_tokens=1200, output_tokens=300)


def test_a_complete_reply_that_breaks_the_schema_is_a_failure() -> None:
    broken = ACME_JSON.replace('"372.49"', '"$372.49"')
    body = response_body(text_content(broken), usage=USAGE)
    extractor = extractor_answering(200, body, [])
    with pytest.raises(LlmExtractionError, match="did not fit the schema"):
        extractor.extract_from_text("x")
    assert extractor.last_usage == TokenUsage(input_tokens=1200, output_tokens=300)


def test_a_server_error_is_a_failure() -> None:
    with pytest.raises(LlmExtractionError):
        extractor_answering(500, {"error": {"message": "boom"}}, []).extract_from_text(
            "x"
        )


# Shaped like the API's `usage`; output_tokens already includes reasoning.
USAGE = {
    "input_tokens": 1200,
    "input_tokens_details": {"cached_tokens": 0},
    "output_tokens": 300,
    "output_tokens_details": {"reasoning_tokens": 180},
    "total_tokens": 1500,
}


def test_the_usage_of_the_last_call_is_kept() -> None:
    # For the cost report in `score` (D29).
    body = response_body(text_content(ACME_JSON), usage=USAGE)
    extractor = extractor_answering(200, body, [])
    assert extractor.last_usage is None  # no call yet
    extractor.extract_from_text("x")
    assert extractor.last_usage == TokenUsage(input_tokens=1200, output_tokens=300)


def test_a_refused_reply_still_reports_its_billed_usage() -> None:
    refusal: list[dict[str, object]] = [
        {"type": "refusal", "refusal": "I can't help with that."}
    ]
    extractor = extractor_answering(200, response_body(refusal, usage=USAGE), [])
    with pytest.raises(LlmExtractionError):
        extractor.extract_from_text("x")
    assert extractor.last_usage == TokenUsage(input_tokens=1200, output_tokens=300)


def test_a_failed_call_does_not_keep_the_previous_usage() -> None:
    replies = iter([(200, response_body(text_content(ACME_JSON), usage=USAGE))])

    def handle(request: httpx2.Request) -> httpx2.Response:
        # First call answers; any later call is a server error.
        status_code, body = next(replies, (500, {"error": {"message": "boom"}}))
        return httpx2.Response(status_code, json=body)

    client = OpenAI(
        api_key="test-key",
        http_client=httpx2.Client(transport=httpx2.MockTransport(handle)),
        max_retries=0,
    )
    extractor = LlmExtractor(client)
    extractor.extract_from_text("x")
    with pytest.raises(LlmExtractionError):
        extractor.extract_from_text("x")
    assert extractor.last_usage is None  # nothing came back for this call
