"""
Workflow orchestration – ties together all services into the end-to-end pipeline.

Processing order for each link (F4 → F5 → F6 → F7 → F8 → F9):
  F4  Scrape XHS note
  F5  AI image analysis  → pic_processed
  F6  AI video analysis  → video_processed
  F7  AI summary         → summary
  F8  Write back to Google Sheets
  F9  Update auto / error status field
"""

import asyncio
from typing import Optional

from app.db import models as db
from app.schemas.config import AIConfig
from app.services import ai_service, sheets_service, sse_manager as sse, xhs_scraper

_current_task: Optional[asyncio.Task] = None


async def start_workflow() -> str:
    global _current_task

    # Guard: only one run at a time
    current = await db.get_current_run()
    if current:
        raise RuntimeError("工作流正在运行中，请等待当前任务完成")

    # Load config from DB
    cfg = await db.get_all_config()

    sheets_id = cfg.get("sheets_id", "").strip()
    if not sheets_id:
        raise RuntimeError("请先在设置页面填写并保存飞书多维表格 ID")

    # Check Feishu credentials
    feishu_app_id = cfg.get("feishu_app_id", "").strip()
    feishu_app_secret = cfg.get("feishu_app_secret", "").strip()
    if not feishu_app_id or not feishu_app_secret:
        raise RuntimeError("请先在设置页面填写并保存飞书 App ID 和 App Secret")

    api_key = cfg.get("ai_api_key", "").strip()
    if not api_key:
        raise RuntimeError("请先在设置页面填写并保存 AI 模型 API Key")

    ai_cfg = AIConfig(
        provider=cfg.get("ai_provider", ""),
        model=cfg.get("ai_model", ""),
        api_base_url=cfg.get("ai_base_url", ""),
        api_key=api_key,
    )
    if not ai_cfg.model:
        raise RuntimeError("请先在设置页面填写并保存 AI 模型名称")

    run_id = await db.create_run()
    xhs_cookies = xhs_scraper.load_cookies()

    _current_task = asyncio.create_task(
        _run(run_id, sheets_id, ai_cfg, xhs_cookies)
    )
    return run_id


async def _run(run_id: str, sheets_id: str, ai_cfg: AIConfig, xhs_cookies: list):
    global _current_task
    success_count = 0
    failed_count = 0

    try:
        await sse.emit(run_id, "info", "🚀 开始读取飞书多维表格...")

        # F1: read pending rows
        try:
            pending = await sheets_service.get_pending_rows(sheets_id)
        except Exception as e:
            await sse.emit(run_id, "error", f"❌ 读取飞书多维表格失败：{e}")
            await db.complete_run(run_id, "failed")
            await sse.close_stream(run_id)
            return

        total = len(pending)
        if total == 0:
            await sse.emit(run_id, "info", "✓ 没有待处理的链接（所有行已处理或表格为空）")
            await db.update_run(run_id, total=0, success=0, failed=0)
            await db.complete_run(run_id, "completed")
            await sse.emit(run_id, "info", "✅ 工作流完成")
            await sse.close_stream(run_id)
            return

        await sse.emit(run_id, "info", f"📋 共找到 {total} 条待处理链接，开始处理...")
        await db.update_run(run_id, total=total)

        for i, (row_index, link) in enumerate(pending, 1):
            await sse.emit(run_id, "progress", f"[{i}/{total}] {link[:80]}")

            try:
                # F4: Scrape
                await sse.emit(run_id, "info", "  → 抓取笔记数据...")
                note = await xhs_scraper.scrape_note(link)
                title_preview = str(note.get("title", ""))[:40]
                await sse.emit(run_id, "info", f"  ✓ 抓取成功：{title_preview}")

                # F5: Image analysis
                pic_urls: list[str] = note.get("pic_url_list", [])
                if pic_urls:
                    await sse.emit(run_id, "info", f"  → 解析 {len(pic_urls)} 张图片...")
                    pic_processed = await ai_service.analyze_images(pic_urls, ai_cfg)
                    await sse.emit(run_id, "info", "  ✓ 图片解析完成")
                else:
                    pic_processed = "0"
                    await sse.emit(run_id, "info", "  - 无图片，跳过图片解析")

                # F6: Video analysis
                video_urls: list[str] = note.get("video_url_list", [])
                video_url = video_urls[0] if video_urls else ""
                if video_url:
                    await sse.emit(run_id, "info", "  → 解析视频内容...")
                    video_processed = await ai_service.analyze_video(
                        video_url, ai_cfg, xhs_cookies
                    )
                    await sse.emit(run_id, "info", "  ✓ 视频解析完成")
                else:
                    video_processed = "0"
                    await sse.emit(run_id, "info", "  - 无视频，跳过视频解析")

                # F7: Summary
                await sse.emit(run_id, "info", "  → 生成内容总结...")
                summary = await ai_service.generate_summary(
                    note.get("text_original", "0"),
                    pic_processed,
                    video_processed,
                    ai_cfg,
                )
                await sse.emit(run_id, "info", "  ✓ 内容总结生成完成")

                # F8: Write back
                await sse.emit(run_id, "info", "  → 写入飞书多维表格...")
                row_data = {
                    "title": note.get("title", "0"),
                    "author": note.get("author", "0"),
                    "date": note.get("date", "0"),
                    "stars": note.get("stars", "0"),
                    "text_original": note.get("text_original", "0"),
                    "pic_url_list": (
                        ", ".join(pic_urls) if pic_urls else "0"
                    ),
                    "video_url_list": (
                        ", ".join(video_urls) if video_urls else "0"
                    ),
                    "pic_processed": pic_processed,
                    "video_processed": video_processed,
                    "summary": summary,
                }
                await sheets_service.write_row(sheets_id, row_index, row_data)

                # F9: Mark success
                await sheets_service.update_status(sheets_id, row_index, "1", None)

                success_count += 1
                await db.update_run(run_id, success=success_count)
                await sse.emit(run_id, "success", f"  ✅ 第 {i}/{total} 条处理完成并已写入表格")

            except Exception as e:
                err_msg = str(e)
                failed_count += 1
                await db.update_run(run_id, failed=failed_count)
                try:
                    await sheets_service.update_status(sheets_id, row_index, None, err_msg)
                except Exception:
                    pass
                await sse.emit(run_id, "error", f"  ✗ 第 {i}/{total} 条处理失败：{err_msg[:200]}")

        await db.update_run(run_id, total=total, success=success_count, failed=failed_count)
        await db.complete_run(run_id, "completed")
        await sse.emit(
            run_id, "info",
            f"🎉 工作流完成！成功 {success_count} 条，失败 {failed_count} 条"
        )

    except Exception as e:
        await db.complete_run(run_id, "failed")
        await sse.emit(run_id, "error", f"💥 工作流异常退出：{e}")
    finally:
        await sse.close_stream(run_id)
        _current_task = None


def is_running() -> bool:
    return _current_task is not None and not _current_task.done()
