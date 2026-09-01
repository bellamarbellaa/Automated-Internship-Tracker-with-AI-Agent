import datetime

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


def current_week_tab_name(today: datetime.date | None = None) -> str:
    today = today or datetime.date.today()
    monday = today - datetime.timedelta(days=today.weekday())
    return f"{monday.day} {monday.strftime('%b')}"


def create_tracker_spreadsheet(service, tab_name: str | None = None) -> str:
    tab_name = tab_name or current_week_tab_name()
    spreadsheet = {
        "properties": {"title": "Internship Tracker"},
        "sheets": [{"properties": {"title": tab_name}}],
    }
    result = service.spreadsheets().create(body=spreadsheet, fields="spreadsheetId").execute()
    spreadsheet_id = result["spreadsheetId"]

    service.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range=f"{tab_name}!A1",
        valueInputOption="RAW",
        body={"values": [HEADERS]},
    ).execute()

    return spreadsheet_id


def ensure_week_tab(service, spreadsheet_id: str, tab_name: str) -> None:
    meta = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    existing_titles = {s["properties"]["title"] for s in meta["sheets"]}
    if tab_name in existing_titles:
        return

    service.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id,
        body={"requests": [{"addSheet": {"properties": {"title": tab_name}}}]},
    ).execute()

    service.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range=f"{tab_name}!A1",
        valueInputOption="RAW",
        body={"values": [HEADERS]},
    ).execute()


if __name__ == "__main__":
    from dotenv import load_dotenv
    from googleapiclient.discovery import build

    load_dotenv()
    creds = get_credentials([SHEETS_SCOPE])
    service = build("sheets", "v4", credentials=creds)
    new_spreadsheet_id = create_tracker_spreadsheet(service)
    print(f"Created tracker spreadsheet: {new_spreadsheet_id}")
    print("Add this to .env as TRACKER_SPREADSHEET_ID")
