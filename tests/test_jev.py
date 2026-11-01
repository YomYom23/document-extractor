"""Contract tests: the real TypeSafe SDK, with only the HTTP layer faked.

These catch a wrong field name or a changed SDK, which a fake `ask` cannot.
The response body is copied from docs.typesafe.ai/primitives/choice.
"""

import json

import httpx2
import pytest
from typesafe_sdk import Choice, RetryPolicy, TypeSafeClient

from document_extractor.jev import Jev, JevError
from document_extractor.token_usage import TokenUsage

DOCS_RESPONSE = {
    "model": "jev-1.13.0",
    "answers": {
        "department": {
            "type": "choice",
            "choice": "returns",
            "confidence": 1.0,
            "probabilities": {"shipping": 0.0, "returns": 1.0, "billing": 0.0},
        }
    },
    "usage": {"input_tokens": 328, "output_tokens": 34},
}
QUESTIONS = {
    "department": Choice(
        instructions="Which team should handle this?",
        criteria={
            "returns": "Exchanges, wrong or damaged items",
            "shipping": "Delivery status, delays, lost packages",
            "billing": "Charges, invoices, payment problems",
        },
    )
}


def jev_answering(status: int, body: object, sent: list[httpx2.Request]) -> Jev:
    def handle(request: httpx2.Request) -> httpx2.Response:
        sent.append(request)
        return httpx2.Response(status, json=body)

    client = TypeSafeClient(
        api_key="test-key",
        transport=httpx2.MockTransport(handle),
        # No retries: a test of the failure path should fail at once.
        retry=RetryPolicy(max_retries=0),
    )
    return Jev(client)


def test_sends_state_and_questions_and_parses_the_choice() -> None:
    sent: list[httpx2.Request] = []
    answers = jev_answering(200, DOCS_RESPONSE, sent).ask(
        "my parcel is late", QUESTIONS
    )

    assert answers["department"].choice == "returns"
    assert answers["department"].confidence == 1.0
    request_body = json.loads(sent[0].content)
    assert request_body["state"] == "my parcel is late"
    assert request_body["questions"]["department"]["type"] == "choice"
    assert set(request_body["questions"]["department"]["criteria"]) == {
        "returns",
        "shipping",
        "billing",
    }


def test_a_missing_answer_is_an_error_not_a_default() -> None:
    body = {**DOCS_RESPONSE, "answers": {}}
    with pytest.raises(JevError):
        jev_answering(200, body, []).ask("my parcel is late", QUESTIONS)


def test_a_server_error_becomes_jev_error() -> None:
    with pytest.raises(JevError):
        jev_answering(500, {"error": "boom"}, []).ask("my parcel is late", QUESTIONS)


def test_the_usage_of_the_last_call_is_kept() -> None:
    # For the cost and size report in `score` (D29).
    jev = jev_answering(200, DOCS_RESPONSE, [])
    assert jev.last_usage is None  # no call yet
    jev.ask("my parcel is late", QUESTIONS)
    assert jev.last_usage == TokenUsage(input_tokens=328, output_tokens=34)


def test_usage_the_api_leaves_out_is_none_not_zero() -> None:
    # The SDK requires the `usage` object but each count in it may be absent.
    body = {**DOCS_RESPONSE, "usage": {}}
    jev = jev_answering(200, body, [])
    jev.ask("my parcel is late", QUESTIONS)
    # Unknown is not zero: a 0 would make the token total look complete.
    assert jev.last_usage == TokenUsage(input_tokens=None, output_tokens=None)
