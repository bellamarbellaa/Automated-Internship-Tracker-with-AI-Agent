from unittest.mock import MagicMock

from tools.update_tracker_sheet import append_postings, get_existing_urls


def test_get_existing_urls_reads_url_column():
    service = MagicMock()
    service.spreadsheets().values().get().execute.return_value = {
        "values": [["https://example.com/1"], ["https://example.com/2"]]
    }

    urls = get_existing_urls(service, "sheet-123", "31 Aug")

    assert urls == {"https://example.com/1", "https://example.com/2"}
    get_call = service.spreadsheets().values().get.call_args
    assert get_call.kwargs["range"] == "31 Aug!G2:G"


def test_get_existing_urls_empty_sheet():
    service = MagicMock()
    service.spreadsheets().values().get().execute.return_value = {}

    urls = get_existing_urls(service, "sheet-123", "31 Aug")

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

    appended = append_postings(service, "sheet-123", postings, "31 Aug")

    assert len(appended) == 1
    assert appended[0]["url"] == "https://example.com/new"

    append_call = service.spreadsheets().values().append.call_args
    assert append_call.kwargs["spreadsheetId"] == "sheet-123"
    assert append_call.kwargs["range"] == "31 Aug!A2:I"
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

    appended = append_postings(service, "sheet-123", postings, "31 Aug")

    assert appended == []
    service.spreadsheets().values().append.assert_not_called()


def test_append_postings_treats_rotating_tracking_param_as_duplicate():
    # Adzuna's "se" query param rotates on every API call for the same
    # listing; a real posting's URL differed only in "se" across two live
    # searches minutes apart. utm_source/utm_medium/utm_campaign are the
    # same kind of tracking noise and should be ignored too.
    service = MagicMock()
    service.spreadsheets().values().get().execute.return_value = {
        "values": [
            [
                "https://www.adzuna.com/land/ad/5856434706"
                "?se=xkkt87Ol8RGS6e_oRoerSw&utm_medium=api&utm_source=3f03cb9c"
                "&v=786217345AE0978B2D686EC0E92B3A6F845291EE"
            ]
        ]
    }

    postings = [
        {
            "title": "Business Analyst Intern",
            "company": "Crowe",
            "location": "Chicago",
            "url": (
                "https://www.adzuna.com/land/ad/5856434706"
                "?se=YNthLLal8RGS6e_oRoerSw&utm_medium=api&utm_source=3f03cb9c"
                "&v=786217345AE0978B2D686EC0E92B3A6F845291EE"
            ),
            "posted_date": "2026-08-26",
            "source": "adzuna",
            "match_percent": 75,
        }
    ]

    appended = append_postings(service, "sheet-123", postings, "31 Aug")

    assert appended == []
    service.spreadsheets().values().append.assert_not_called()


def test_append_postings_dedups_within_the_incoming_batch_itself():
    # Two entries for the same job can both surface in one search (e.g. via
    # two different query variants), each with a different rotating
    # tracking token. Neither is in the sheet yet, so a check against only
    # the sheet's existing URLs would let both through as separate rows.
    service = MagicMock()
    service.spreadsheets().values().get().execute.return_value = {"values": []}

    postings = [
        {
            "title": "Strategy Consultant Intern 2027",
            "company": "IBM",
            "location": "Chicago",
            "url": "https://www.adzuna.com/land/ad/5842069002?se=aaa&v=SAMEJOB",
            "posted_date": "2026-08-01",
            "source": "adzuna",
            "match_percent": 88,
        },
        {
            "title": "Strategy Consultant Intern 2027",
            "company": "IBM",
            "location": "Chicago",
            "url": "https://www.adzuna.com/land/ad/5842069002?se=bbb&v=SAMEJOB",
            "posted_date": "2026-08-01",
            "source": "adzuna",
            "match_percent": 88,
        },
    ]

    appended = append_postings(service, "sheet-123", postings, "31 Aug")

    assert len(appended) == 1
    append_call = service.spreadsheets().values().append.call_args
    assert len(append_call.kwargs["body"]["values"]) == 1


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

    appended = append_postings(service, "sheet-123", postings, "31 Aug")

    assert appended == []
    service.spreadsheets().values().append.assert_not_called()


def _make_posting(n: int, match_percent: int) -> dict:
    return {
        "title": f"Intern {n}",
        "company": f"Company {n}",
        "location": "Remote",
        "url": f"https://example.com/job-{n}",
        "posted_date": "2026-08-01",
        "source": "adzuna",
        "match_percent": match_percent,
    }


def test_append_postings_caps_at_20_keeping_highest_match_first():
    service = MagicMock()
    service.spreadsheets().values().get().execute.return_value = {"values": []}

    # 25 candidates, scores 60..84 in ascending order so the top 20 by
    # score are NOT simply "the first 20 in the input list".
    postings = [_make_posting(n, 60 + n) for n in range(25)]

    appended = append_postings(service, "sheet-123", postings, "31 Aug")

    assert len(appended) == 20
    scores = [p["match_percent"] for p in appended]
    assert scores == sorted(scores, reverse=True)
    assert min(scores) == 65  # the 20 highest scores out of 60..84 are 65..84
    assert all(s >= 65 for s in scores)


def test_append_postings_caps_respect_rows_already_in_this_weeks_tab():
    service = MagicMock()
    # Tab already has 18 rows this week -- only 2 more should fit.
    service.spreadsheets().values().get().execute.return_value = {
        "values": [[f"https://example.com/existing-{n}"] for n in range(18)]
    }

    postings = [_make_posting(n, 70 + n) for n in range(5)]

    appended = append_postings(service, "sheet-123", postings, "31 Aug")

    assert len(appended) == 2
    # The two highest-scoring candidates should be the ones kept.
    assert {p["match_percent"] for p in appended} == {73, 74}
