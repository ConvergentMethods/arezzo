"""OAuth2 authentication for the Arezzo MCP server.

Credential lookup order:
  1. AREZZO_CREDENTIALS_FILE env var (absolute path)
  2. ~/.config/arezzo/credentials.json  (installed / arezzo init)
  3. <repo-root>/credentials.json       (development fallback)

Token is always cached next to the credentials file it was derived from.
"""

from __future__ import annotations

import os
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/drive",
]

_CONFIG_DIR = Path.home() / ".config" / "arezzo"
_REPO_ROOT = Path(__file__).parent.parent  # dev/arezzo/


def _resolve_credentials_file() -> Path:
    """Return the credentials.json path to use, in priority order."""
    env_path = os.environ.get("AREZZO_CREDENTIALS_FILE")
    if env_path:
        return Path(env_path)

    installed = _CONFIG_DIR / "credentials.json"
    if installed.exists():
        return installed

    dev = _REPO_ROOT / "credentials.json"
    if dev.exists():
        return dev

    raise FileNotFoundError(
        "No credentials.json found. Run `arezzo init` to set up authentication, "
        "or set AREZZO_CREDENTIALS_FILE to the path of your OAuth client secret."
    )


def _token_file_for(credentials_file: Path) -> Path:
    """Return the token.json path co-located with the given credentials file."""
    return credentials_file.parent / "token.json"


def get_credentials() -> Credentials:
    """Return valid OAuth2 credentials, running the consent flow if needed."""
    credentials_file = _resolve_credentials_file()
    token_file = _token_file_for(credentials_file)

    creds = None
    if token_file.exists():
        creds = Credentials.from_authorized_user_file(str(token_file), SCOPES)

    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    elif not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file(str(credentials_file), SCOPES)
        creds = flow.run_local_server(port=0)

    token_file.parent.mkdir(parents=True, exist_ok=True)
    token_file.write_text(creds.to_json())
    return creds


def get_docs_service():
    """Return an authenticated Google Docs API service."""
    from googleapiclient.discovery import build

    return build("docs", "v1", credentials=get_credentials())
