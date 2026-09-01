import datetime
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from tools.google_auth import SHEETS_SCOPE, get_credentials
from tools.setup_tracker_sheet import current_week_tab_name

# Cap on how many rows get added to a single week's tab. If a week's tab
# already has some rows (e.g. a manual re-run the same week), only the
# remaining headroom up to this cap gets filled.
WEEKLY_CAP = 20

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


def get_existing_urls(service, spreadsheet_id: str, sheet_name: str) -> set[str]:
    result = (
        service.spreadsheets()
        .values()
        .get(spreadsheetId=spreadsheet_id, range=f"{sheet_name}!G2:G")
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


def append_postings(
    service, spreadsheet_id: str, postings: list[dict], sheet_name: str
) -> list[dict]:
    existing_urls = get_existing_urls(service, spreadsheet_id, sheet_name)

    candidates = []
    seen_in_batch = set()
    for p in postings:
        key = _normalize_url(p["url"])
        if key in existing_urls or key in seen_in_batch:
            continue
        seen_in_batch.add(key)
        candidates.append(p)

    headroom = max(0, WEEKLY_CAP - len(existing_urls))
    new_postings = sorted(candidates, key=lambda p: p["match_percent"], reverse=True)[:headroom]

    if not new_postings:
        return []

    rows = [_build_row(p) for p in new_postings]
    service.spreadsheets().values().append(
        spreadsheetId=spreadsheet_id,
        range=f"{sheet_name}!A2:I",
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

    result_postings = append_postings(
        service, spreadsheet_id, input_postings, current_week_tab_name()
    )
    json.dump(result_postings, sys.stdout)
