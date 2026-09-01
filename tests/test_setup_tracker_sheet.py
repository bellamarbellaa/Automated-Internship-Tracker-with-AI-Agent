import datetime
from unittest.mock import MagicMock

from tools.setup_tracker_sheet import (
    HEADERS,
    create_tracker_spreadsheet,
    current_week_tab_name,
    ensure_week_tab,
)


def test_create_tracker_spreadsheet_creates_and_labels_headers():
    service = MagicMock()
    service.spreadsheets().create().execute.return_value = {"spreadsheetId": "sheet-123"}

    spreadsheet_id = create_tracker_spreadsheet(service, tab_name="31 Aug")

    assert spreadsheet_id == "sheet-123"
    create_call = service.spreadsheets().create.call_args
    assert create_call.kwargs["body"]["properties"]["title"] == "Internship Tracker"
    assert create_call.kwargs["body"]["sheets"][0]["properties"]["title"] == "31 Aug"

    update_call = service.spreadsheets().values().update.call_args
    assert update_call.kwargs["spreadsheetId"] == "sheet-123"
    assert update_call.kwargs["range"] == "31 Aug!A1"
    assert update_call.kwargs["body"]["values"] == [HEADERS]


def test_create_tracker_spreadsheet_defaults_to_current_week_tab_name():
    service = MagicMock()
    service.spreadsheets().create().execute.return_value = {"spreadsheetId": "sheet-123"}

    create_tracker_spreadsheet(service)

    create_call = service.spreadsheets().create.call_args
    assert create_call.kwargs["body"]["sheets"][0]["properties"]["title"] == current_week_tab_name()


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


def test_current_week_tab_name_uses_monday_as_first_day():
    # Tuesday 2026-09-01 -> the Monday that started that week is 2026-08-31
    tuesday = datetime.date(2026, 9, 1)
    assert current_week_tab_name(tuesday) == "31 Aug"


def test_current_week_tab_name_on_a_monday_is_itself():
    monday = datetime.date(2026, 8, 31)
    assert current_week_tab_name(monday) == "31 Aug"


def test_ensure_week_tab_creates_tab_when_missing():
    service = MagicMock()
    service.spreadsheets().get().execute.return_value = {
        "sheets": [{"properties": {"title": "24 Aug"}}]
    }

    ensure_week_tab(service, "sheet-123", "31 Aug")

    batch_call = service.spreadsheets().batchUpdate.call_args
    assert batch_call.kwargs["spreadsheetId"] == "sheet-123"
    add_sheet_request = batch_call.kwargs["body"]["requests"][0]["addSheet"]
    assert add_sheet_request["properties"]["title"] == "31 Aug"

    update_call = service.spreadsheets().values().update.call_args
    assert update_call.kwargs["range"] == "31 Aug!A1"
    assert update_call.kwargs["body"]["values"] == [HEADERS]


def test_ensure_week_tab_noop_when_tab_already_exists():
    service = MagicMock()
    service.spreadsheets().get().execute.return_value = {
        "sheets": [{"properties": {"title": "31 Aug"}}]
    }

    ensure_week_tab(service, "sheet-123", "31 Aug")

    service.spreadsheets().batchUpdate.assert_not_called()
    service.spreadsheets().values().update.assert_not_called()
