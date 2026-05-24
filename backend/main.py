"""
FastAPI app entry point
Run: uvicorn backend.main:app --reload --port 8000
"""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.routes.scrape import router as scrape_router
from backend.database import init_db

# ── Logging setup ──────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("backend")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Inisialisasi DB saat startup."""
    init_db()
    yield


# ── FastAPI app ─────────────────────────────────────────────────
app = FastAPI(
    title="Job Scraper API",
    description="REST API untuk menjalankan Jora & Seek scraper",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ── CORS — izinkan React dev server ────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",   # Vite React
        "http://localhost:3000",   # Create React App (fallback)
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ─────────────────────────────────────────────────────
app.include_router(scrape_router)


@app.get("/", tags=["health"])
def root():
    return {
        "status": "ok",
        "message": "Job Scraper API is running",
        "docs": "/docs",
    }


@app.get("/health", tags=["health"])
def health():
    return {"status": "healthy"}
