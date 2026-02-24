"""
Google Sheets service – OAuth2 authentication and spreadsheet read/write.

Column layout (A–M, 1-based):
  A=link  B=title  C=author  D=date  E=stars  F=text_original
  G=pic_url_list  H=video_url_list  I=pic_processed  J=video_processed
  K=summary  L=auto  M=error
"""

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

from config import CREDENTIALS_PATH, GOOGLE_SCOPES, TOKEN_PATH


# ── Auth helpers ───────────────────────────────────────────────────────────────

def get_credentials() -> Credentials | None:
    creds = None
    if TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), GOOGLE_SCOPES)
    if creds and creds.valid:
        return creds
    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            TOKEN_PATH.write_text(creds.to_json())
            return creds
        except Exception:
            pass
    return None


def get_auth_url(redirect_uri: str) -> str:
    flow = Flow.from_client_secrets_file(
        str(CREDENTIALS_PATH),
        scopes=GOOGLE_SCOPES,
        redirect_uri=redirect_uri,
    )
    auth_url, _ = flow.authorization_url(access_type="offline", prompt="consent")
    return auth_url


def exchange_code(code: str, redirect_uri: str):
    flow = Flow.from_client_secrets_file(
        str(CREDENTIALS_PATH),
        scopes=GOOGLE_SCOPES,
        redirect_uri=redirect_uri,
    )
    flow.fetch_token(code=code)
    TOKEN_PATH.write_text(flow.credentials.to_json())


def get_auth_status() -> dict:
    if not CREDENTIALS_PATH.exists():
        return {
            "status": "no_credentials",
            "message": "请将 credentials.json 放入 data/ 目录",
        }
    creds = get_credentials()
    if creds:
        return {"status": "authorized", "message": "已授权"}
    return {"status": "unauthorized", "message": "未授权，请点击授权按钮"}


# ── Sheets read/write ──────────────────────────────────────────────────────────

def _build_service():
    creds = get_credentials()
    if not creds:
        raise RuntimeError("Google Sheets 未授权，请在设置页面完成授权")
    return build("sheets", "v4", credentials=creds)


def get_pending_rows(sheet_id: str) -> list[tuple[int, str]]:
    """
    Return (row_index, link) for every row where auto='' AND error=''.
    Row indices are 1-based (row 1 = header, data starts at row 2).
    """
    service = _build_service()
    result = (
        service.spreadsheets()
        .values()
        .get(spreadsheetId=sheet_id, range="A:M")
        .execute()
    )
    values = result.get("values", [])

    pending: list[tuple[int, str]] = []
    for i, row in enumerate(values[1:], start=2):  # skip header row
        # Pad to 13 columns
        row = list(row) + [""] * (13 - len(row))
        link = row[0].strip()
        auto = row[11].strip()
        error = row[12].strip()
        if link and not auto and not error:
            pending.append((i, link))

    return pending


def write_row(sheet_id: str, row_index: int, data: dict):
    """
    Write scraped + processed fields to columns B–K of the given row.
    Empty values are replaced with '0'.
    """
    service = _build_service()

    fields = [
        "title", "author", "date", "stars", "text_original",
        "pic_url_list", "video_url_list",
        "pic_processed", "video_processed", "summary",
    ]
    values = []
    for field in fields:
        val = data.get(field, "0")
        if val is None or val == "":
            val = "0"
        if isinstance(val, list):
            val = ", ".join(str(v) for v in val) if val else "0"
        values.append(str(val))

    service.spreadsheets().values().update(
        spreadsheetId=sheet_id,
        range=f"B{row_index}:K{row_index}",
        valueInputOption="RAW",
        body={"values": [values]},
    ).execute()


def update_status(
    sheet_id: str,
    row_index: int,
    auto: str | None = None,
    error: str | None = None,
):
    """Update the auto (column L) and/or error (column M) fields."""
    service = _build_service()

    if auto is not None:
        service.spreadsheets().values().update(
            spreadsheetId=sheet_id,
            range=f"L{row_index}",
            valueInputOption="RAW",
            body={"values": [[str(auto)]]},
        ).execute()

    if error is not None:
        service.spreadsheets().values().update(
            spreadsheetId=sheet_id,
            range=f"M{row_index}",
            valueInputOption="RAW",
            body={"values": [[str(error)[:500]]]},
        ).execute()
