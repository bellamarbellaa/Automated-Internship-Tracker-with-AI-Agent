import os

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

TOKEN_PATH = "token.json"
CREDENTIALS_PATH = "credentials.json"

SHEETS_SCOPE = "https://www.googleapis.com/auth/spreadsheets"
GMAIL_SEND_SCOPE = "https://www.googleapis.com/auth/gmail.send"
ALL_SCOPES = [SHEETS_SCOPE, GMAIL_SEND_SCOPE]


def get_credentials(scopes: list[str]) -> Credentials:
    creds = None
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, scopes)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, scopes)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_PATH, "w") as token_file:
            token_file.write(creds.to_json())

    return creds
