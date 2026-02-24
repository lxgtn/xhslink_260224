import uuid
from datetime import datetime, timezone

from app.db.database import get_db


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Config ─────────────────────────────────────────────────────────────────────

async def get_config(key: str) -> str | None:
    db = await get_db()
    async with db.execute("SELECT value FROM config WHERE key = ?", (key,)) as cur:
        row = await cur.fetchone()
        return row[0] if row else None


async def set_config(key: str, value: str):
    db = await get_db()
    await db.execute(
        "INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)", (key, value)
    )
    await db.commit()


async def get_all_config() -> dict:
    db = await get_db()
    async with db.execute("SELECT key, value FROM config") as cur:
        rows = await cur.fetchall()
        return {row[0]: row[1] for row in rows}


# ── Runs ───────────────────────────────────────────────────────────────────────

async def create_run() -> str:
    run_id = str(uuid.uuid4())
    db = await get_db()
    await db.execute(
        "INSERT INTO runs (id, started_at, status) VALUES (?, ?, 'running')",
        (run_id, _now()),
    )
    await db.commit()
    return run_id


async def update_run(run_id: str, **kwargs):
    db = await get_db()
    for k, v in kwargs.items():
        await db.execute(f"UPDATE runs SET {k} = ? WHERE id = ?", (v, run_id))
    await db.commit()


async def complete_run(run_id: str, status: str = "completed"):
    db = await get_db()
    await db.execute(
        "UPDATE runs SET status = ?, completed_at = ? WHERE id = ?",
        (status, _now(), run_id),
    )
    await db.commit()


async def get_runs(limit: int = 30) -> list[dict]:
    db = await get_db()
    async with db.execute(
        "SELECT * FROM runs ORDER BY started_at DESC LIMIT ?", (limit,)
    ) as cur:
        rows = await cur.fetchall()
        return [dict(row) for row in rows]


async def get_run(run_id: str) -> dict | None:
    db = await get_db()
    async with db.execute("SELECT * FROM runs WHERE id = ?", (run_id,)) as cur:
        row = await cur.fetchone()
        return dict(row) if row else None


async def get_current_run() -> dict | None:
    db = await get_db()
    async with db.execute(
        "SELECT * FROM runs WHERE status = 'running' ORDER BY started_at DESC LIMIT 1"
    ) as cur:
        row = await cur.fetchone()
        return dict(row) if row else None


# ── Events ─────────────────────────────────────────────────────────────────────

async def insert_event(run_id: str, level: str, message: str) -> int:
    db = await get_db()
    cur = await db.execute(
        "INSERT INTO run_events (run_id, ts, level, message) VALUES (?, ?, ?, ?)",
        (run_id, _now(), level, message),
    )
    await db.commit()
    return cur.lastrowid


async def get_events(run_id: str) -> list[dict]:
    db = await get_db()
    async with db.execute(
        "SELECT * FROM run_events WHERE run_id = ? ORDER BY id", (run_id,)
    ) as cur:
        rows = await cur.fetchall()
        return [dict(row) for row in rows]


async def get_events_after(run_id: str, after_id: int = 0) -> list[dict]:
    db = await get_db()
    async with db.execute(
        "SELECT * FROM run_events WHERE run_id = ? AND id > ? ORDER BY id",
        (run_id, after_id),
    ) as cur:
        rows = await cur.fetchall()
        return [dict(row) for row in rows]
