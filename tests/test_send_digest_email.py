import base64
from unittest.mock import MagicMock

from tools.send_digest_email import build_digest_email, send_digest


def _sample_postings():
    return [
        {
            "role": "Business Analyst",
            "company": "Acme",
            "title": "Business Analyst Intern",
            "location": "Jakarta",
            "posted_date": "2026-08-01",
            "match_percent": 82,
            "url": "https://example.com/1",
        },
        {
            "role": "Data Analyst",
            "company": "Beta",
            "title": "Data Analyst Intern",
            "location": "Singapore",
            "posted_date": "2026-08-02",
            "match_percent": 91,
            "url": "https://example.com/2",
        },
    ]


def test_build_digest_email_groups_by_role_and_notes_failures():
    source_status = {
        "adzuna": {"success": True, "error": None},
        "serpapi": {"success": False, "error": "rate limited"},
    }

    message = build_digest_email(_sample_postings(), source_status, "user@example.com")
    # Non-ASCII body content (em dashes) makes MIMEText pick utf-8 + base64
    # transfer encoding, so decode=True is required to read plain text back.
    body = message.get_payload(decode=True).decode("utf-8")

    assert message["to"] == "user@example.com"
    assert "2 new posting(s)" in message["subject"]
    assert "Business Analyst" in body
    assert "Acme" in body
    assert "Data Analyst" in body
    assert "Beta" in body
    assert "adzuna: ok" in body
    assert "serpapi: failed (rate limited)" in body


def test_send_digest_noop_when_no_postings():
    service = MagicMock()

    send_digest(service, [], {"adzuna": {"success": True, "error": None}}, "user@example.com")

    service.users().messages().send.assert_not_called()


def test_send_digest_sends_when_postings_present():
    service = MagicMock()

    send_digest(
        service,
        _sample_postings(),
        {"adzuna": {"success": True, "error": None}},
        "user@example.com",
    )

    send_call = service.users().messages().send.call_args
    assert send_call.kwargs["userId"] == "me"
    raw = send_call.kwargs["body"]["raw"]
    decoded = base64.urlsafe_b64decode(raw).decode()
    assert "user@example.com" in decoded
