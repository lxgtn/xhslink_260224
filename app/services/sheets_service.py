"""
Feishu Sheets service – App-based authentication and spreadsheet read/write.

Column layout (flexible – based on header names):
  Required columns: link, title, author, date, stars, text_original,
                    pic_url_list, video_url_list, pic_processed, video_processed,
                    summary, auto, error
  Columns can be in any order as long as headers match exactly.
"""

import httpx
import time

from app.db import models as db

FEISHU_BASE = "https://open.feishu.cn/open-apis"
_token_cache: dict = {"token": "", "expires_at": 0.0}
_sheet_id_cache: dict[str, str] = {}
_column_map_cache: dict[str, dict[str, int]] = {}

# Required column headers
REQUIRED_COLUMNS = [
    "link", "title", "author", "date", "stars", "text_original",
    "pic_url_list", "video_url_list", "pic_processed", "video_processed",
    "summary", "auto", "error",
]


async def _get_access_token() -> str:
    """Get Feishu app_access_token (cached for ~2 hours)."""
    now = time.time()
    if _token_cache["token"] and now < _token_cache["expires_at"] - 300:
        return _token_cache["token"]

    cfg = await db.get_all_config()
    app_id = cfg.get("feishu_app_id", "").strip()
    app_secret = cfg.get("feishu_app_secret", "").strip()

    if not app_id or not app_secret:
        raise RuntimeError("飞书 App ID 或 App Secret 未配置")

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{FEISHU_BASE}/auth/v3/app_access_token/internal",
            json={"app_id": app_id, "app_secret": app_secret},
            timeout=30.0,
        )
        resp.raise_for_status()
        data = resp.json()

    if data.get("code") != 0:
        raise RuntimeError(f"飞书授权失败: {data.get('msg', '未知错误')}")

    token = data.get("app_access_token", "")
    expire = data.get("expire", 7200)
    _token_cache["token"] = token
    _token_cache["expires_at"] = now + expire
    return token


async def _get_sheet_id(token: str, spreadsheet_token: str) -> str:
    """Get the first sheet ID (cached)."""
    if spreadsheet_token in _sheet_id_cache:
        return _sheet_id_cache[spreadsheet_token]

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{FEISHU_BASE}/sheets/v3/spreadsheets/{spreadsheet_token}/sheets/query",
            headers={"Authorization": f"Bearer {token}"},
            timeout=30.0,
        )
        if resp.status_code == 400:
            error_data = resp.json() if resp.text else {}
            error_msg = error_data.get("msg", "请求参数错误")
            raise RuntimeError(f"访问文档库表格失败: {error_msg}（请确认: 1.表格ID正确 2.应用已发布或表格已分享给应用）")
        resp.raise_for_status()
        data = resp.json()

    if data.get("code") != 0:
        error_msg = data.get('msg', '未知错误')
        # 常见错误提示
        if "permission" in error_msg.lower() or "access" in error_msg.lower():
            error_msg += "（请检查：1.应用是否已发布 2.表格是否已分享给应用所在企业）"
        elif "not found" in error_msg.lower() or "exist" in error_msg.lower():
            error_msg += "（请检查文档库表格ID是否正确）"
        raise RuntimeError(f"获取工作表失败: {error_msg}")

    sheets = data.get("data", {}).get("sheets", [])
    if not sheets:
        raise RuntimeError("电子表格中没有找到工作表")

    raw_sheet_id = sheets[0].get("sheet_id", "")
    # 确保返回字符串（API 有时会返回列表）
    if isinstance(raw_sheet_id, list):
        sheet_id = raw_sheet_id[0] if raw_sheet_id else ""
    else:
        sheet_id = str(raw_sheet_id)
    _sheet_id_cache[spreadsheet_token] = sheet_id
    return sheet_id


def _build_column_map(header_row: list) -> dict[str, int]:
    """
    Build a mapping from column name to column index (0-based).
    Only includes recognized column names.
    """
    col_map = {}
    for idx, cell in enumerate(header_row):
        if cell:
            col_name = str(cell).strip().lower()
            if col_name in REQUIRED_COLUMNS:
                col_map[col_name] = idx
    return col_map


def _col_index(col_map: dict[str, int], name: str) -> int:
    """Get column index, raise error if column not found."""
    if name not in col_map:
        raise RuntimeError(f"表格缺少必需的列: '{name}'，请检查表头")
    return col_map[name]


def _col_to_letter(idx: int) -> str:
    """Convert 0-based column index to Excel column letter (A, B, C...)."""
    result = ""
    idx += 1  # Convert to 1-based
    while idx > 0:
        idx, remainder = divmod(idx - 1, 26)
        result = chr(65 + remainder) + result
    return result


async def _get_column_map(token: str, spreadsheet_token: str, sheet_id: str) -> dict[str, int]:
    """Get column mapping from header row (cached per spreadsheet)."""
    cache_key = f"{spreadsheet_token}:{sheet_id}"
    if cache_key in _column_map_cache:
        return _column_map_cache[cache_key]

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{FEISHU_BASE}/sheets/v2/spreadsheets/{spreadsheet_token}/values/{sheet_id}!A1:Z1",
            headers={"Authorization": f"Bearer {token}"},
            timeout=30.0,
        )
        resp.raise_for_status()
        data = resp.json()

    if data.get("code") != 0:
        raise RuntimeError(f"读取表头失败: {data.get('msg', '未知错误')}")

    values = data.get("data", {}).get("valueRange", {}).get("values", [])
    if not values:
        raise RuntimeError("无法读取表格表头，请确保表格不为空")

    header_row = values[0] if values else []
    col_map = _build_column_map(header_row)

    # Validate required columns
    missing = [col for col in REQUIRED_COLUMNS if col not in col_map]
    if missing:
        raise RuntimeError(f"表格缺少以下列: {', '.join(missing)}")

    _column_map_cache[cache_key] = col_map
    return col_map


def clear_column_map_cache(spreadsheet_token: str = None):
    """Clear column map cache, optionally for a specific spreadsheet."""
    global _column_map_cache
    if spreadsheet_token:
        keys_to_remove = [k for k in _column_map_cache if k.startswith(f"{spreadsheet_token}:")]
        for k in keys_to_remove:
            del _column_map_cache[k]
    else:
        _column_map_cache = {}


async def get_auth_status() -> dict:
    """Check if Feishu credentials are configured and valid."""
    cfg = await db.get_all_config()
    app_id = cfg.get("feishu_app_id", "").strip()
    app_secret = cfg.get("feishu_app_secret", "").strip()

    if not app_id or not app_secret:
        return {
            "status": "no_credentials",
            "message": "请先在设置页面填写飞书 App ID 和 App Secret",
        }

    try:
        await _get_access_token()
        return {"status": "authorized", "message": "飞书授权正常"}
    except Exception as e:
        return {"status": "unauthorized", "message": f"授权失败: {e}"}


async def get_pending_rows(spreadsheet_token: str) -> list[tuple[int, str]]:
    """
    Return (row_index, link) for every row where auto='' AND error=''.
    Row indices are 1-based (row 1 = header, data starts at row 2).
    """
    token = await _get_access_token()
    sheet_id = await _get_sheet_id(token, spreadsheet_token)
    col_map = await _get_column_map(token, spreadsheet_token, sheet_id)

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{FEISHU_BASE}/sheets/v2/spreadsheets/{spreadsheet_token}/values/{sheet_id}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=30.0,
        )
        resp.raise_for_status()
        data = resp.json()

    if data.get("code") != 0:
        raise RuntimeError(f"读取表格失败: {data.get('msg', '未知错误')}")

    values = data.get("data", {}).get("valueRange", {}).get("values", [])

    pending: list[tuple[int, str]] = []
    link_idx = _col_index(col_map, "link")
    auto_idx = _col_index(col_map, "auto")
    error_idx = _col_index(col_map, "error")

    for i, row in enumerate(values[1:], start=2):  # skip header row
        # Ensure row has enough columns
        row_len = len(row)
        link = str(row[link_idx]).strip() if row_len > link_idx and row[link_idx] else ""
        auto = str(row[auto_idx]).strip() if row_len > auto_idx and row[auto_idx] else ""
        error = str(row[error_idx]).strip() if row_len > error_idx and row[error_idx] else ""

        if link and not auto and not error:
            pending.append((i, link))

    return pending


async def write_row(spreadsheet_token: str, row_index: int, data: dict):
    """
    Write scraped + processed fields to the corresponding columns.
    Empty values are replaced with '0'.
    """
    token = await _get_access_token()
    sheet_id = await _get_sheet_id(token, spreadsheet_token)
    col_map = await _get_column_map(token, spreadsheet_token, sheet_id)

    fields = [
        "title", "author", "date", "stars", "text_original",
        "pic_url_list", "video_url_list",
        "pic_processed", "video_processed", "summary",
    ]

    # Build list of (column_letter, value) to update
    updates = []
    for field in fields:
        val = data.get(field, "0")
        if val is None or val == "":
            val = "0"
        if isinstance(val, list):
            val = ", ".join(str(v) for v in val) if val else "0"

        col_idx = _col_index(col_map, field)
        col_letter = _col_to_letter(col_idx)
        updates.append((col_letter, str(val)))

    # Batch update all fields
    for col_letter, val in updates:
        range_str = f"{sheet_id}!{col_letter}{row_index}:{col_letter}{row_index}"
        async with httpx.AsyncClient() as client:
            resp = await client.put(
                f"{FEISHU_BASE}/sheets/v2/spreadsheets/{spreadsheet_token}/values",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "valueRange": {
                        "range": range_str,
                        "values": [[val]],
                    }
                },
                timeout=30.0,
            )
            resp.raise_for_status()
            result = resp.json()

        if result.get("code") != 0:
            raise RuntimeError(f"写入表格失败: {result.get('msg', '未知错误')}")


async def update_status(
    spreadsheet_token: str,
    row_index: int,
    auto: str | None = None,
    error: str | None = None,
):
    """Update the auto and/or error fields based on column mapping."""
    token = await _get_access_token()
    sheet_id = await _get_sheet_id(token, spreadsheet_token)
    col_map = await _get_column_map(token, spreadsheet_token, sheet_id)

    updates = []
    if auto is not None:
        col_idx = _col_index(col_map, "auto")
        col_letter = _col_to_letter(col_idx)
        updates.append((col_letter, str(auto)))
    if error is not None:
        col_idx = _col_index(col_map, "error")
        col_letter = _col_to_letter(col_idx)
        updates.append((col_letter, str(error)[:500]))

    for col_letter, val in updates:
        range_str = f"{sheet_id}!{col_letter}{row_index}:{col_letter}{row_index}"
        async with httpx.AsyncClient() as client:
            resp = await client.put(
                f"{FEISHU_BASE}/sheets/v2/spreadsheets/{spreadsheet_token}/values",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "valueRange": {
                        "range": range_str,
                        "values": [[val]],
                    }
                },
                timeout=30.0,
            )
            resp.raise_for_status()
            result = resp.json()
            if result.get("code") != 0:
                raise RuntimeError(f"更新状态失败: {result.get('msg', '未知错误')}")
