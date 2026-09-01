import datetime
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from tools.google_auth import SHEETS_SCOPE, get_credentials

SHEET_NAME = "Internship Tracker"
URL_COLUMN_RANGE = f"{SHEET_NAME}!G2:G"
DATA_APPEND_RANGE = f"{SHEET_NAME}!A2:I"

# Query params known to be per-request tracking noise rather than part of a
# job's identity. Adzuna's "se" token rotates on every API call for the same
# job listing (confirmed by comparing two live searches: same URL path and
# "v" value, different "se") -- without stripping it, the same still-open
# posting would look "new" every week and get re-appended as a duplicate row.
_TRACKING_QUERY_PARAMS = {"se", "utm_source", "utm_medium", "utm_campaign"}


def _normalize_url(url: str) -> str:
    url = url.strip().rstrip("/")
    parts = urlsplit(url)
    kept_query = [
        (k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True)
        if k not in _TRACKING_QUERY_PARAMS
    ]
    return urlunsplit(
        (parts.scheme, parts.netloc, parts.path, urlencode(kept_query), parts.fragment)
    )


def get_existing_urls(service, spreadsheet_id: str) -> set[str]:
    result = (
        service.spreadsheets()
        .values()
        .get(spreadsheetId=spreadsheet_id, range=URL_COLUMN_RANGE)
        .execute()
    )
    rows = result.get("values", [])
    return {_normalize_url(row[0]) for row in rows if row}


def _build_row(posting: dict) -> list:
    return [
        datetime.date.today().isoformat(),
        posting["title"],
        posting["company"],
        posting["location"],
        posting["source"],
        posting["posted_date"],
        _normalize_url(posting["url"]),
        posting["match_percent"],
        "New",
    ]


def append_postings(service, spreadsheet_id: str, postings: list[dict]) -> list[dict]:
    existing_urls = get_existing_urls(service, spreadsheet_id)

    new_postings = []
    seen_in_batch = set()
    for p in postings:
        key = _normalize_url(p["url"])
        if key in existing_urls or key in seen_in_batch:
            continue
        seen_in_batch.add(key)
        new_postings.append(p)

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
