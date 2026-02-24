"""
AI service – unified LLM calls via OpenAI-compatible SDK.

All major providers (OpenAI, Anthropic via proxy, Google Gemini via openai-compat,
DeepSeek, etc.) support the OpenAI API format, so we use the `openai` library
throughout with configurable base_url.

Image analysis:  pass image URL directly to the multimodal model.
Video analysis:  try URL-based analysis first (works with Gemini);
                 fall back to a descriptive placeholder for other providers.
Summary:         text-only completion combining all three sources.
"""

import tempfile
import os
from typing import Optional

import httpx
from openai import AsyncOpenAI

from app.schemas.config import AIConfig

_IMAGE_PROMPT = (
    "请分析此图片内容："
    "如果图片中包含文字，请提取所有文字内容；"
    "如果是纯视觉图片（照片、插图等，无文字或文字极少），请简短描述图片中的主要内容。"
    "直接输出内容，不要加前缀说明。"
)

_VIDEO_PROMPT = (
    "请分析以下视频内容，描述：\n"
    "1. 声音内容（语音/旁白/背景音乐等）\n"
    "2. 画面内容（场景/人物/字幕/关键视觉信息等）\n"
    "请归纳为结构化文字描述，语言简洁清晰。"
)

_SUMMARY_PROMPT = (
    "请基于以下小红书笔记的完整内容，生成一篇全面的内容总结。"
    "总结应覆盖核心观点、关键信息和主要内容，语言简洁清晰，不超过 500 字。\n\n"
    "{content}"
)


def _make_client(config: AIConfig) -> AsyncOpenAI:
    return AsyncOpenAI(
        api_key=config.api_key or "placeholder",
        base_url=config.api_base_url if config.api_base_url else None,
        timeout=120.0,
        max_retries=1,
    )


async def analyze_images(image_urls: list[str], config: AIConfig) -> str:
    """
    Analyze each image and return numbered descriptions joined by newlines.
    Returns '0' if no images provided.
    """
    if not image_urls:
        return "0"

    client = _make_client(config)
    results: list[str] = []

    for i, url in enumerate(image_urls, 1):
        if url.startswith("//"):
            url = "https:" + url
        try:
            resp = await client.chat.completions.create(
                model=config.model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {"url": url, "detail": "high"},
                            },
                            {"type": "text", "text": _IMAGE_PROMPT},
                        ],
                    }
                ],
                max_tokens=1000,
            )
            content = resp.choices[0].message.content.strip()
            results.append(f"{i}. {content}")
        except Exception as e:
            results.append(f"{i}. [图片解析失败: {str(e)[:120]}]")

    return "\n".join(results)


async def analyze_video(
    video_url: str,
    config: AIConfig,
    xhs_cookies: Optional[list] = None,
) -> str:
    """
    Analyze video content.
    Strategy:
      1. Try sending the video URL directly (works with Gemini's OpenAI-compat API).
      2. Try downloading the video and uploading via Files API.
      3. Fall back to a placeholder noting the video URL.
    Returns '0' if no URL provided.
    """
    if not video_url:
        return "0"

    client = _make_client(config)

    # Strategy 1: URL-based (Gemini supports this)
    try:
        resp = await client.chat.completions.create(
            model=config.model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": f"{_VIDEO_PROMPT}\n\n视频地址：{video_url}",
                        }
                    ],
                }
            ],
            max_tokens=2000,
        )
        result = resp.choices[0].message.content.strip()
        if result and len(result) > 30:
            return result
    except Exception:
        pass

    # Strategy 2: Download + upload via Files API
    try:
        tmp_path = await _download_video(video_url, xhs_cookies)
        if tmp_path:
            try:
                with open(tmp_path, "rb") as f:
                    file_obj = await client.files.create(
                        file=(os.path.basename(tmp_path), f, "video/mp4"),
                        purpose="assistants",
                    )
                resp = await client.chat.completions.create(
                    model=config.model,
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    "text": f"{_VIDEO_PROMPT}\n\n文件ID：{file_obj.id}",
                                }
                            ],
                        }
                    ],
                    max_tokens=2000,
                )
                return resp.choices[0].message.content.strip()
            finally:
                try:
                    os.unlink(tmp_path)
                except Exception:
                    pass
    except Exception:
        pass

    # Fallback: placeholder
    return f"[视频内容待分析，地址：{video_url[:120]}...]"


async def _download_video(
    video_url: str,
    xhs_cookies: Optional[list] = None,
    max_mb: int = 50,
) -> Optional[str]:
    """Download video to a temp file. Returns path or None on failure."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Referer": "https://www.xiaohongshu.com/",
    }
    cookie_dict = {}
    if xhs_cookies:
        for c in xhs_cookies:
            cookie_dict[c["name"]] = c["value"]

    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=60) as client:
            resp = await client.get(video_url, headers=headers, cookies=cookie_dict)
            resp.raise_for_status()

            content_length = int(resp.headers.get("content-length", 0))
            if content_length > max_mb * 1024 * 1024:
                return None  # too large

            suffix = ".mp4"
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
            tmp.write(resp.content)
            tmp.close()
            return tmp.name
    except Exception:
        return None


async def generate_summary(
    text: str, pics: str, video: str, config: AIConfig
) -> str:
    """
    Generate a comprehensive summary from text + image + video content.
    Returns '0' if all inputs are '0'.
    """
    if text == "0" and pics == "0" and video == "0":
        return "0"

    parts: list[str] = []
    if text and text != "0":
        parts.append(f"【原文内容】\n{text}")
    if pics and pics != "0":
        parts.append(f"【图片内容】\n{pics}")
    if video and video != "0":
        parts.append(f"【视频内容】\n{video}")

    combined = "\n\n".join(parts)
    prompt = _SUMMARY_PROMPT.format(content=combined)

    client = _make_client(config)
    resp = await client.chat.completions.create(
        model=config.model,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=2000,
    )
    return resp.choices[0].message.content.strip()
