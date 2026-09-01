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
