import os

import requests

from tools.job_filters import has_internship_keyword, matches_duration, passes_visa_check
from tools.role_queries import ROLE_QUERIES

ADZUNA_BASE_URL = "https://api.adzuna.com/v1/api/jobs"

# NOTE: Not yet verified against a live Adzuna response (no API keys available
# in this environment). Confirm coverage/field mapping during the project's
# live end-to-end run and adjust if any country 404s or fields differ.
DEFAULT_COUNTRIES = ["us", "sg", "in", "gb", "au"]


def search_postings(role: str, countries: list[str] | None = None) -> dict:
    app_id = os.environ.get("ADZUNA_APP_ID")
    app_key = os.environ.get("ADZUNA_APP_KEY")
    countries = countries or DEFAULT_COUNTRIES
    queries = ROLE_QUERIES.get(role, [role])

    postings = []
    seen_urls = set()
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
