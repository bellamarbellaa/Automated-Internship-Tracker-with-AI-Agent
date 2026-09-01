import os

import requests

from tools.job_filters import has_internship_keyword, matches_duration, passes_visa_check
from tools.role_queries import ROLE_QUERIES

SERPAPI_BASE_URL = "https://serpapi.com/search.json"

# NOTE: Field names below (jobs_results, title, company_name, location,
# description, apply_options[0].link, detected_extensions.posted_at) follow
# SerpAPI's documented Google Jobs schema but are not yet verified against a
# live response (no API key available in this environment). Confirm field
# mapping during the project's live end-to-end run and adjust if any differ.


def search_postings(role: str) -> dict:
    api_key = os.environ.get("SERPAPI_API_KEY")
    queries = ROLE_QUERIES.get(role, [role])

    postings = []
    seen_urls = set()
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
