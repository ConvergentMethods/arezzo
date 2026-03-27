"""OAuth2 authentication for Google Docs API."""

from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/drive",
]

REPO_ROOT = Path(__file__).parent
CREDENTIALS_FILE = REPO_ROOT / "credentials.json"
TOKEN_FILE = REPO_ROOT / "token.json"


def get_credentials() -> Credentials:
    """Return valid OAuth2 credentials, running the consent flow if needed."""
    creds = None

    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)

    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    elif not creds or not creds.valid:
        if not CREDENTIALS_FILE.exists():
            raise FileNotFoundError(
                f"OAuth client secret not found at {CREDENTIALS_FILE}. "
                "Copy your client_secret.json there."
            )
        flow = InstalledAppFlow.from_client_secrets_file(
            str(CREDENTIALS_FILE), SCOPES
        )
        creds = flow.run_local_server(port=0)

    # Cache for next run
    TOKEN_FILE.write_text(creds.to_json())
    return creds


def get_docs_service():
    """Return an authenticated Google Docs API service."""
    from googleapiclient.discovery import build

    return build("docs", "v1", credentials=get_credentials())


def get_drive_service():
    """Return an authenticated Google Drive API service."""
    from googleapiclient.discovery import build

    return build("drive", "v3", credentials=get_credentials())
