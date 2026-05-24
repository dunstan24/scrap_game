import sys
import logging
import threading
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from pcgamingwiki_scraper import PCGamingWikiScraper
from utils import save_to_csv
from backend.database import update_job

logger = logging.getLogger("backend.pcgamingwiki_service")

class _JobLogHandler(logging.Handler):
    """Injects log records into the jobs dict so frontend can display them."""
    def __init__(self, job_id: int, jobs: dict):
        super().__init__()
        self.job_id = job_id
        self.jobs = jobs
        self.setFormatter(logging.Formatter("%(message)s"))

    _SKIP_PATTERNS = (
        ":\\", ":/", "Using local", "WDM -", "DeprecationWarning",
    )

    def emit(self, record: logging.LogRecord):
        try:
            msg = self.format(record)
            if any(p in msg for p in self._SKIP_PATTERNS):
                return
            ts = datetime.now().strftime("%H:%M:%S")
            entry = f"[{ts}] {msg}"
            if self.job_id in self.jobs:
                self.jobs[self.job_id]["logs"].append(entry)
        except Exception:
            pass


def run_pcgamingwiki_scraper(job_id: int, jobs: dict, start_url: str, pages: int, scrape_mode: str = "all", target_alphabet: str = None, skip_existing: bool = True, pause_event=None):
    """Background thread to run PCGamingWikiScraper."""
    jobs[job_id]["status"] = "running"
    jobs[job_id]["started_at"] = datetime.now().isoformat()
    update_job(job_id, status="running", started_at=jobs[job_id]["started_at"])

    def log(msg: str):
        ts = datetime.now().strftime("%H:%M:%S")
        jobs[job_id]["logs"].append(f"[{ts}] {msg}")
        logger.info(f"[job:{job_id}] {msg}")

    def check_pause():
        if pause_event and not pause_event.is_set():
            log("[PAUSE] Scraping paused. Waiting to resume...")
            pause_event.wait()
            log("[RESUME] Scraping resumed.")

    # Attach log handler
    handler = _JobLogHandler(job_id, jobs)
    handler.setLevel(logging.DEBUG)
    target_loggers = [
        logging.getLogger("utils"),
        logging.getLogger("PCGamingWikiScraper"),
        logging.getLogger("pcgamingwiki_scraper"),
        logging.getLogger(),
    ]
    for lg in target_loggers:
        lg.addHandler(handler)
        if lg.level == logging.NOTSET or lg.level > logging.INFO:
            lg.setLevel(logging.INFO)

    all_jobs = []
    try:
        log(f"Starting PCGamingWiki Scraping | URL='{start_url}' | pages={pages}")
        
        # We reuse the cancellation logic from the previous setup
        def should_cancel():
            check_pause()
            return jobs[job_id].get("status") == "cancelled"

        existing_urls = set()
        if skip_existing:
            import pandas as pd
            from backend.database import get_completed_jobs_for_platform
            log("Loading existing URLs to skip...")
            prev_jobs = get_completed_jobs_for_platform("pcgamingwiki")
            for pj in prev_jobs:
                fpath = pj.get("output_file")
                if fpath and Path(fpath).exists():
                    try:
                        df = pd.read_csv(fpath)
                        if "URL" in df.columns:
                            existing_urls.update(df["URL"].dropna().tolist())
                    except Exception as e:
                        log(f"Warning: Failed to read {fpath}: {e}")
            log(f"Found {len(existing_urls)} existing game URLs to skip.")

        scraper = PCGamingWikiScraper(headless=True)
        
        # Scrape
        scraper_target_alphabet = target_alphabet if scrape_mode == "alphabet" else None
        
        scraped_data = asyncio_run_sync(scraper.scrape(
            start_url=start_url, 
            max_pages=pages, 
            should_cancel=should_cancel,
            target_alphabet=scraper_target_alphabet,
            existing_urls=existing_urls
        ))
        all_jobs.extend(scraped_data)

        # Update progress
        jobs[job_id]["progress"] = len(all_jobs)
        
        was_cancelled = jobs[job_id].get("status") == "cancelled"
        
        # Save to CSV
        if all_jobs:
            suffix = "_partial" if was_cancelled else ""
            filename = f"pcgamingwiki_export{suffix}"
            output_path = save_to_csv(all_jobs, filename)

            status_label = "cancelled" if was_cancelled else "done"
            msg = f"Saved {len(all_jobs)} games" if was_cancelled else f"Finished! {len(all_jobs)} games scraped"

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
            log("No data was collected.")
            if not was_cancelled:
                jobs[job_id].update({"status": "done", "finished_at": datetime.now().isoformat()})
                update_job(job_id, status="done", finished_at=jobs[job_id]["finished_at"])

    except Exception as e:
        if all_jobs:
            try:
                filename = f"pcgamingwiki_export_error"
                output_path = save_to_csv(all_jobs, filename)
                jobs[job_id].update({
                    "status": "error",
                    "error": str(e),
                    "total_found": len(all_jobs),
                    "output_file": str(output_path),
                    "finished_at": datetime.now().isoformat(),
                })
                update_job(job_id, status="error", error=str(e), total_found=len(all_jobs), output_file=str(output_path), file_name=Path(output_path).name, finished_at=jobs[job_id]["finished_at"])
                log(f"ERROR: {e} | {len(all_jobs)} games partially saved -> {output_path}")
            except Exception as save_err:
                jobs[job_id].update({"status": "error", "error": str(e), "finished_at": datetime.now().isoformat()})
                update_job(job_id, status="error", error=str(e), finished_at=jobs[job_id]["finished_at"])
                log(f"ERROR: {e} | Failed to save partial data: {save_err}")
        else:
            jobs[job_id].update({"status": "error", "error": str(e), "finished_at": datetime.now().isoformat()})
            update_job(job_id, status="error", error=str(e), finished_at=jobs[job_id]["finished_at"])
            log(f"ERROR: {e}")
        logger.exception(f"PCGamingWiki error job {job_id}")

    finally:
        for lg in target_loggers:
            lg.removeHandler(handler)

def asyncio_run_sync(coro):
    import asyncio
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
        
    if loop and loop.is_running():
        # If there's an active loop, we run it in a thread (though this is already in a thread)
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as pool:
            future = pool.submit(asyncio.run, coro)
            return future.result()
    else:
        return asyncio.run(coro)

def start_pcgamingwiki_job(job_id: int, jobs: dict, start_url: str, pages: int, scrape_mode: str = "all", target_alphabet: str = None, skip_existing: bool = True, pause_event=None):
    t = threading.Thread(
        target=run_pcgamingwiki_scraper,
        args=(job_id, jobs, start_url, pages, scrape_mode, target_alphabet, skip_existing, pause_event),
        daemon=True
    )
    t.start()
