"""
Scrape routes — POST /scrape, GET /status, GET /result, GET /download, DELETE /job
job_id is an INTEGER auto-increment from SQLite
"""
import math
import sys
import threading
from datetime import datetime
from pathlib import Path

import pandas as pd
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from backend.models import ScrapeRequest, ScrapeResponse, JobStatus
from backend.services.pcgamingwiki_service import start_pcgamingwiki_job
from backend.database import insert_job, list_all_jobs, get_job, update_job

# Add src to path for utils import
SRC = Path(__file__).resolve().parent.parent.parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from utils import save_to_csv

router = APIRouter(prefix="/api", tags=["scraper"])

# In-memory job store  {int job_id: dict}
jobs: dict[int, dict] = {}

# Pause events: {job_id: threading.Event} — set=running, clear=paused
pause_events: dict[int, threading.Event] = {}

def _job_from_db(job_id: int) -> dict | None:
    """Get job from DB and convert to in-memory dict. Used after server restart."""
    row = get_job(job_id)
    if not row:
        return None
    return {
        "job_id":      row["id"],
        "platform":    row["platform"],
        "status":      row["status"],
        "progress":    row["progress"],
        "total_found": row["total_found"],
        "logs":        ["[INFO] Server restarted — log not available"],
        "error":       row["error"],
        "output_file": row["output_file"],
        "started_at":  row["started_at"],
        "finished_at": row["finished_at"],
    }

def clean_nan(value):
    """Replace float NaN/Inf → None for JSON compliance."""
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    return value

# ── POST /scrape ───────────────────────────────────────────────────────────────

@router.post("/scrape", response_model=ScrapeResponse)
def start_scrape(req: ScrapeRequest):
    """Start new scrape. Returns integer job_id."""
    job_id: int = insert_job(req.platform, req.start_url, req.pages)

    jobs[job_id] = {
        "job_id":      job_id,
        "platform":    req.platform,
        "start_url":   req.start_url,
        "pages":       req.pages,
        "status":      "queued",
        "progress":    0,
        "total_found": 0,
        "logs":        [],
        "error":       None,
        "output_file": None,
        "started_at":  None,
        "finished_at": None,
        "current_jobs": [],
        "partial_file": None,
    }

    # Create pause event (initially SET = running)
    ev = threading.Event()
    ev.set()
    pause_events[job_id] = ev

    if req.platform == "pcgamingwiki":
        start_pcgamingwiki_job(job_id, jobs, req.start_url, req.pages, req.scrape_mode, req.target_alphabet, req.skip_existing, ev)
    else:
        # Fallback for future platforms
        start_pcgamingwiki_job(job_id, jobs, req.start_url, req.pages, req.scrape_mode, req.target_alphabet, req.skip_existing, ev)

    return ScrapeResponse(job_id=job_id, platform=req.platform)

# ── POST /pause/{job_id} ───────────────────────────────────────────────────────

@router.post("/pause/{job_id}")
def pause_job(job_id: int):
    """Pause running job."""
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job["status"] not in ("running",):
        raise HTTPException(status_code=400, detail=f"Job not running (status: {job['status']})")

    ev = pause_events.get(job_id)
    if ev:
        ev.clear() 
    jobs[job_id]["status"] = "paused"
    update_job(job_id, status="paused")
    ts = datetime.now().strftime("%H:%M:%S")
    jobs[job_id]["logs"].append(f"[{ts}] [PAUSE] Scraping paused by user")
    
    return {"message": f"Job {job_id} paused"}

# ── POST /resume/{job_id} ──────────────────────────────────────────────────────

@router.post("/resume/{job_id}")
def resume_job(job_id: int):
    """Resume paused job."""
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job["status"] != "paused":
        raise HTTPException(status_code=400, detail=f"Job not paused (status: {job['status']})")

    ev = pause_events.get(job_id)
    if ev:
        ev.set() 
    jobs[job_id]["status"] = "running"
    update_job(job_id, status="running")
    ts = datetime.now().strftime("%H:%M:%S")
    jobs[job_id]["logs"].append(f"[{ts}] [RESUME] Scraping resumed")
    return {"message": f"Job {job_id} resumed"}

# ── GET /status/{job_id} ───────────────────────────────────────────────────────

@router.get("/status/{job_id}", response_model=JobStatus)
def get_status(job_id: int):
    """Poll job status."""
    job = jobs.get(job_id)
    if not job:
        db_row = get_job(job_id)
        if not db_row:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
        job = {
            "job_id":      db_row["id"],
            "platform":    db_row["platform"],
            "status":      db_row["status"],
            "progress":    db_row["progress"],
            "total_found": db_row["total_found"],
            "logs":        ["[INFO] Server restarted — log not available"],
            "error":       db_row["error"],
            "output_file": db_row["output_file"],
            "started_at":  db_row["started_at"],
            "finished_at": db_row["finished_at"],
        }
    return JobStatus(**job)

# ── GET /result/{job_id} ───────────────────────────────────────────────────────

@router.get("/result/{job_id}")
def get_result(job_id: int):
    """Get scraping result as JSON."""
    job = jobs.get(job_id) or _job_from_db(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job["status"] != "done":
        raise HTTPException(status_code=202, detail=f"Job status: {job['status']}")

    output_file = job.get("output_file")
    if not output_file or not Path(output_file).exists():
        raise HTTPException(status_code=404, detail="Output file not found")

    try:
        df = pd.read_csv(output_file, encoding="utf-8-sig")
        raw_records = df.to_dict(orient="records")
        clean_records = [{k: clean_nan(v) for k, v in row.items()} for row in raw_records]
        return {"job_id": job_id, "total": len(clean_records), "data": clean_records}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read output: {e}")

# ── GET /download/{job_id} ─────────────────────────────────────────────────────

@router.get("/download/{job_id}")
def download_csv(job_id: int):
    """Download CSV file."""
    job = jobs.get(job_id) or _job_from_db(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job["status"] != "done":
        raise HTTPException(status_code=202, detail=f"Job not ready: {job['status']}")

    output_file = job.get("output_file")
    if not output_file or not Path(output_file).exists():
        raise HTTPException(status_code=404, detail="Output file not found")

    return FileResponse(
        path=output_file,
        media_type="text/csv",
        filename=Path(output_file).name
    )

# ── GET /jobs ──────────────────────────────────────────────────────────────────

@router.get("/jobs")
def list_jobs():
    """List all jobs."""
    return [
        {
            "id":          row["id"],
            "platform":    row["platform"],
            "start_url":   row.get("start_url", ""),
            "status":      row["status"],
            "total_found": row["total_found"],
            "file_name":   row["file_name"],
            "output_file": row["output_file"],
            "started_at":  row["started_at"],
            "finished_at": row["finished_at"],
        }
        for row in list_all_jobs()
    ]

# ── DELETE /job/{job_id} ───────────────────────────────────────────────────────

@router.delete("/job/{job_id}")
def delete_job(job_id: int):
    """Delete job from memory."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    del jobs[job_id]
    return {"message": f"Job {job_id} deleted from memory"}

# ── POST /cancel/{job_id} ───────────────────────────────────────────────────────

@router.post("/cancel/{job_id}")
def cancel_job(job_id: int):
    """Cancel job."""
    def do_cancel(jid: int):
        job = jobs.get(jid)
        if not job:
            return False 
        
        if job["status"] in ("queued", "running", "paused"):
            job["status"] = "cancelled"
            job["finished_at"] = datetime.now().isoformat()
            ts = datetime.now().strftime("%H:%M:%S")
            job["logs"].append(f"[{ts}] [WARN] Job cancelled by user")
            update_job(jid, status="cancelled", finished_at=job["finished_at"])

            ev = pause_events.get(jid)
            if ev and not ev.is_set():
                ev.set() 
            return True
        return False

    if job_id in jobs:
        success = do_cancel(job_id)
        if success:
            return {"message": f"Job {job_id} cancelled successfully", "job_id": job_id}
        else:
            job_status = jobs[job_id]["status"]
            return {"message": f"Job {job_id} already {job_status} - cannot cancel", "job_id": job_id, "status": job_status}
    else:
        db_row = get_job(job_id)
        if not db_row:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
        
        db_status = db_row["status"]
        if db_status in ("done", "error", "cancelled"):
            return {"message": f"Job {job_id} already {db_status} - cannot cancel", "job_id": job_id, "status": db_status}
        else:
            update_job(job_id, status="cancelled", finished_at=datetime.now().isoformat())
            return {"message": f"Job {job_id} cancelled (from DB after restart)", "job_id": job_id, "status": "cancelled"}