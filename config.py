import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

DB_PATH = DATA_DIR / "xhslink.db"
CREDENTIALS_PATH = DATA_DIR / "credentials.json"
TOKEN_PATH = DATA_DIR / "token.json"
XHS_COOKIES_PATH = DATA_DIR / "xhs_cookies.json"

PORT = int(os.getenv("PORT", 8000))

GOOGLE_SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

# Google Sheets column order (A=1, 1-based index)
SHEETS_COLUMNS = {
    "link": 1,
    "title": 2,
    "author": 3,
    "date": 4,
    "stars": 5,
    "text_original": 6,
    "pic_url_list": 7,
    "video_url_list": 8,
    "pic_processed": 9,
    "video_processed": 10,
    "summary": 11,
    "auto": 12,
    "error": 13,
}
