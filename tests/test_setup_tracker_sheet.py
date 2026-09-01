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
