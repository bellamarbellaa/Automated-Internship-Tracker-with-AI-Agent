from unittest.mock import MagicMock

from tools.update_tracker_sheet import append_postings, get_existing_urls


def test_get_existing_urls_reads_url_column():
    service = MagicMock()
    service.spreadsheets().values().get().execute.return_value = {
        "values": [["https://example.com/1"], ["https://example.com/2"]]
    }

    urls = get_existing_urls(service, "sheet-123")

    assert urls == {"https://example.com/1", "https://example.com/2"}


def test_get_existing_urls_empty_sheet():
    service = MagicMock()
    service.spreadsheets().values().get().execute.return_value = {}

    urls = get_existing_urls(service, "sheet-123")

    assert urls == set()


def test_append_postings_dedups_and_appends_new_only():
    import datetime

    service = MagicMock()
    service.spreadsheets().values().get().execute.return_value = {
        "values": [["https://example.com/existing"]]
    }

    today = datetime.date.today().isoformat()

    postings = [
        {
            "title": "Data Analyst Intern",
            "company": "Acme",
            "location": "Jakarta",
            "url": "https://example.com/existing",
            "posted_date": "2026-08-01",
            "source": "adzuna",
            "match_percent": 80,
        },
        {
            "title": "Business Analyst Intern",
            "company": "Beta",
            "location": "Singapore",
            "url": "https://example.com/new",
            "posted_date": "2026-08-02",
            "source": "serpapi",
            "match_percent": 75,
        },
    ]

    appended = append_postings(service, "sheet-123", postings)

    assert len(appended) == 1
    assert appended[0]["url"] == "https://example.com/new"

    append_call = service.spreadsheets().values().append.call_args
    assert append_call.kwargs["spreadsheetId"] == "sheet-123"
    row = append_call.kwargs["body"]["values"][0]
    assert row == [
        today,
        "Business Analyst Intern",
        "Beta",
        "Singapore",
        "serpapi",
        "2026-08-02",
        "https://example.com/new",
        75,
        "New",
    ]


def test_append_postings_treats_trailing_slash_and_whitespace_as_duplicate():
    service = MagicMock()
    service.spreadsheets().values().get().execute.return_value = {
        "values": [["https://example.com/existing"]]
    }

    postings = [
        {
            "title": "Data Analyst Intern",
            "company": "Acme",
            "location": "Jakarta",
            "url": "  https://example.com/existing/  ",
            "posted_date": "2026-08-01",
            "source": "adzuna",
            "match_percent": 80,
        }
    ]

    appended = append_postings(service, "sheet-123", postings)

    assert appended == []
    service.spreadsheets().values().append.assert_not_called()


def test_append_postings_all_duplicates_skips_api_call():
    service = MagicMock()
    service.spreadsheets().values().get().execute.return_value = {
        "values": [["https://example.com/existing"]]
    }

    postings = [
        {
            "title": "Data Analyst Intern",
            "company": "Acme",
            "location": "Jakarta",
            "url": "https://example.com/existing",
            "posted_date": "2026-08-01",
            "source": "adzuna",
            "match_percent": 80,
        }
    ]

    appended = append_postings(service, "sheet-123", postings)

    assert appended == []
    service.spreadsheets().values().append.assert_not_called()
