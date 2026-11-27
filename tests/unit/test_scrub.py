"""Secret scrub (N7, CLAUDE.md 7.5): cards, keys, tokens and passwords never reach memory."""

import pytest

from app.core.scrub import SECRET_PATTERNS, find_secrets, luhn_valid, scrub

JWT = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4ifQ."
    "SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
)


@pytest.mark.parametrize(
    ("text", "kind"),
    [
        ("my card is 4111 1111 1111 1111 thanks", "card_number"),
        ("card 4111-1111-1111-1111", "card_number"),
        ("card 4111111111111111.", "card_number"),
        ("amex 378282246310005", "card_number"),
        ("key sk-abcdefghijklmnopqrstuvwx1234", "api_key"),
        ("key sk-proj-abcdefghijklmnopqrstuvwx1234", "api_key"),
        ("aws AKIAIOSFODNN7EXAMPLE here", "aws_access_key"),
        ("Authorization: Bearer abc123def456ghi789jkl012", "bearer_token"),
        ("password=hunter2hunter", "password"),
        ("my password: Tr0ub4dor&3 ok", "password"),
        ("pwd = s3cretvalue", "password"),
        (f"token {JWT} end", "jwt"),
    ],
)
def test_secret_fixtures_are_removed(text, kind):
    out = scrub(text)
    assert f"[REDACTED:{kind}]" in out
    assert kind in find_secrets(text)
    assert find_secrets(out) == []


def test_the_secret_value_is_gone_not_just_marked():
    out = scrub("card 4111 1111 1111 1111 and password=hunter2hunter and sk-abcdefghijklmnopqrstuv")
    for leaked in ("4111", "hunter2hunter", "abcdefghijklmnopqrstuv"):
        assert leaked not in out
    assert out.startswith("card ")  # the surrounding words survive


@pytest.mark.parametrize(
    "text",
    [
        "The nightly sync returns HTTP 429 since 02:00.",
        "Order 1234567890123 shipped",  # 13 digits but fails Luhn
        "Call +1 415 555 0132 about the invoice",
        "Ticket CD-1002 refund 3 seats, we pay 12.50 per seat.",
        "We reset the password via the login page.",
        "The sk- prefix is documented; use your key.",
        "",
    ],
)
def test_clean_text_is_unchanged(text):
    assert scrub(text) == text
    assert find_secrets(text) == []


def test_scrub_is_idempotent():
    once = scrub(f"4111 1111 1111 1111 sk-abcdefghijklmnopqrstuv password=abcdefgh {JWT}")
    assert scrub(once) == once


def test_luhn():
    assert luhn_valid("4111111111111111")
    assert not luhn_valid("4111111111111112")


def test_patterns_are_named_and_exported():
    assert {"card_number", "api_key", "aws_access_key", "bearer_token", "password", "jwt"} <= set(
        SECRET_PATTERNS
    )


def test_none_is_treated_as_empty():
    assert scrub(None) == ""
