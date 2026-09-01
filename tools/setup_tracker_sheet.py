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
