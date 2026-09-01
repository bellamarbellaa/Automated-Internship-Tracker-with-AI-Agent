import tools.search_serpapi_jobs as search_serpapi_jobs


class FakeResponse:
    def __init__(self, json_data, status=200):
        self._json_data = json_data
        self.status_code = status

    def raise_for_status(self):
        if self.status_code >= 400:
            import requests
            raise requests.HTTPError(f"status {self.status_code}")

    def json(self):
        return self._json_data


def test_search_postings_filters_and_normalizes(monkeypatch):
    fake_result = {
        "jobs_results": [
            {
                "title": "Data Analyst Intern",
                "company_name": "Fintech Co",
                "location": "Jakarta, Indonesia",
                "description": "A 12-week internship, Summer 2027.",
                "apply_options": [{"link": "https://example.com/apply/1"}],
                "detected_extensions": {"posted_at": "2026-08-01"},
            },
            {
                "title": "Data Analyst",
                "company_name": "Big Bank",
                "location": "Sydney",
                "description": "Full-time role, must be authorized to work in Australia.",
                "apply_options": [{"link": "https://example.com/apply/2"}],
                "detected_extensions": {"posted_at": "2026-08-01"},
            },
        ]
    }

    def fake_get(url, params=None, timeout=None):
        return FakeResponse(fake_result)

    monkeypatch.setattr(search_serpapi_jobs.requests, "get", fake_get)

    result = search_serpapi_jobs.search_postings("Data Analyst")

    assert result["source"] == "serpapi"
    assert result["success"] is True
    assert len(result["postings"]) == 1
    posting = result["postings"][0]
    assert posting["title"] == "Data Analyst Intern"
    assert posting["company"] == "Fintech Co"
    assert posting["location"] == "Jakarta, Indonesia"
    assert posting["url"] == "https://example.com/apply/1"
    assert posting["posted_date"] == "2026-08-01"
    assert posting["role"] == "Data Analyst"


def test_search_postings_handles_request_failure(monkeypatch):
    def fake_get(url, params=None, timeout=None):
        raise search_serpapi_jobs.requests.RequestException("rate limited")

    monkeypatch.setattr(search_serpapi_jobs.requests, "get", fake_get)

    result = search_serpapi_jobs.search_postings("Consultant")

    assert result["success"] is False
    assert result["error"] == "rate limited"
    assert result["postings"] == []
