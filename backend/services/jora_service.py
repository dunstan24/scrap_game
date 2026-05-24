"""
Jora Scraper service wrapper for FastAPI
"""
import sys
import logging
import threading
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent  # project root
SRC  = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from scraper import JoraScraper
from utils import save_to_csv
from backend.database import update_job
from backend.logging_utils import get_job_logger, cleanup_job_logger

logger = logging.getLogger("backend.jora_service")

AUSTRALIAN_STATES = [
    "New South Wales", "Victoria", "Queensland",
    "Western Australia", "South Australia", "Tasmania",
    "Australian Capital Territory", "Northern Territory"
]


class _JobLogHandler(logging.Handler):
    """Menyuntikkan log record ke jobs dict agar frontend bisa lihat via polling."""
    def __init__(self, job_id: int, jobs: dict):
        super().__init__()
        self.job_id = job_id
        self.jobs   = jobs
        self.setFormatter(logging.Formatter("%(message)s"))

    # Pola log yang tidak perlu ditampilkan di frontend
    _SKIP_PATTERNS = (
        ":\\",          # path Windows (D:\, C:\, ...)
        ":/",           # path Unix/Mac
        "Using local",  # webdriver_manager: "Using local Chrome driver: ..."
        "WDM -",        # webdriver_manager prefix
        "DeprecationWarning",
    )

    def emit(self, record: logging.LogRecord):
        try:
            msg = self.format(record)
            # Buang log yang mengandung path direktori atau info tidak relevan
            if any(p in msg for p in self._SKIP_PATTERNS):
                return
            ts    = datetime.now().strftime("%H:%M:%S")
            entry = f"[{ts}] {msg}"
            if self.job_id in self.jobs:
                self.jobs[self.job_id]["logs"].append(entry)
        except Exception:
            pass


def run_jora_scraper(job_id: int, jobs: dict, keyword: str, states: list, pages: int,
                     pause_event=None, date_filter: int = None):
    """Background thread — jalankan JoraScraper dan update jobs dict."""
    # Setup job-specific logger dengan file handler
    job_logger = get_job_logger(job_id, "jora", keyword)
    
    jobs[job_id]["status"]     = "running"
    jobs[job_id]["started_at"] = datetime.now().isoformat()
    update_job(job_id, status="running", started_at=jobs[job_id]["started_at"])

    def log(msg: str):
        ts = datetime.now().strftime("%H:%M:%S")
        jobs[job_id]["logs"].append(f"[{ts}] {msg}")
        logger.info(f"[job:{job_id}] {msg}")
        job_logger.info(msg)  # Juga log ke file handler

    def check_pause():
        """Block disini jika paused, lanjut jika resumed."""
        if pause_event and not pause_event.is_set():
            log("[PAUSE] Scraping dijeda. Menunggu resume...")
            pause_event.wait()
            log("[RESUME] Scraping dilanjutkan.")

    # ── Pasang handler ke semua logger yang relevan ──
    handler = _JobLogHandler(job_id, jobs)
    handler.setLevel(logging.DEBUG)
    target_loggers = [
        logging.getLogger("utils"),
        logging.getLogger("JoraScraper"),
        logging.getLogger("scraper"),
        logging.getLogger(),
    ]
    for lg in target_loggers:
        lg.addHandler(handler)
        if lg.level == logging.NOTSET or lg.level > logging.INFO:
            lg.setLevel(logging.INFO)

    try:
        target_states = AUSTRALIAN_STATES if "ALL" in states else states
        date_label = "Last 24 hours" if date_filter == 1 else "Any time"
        log(f"Mulai scraping | keyword='{keyword}' | states={target_states} | pages={pages} | date={date_label}")

        all_jobs = []
        # Store jobs list in job dict so pause endpoint can access it
        jobs[job_id]["current_jobs"] = all_jobs
        for state in target_states:
            # Check for cancellation
            if jobs[job_id].get("status") == "cancelled":
                log("Scraping dibatalkan oleh user.")
                break   # break agar partial save di bawah bisa berjalan

            # Check for pause (antara state)
            check_pause()

            # Cek cancel lagi setelah resume dari pause
            if jobs[job_id].get("status") == "cancelled":
                log("Scraping dibatalkan setelah resume.")
                break

            log(f"Scraping {state}...")
            scraper = JoraScraper(headless=False, use_ai=False)  # Show browser window

            try:
                scraped = scraper.search_jobs(
                    keyword, state, pages,
                    should_cancel=lambda: jobs[job_id].get("status") == "cancelled",
                    date_filter=date_filter,
                )
                all_jobs.extend(scraped)

                jobs[job_id]["progress"] = len(all_jobs)
                log(f"  -> {len(scraped)} jobs dari {state} (total: {len(all_jobs)})")
            finally:
                scraper.close()

        # ── Simpan data (penuh atau parsial) ──────────────────────
        was_cancelled = jobs[job_id].get("status") == "cancelled"
        if all_jobs:
            label    = "all" if "ALL" in states else "-".join(
                s.replace(" ", "_").lower() for s in states
            )
            filename = f"jora_{keyword or 'all'}_{label}"
            output_path = save_to_csv(all_jobs, filename)

            status_label = "cancelled" if was_cancelled else "done"
            msg = f"{len(all_jobs)} jobs tersimpan" if was_cancelled else f"Selesai! {len(all_jobs)} jobs"

            jobs[job_id].update({
                "status":      status_label,
                "total_found": len(all_jobs),
                "progress":    len(all_jobs),
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
        # Try to save whatever data we have on error
        if all_jobs:
            try:
                label    = "all" if "ALL" in states else "-".join(
                    s.replace(" ", "_").lower() for s in states
                )
                filename = f"jora_{keyword or 'all'}_{label}"
                output_path = save_to_csv(all_jobs, filename)
                jobs[job_id].update({
                    "status":      "error",
                    "error":       str(e),
                    "total_found": len(all_jobs),
                    "output_file": str(output_path),
                    "finished_at": datetime.now().isoformat(),
                })
                update_job(
                    job_id, status="error", error=str(e),
                    total_found=len(all_jobs),
                    output_file=str(output_path),
                    file_name=Path(output_path).name,
                    finished_at=jobs[job_id]["finished_at"],
                )
                log(f"ERROR: {e} | {len(all_jobs)} jobs tersimpan → {output_path}")
            except Exception as save_err:
                jobs[job_id].update({"status": "error", "error": str(e), "finished_at": datetime.now().isoformat()})
                update_job(job_id, status="error", error=str(e), finished_at=jobs[job_id]["finished_at"])
                log(f"ERROR: {e} | Gagal menyimpan: {save_err}")
        else:
            jobs[job_id].update({"status": "error", "error": str(e), "finished_at": datetime.now().isoformat()})
            update_job(job_id, status="error", error=str(e), finished_at=jobs[job_id]["finished_at"])
            log(f"ERROR: {e}")
        logger.exception(f"Jora error job {job_id}")

    finally:
        # ── Lepas handler setelah selesai ──
        for lg in target_loggers:
            lg.removeHandler(handler)
        
        # ── Cleanup job logger ──
        cleanup_job_logger(job_id)


def start_jora_job(job_id: int, jobs: dict, keyword: str, states: list, pages: int,
                   pause_event=None, date_filter: int = None):
    t = threading.Thread(
        target=run_jora_scraper,
        args=(job_id, jobs, keyword, states, pages, pause_event, date_filter),
        daemon=True
    )
    t.start()
