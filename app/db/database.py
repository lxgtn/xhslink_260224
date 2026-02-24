import aiosqlite
from config import DB_PATH

_db: aiosqlite.Connection | None = None


async def get_db() -> aiosqlite.Connection:
    global _db
    if _db is None:
        _db = await aiosqlite.connect(str(DB_PATH))
        _db.row_factory = aiosqlite.Row
    return _db


async def init_db():
    db = await get_db()
    await db.executescript("""
        CREATE TABLE IF NOT EXISTS config (
            key   TEXT PRIMARY KEY,
            value TEXT
        );

        CREATE TABLE IF NOT EXISTS runs (
            id           TEXT PRIMARY KEY,
            started_at   TEXT NOT NULL,
            completed_at TEXT,
            status       TEXT NOT NULL DEFAULT 'running',
            total        INTEGER DEFAULT 0,
            success      INTEGER DEFAULT 0,
            failed       INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS run_events (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id   TEXT NOT NULL,
            ts       TEXT NOT NULL,
            level    TEXT NOT NULL,
            message  TEXT NOT NULL,
            FOREIGN KEY(run_id) REFERENCES runs(id)
        );
    """)
    await db.commit()


async def close_db():
    global _db
    if _db:
        await _db.close()
        _db = None
