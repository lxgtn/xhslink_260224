"""
Feishu Sheets service – App-based authentication and spreadsheet read/write.

Column layout (A–M, 1-based):
  A=link  B=title  C=author  D=date  E=stars  F=text_original
  G=pic_url_list  H=video_url_list  I=pic_processed  J=video_processed
  K=summary  L=auto  M=error
"""

import httpx
import time

from app.db import models as db

FEISHU_BASE = "https://open.feishu.cn/open-apis"
_token_cache: dict = {"token": "", "expires_at": 0.0}
_sheet_id_cache: dict[str, str] = {}


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
            raise RuntimeError(f"访问多维表格失败: {error_msg}（请确认: 1.表格ID正确 2.应用已发布或表格已分享给应用）")
        resp.raise_for_status()
        data = resp.json()

    if data.get("code") != 0:
        error_msg = data.get('msg', '未知错误')
        # 常见错误提示
        if "permission" in error_msg.lower() or "access" in error_msg.lower():
            error_msg += "（请检查：1.应用是否已发布 2.表格是否已分享给应用所在企业）"
        elif "not found" in error_msg.lower() or "exist" in error_msg.lower():
            error_msg += "（请检查多维表格ID是否正确）"
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
    for i, row in enumerate(values[1:], start=2):  # skip header row
        # Pad to 13 columns
        row = list(row) + [""] * (13 - len(row))
        link = row[0].strip()
        auto = row[11].strip()
        error = row[12].strip()
        if link and not auto and not error:
            pending.append((i, link))

    return pending


async def write_row(spreadsheet_token: str, row_index: int, data: dict):
    """
    Write scraped + processed fields to columns B–K of the given row.
    Empty values are replaced with '0'.
    """
    token = await _get_access_token()
    sheet_id = await _get_sheet_id(token, spreadsheet_token)

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

    range_str = f"{sheet_id}!B{row_index}:K{row_index}"

    async with httpx.AsyncClient() as client:
        resp = await client.put(
            f"{FEISHU_BASE}/sheets/v2/spreadsheets/{spreadsheet_token}/values",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "valueRange": {
                    "range": range_str,
                    "values": [values],
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
    """Update the auto (column L) and/or error (column M) fields."""
    token = await _get_access_token()
    sheet_id = await _get_sheet_id(token, spreadsheet_token)

    updates = []
    if auto is not None:
        updates.append(("L", str(auto)))
    if error is not None:
        updates.append(("M", str(error)[:500]))

    for col, val in updates:
        range_str = f"{sheet_id}!{col}{row_index}"
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
