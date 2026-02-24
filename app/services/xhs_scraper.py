"""
XHS (Xiaohongshu) scraper – Playwright-based.

Cookie capture:
  Opens a visible browser, waits for the user to log in, detects the
  'web_session' cookie, then saves all cookies to xhs_cookies.json.

Note scraping:
  Navigates to the note URL with saved cookies, intercepts XHS API
  responses, and extracts structured note data.
  Falls back to window.__INITIAL_STATE__ or DOM extraction if needed.
"""

import asyncio
import json
import os
import re
from datetime import datetime
from typing import Optional

from playwright.async_api import Browser, async_playwright

from config import XHS_COOKIES_PATH


def _get_chromium_path() -> Optional[str]:
    """Find Chromium executable on Render or other environments."""
    import glob

    # Possible chromium paths on Render
    patterns = [
        "/opt/render/.cache/ms-playwright/chromium-*/chrome-linux/chrome",
        "/opt/render/.cache/ms-playwright/chromium_headless_shell-*/chrome-headless-shell-linux64/chrome-headless-shell",
    ]

    for pattern in patterns:
        paths = glob.glob(pattern)
        if paths:
            return paths[0]

    # Check environment variable
    env_path = os.getenv("PLAYWRIGHT_CHROMIUM_PATH")
    if env_path and os.path.exists(env_path):
        return env_path

    return None

# ── Global state for cookie capture ───────────────────────────────────────────
_capture_browser: Optional[Browser] = None
_capture_in_progress: bool = False


# ── Cookie helpers ─────────────────────────────────────────────────────────────

def load_cookies() -> list:
    if XHS_COOKIES_PATH.exists():
        try:
            return json.loads(XHS_COOKIES_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return []


def save_cookies(cookies: list):
    XHS_COOKIES_PATH.write_text(
        json.dumps(cookies, ensure_ascii=False, indent=2), encoding="utf-8"
    )


# Path to store raw cookie string for auto-fill
XHS_COOKIE_RAW_PATH = XHS_COOKIES_PATH.parent / "xhs_cookie_raw.txt"


def save_cookie_raw_string(cookie_string: str):
    """Save raw cookie string for auto-fill."""
    XHS_COOKIE_RAW_PATH.write_text(cookie_string, encoding="utf-8")


def get_cookie_raw_string() -> str:
    """Get saved raw cookie string for auto-fill."""
    if XHS_COOKIE_RAW_PATH.exists():
        return XHS_COOKIE_RAW_PATH.read_text(encoding="utf-8")
    return ""


def get_cookie_status() -> dict:
    if not XHS_COOKIES_PATH.exists():
        return {"status": "not_captured", "message": "未获取"}
    cookies = load_cookies()
    if not cookies:
        return {"status": "not_captured", "message": "未获取"}
    has_session = any(c.get("name") == "web_session" for c in cookies)
    if not has_session:
        return {"status": "invalid", "message": "Cookie 无效，请重新获取"}
    return {
        "status": "captured",
        "message": f"已获取（共 {len(cookies)} 个）",
        "count": len(cookies),
    }


def import_cookies_from_string(cookie_string: str) -> dict:
    """
    Parse and import cookies from various formats:
    1. document.cookie format: "key1=value1; key2=value2"
    2. JSON array from DevTools
    3. Curl format
    """
    import json
    cookies = []

    # Save raw string for auto-fill (even if parsing fails, user can edit and retry)
    save_cookie_raw_string(cookie_string)

    # Try parsing as JSON first
    try:
        data = json.loads(cookie_string)
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict) and "name" in item and "value" in item:
                    cookies.append({
                        "name": item["name"],
                        "value": item["value"],
                        "domain": item.get("domain", ".xiaohongshu.com"),
                        "path": item.get("path", "/"),
                    })
            if cookies:
                save_cookies(cookies)
                has_session = any(c["name"] == "web_session" for c in cookies)
                return {
                    "status": "captured" if has_session else "imported",
                    "message": f"成功导入 {len(cookies)} 个 Cookie" + (
                        "" if has_session else "（缺少 web_session，可能无法正常工作）"
                    ),
                    "count": len(cookies),
                }
    except json.JSONDecodeError:
        pass

    # Parse as document.cookie format: "key=value; key2=value2"
    if "=" in cookie_string and ";" in cookie_string:
        pairs = [p.strip() for p in cookie_string.split(";") if p.strip()]
        for pair in pairs:
            if "=" not in pair:
                continue
            # Handle multiple "=" in value
            eq_pos = pair.find("=")
            name = pair[:eq_pos].strip()
            value = pair[eq_pos + 1 :].strip()
            if name:
                cookies.append(
                    {
                        "name": name,
                        "value": value,
                        "domain": ".xiaohongshu.com",
                        "path": "/",
                    }
                )

        if cookies:
            save_cookies(cookies)
            has_session = any(c["name"] == "web_session" for c in cookies)
            return {
                "status": "captured" if has_session else "imported",
                "message": f"成功导入 {len(cookies)} 个 Cookie" + (
                    "" if has_session else "（缺少 web_session，可能无法正常工作）"
                ),
                "count": len(cookies),
            }

    return {"status": "error", "message": "无法解析 Cookie 格式，请检查输入内容"}


def is_capturing() -> bool:
    return _capture_in_progress


# ── Cookie capture flow ────────────────────────────────────────────────────────

async def capture_cookies_async():
    """
    Opens a visible Chromium window navigating to xiaohongshu.com.
    Polls every 2 s for the web_session cookie (login success signal).
    Saves cookies and closes the browser when found, or after 5 min timeout.
    """
    global _capture_browser, _capture_in_progress
    if _capture_in_progress:
        return

    _capture_in_progress = True
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=False,
                args=["--start-maximized"],
            )
            _capture_browser = browser
            context = await browser.new_context(
                viewport={"width": 1280, "height": 800},
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
            )
            page = await context.new_page()
            await page.goto("https://www.xiaohongshu.com")

            # Poll for up to 5 minutes
            for _ in range(150):
                if _capture_browser is None:
                    break  # cancelled
                await asyncio.sleep(2)
                cookies = await context.cookies("https://www.xiaohongshu.com")
                if any(c["name"] == "web_session" for c in cookies):
                    save_cookies(cookies)
                    break

            await browser.close()
    except Exception:
        pass
    finally:
        _capture_browser = None
        _capture_in_progress = False


async def cancel_capture():
    global _capture_browser
    if _capture_browser:
        try:
            await _capture_browser.close()
        except Exception:
            pass
        _capture_browser = None


# ── Note data parsing ──────────────────────────────────────────────────────────

def _fmt_ts(ts_ms: int) -> str:
    try:
        return datetime.fromtimestamp(ts_ms / 1000).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return "0"


def _parse_image_list(image_list: list) -> list[str]:
    urls = []
    for img in image_list:
        url = (
            img.get("url_default")
            or img.get("urlDefault")
            or img.get("url")
            or ""
        )
        if not url:
            info_list = img.get("infoList", img.get("info_list", []))
            if info_list:
                url = info_list[0].get("url", "")
        if url:
            if url.startswith("//"):
                url = "https:" + url
            urls.append(url)
    return urls


def _parse_video(video: dict) -> list[str]:
    try:
        streams = video.get("media", {}).get("stream", {})
        if not isinstance(streams, dict):
            return []
        for quality in ("h265", "h264", "av1"):
            stream_list = streams.get(quality, [])
            if stream_list:
                master_url = (
                    stream_list[0].get("master_url")
                    or stream_list[0].get("masterUrl")
                    or (stream_list[0].get("backupUrls") or [""])[0]
                    or (stream_list[0].get("backup_urls") or [""])[0]
                )
                if master_url:
                    return [master_url]
    except Exception:
        pass
    return []


def _parse_from_note_card(note: dict) -> dict:
    """Parse from XHS API note_card / note dict (various response formats)."""
    result = {
        "title": "0", "author": "0", "date": "0", "stars": "0",
        "text_original": "0", "pic_url_list": [], "video_url_list": [],
    }

    result["title"] = note.get("title") or note.get("desc", "")[:80] or "0"

    user = note.get("user") or note.get("author") or {}
    result["author"] = user.get("nickname") or user.get("name") or "0"

    ts = note.get("time") or note.get("create_time") or 0
    if ts:
        result["date"] = _fmt_ts(int(ts))

    interact = note.get("interact_info") or note.get("interactInfo") or {}
    collected = (
        interact.get("collected_count")
        or interact.get("collectCount")
        or interact.get("collect_count")
        or "0"
    )
    result["stars"] = str(collected)

    desc = note.get("desc") or note.get("content") or ""
    result["text_original"] = desc if desc else "0"

    images = note.get("image_list") or note.get("imageList") or []
    result["pic_url_list"] = _parse_image_list(images)

    video = note.get("video") or {}
    if video:
        result["video_url_list"] = _parse_video(video)

    return result


def _parse_initial_state(state: dict) -> dict:
    """Parse from window.__INITIAL_STATE__."""
    try:
        note_map = state.get("note", {}).get("noteDetailMap", {})
        if not note_map:
            return {}
        note_id = next(iter(note_map))
        note = note_map[note_id].get("note", {})
        return _parse_from_note_card(note)
    except Exception:
        return {}


# ── Main scrape function ───────────────────────────────────────────────────────

async def scrape_note(url: str) -> dict:
    """
    Scrape a Xiaohongshu note URL and return structured data.
    Raises RuntimeError if cookies are missing or data cannot be parsed.
    """
    cookies = load_cookies()
    if not cookies:
        raise RuntimeError("未获取小红书 Cookie，请先在设置页面获取 Cookie")

    async with async_playwright() as p:
        # Launch browser with Render-compatible settings
        chromium_path = _get_chromium_path()
        launch_options = {
            "headless": True,
            "args": [
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
            ],
        }
        if chromium_path:
            launch_options["executable_path"] = chromium_path

        browser = await p.chromium.launch(**launch_options)
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        )
        await context.add_cookies(cookies)
        page = await context.new_page()

        note_data: dict = {}

        async def on_response(response):
            nonlocal note_data
            url_lower = response.url.lower()
            if any(
                kw in url_lower
                for kw in ("/api/sns/web/v1/feed", "/api/sns/web/v1/note/detail", "/api/sns/web/v2/note")
            ):
                try:
                    body = await response.json()
                    items = body.get("data", {}).get("items", [])
                    if items:
                        note_card = items[0].get("note_card") or items[0]
                        parsed = _parse_from_note_card(note_card)
                        if parsed.get("title") and parsed["title"] != "0":
                            note_data = parsed
                except Exception:
                    pass

        page.on("response", on_response)

        try:
            await page.goto(url, wait_until="networkidle", timeout=30_000)
        except Exception:
            try:
                await page.goto(url, timeout=30_000)
                await page.wait_for_timeout(3000)
            except Exception:
                pass

        # Fallback 1: window.__INITIAL_STATE__
        if not note_data.get("title") or note_data.get("title") == "0":
            try:
                state = await page.evaluate("() => window.__INITIAL_STATE__")
                if state:
                    note_data = _parse_initial_state(state)
            except Exception:
                pass

        # Fallback 2: DOM extraction
        if not note_data.get("title") or note_data.get("title") == "0":
            try:
                note_data = await _extract_from_dom(page)
            except Exception:
                pass

        await browser.close()

    if not note_data or (note_data.get("title") == "0" and not note_data.get("text_original")):
        raise RuntimeError("无法解析笔记内容，Cookie 可能已过期或链接无效")

    return note_data


async def _extract_from_dom(page) -> dict:
    """Last-resort DOM extraction."""
    result = {
        "title": "0", "author": "0", "date": "0", "stars": "0",
        "text_original": "0", "pic_url_list": [], "video_url_list": [],
    }
    try:
        selectors = {
            "title": "#detail-title, .note-title, h1",
            "author": ".username, .author-name, [class*='user'] [class*='name']",
            "text_original": "#detail-desc .desc, .note-content, [class*='content']",
        }
        for key, selector in selectors.items():
            try:
                el = await page.query_selector(selector)
                if el:
                    text = (await el.inner_text()).strip()
                    if text:
                        result[key] = text
            except Exception:
                pass

        # Images
        img_els = await page.query_selector_all("img[src*='xhscdn'], img[src*='xhsimg']")
        pic_urls = []
        for img in img_els:
            src = await img.get_attribute("src") or ""
            if src and src not in pic_urls:
                pic_urls.append(src)
        result["pic_url_list"] = pic_urls[:20]  # cap at 20

    except Exception:
        pass
    return result
