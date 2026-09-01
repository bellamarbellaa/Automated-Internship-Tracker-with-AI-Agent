import tools.search_adzuna as search_adzuna


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
        "results": [
            {
                "title": "Business Analyst Intern",
                "company": {"display_name": "Acme Corp"},
                "location": {"display_name": "Singapore"},
                "redirect_url": "https://example.com/job/1",
                "created": "2026-08-01T00:00:00Z",
                "description": "An 8-week internship, Summer 2027 start.",
            },
            {
                "title": "Senior Business Analyst",
                "company": {"display_name": "Beta Inc"},
                "location": {"display_name": "London"},
                "redirect_url": "https://example.com/job/2",
                "created": "2026-08-01T00:00:00Z",
                "description": "Full-time permanent role for experienced professionals.",
            },
        ]
    }

    def fake_get(url, params=None, timeout=None):
        return FakeResponse(fake_result)

    monkeypatch.setattr(search_adzuna.requests, "get", fake_get)

    result = search_adzuna.search_postings("Business Analyst", countries=["sg"])

    assert result["source"] == "adzuna"
    assert result["success"] is True
    assert result["error"] is None
    assert len(result["postings"]) == 1
    posting = result["postings"][0]
    assert posting["title"] == "Business Analyst Intern"
    assert posting["company"] == "Acme Corp"
    assert posting["location"] == "Singapore"
    assert posting["url"] == "https://example.com/job/1"
    assert posting["posted_date"] == "2026-08-01"
    assert posting["source"] == "adzuna"
    assert posting["role"] == "Business Analyst"


def test_search_postings_handles_request_failure(monkeypatch):
    def fake_get(url, params=None, timeout=None):
        raise search_adzuna.requests.RequestException("timeout")

    monkeypatch.setattr(search_adzuna.requests, "get", fake_get)

    result = search_adzuna.search_postings("Data Analyst", countries=["sg"])

    assert result["success"] is False
    assert result["error"] == "timeout"
    assert result["postings"] == []
