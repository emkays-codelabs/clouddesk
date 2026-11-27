"""Customer output validation (N5, CLAUDE.md 9): block leaks, score groundedness, revise once."""

import pytest

from app.core.output_validation import (
    GROUNDEDNESS_THRESHOLD,
    next_step,
    should_escalate,
    should_revise,
    validate_customer_output,
)

CHUNKS = [
    {
        "id": "c1",
        "snippet": "Open Settings, choose Billing and select Request refund. "
        "Unused seats are refunded for the current billing period after approval.",
    },
    "Refunds are returned to the original payment method within five business days.",
]
CONTEXT = {
    "name": "Marcus Webb",
    "email": "marcus.webb@brightpath.example",
    "other_customers": ["Priya Raman", "priya.raman@northwind.example"],
}
GROUNDED = (
    "Hi Marcus, we can refund the unused seats for the current billing period after approval. "
    "Refunds are returned to the original payment method within five business days."
)


def test_grounded_clean_reply_is_ok():
    r = validate_customer_output(GROUNDED, CHUNKS, CONTEXT)
    assert r.ok and r.reasons == [] and r.risk == "low"
    assert r.groundedness >= GROUNDEDNESS_THRESHOLD == 0.8


@pytest.mark.parametrize(
    "url",
    [
        "http://localhost:8000/admin",
        "see 127.0.0.1/health",
        "https://db.corp.internal/x",
        "http://10.2.3.4/console",
        "http://192.168.1.5/",
        "http://172.20.0.9/",
        "kb://refunds-and-seat-billing#steps",
        "https://wiki.acme.local/page",
    ],
)
def test_internal_urls_are_blocked(url):
    r = validate_customer_output(f"{GROUNDED} {url}", CHUNKS, CONTEXT)
    assert not r.ok and r.risk == "high" and "internal_url" in r.reasons


def test_public_url_is_allowed():
    r = validate_customer_output(f"{GROUNDED} See https://clouddesk.example/help.", CHUNKS, CONTEXT)
    assert "internal_url" not in r.reasons


@pytest.mark.parametrize(
    "secret",
    ["sk-abcdefghijklmnopqrstuvwx1234", "password=hunter2hunter", "card 4111 1111 1111 1111"],
)
def test_secrets_are_blocked(secret):
    r = validate_customer_output(f"{GROUNDED} {secret}", CHUNKS, CONTEXT)
    assert not r.ok and r.risk == "high" and "secret" in r.reasons


@pytest.mark.parametrize("leak", ["Priya Raman", "priya.raman@northwind.example", "PRIYA RAMAN"])
def test_another_customer_data_is_blocked(leak):
    r = validate_customer_output(f"{GROUNDED} Similar to {leak}.", CHUNKS, CONTEXT)
    assert not r.ok and r.risk == "high" and "other_customer_data" in r.reasons


def test_the_customer_own_details_are_allowed():
    text = f"{GROUNDED} We wrote to marcus.webb@brightpath.example."
    assert "other_customer_data" not in validate_customer_output(text, CHUNKS, CONTEXT).reasons


def test_unsupported_claim_scores_below_floor():
    reply = (
        "We will refund five hundred dollars into your bitcoin wallet within ten minutes. "
        "Our engineers permanently upgraded your servers overnight."
    )
    r = validate_customer_output(reply, CHUNKS, CONTEXT)
    assert r.groundedness < GROUNDEDNESS_THRESHOLD
    assert not r.ok and r.risk == "high" and "ungrounded" in r.reasons


def test_no_cited_chunks_means_claims_are_ungrounded():
    r = validate_customer_output(GROUNDED, [], CONTEXT)
    assert r.groundedness == 0.0 and not r.ok


def test_pleasantries_and_questions_are_not_claims():
    r = validate_customer_output(
        "Hi Marcus, thanks! Could you confirm the seat count?", [], CONTEXT
    )
    assert r.ok and r.groundedness == 1.0


def test_chunk_shapes_dict_object_and_string_are_accepted():
    class Chunk:
        snippet = "Unused seats are refunded for the current billing period after approval."

    r = validate_customer_output(
        "Unused seats are refunded for the current billing period after approval.",
        [Chunk()],
        CONTEXT,
    )
    assert r.ok


def test_revise_once_then_escalate():
    reply = "We will wire you ten thousand dollars tomorrow morning."
    bad = validate_customer_output(reply, CHUNKS, CONTEXT)
    assert should_revise(bad, revisions_done=0) and not should_escalate(bad, revisions_done=0)
    assert next_step(bad, 0) == "revise"
    assert not should_revise(bad, revisions_done=1) and should_escalate(bad, revisions_done=1)
    assert next_step(bad, 1) == "escalate"


def test_a_leak_escalates_without_a_revise():
    leak = validate_customer_output(
        f"{GROUNDED} token sk-abcdefghijklmnopqrstuvwx1234", CHUNKS, CONTEXT
    )
    assert next_step(leak, 0) == "escalate"


def test_ok_result_is_sent():
    assert next_step(validate_customer_output(GROUNDED, CHUNKS, CONTEXT), 0) == "send"
