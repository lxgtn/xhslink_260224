from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from app.db.database import close_db, init_db
from app.api import auth, config_api, cookies, history, logs, workflow

FRONTEND_DIR = Path(__file__).parent.parent / "frontend"


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield
    await close_db()


app = FastAPI(title="XHS Link", version="1.0.0", lifespan=lifespan)

# ── CORS for GitHub Pages frontend ────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://lxgtn.github.io",
        "https://lxgtn.github.io/xhslink_260224",
        "https://lxgtn.github.io/xhslink_260224/frontend",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── API routes ─────────────────────────────────────────────────────────────────
app.include_router(workflow.router, prefix="/api")
app.include_router(logs.router, prefix="/api")
app.include_router(history.router, prefix="/api")
app.include_router(config_api.router, prefix="/api")
app.include_router(cookies.router, prefix="/api")
app.include_router(auth.router, prefix="/api")

# ── Static assets (css / js) ───────────────────────────────────────────────────
app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIR)), name="assets")


# ── Frontend SPA ───────────────────────────────────────────────────────────────
@app.get("/")
async def index():
    return FileResponse(str(FRONTEND_DIR / "index.html"))


@app.get("/{path:path}")
async def spa_fallback(path: str):
    # Let API routes handle themselves; everything else → SPA
    return FileResponse(str(FRONTEND_DIR / "index.html"))
