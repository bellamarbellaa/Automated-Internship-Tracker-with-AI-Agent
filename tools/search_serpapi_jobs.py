import os

import requests

from tools.job_filters import (
    has_internship_keyword,
    matches_duration,
    passes_visa_check,
    requires_completed_degree,
)
from tools.role_queries import INDONESIA_QUERIES, ROLE_QUERIES

SERPAPI_BASE_URL = "https://serpapi.com/search.json"

# Field names below (jobs_results, title, company_name, location,
# description, apply_options[0].link, detected_extensions.posted_at) were
# verified against a live SerpAPI Google Jobs response during the project's
# end-to-end run (2026-09-01).


def search_postings(role: str) -> dict:
    api_key = os.environ.get("SERPAPI_API_KEY")
    queries = ROLE_QUERIES.get(role, [role]) + INDONESIA_QUERIES.get(role, [])

    postings = []
    seen_urls = set()
    errors = []

    for query in queries:
        params = {
            "engine": "google_jobs",
            "q": query,
            "api_key": api_key,
            "hl": "en",
        }
        try:
            response = requests.get(SERPAPI_BASE_URL, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as exc:
            # A single failed request must not discard postings already
            # collected from other queries -- see the matching note in
            # search_adzuna.py for the real failure mode this fixes.
            errors.append(f"{query}: {exc}")
            continue

        for item in data.get("jobs_results", []):
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
            apply_options = item.get("apply_options") or []
            url = apply_options[0]["link"] if apply_options else ""
            if url in seen_urls:
                continue
            seen_urls.add(url)
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
                    "description": description,
                }
            )

    if not postings and errors:
        return {"source": "serpapi", "success": False, "error": "; ".join(errors), "postings": []}
    return {
        "source": "serpapi",
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
