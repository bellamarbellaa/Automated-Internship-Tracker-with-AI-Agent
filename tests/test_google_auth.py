from unittest.mock import MagicMock

import tools.google_auth as google_auth


def test_get_credentials_uses_valid_existing_token(monkeypatch, tmp_path):
    token_path = tmp_path / "token.json"
    token_path.write_text("{}")
    monkeypatch.setattr(google_auth, "TOKEN_PATH", str(token_path))

    fake_creds = MagicMock(valid=True)
    monkeypatch.setattr(
        google_auth.Credentials, "from_authorized_user_file", lambda path, scopes: fake_creds
    )
    flow_called = MagicMock()
    monkeypatch.setattr(
        google_auth.InstalledAppFlow, "from_client_secrets_file", flow_called
    )

    result = google_auth.get_credentials(["scope-a"])

    assert result is fake_creds
    flow_called.assert_not_called()


def test_get_credentials_runs_flow_when_token_missing(monkeypatch, tmp_path):
    token_path = tmp_path / "token.json"
    monkeypatch.setattr(google_auth, "TOKEN_PATH", str(token_path))
    monkeypatch.setattr(google_auth, "CREDENTIALS_PATH", "credentials.json")

    fake_creds = MagicMock(valid=True)
    fake_creds.to_json.return_value = "{}"
    fake_flow = MagicMock()
    fake_flow.run_local_server.return_value = fake_creds

    monkeypatch.setattr(
        google_auth.InstalledAppFlow,
        "from_client_secrets_file",
        lambda path, scopes: fake_flow,
    )

    result = google_auth.get_credentials(["scope-a"])

    assert result is fake_creds
    fake_flow.run_local_server.assert_called_once_with(port=0)
    assert token_path.read_text() == "{}"
