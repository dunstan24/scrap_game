"""
Seek Scraper service wrapper for FastAPI
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

from seek_scraper.scraper import SeekScraper
from backend.database import update_job
from backend.logging_utils import get_job_logger, cleanup_job_logger

logger = logging.getLogger("backend.seek_service")

AUSTRALIAN_STATES = [
    "New South Wales", "Victoria", "Queensland",
    "Western Australia", "South Australia", "Tasmania",
    "Australian Capital Territory", "Northern Territory"
]


def run_seek_scraper(job_id: str, jobs: dict, keyword: str, states: list, pages: int,
                     pause_event=None, date_filter: int = None):
    """Background thread — jalankan SeekScraper dan update jobs dict."""
    # Setup job-specific logger dengan file handler
    job_logger = get_job_logger(job_id, "seek", keyword)
    
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
        date_label = {1: "Today", 3: "3 days", 7: "7 days", 14: "14 days", 30: "30 days"}.get(date_filter, "Any time")
        log(f"Mulai scraping | keyword='{keyword}' | states={target_states} | pages={pages} | date={date_label}")

        scraper = SeekScraper(use_ai=False)
        scraper.keyword     = keyword
        scraper.states      = target_states
        scraper.page_limit  = pages
        scraper.date_filter = date_filter   # None = any time

        # Attach live log callback ke scraper logger
        scraper_logger = logging.getLogger("SeekScraper")
        class LogCapture(logging.Handler):
            def emit(self, record):
                log(self.format(record))
        handler = LogCapture()
        handler.setFormatter(logging.Formatter("%(message)s"))
        scraper_logger.addHandler(handler)

        try:
            output_path = scraper.scrape(
                should_cancel=lambda: jobs[job_id].get("status") == "cancelled",
                pause_event=pause_event,
            )
            if jobs[job_id].get("status") == "cancelled":
                total = len(scraper.jobs_data)
                if total > 0 and output_path:
                    log(f"Scraping dibatalkan. {total} jobs parsial tersimpan → {output_path}")
                    jobs[job_id].update({
                        "total_found": total,
                        "progress":    total,
                        "output_file": str(output_path),
                        "finished_at": datetime.now().isoformat(),
                    })
                    update_job(
                        job_id,
                        total_found=total,
                        progress=total,
                        output_file=str(output_path),
                        file_name=Path(output_path).name,
                        finished_at=jobs[job_id]["finished_at"],
                    )
                else:
                    log("Scraping dibatalkan. Tidak ada data yang tersimpan.")
                return
        finally:

            scraper_logger.removeHandler(handler)

        # Update progress dari data scraper
        total = len(scraper.jobs_data)

        jobs[job_id].update({
            "status": "done",
            "total_found": total,
            "progress": total,
            "output_file": str(output_path) if output_path else None,
            "finished_at": datetime.now().isoformat(),
        })
        update_job(
            job_id,
            status="done",
            total_found=total,
            progress=total,
            output_file=str(output_path) if output_path else None,
            file_name=Path(output_path).name if output_path else None,
            finished_at=jobs[job_id]["finished_at"],
        )
        log(f"Selesai! {total} jobs -> {output_path}")

    except Exception as e:
        jobs[job_id].update({
            "status": "error",
            "error": str(e),
            "finished_at": datetime.now().isoformat(),
        })
        update_job(job_id, status="error", error=str(e), finished_at=jobs[job_id]["finished_at"])
        log(f"ERROR: {e}")
        logger.exception(f"Seek error job {job_id}")
    
    finally:
        # ── Cleanup job logger ──
        cleanup_job_logger(job_id)


def start_seek_job(job_id: str, jobs: dict, keyword: str, states: list, pages: int,
                   pause_event=None, date_filter: int = None):
    t = threading.Thread(
        target=run_seek_scraper,
        args=(job_id, jobs, keyword, states, pages, pause_event, date_filter),
        daemon=True
    )
    t.start()
