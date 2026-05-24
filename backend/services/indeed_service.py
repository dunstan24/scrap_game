"""
Indeed Scraper service wrapper for FastAPI
Uses existing IndeedScraper from src/indeed_scraper.py (Playwright + Camoufox)
"""
import sys
import threading
import logging
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent  # project root
SRC  = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from indeed_scraper import IndeedScraper
from utils import save_to_csv
from backend.database import update_job
from backend.logging_utils import get_job_logger, cleanup_job_logger

logger = logging.getLogger("backend.indeed_service")

AUSTRALIAN_STATES = [
    "New South Wales", "Victoria", "Queensland",
    "Western Australia", "South Australia", "Tasmania",
    "Australian Capital Territory", "Northern Territory"
]


def run_indeed_scraper(job_id: int, jobs: dict, keyword: str, states: list, pages: int,
                       date_filter: int = None):
    """Background thread — jalankan IndeedScraper dan update jobs dict."""
    # Setup job-specific logger dengan file handler
    job_logger = get_job_logger(job_id, "indeed", keyword)
    
    jobs[job_id]["status"] = "running"
    jobs[job_id]["started_at"] = datetime.now().isoformat()
    update_job(job_id, status="running", started_at=jobs[job_id]["started_at"])

    def log(msg: str):
        ts = datetime.now().strftime("%H:%M:%S")
        jobs[job_id]["logs"].append(f"[{ts}] {msg}")
        logger.info(f"[job:{job_id}] {msg}")
        job_logger.info(msg)  # Juga log ke file handler

    try:
        target_states = AUSTRALIAN_STATES if "ALL" in states else states
        log(f"Mulai scraping Indeed | keyword='{keyword}' | states={target_states} | pages={pages}")

        all_jobs = []
        scraper = IndeedScraper(use_ai=False)

        for state in target_states:
            # Check for cancellation
            if jobs[job_id].get("status") == "cancelled":
                log("Scraping Indeed dibatalkan oleh user.")
                break  # ← CHANGE: break instead of return, so partial save logic runs

            log(f"Scraping Indeed - {state}...")

            try:
                scraped = scraper.search_jobs(
                    job_keyword=keyword,
                    location=state,
                    max_pages=pages,
                    should_cancel=lambda: jobs[job_id].get("status") == "cancelled",
                    progress_callback=log,
                    fromage=date_filter,   # None=any time, 1=last 24h
                )

                all_jobs.extend(scraped)
                jobs[job_id]["progress"] = len(all_jobs)
                log(f"  -> {len(scraped)} jobs dari {state} (total: {len(all_jobs)})")
            except Exception as e:
                log(f"  [WARN] Error scraping {state}: {e}")

        # ── Simpan data (penuh atau parsial) ──────────────────────
        was_cancelled = jobs[job_id].get("status") == "cancelled"
        if all_jobs:
            state_label = "all" if "ALL" in states else "-".join(
                s.replace(" ", "_").lower() for s in states
            )
            suffix = "_partial" if was_cancelled else ""
            filename = f"indeed_{keyword or 'all'}_{state_label}{suffix}"
            output_path = save_to_csv(all_jobs, filename)

            status_label = "cancelled" if was_cancelled else "done"
            msg = f"{len(all_jobs)} jobs parsial tersimpan" if was_cancelled else f"Selesai! {len(all_jobs)} jobs"

            jobs[job_id].update({
                "status": status_label,
                "total_found": len(all_jobs),
                "progress": len(all_jobs),
                "output_file": str(output_path),
                "finished_at": datetime.now().isoformat(),
            })
            update_job(
                job_id,
                status=status_label,
                progress=len(all_jobs),
                total_found=len(all_jobs),
                output_file=str(output_path),
                file_name=Path(output_path).name if output_path else None,
                finished_at=jobs[job_id]["finished_at"],
            )
            log(f"{msg} -> {output_path}")
        else:
            log("Tidak ada data yang berhasil dikumpulkan.")
            if not was_cancelled:
                jobs[job_id].update({
                    "status": "done",
                    "finished_at": datetime.now().isoformat(),
                })
                update_job(job_id, status="done", finished_at=jobs[job_id]["finished_at"])

    except Exception as e:
        # ── Coba simpan parsial jika ada data saat error ──
        if all_jobs:
            try:
                state_label = "all" if "ALL" in states else "-".join(
                    s.replace(" ", "_").lower() for s in states
                )
                filename = f"indeed_{keyword or 'all'}_{state_label}_error"
                output_path = save_to_csv(all_jobs, filename)
                jobs[job_id].update({
                    "status": "error",
                    "error": str(e),
                    "total_found": len(all_jobs),
                    "output_file": str(output_path),
                    "finished_at": datetime.now().isoformat(),
                })
                update_job(
                    job_id,
                    status="error",
                    error=str(e),
                    total_found=len(all_jobs),
                    output_file=str(output_path),
                    file_name=Path(output_path).name if output_path else None,
                    finished_at=jobs[job_id]["finished_at"],
                )
                log(f"ERROR: {e}")
                log(f"Partial data tersimpan sebelum error: {len(all_jobs)} jobs -> {output_path}")
            except Exception as save_err:
                log(f"ERROR during partial save: {save_err}")
                jobs[job_id].update({
                    "status": "error",
                    "error": str(e),
                    "finished_at": datetime.now().isoformat(),
                })
                update_job(job_id, status="error", error=str(e), finished_at=jobs[job_id]["finished_at"])
        else:
            # No data collected at all
            jobs[job_id].update({
                "status": "error",
                "error": str(e),
                "finished_at": datetime.now().isoformat(),
            })
            update_job(job_id, status="error", error=str(e), finished_at=jobs[job_id]["finished_at"])
            log(f"ERROR: {e}")
        
        logger.exception(f"Indeed error job {job_id}")
    
    finally:
        # ── Cleanup job logger ──
        cleanup_job_logger(job_id)


def start_indeed_job(job_id: int, jobs: dict, keyword: str, states: list, pages: int,
                     date_filter: int = None):
    t = threading.Thread(
        target=run_indeed_scraper,
        args=(job_id, jobs, keyword, states, pages, date_filter),
        daemon=True
    )
    t.start()
