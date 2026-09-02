# Internship Tracker Automation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a weekly automation that searches free job APIs for Business Analyst / Data Analyst / Consultant internships, filters them against the user's CVs and criteria, appends new matches to a Google Sheet tracker, and emails a digest — all orchestrated per the WAT (Workflows, Agents, Tools) framework.

**Architecture:** Deterministic Python tools (`tools/`) handle API calls, textual filtering, sheet updates, and email sending. The agent (Claude, at scheduled run time) handles judgment calls — CV-to-posting matching — per the WAT principle that reasoning belongs at the Agent layer, not in scripts. A markdown SOP (`workflows/weekly_internship_search.md`) ties it together; a weekly scheduled cloud agent triggers it.

**Tech Stack:** Python 3, `requests`, `google-api-python-client` + `google-auth-oauthlib` (Sheets + Gmail), `python-dotenv`, `pytest` for tests.

**Spec:** `docs/superpowers/specs/2026-08-31-internship-tracker-automation-design.md`

## Global Constraints

- Free sources/tools only, no paid services anywhere in the pipeline. Max 8 distinct sources total; this plan implements 2 (Adzuna, SerpAPI).
- Roles are exactly: Business Analyst, Data Analyst, Consultant — no others.
- Industry is not a hard filter; queries are biased toward Consulting, Banking, Fintech.
- Internship requirement is a hard filter: "intern"/"internship" must appear in title or description.
- Duration: postings must indicate 8, 10, or 12 weeks (or "3 months"), or Summer 2027, or say nothing about duration (benefit of the doubt). Explicit non-matching durations are excluded.
- CV match ≥70% is a hard filter, computed by the agent at run time (not a deterministic tool) — this is a judgment call per WAT's "probabilistic AI handles reasoning" principle.
- Location/visa is a soft filter: exclude only if a posting explicitly requires existing work authorization or states no visa sponsorship. Silence on visa status means include.
- Google Sheet tab "Internship Tracker" has exactly these columns in this order: Date Found, Title, Company, Location, Source, Posted Date, URL, Match %, Status. The automation only ever appends rows; it never edits `Status`.
- Email digest is sent only when new rows were appended that week.
- All secrets (`ADZUNA_APP_ID`, `ADZUNA_APP_KEY`, `SERPAPI_API_KEY`, `credentials.json`, `token.json`) stay out of git — `.gitignore` already covers `.env`, `credentials.json`, `token.json`, `reference/`.
- User's Google OAuth client (`credentials.json`) is already Desktop-app type — no redirect URI registration needed.

---

## Task 1: Project Setup

**Files:**
- Create: `requirements.txt`
- Create: `.env.example`
- Create: `pytest.ini`
- Create: `tools/__init__.py`
- Test: `tests/test_setup.py`

**Interfaces:**
- Produces: a working Python environment where `tools.*` is importable from `tests/*`, and where `pytest` runs.

- [ ] **Step 1: Write `requirements.txt`**

```
requests==2.32.3
python-dotenv==1.0.1
google-api-python-client==2.149.0
google-auth-httplib2==0.2.0
google-auth-oauthlib==1.2.1
pytest==8.3.3
```

- [ ] **Step 2: Write `.env.example`**

```
ADZUNA_APP_ID=
ADZUNA_APP_KEY=
SERPAPI_API_KEY=
TRACKER_SPREADSHEET_ID=
DIGEST_EMAIL_TO=belbel.bella00@gmail.com
```

- [ ] **Step 3: Write `pytest.ini`**

```ini
[pytest]
testpaths = tests
pythonpath = .
```

- [ ] **Step 4: Create empty `tools/__init__.py`**

Empty file — makes `tools` an importable package.

- [ ] **Step 5: Human action required — you, not the agent, must do this**

1. Copy `.env.example` to `.env`.
2. Fill in your real `ADZUNA_APP_ID`, `ADZUNA_APP_KEY`, and `SERPAPI_API_KEY` (you said you already have these).
3. Confirm your `credentials.json` (Desktop-app OAuth client) is in the project root.

This step can't be done by the agent — these are secrets that must never be typed into chat or committed. Confirm to the agent once done so it can proceed to Task 10's live verification later (Tasks 2–9 don't need real keys, they're mocked).

- [ ] **Step 6: Write the failing smoke test**

```python
# tests/test_setup.py
def test_dependencies_importable():
    import dotenv
    import requests
    import googleapiclient.discovery
    import google_auth_oauthlib.flow
```

- [ ] **Step 7: Run test to verify it fails (dependencies not installed yet)**

Run: `pytest tests/test_setup.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 8: Install dependencies**

Run: `pip install -r requirements.txt`

- [ ] **Step 9: Run test to verify it passes**

Run: `pytest tests/test_setup.py -v`
Expected: PASS

- [ ] **Step 10: Commit**

```bash
git add requirements.txt .env.example pytest.ini tools/__init__.py tests/test_setup.py
git commit -m "chore: project scaffolding for internship tracker automation"
```

---

## Task 2: Shared Job Filters and Role Queries

**Files:**
- Create: `tools/job_filters.py`
- Create: `tools/role_queries.py`
- Test: `tests/test_job_filters.py`
- Test: `tests/test_role_queries.py`

**Interfaces:**
- Produces:
  - `has_internship_keyword(title: str, description: str) -> bool`
  - `matches_duration(description: str) -> bool`
  - `passes_visa_check(description: str) -> bool`
  - `ROLE_QUERIES: dict[str, list[str]]` — one shared query-term mapping used
    by both search tools, so the role→query list is defined in exactly one
    place instead of duplicated across files.
- Consumed by: Task 3 (`search_adzuna.py`), Task 4 (`search_serpapi_jobs.py`)

- [ ] **Step 1: Write failing tests**

```python
# tests/test_job_filters.py
from tools.job_filters import has_internship_keyword, matches_duration, passes_visa_check


def test_has_internship_keyword_in_title():
    assert has_internship_keyword("Business Analyst Internship", "") is True


def test_has_internship_keyword_in_description():
    assert has_internship_keyword(
        "Business Analyst", "This is a full-time internship program"
    ) is True


def test_has_internship_keyword_absent():
    assert has_internship_keyword(
        "Senior Business Analyst", "Full-time permanent role"
    ) is False


def test_matches_duration_explicit_week_match():
    assert matches_duration("This is an 8-week summer internship") is True


def test_matches_duration_explicit_week_mismatch():
    assert matches_duration("This is a 16-week internship") is False


def test_matches_duration_month_match():
    assert matches_duration("A 3-month internship program") is True


def test_matches_duration_month_mismatch():
    assert matches_duration("A 6-month internship program") is False


def test_matches_duration_summer_2027_overrides():
    assert matches_duration("Summer 2027 internship, duration TBD") is True


def test_matches_duration_no_info_defaults_true():
    assert matches_duration("Full-time internship, great learning experience") is True


def test_passes_visa_check_no_sponsorship_excluded():
    assert passes_visa_check(
        "We are unable to sponsor work visas for this position"
    ) is False


def test_passes_visa_check_requires_authorization_excluded():
    assert passes_visa_check(
        "Applicants must be authorized to work in the United States"
    ) is False


def test_passes_visa_check_silent_included():
    assert passes_visa_check("Join our team as a summer intern") is True
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_job_filters.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'tools.job_filters'`

- [ ] **Step 3: Implement `tools/job_filters.py`**

```python
import re

_MATCHING_WEEKS = {8, 10, 12}
_MATCHING_MONTHS = {3}

_VISA_EXCLUSION_PHRASES = [
    "must be authorized to work",
    "no visa sponsorship",
    "not sponsor",
    "without sponsorship",
    "does not provide sponsorship",
    "must have valid work authorization",
    "unable to sponsor",
    "cannot sponsor",
]


def has_internship_keyword(title: str, description: str) -> bool:
    text = f"{title} {description}".lower()
    return "intern" in text


def matches_duration(description: str) -> bool:
    text = description.lower()
    if "summer 2027" in text:
        return True

    week_numbers = [int(n) for n in re.findall(r"(\d{1,2})\s*-?\s*weeks?", text)]
    if week_numbers:
        return any(w in _MATCHING_WEEKS for w in week_numbers)

    month_numbers = [int(n) for n in re.findall(r"(\d{1,2})\s*-?\s*months?", text)]
    if month_numbers:
        return any(m in _MATCHING_MONTHS for m in month_numbers)

    return True


def passes_visa_check(description: str) -> bool:
    text = description.lower()
    return not any(phrase in text for phrase in _VISA_EXCLUSION_PHRASES)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_job_filters.py -v`
Expected: PASS (12 tests)

- [ ] **Step 5: Write failing test for the shared role→query mapping**

```python
# tests/test_role_queries.py
from tools.role_queries import ROLE_QUERIES


def test_role_queries_covers_exactly_the_three_roles():
    assert set(ROLE_QUERIES.keys()) == {"Business Analyst", "Data Analyst", "Consultant"}


def test_role_queries_each_role_has_nonempty_query_list():
    for role, queries in ROLE_QUERIES.items():
        assert isinstance(queries, list)
        assert len(queries) > 0
        assert all(isinstance(q, str) and q for q in queries)
```

- [ ] **Step 6: Run test to verify it fails**

Run: `pytest tests/test_role_queries.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'tools.role_queries'`

- [ ] **Step 7: Implement `tools/role_queries.py`**

```python
ROLE_QUERIES = {
    "Business Analyst": [
        "business analyst intern",
        "business analyst intern consulting",
        "business analyst intern banking",
    ],
    "Data Analyst": [
        "data analyst intern",
        "data analyst intern banking",
        "data analyst intern fintech",
    ],
    "Consultant": [
        "consultant intern",
        "consulting intern",
        "consultant intern banking",
    ],
}
```

- [ ] **Step 8: Run test to verify it passes**

Run: `pytest tests/test_role_queries.py -v`
Expected: PASS (2 tests)

- [ ] **Step 9: Commit**

```bash
git add tools/job_filters.py tests/test_job_filters.py tools/role_queries.py tests/test_role_queries.py
git commit -m "feat: add shared job filtering heuristics and role query mapping"
```

---

## Task 3: Adzuna Search Tool

**Files:**
- Create: `tools/search_adzuna.py`
- Test: `tests/test_search_adzuna.py`

**Interfaces:**
- Consumes: `tools.job_filters.has_internship_keyword`, `matches_duration`, `passes_visa_check`; `tools.role_queries.ROLE_QUERIES`
- Produces: `search_postings(role: str, countries: list[str] | None = None) -> dict` returning
  `{"source": "adzuna", "success": bool, "error": str | None, "postings": [ {title, company, location, url, posted_date, source, role}, ... ]}`

- [ ] **Step 1: Verify Adzuna's supported country codes and response shape with a real call**

Adzuna's API is per-country, not global — confirm which of your target markets it actually covers before hardcoding a list. With your real key in `.env`, run:

```bash
source .env
curl -s "https://api.adzuna.com/v1/api/jobs/us/search/1?app_id=$ADZUNA_APP_ID&app_key=$ADZUNA_APP_KEY&results_per_page=1&what=intern&content-type=application/json" | python3 -m json.tool | head -40
```

Repeat with `sg`, `in`, `gb`, `au` in place of `us` (Singapore, India, UK, Australia — Adzuna does not cover Indonesia directly). Confirm each returns `"results"` with `title`, `company.display_name`, `location.display_name`, `redirect_url`, `created`, `description` fields as expected. If any country 404s or a field name differs, note it — you'll adjust `DEFAULT_COUNTRIES` or the field mapping in Step 3 accordingly.

- [ ] **Step 2: Write failing tests**

```python
# tests/test_search_adzuna.py
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
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `pytest tests/test_search_adzuna.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'tools.search_adzuna'`

- [ ] **Step 4: Implement `tools/search_adzuna.py`**

```python
import os

import requests

from tools.job_filters import has_internship_keyword, matches_duration, passes_visa_check
from tools.role_queries import ROLE_QUERIES

ADZUNA_BASE_URL = "https://api.adzuna.com/v1/api/jobs"

# Confirmed supported in Step 1; adjust if verification found otherwise.
DEFAULT_COUNTRIES = ["us", "sg", "in", "gb", "au"]


def search_postings(role: str, countries: list[str] | None = None) -> dict:
    app_id = os.environ.get("ADZUNA_APP_ID")
    app_key = os.environ.get("ADZUNA_APP_KEY")
    countries = countries or DEFAULT_COUNTRIES
    queries = ROLE_QUERIES.get(role, [role])

    postings = []
    try:
        for country in countries:
            for query in queries:
                url = f"{ADZUNA_BASE_URL}/{country}/search/1"
                params = {
                    "app_id": app_id,
                    "app_key": app_key,
                    "results_per_page": 20,
                    "what": query,
                    "content-type": "application/json",
                }
                response = requests.get(url, params=params, timeout=15)
                response.raise_for_status()
                data = response.json()
                for item in data.get("results", []):
                    title = item.get("title", "")
                    description = item.get("description", "")
                    if not has_internship_keyword(title, description):
                        continue
                    if not matches_duration(description):
                        continue
                    if not passes_visa_check(description):
                        continue
                    postings.append(
                        {
                            "title": title,
                            "company": item.get("company", {}).get("display_name", ""),
                            "location": item.get("location", {}).get("display_name", ""),
                            "url": item.get("redirect_url", ""),
                            "posted_date": item.get("created", "")[:10],
                            "source": "adzuna",
                            "role": role,
                        }
                    )
        return {"source": "adzuna", "success": True, "error": None, "postings": postings}
    except requests.RequestException as exc:
        return {"source": "adzuna", "success": False, "error": str(exc), "postings": []}


if __name__ == "__main__":
    import argparse
    import json

    from dotenv import load_dotenv

    load_dotenv()
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--role", required=True, choices=["Business Analyst", "Data Analyst", "Consultant"]
    )
    args = parser.parse_args()
    print(json.dumps(search_postings(args.role)))
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_search_adzuna.py -v`
Expected: PASS (2 tests)

- [ ] **Step 6: Commit**

```bash
git add tools/search_adzuna.py tests/test_search_adzuna.py
git commit -m "feat: add Adzuna search tool"
```

---

## Task 4: SerpAPI Google Jobs Search Tool

**Files:**
- Create: `tools/search_serpapi_jobs.py`
- Test: `tests/test_search_serpapi_jobs.py`

**Interfaces:**
- Consumes: `tools.job_filters.has_internship_keyword`, `matches_duration`, `passes_visa_check`; `tools.role_queries.ROLE_QUERIES`
- Produces: `search_postings(role: str) -> dict`, same return shape as Task 3, with `"source": "serpapi"`.

- [ ] **Step 1: Verify SerpAPI's Google Jobs response shape with a real call**

Field names below are based on SerpAPI's documented Google Jobs schema, but confirm against a live response before trusting it. With your real key in `.env`, run:

```bash
source .env
curl -s "https://serpapi.com/search.json?engine=google_jobs&q=business+analyst+intern&api_key=$SERPAPI_API_KEY&hl=en" | python3 -m json.tool | head -60
```

Confirm `jobs_results` contains `title`, `company_name`, `location`, `description`, `apply_options` (list with `link`), and `detected_extensions.posted_at`. Adjust the field mapping in Step 3 if any of these differ in your actual response.

- [ ] **Step 2: Write failing tests**

```python
# tests/test_search_serpapi_jobs.py
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
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `pytest tests/test_search_serpapi_jobs.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 4: Implement `tools/search_serpapi_jobs.py`**

```python
import os

import requests

from tools.job_filters import has_internship_keyword, matches_duration, passes_visa_check
from tools.role_queries import ROLE_QUERIES

SERPAPI_BASE_URL = "https://serpapi.com/search.json"


def search_postings(role: str) -> dict:
    api_key = os.environ.get("SERPAPI_API_KEY")
    queries = ROLE_QUERIES.get(role, [role])

    postings = []
    try:
        for query in queries:
            params = {
                "engine": "google_jobs",
                "q": query,
                "api_key": api_key,
                "hl": "en",
            }
            response = requests.get(SERPAPI_BASE_URL, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()
            for item in data.get("jobs_results", []):
                title = item.get("title", "")
                description = item.get("description", "")
                if not has_internship_keyword(title, description):
                    continue
                if not matches_duration(description):
                    continue
                if not passes_visa_check(description):
                    continue
                apply_options = item.get("apply_options") or []
                url = apply_options[0]["link"] if apply_options else ""
                posted_date = item.get("detected_extensions", {}).get("posted_at", "")
                postings.append(
                    {
                        "title": title,
                        "company": item.get("company_name", ""),
                        "location": item.get("location", ""),
                        "url": url,
                        "posted_date": posted_date,
                        "source": "serpapi",
                        "role": role,
                    }
                )
        return {"source": "serpapi", "success": True, "error": None, "postings": postings}
    except requests.RequestException as exc:
        return {"source": "serpapi", "success": False, "error": str(exc), "postings": []}


if __name__ == "__main__":
    import argparse
    import json

    from dotenv import load_dotenv

    load_dotenv()
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--role", required=True, choices=["Business Analyst", "Data Analyst", "Consultant"]
    )
    args = parser.parse_args()
    print(json.dumps(search_postings(args.role)))
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_search_serpapi_jobs.py -v`
Expected: PASS (2 tests)

- [ ] **Step 6: Commit**

```bash
git add tools/search_serpapi_jobs.py tests/test_search_serpapi_jobs.py
git commit -m "feat: add SerpAPI Google Jobs search tool"
```

---

## Task 5: Google Auth Helper

**Files:**
- Create: `tools/google_auth.py`
- Test: `tests/test_google_auth.py`

**Interfaces:**
- Produces:
  - `get_credentials(scopes: list[str]) -> Credentials`
  - `SHEETS_SCOPE: str`, `GMAIL_SEND_SCOPE: str`, `ALL_SCOPES: list[str]`
- Consumed by: Task 6, 7, 8

- [ ] **Step 1: Write failing tests**

```python
# tests/test_google_auth.py
from unittest.mock import MagicMock

import tools.google_auth as google_auth


def test_get_credentials_uses_valid_existing_token(monkeypatch, tmp_path):
    token_path = tmp_path / "token.json"
    token_path.write_text("{}")
    monkeypatch.setattr(google_auth, "TOKEN_PATH", str(token_path))

    fake_creds = MagicMock(valid=True)
    monkeypatch.setattr(
        google_auth.Credentials, "from_authorized_user_file", lambda path, scopes: fake_creds
    )
    flow_called = MagicMock()
    monkeypatch.setattr(
        google_auth.InstalledAppFlow, "from_client_secrets_file", flow_called
    )

    result = google_auth.get_credentials(["scope-a"])

    assert result is fake_creds
    flow_called.assert_not_called()


def test_get_credentials_runs_flow_when_token_missing(monkeypatch, tmp_path):
    token_path = tmp_path / "token.json"
    monkeypatch.setattr(google_auth, "TOKEN_PATH", str(token_path))
    monkeypatch.setattr(google_auth, "CREDENTIALS_PATH", "credentials.json")

    fake_creds = MagicMock(valid=True)
    fake_creds.to_json.return_value = "{}"
    fake_flow = MagicMock()
    fake_flow.run_local_server.return_value = fake_creds

    monkeypatch.setattr(
        google_auth.InstalledAppFlow,
        "from_client_secrets_file",
        lambda path, scopes: fake_flow,
    )

    result = google_auth.get_credentials(["scope-a"])

    assert result is fake_creds
    fake_flow.run_local_server.assert_called_once_with(port=0)
    assert token_path.read_text() == "{}"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_google_auth.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement `tools/google_auth.py`**

```python
import os

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

TOKEN_PATH = "token.json"
CREDENTIALS_PATH = "credentials.json"

SHEETS_SCOPE = "https://www.googleapis.com/auth/spreadsheets"
GMAIL_SEND_SCOPE = "https://www.googleapis.com/auth/gmail.send"
ALL_SCOPES = [SHEETS_SCOPE, GMAIL_SEND_SCOPE]


def get_credentials(scopes: list[str]) -> Credentials:
    creds = None
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, scopes)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, scopes)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_PATH, "w") as token_file:
            token_file.write(creds.to_json())

    return creds
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_google_auth.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add tools/google_auth.py tests/test_google_auth.py
git commit -m "feat: add Google OAuth credential helper for Sheets and Gmail"
```

---

## Task 6: Tracker Sheet Setup Tool

**Files:**
- Create: `tools/setup_tracker_sheet.py`
- Test: `tests/test_setup_tracker_sheet.py`

**Interfaces:**
- Consumes: `tools.google_auth.get_credentials`, `SHEETS_SCOPE`
- Produces: `create_tracker_spreadsheet(service) -> str` (spreadsheet ID), `HEADERS: list[str]`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_setup_tracker_sheet.py
from unittest.mock import MagicMock

from tools.setup_tracker_sheet import HEADERS, create_tracker_spreadsheet


def test_create_tracker_spreadsheet_creates_and_labels_headers():
    service = MagicMock()
    service.spreadsheets().create().execute.return_value = {"spreadsheetId": "sheet-123"}

    spreadsheet_id = create_tracker_spreadsheet(service)

    assert spreadsheet_id == "sheet-123"
    create_call = service.spreadsheets().create.call_args
    assert create_call.kwargs["body"]["properties"]["title"] == "Internship Tracker"

    update_call = service.spreadsheets().values().update.call_args
    assert update_call.kwargs["spreadsheetId"] == "sheet-123"
    assert update_call.kwargs["range"] == "Internship Tracker!A1"
    assert update_call.kwargs["body"]["values"] == [HEADERS]


def test_headers_match_spec_column_order():
    assert HEADERS == [
        "Date Found",
        "Title",
        "Company",
        "Location",
        "Source",
        "Posted Date",
        "URL",
        "Match %",
        "Status",
    ]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_setup_tracker_sheet.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement `tools/setup_tracker_sheet.py`**

```python
from tools.google_auth import SHEETS_SCOPE, get_credentials

HEADERS = [
    "Date Found",
    "Title",
    "Company",
    "Location",
    "Source",
    "Posted Date",
    "URL",
    "Match %",
    "Status",
]


def create_tracker_spreadsheet(service) -> str:
    spreadsheet = {
        "properties": {"title": "Internship Tracker"},
        "sheets": [{"properties": {"title": "Internship Tracker"}}],
    }
    result = service.spreadsheets().create(body=spreadsheet, fields="spreadsheetId").execute()
    spreadsheet_id = result["spreadsheetId"]

    service.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range="Internship Tracker!A1",
        valueInputOption="RAW",
        body={"values": [HEADERS]},
    ).execute()

    return spreadsheet_id


if __name__ == "__main__":
    from dotenv import load_dotenv
    from googleapiclient.discovery import build

    load_dotenv()
    creds = get_credentials([SHEETS_SCOPE])
    service = build("sheets", "v4", credentials=creds)
    new_spreadsheet_id = create_tracker_spreadsheet(service)
    print(f"Created tracker spreadsheet: {new_spreadsheet_id}")
    print("Add this to .env as TRACKER_SPREADSHEET_ID")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_setup_tracker_sheet.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add tools/setup_tracker_sheet.py tests/test_setup_tracker_sheet.py
git commit -m "feat: add one-time tracker spreadsheet setup tool"
```

---

## Task 7: Update Tracker Sheet Tool

**Files:**
- Create: `tools/update_tracker_sheet.py`
- Test: `tests/test_update_tracker_sheet.py`

**Interfaces:**
- Consumes: `tools.google_auth.get_credentials`, `SHEETS_SCOPE`
- Produces:
  - `get_existing_urls(service, spreadsheet_id: str) -> set[str]`
  - `append_postings(service, spreadsheet_id: str, postings: list[dict]) -> list[dict]` — postings must each have `title, company, location, url, posted_date, source, match_percent`; returns only the ones actually appended (post-dedup).

- [ ] **Step 1: Write failing tests**

```python
# tests/test_update_tracker_sheet.py
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_update_tracker_sheet.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement `tools/update_tracker_sheet.py`**

```python
import datetime

from tools.google_auth import SHEETS_SCOPE, get_credentials

SHEET_NAME = "Internship Tracker"
URL_COLUMN_RANGE = f"{SHEET_NAME}!G2:G"
DATA_APPEND_RANGE = f"{SHEET_NAME}!A2:I"


def get_existing_urls(service, spreadsheet_id: str) -> set[str]:
    result = (
        service.spreadsheets()
        .values()
        .get(spreadsheetId=spreadsheet_id, range=URL_COLUMN_RANGE)
        .execute()
    )
    rows = result.get("values", [])
    return {row[0] for row in rows if row}


def _build_row(posting: dict) -> list:
    return [
        datetime.date.today().isoformat(),
        posting["title"],
        posting["company"],
        posting["location"],
        posting["source"],
        posting["posted_date"],
        posting["url"],
        posting["match_percent"],
        "New",
    ]


def append_postings(service, spreadsheet_id: str, postings: list[dict]) -> list[dict]:
    existing_urls = get_existing_urls(service, spreadsheet_id)
    new_postings = [p for p in postings if p["url"] not in existing_urls]

    if not new_postings:
        return []

    rows = [_build_row(p) for p in new_postings]
    service.spreadsheets().values().append(
        spreadsheetId=spreadsheet_id,
        range=DATA_APPEND_RANGE,
        valueInputOption="RAW",
        insertDataOption="INSERT_ROWS",
        body={"values": rows},
    ).execute()

    return new_postings


if __name__ == "__main__":
    import json
    import os
    import sys

    from dotenv import load_dotenv
    from googleapiclient.discovery import build

    load_dotenv()
    spreadsheet_id = os.environ["TRACKER_SPREADSHEET_ID"]
    input_postings = json.load(sys.stdin)

    creds = get_credentials([SHEETS_SCOPE])
    service = build("sheets", "v4", credentials=creds)

    result_postings = append_postings(service, spreadsheet_id, input_postings)
    json.dump(result_postings, sys.stdout)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_update_tracker_sheet.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add tools/update_tracker_sheet.py tests/test_update_tracker_sheet.py
git commit -m "feat: add tracker sheet dedup and append tool"
```

---

## Task 8: Digest Email Tool

**Files:**
- Create: `tools/send_digest_email.py`
- Test: `tests/test_send_digest_email.py`

**Interfaces:**
- Consumes: `tools.google_auth.get_credentials`, `GMAIL_SEND_SCOPE`
- Produces:
  - `build_digest_email(postings: list[dict], source_status: dict, to_address: str) -> MIMEText` — postings need `role, company, title, location, posted_date, match_percent, url`; `source_status` is `{source_name: {"success": bool, "error": str | None}}`.
  - `send_digest(service, postings: list[dict], source_status: dict, to_address: str) -> None` — no-ops if `postings` is empty.

- [ ] **Step 1: Write failing tests**

```python
# tests/test_send_digest_email.py
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_send_digest_email.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement `tools/send_digest_email.py`**

```python
import base64
from email.mime.text import MIMEText

from tools.google_auth import GMAIL_SEND_SCOPE, get_credentials

ROLE_ORDER = ["Business Analyst", "Data Analyst", "Consultant"]


def build_digest_email(postings: list[dict], source_status: dict, to_address: str) -> MIMEText:
    grouped: dict[str, list[dict]] = {role: [] for role in ROLE_ORDER}
    for posting in postings:
        grouped.setdefault(posting.get("role", "Other"), []).append(posting)

    lines = []
    for role in ROLE_ORDER:
        role_postings = grouped.get(role, [])
        if not role_postings:
            continue
        lines.append(f"\n{role} ({len(role_postings)})")
        for p in role_postings:
            lines.append(
                f"- {p['company']} — {p['title']} ({p['location']}, posted {p['posted_date']}, "
                f"match {p['match_percent']}%)\n  {p['url']}"
            )

    lines.append("\n---")
    for source, status in source_status.items():
        if status.get("success"):
            lines.append(f"{source}: ok")
        else:
            lines.append(f"{source}: failed ({status.get('error')})")

    body = "\n".join(lines)
    message = MIMEText(body)
    message["to"] = to_address
    message["subject"] = f"Internship digest — {len(postings)} new posting(s)"
    return message


def send_digest(service, postings: list[dict], source_status: dict, to_address: str) -> None:
    if not postings:
        return

    message = build_digest_email(postings, source_status, to_address)
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    service.users().messages().send(userId="me", body={"raw": raw}).execute()


if __name__ == "__main__":
    import json
    import os
    import sys

    from dotenv import load_dotenv
    from googleapiclient.discovery import build

    load_dotenv()
    payload = json.load(sys.stdin)
    to_address = os.environ["DIGEST_EMAIL_TO"]

    creds = get_credentials([GMAIL_SEND_SCOPE])
    service = build("gmail", "v1", credentials=creds)

    send_digest(service, payload["postings"], payload["source_status"], to_address)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_send_digest_email.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add tools/send_digest_email.py tests/test_send_digest_email.py
git commit -m "feat: add digest email tool"
```

---

## Task 9: Workflow SOP

**Files:**
- Create: `workflows/weekly_internship_search.md`

**Interfaces:**
- Consumes: CLI interfaces of all Task 2–8 tools.
- Produces: the SOP the agent follows on every scheduled run.

- [ ] **Step 1: Write `workflows/weekly_internship_search.md`**

```markdown
# Weekly Internship Search

## Objective

Find new Business Analyst / Data Analyst / Consultant internship postings
matching the user's criteria, add genuinely new ones to the Google Sheet
tracker, and email a digest if anything new was found.

## Required inputs

- `.env` populated with `ADZUNA_APP_ID`, `ADZUNA_APP_KEY`, `SERPAPI_API_KEY`,
  `TRACKER_SPREADSHEET_ID`, `DIGEST_EMAIL_TO`.
- `credentials.json` (Desktop OAuth client) and `token.json` present.
- `reference/cv_business.txt`, `reference/cv_data.txt`, `reference/cv_consulting.txt`.

## Steps

1. For each role in ["Business Analyst", "Data Analyst", "Consultant"], run:
   ```bash
   python tools/search_adzuna.py --role "<role>"
   python tools/search_serpapi_jobs.py --role "<role>"
   ```
   Each prints a JSON object: `{"source": ..., "success": ..., "error": ...,
   "postings": [...]}`. Record `success`/`error` per source for the digest
   footer later. If a source fails, proceed with whatever the other source
   returned — don't abort the run.

2. Merge all postings from both sources across all three roles into one
   list. Deduplicate this merged list by `url` (a posting can appear in
   both sources).

3. Filter out postings whose `url` is already in the sheet. Run:
   ```bash
   python -c "
   import json, os, sys
   from dotenv import load_dotenv
   from googleapiclient.discovery import build
   from tools.google_auth import get_credentials, SHEETS_SCOPE
   from tools.update_tracker_sheet import get_existing_urls
   load_dotenv()
   creds = get_credentials([SHEETS_SCOPE])
   service = build('sheets', 'v4', credentials=creds)
   urls = get_existing_urls(service, os.environ['TRACKER_SPREADSHEET_ID'])
   print(json.dumps(sorted(urls)))
   "
   ```
   Drop any merged posting whose `url` is in this set.

4. For each remaining posting, read the CV matching its `role`:
   - Business Analyst → `reference/cv_business.txt`
   - Data Analyst → `reference/cv_data.txt`
   - Consultant → `reference/cv_consulting.txt`

   Estimate a skills/qualifications match percentage (0-100) between the
   CV and the posting's title + description. This is a judgment call — use
   your own reasoning, not a script. Add the result as `"match_percent"`
   on the posting dict. Drop any posting scoring below 70.

5. Pipe the surviving postings (as a JSON array, each with `match_percent`
   added) to the tracker sheet tool:
   ```bash
   echo '<json array>' | python tools/update_tracker_sheet.py
   ```
   This prints back the JSON array of postings that were actually appended
   (it dedups again internally in case of a race between steps 3 and 5).

6. If the array from step 5 is non-empty, send the digest:
   ```bash
   echo '{"postings": <appended array>, "source_status": <status dict from step 1>}' \
     | python tools/send_digest_email.py
   ```
   If the array is empty, skip this step — no email on a quiet week.

7. Summarize what happened in your final response: how many new postings
   were added per role, and whether any source failed this run.

## Handling recurring problems (WAT self-improvement loop)

- If a source consistently returns 0 postings or errors, investigate (check
  API docs, rate limits, key validity) and fix the relevant tool, then
  document the fix here.
- If CV matching feels systematically too strict or too lenient after a
  few runs, note it here and adjust the 70% threshold or matching approach
  by agreement with the user — don't silently change it.
- If the duration/visa keyword heuristics in `tools/job_filters.py` are
  letting through or excluding things they shouldn't, update the heuristics
  and document the change and why here.
```

- [ ] **Step 2: Verify CLI commands referenced in the workflow match actual tool flags**

Run each of these and confirm no errors (aside from missing real data, which is expected until Task 10):

```bash
python tools/search_adzuna.py --help
python tools/search_serpapi_jobs.py --help
python -c "from tools.update_tracker_sheet import get_existing_urls, append_postings; print('ok')"
python -c "from tools.send_digest_email import build_digest_email, send_digest; print('ok')"
```

Expected: all four succeed without `ImportError`/`AttributeError`.

- [ ] **Step 3: Commit**

```bash
git add workflows/weekly_internship_search.md
git commit -m "docs: add weekly internship search workflow SOP"
```

---

## Task 10: First Live End-to-End Run

This task can't be unit tested — it exercises real APIs and real Google
OAuth consent (a browser window will open once). Do this yourself with the
agent, following `workflows/weekly_internship_search.md` step by step.

**Files:** none created; this is a verification pass using everything built
in Tasks 1-9.

- [ ] **Step 1: Create the real tracker spreadsheet**

```bash
python tools/setup_tracker_sheet.py
```

This opens a browser for Google OAuth consent (first time only — grants
Sheets + Gmail scopes together since both are needed). It prints a
spreadsheet ID.

- [ ] **Step 2: Save the spreadsheet ID**

Add the printed ID to `.env` as `TRACKER_SPREADSHEET_ID=<id>`.

- [ ] **Step 3: Run the workflow once, manually, following each step in `workflows/weekly_internship_search.md`**

Use your real Adzuna/SerpAPI keys already in `.env`. Let the agent perform
step 4 (CV matching) live using your actual `reference/*.txt` files.

- [ ] **Step 4: Verify the sheet**

Open the spreadsheet (URL is `https://docs.google.com/spreadsheets/d/<TRACKER_SPREADSHEET_ID>/edit`).
Confirm: header row intact, new rows appended with sensible `Match %`
values, `Status` column reads "New" on every new row.

- [ ] **Step 5: Verify the email**

If any postings were found, confirm a digest email arrived at
`belbel.bella00@gmail.com`, grouped by role, with working links. If zero
postings passed the filters this run, confirm no email was sent — that's
correct behavior, not a bug.

- [ ] **Step 6: Re-run the workflow immediately a second time**

Confirm it appends nothing new (everything just added is now correctly
deduplicated) and, correctly, sends no email.

---

## Task 11: Weekly Scheduling

**Files:** none — this configures a Claude Code scheduled cloud agent, not
project files.

- [ ] **Step 1: Invoke the `schedule` skill to create a weekly routine**

Use the `schedule` skill (available in this environment) to create a
recurring cloud agent with:
- Cron: weekly, e.g. Monday 08:00 — confirm which timezone the scheduler
  uses when setting this up, and adjust the cron expression so it lands at
  8am Jakarta time (WIB, UTC+7) if the scheduler runs in UTC.
- Working directory: this project's path.
- Prompt: instruct the agent to read and execute
  `workflows/weekly_internship_search.md` end to end, exactly as done
  manually in Task 10, and to report a short summary of what it found.

- [ ] **Step 2: Verify the schedule was created**

List scheduled routines (via the `schedule` skill) and confirm the new
weekly internship search routine appears with the correct cron expression
and working directory.

- [ ] **Step 3: Commit any config the schedule skill writes to the repo, if applicable**

If the `schedule` skill stores its config as a file in this repo, add and
commit it:

```bash
git add -A
git status
git commit -m "chore: schedule weekly internship search automation"
```

If the schedule lives entirely in cloud config with nothing written to the
repo, skip this step — nothing to commit.
