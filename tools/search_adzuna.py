import os

import requests

from tools.job_filters import (
    has_internship_keyword,
    matches_duration,
    passes_visa_check,
    requires_completed_degree,
)
from tools.role_queries import ROLE_QUERIES

ADZUNA_BASE_URL = "https://api.adzuna.com/v1/api/jobs"

# Verified against a live Adzuna response during the project's end-to-end run
# (2026-09-01): all five countries return results with this field mapping.
DEFAULT_COUNTRIES = ["us", "sg", "in", "gb", "au"]


def search_postings(role: str, countries: list[str] | None = None) -> dict:
    app_id = os.environ.get("ADZUNA_APP_ID")
    app_key = os.environ.get("ADZUNA_APP_KEY")
    countries = countries or DEFAULT_COUNTRIES
    queries = ROLE_QUERIES.get(role, [role])

    postings = []
    seen_urls = set()
    errors = []

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
            try:
                response = requests.get(url, params=params, timeout=15)
                response.raise_for_status()
                data = response.json()
            except requests.RequestException as exc:
                # A single failed request (e.g. transient rate limit) must
                # not discard postings already collected from other
                # country/query combinations -- confirmed as a real failure
                # mode live: a full 3-role back-to-back run silently
                # returned zero Data Analyst postings because one request
                # out of ~15-20 for that role hit a transient error and the
                # old code discarded the whole role's results on any single
                # failure.
                errors.append(f"{country}/{query}: {exc}")
                continue

            for item in data.get("results", []):
                title = item.get("title", "")
                description = item.get("description", "")
                if not has_internship_keyword(title, description):
                    continue
                if not matches_duration(description):
                    continue
                if not passes_visa_check(description):
                    continue
                if requires_completed_degree(description):
                    continue
                url_value = item.get("redirect_url", "")
                if url_value in seen_urls:
                    continue
                seen_urls.add(url_value)
                postings.append(
                    {
                        "title": title,
                        "company": item.get("company", {}).get("display_name", ""),
                        "location": item.get("location", {}).get("display_name", ""),
                        "url": url_value,
                        "posted_date": item.get("created", "")[:10],
                        "source": "adzuna",
                        "role": role,
                        "description": description,
                    }
                )

    if not postings and errors:
        return {"source": "adzuna", "success": False, "error": "; ".join(errors), "postings": []}
    return {
        "source": "adzuna",
        "success": True,
        "error": "; ".join(errors) if errors else None,
        "postings": postings,
    }


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
