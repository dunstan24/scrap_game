"""
CareerOne Scraper service wrapper for FastAPI
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

from careerone_scraper import CareerOneScraper, run_async_search, run_async_close
from utils import save_to_csv
from backend.database import update_job

logger = logging.getLogger("backend.careerone_service")

AUSTRALIAN_LOCATIONS = [
    "All Australia",  # Default for no location filtering
    "Australian Capital Territory", "New South Wales", "Northern Territory",
    "Queensland", "South Australia", "Tasmania", "Victoria", "Western Australia"
]


class _JobLogHandler(logging.Handler):
    """Inject log records into jobs dict for frontend polling"""
    def __init__(self, job_id: int, jobs: dict):
        super().__init__()
        self.job_id = job_id
        self.jobs   = jobs
        self.setFormatter(logging.Formatter("%(message)s"))

    _SKIP_PATTERNS = (
        ":\\",          # Windows paths
        ":/",           # Unix/Mac paths
        "Using local",  # webdriver_manager
        "WDM -",        # webdriver_manager prefix
        "DeprecationWarning",
    )

    def emit(self, record: logging.LogRecord):
        try:
            msg = self.format(record)
            if any(p in msg for p in self._SKIP_PATTERNS):
                return
            ts    = datetime.now().strftime("%H:%M:%S")
            entry = f"[{ts}] {msg}"
            if self.job_id in self.jobs:
                self.jobs[self.job_id]["logs"].append(entry)
        except Exception:
            pass


def run_careerone_scraper(job_id: int, jobs: dict, keyword: str, location: str, pages: int,
                          pause_event=None, date_filter: int = None, state_index: int = None, total_states: int = None):
    """Background thread — run CareerOneScraper and update jobs dict with deduplication
    
    For multiple states:
    - Accumulate jobs from each state in jobs[job_id]["all_accumulated_jobs"]
    - Deduplicate on title + employer + location (exact match)
    - On final state, save 1 file with all deduplicated data
    
    Args:
        job_id: Job ID for tracking
        jobs: Job dictionary for status updates
        keyword: Job keyword to search
        location: Location to search
        pages: Number of pages to scrape
        pause_event: Event for pause/resume
        date_filter: 1 = last 24 hours, None = any time
        state_index: Current state index for multi-state scraping
        total_states: Total number of states for multi-state scraping
    """
    jobs[job_id]["status"]     = "running"
    jobs[job_id]["started_at"] = datetime.now().isoformat()
    update_job(job_id, status="running", started_at=jobs[job_id]["started_at"])
    
    # Initialize accumulated jobs list if multi-state
    if state_index is not None and "all_accumulated_jobs" not in jobs[job_id]:
        jobs[job_id]["all_accumulated_jobs"] = []

    def log(msg: str):
        ts = datetime.now().strftime("%H:%M:%S")
        jobs[job_id]["logs"].append(f"[{ts}] {msg}")
        logger.info(f"[job:{job_id}] {msg}")
    
    def deduplicate_jobs(jobs_list, existing_jobs_set):
        """Deduplicate jobs based on title + employer + location (exact match)
        
        Args:
            jobs_list: New jobs to add
            existing_jobs_set: Set of existing job signatures to check against
            
        Returns:
            (unique_jobs, new_signatures) - unique jobs and updated signatures set
        """
        unique_jobs = []
        new_sigs = set(existing_jobs_set)
        
        for job in jobs_list:
            # Create signature: title + employer + location (exact match)
            sig = (
                str(job.get('title', '')).strip(),
                str(job.get('employer_company_name', '')).strip(),
                str(job.get('location', '')).strip()
            )
            
            if sig not in new_sigs:
                unique_jobs.append(job)
                new_sigs.add(sig)
            else:
                # Log that this job is duplicate
                logger.debug(f"[job:{job_id}] Duplicate skipped: {sig[0]} at {sig[1]} ({sig[2]})")
        
        return unique_jobs, new_sigs
    


    def check_pause():
        """Block if paused, continue if resumed"""
        if pause_event and not pause_event.is_set():
            log("[PAUSE] Scraping paused. Waiting for resume...")
            pause_event.wait()
            log("[RESUME] Scraping resumed.")

    # ── Setup logging handler ──
    handler = _JobLogHandler(job_id, jobs)
    handler.setLevel(logging.DEBUG)
    target_loggers = [
        logging.getLogger("utils"),
        logging.getLogger("CareerOneScraper"),
        logging.getLogger("careerone_scraper"),
        logging.getLogger(),
    ]
    for lg in target_loggers:
        lg.addHandler(handler)
        if lg.level == logging.NOTSET or lg.level > logging.INFO:
            lg.setLevel(logging.INFO)

    try:
        target_location = location if location != "ALL" else "All Australia"
        
        # Log state progress if processing multiple states
        state_info = ""
        if state_index is not None and total_states is not None:
            state_info = f" [State {state_index + 1}/{total_states}]"
        
        log(f"🚀 Starting CareerOne scrape{state_info}")
        log(f"   Keyword: '{keyword}'")
        log(f"   Location (from frontend): '{location}'")
        log(f"   Target location (for CareerOne): '{target_location}'")
        log(f"   Pages: {pages}")
        date_label = "Last 24 hours" if date_filter == 1 else "Any time" if date_filter is None else f"Date filter: {date_filter}"
        log(f"   Date filter: {date_label}")
        if state_info:
            log(f"   Progress: {state_index + 1} of {total_states} states")
        log(f"🌐 Website: https://www.careerone.com.au")

        all_jobs = []
        jobs[job_id]["current_jobs"] = all_jobs

        # Check for cancellation
        if jobs[job_id].get("status") == "cancelled":
            log("❌ Scraping cancelled by user.")
            return

        # Check for pause
        check_pause()

        log(f"📋 Initializing browser and navigating to CareerOne...")
        scraper = CareerOneScraper(headless=False, use_ai=False)  # Show browser window
        log(f"✓ Browser initialized successfully (visible window)")

        try:
            scraped = run_async_search(scraper, keyword, target_location, pages,
                should_cancel=lambda: jobs[job_id].get("status") == "cancelled",
                date_filter=date_filter
            )
            
            # For multi-state: accumulate and deduplicate
            if state_index is not None:
                # Get existing signatures from accumulated jobs
                existing_sigs = set(
                    (
                        str(j.get('title', '')).strip(),
                        str(j.get('employer_company_name', '')).strip(),
                        str(j.get('location', '')).strip()
                    )
                    for j in jobs[job_id]["all_accumulated_jobs"]
                )
                
                # Deduplicate new jobs
                unique_scraped, new_sigs = deduplicate_jobs(scraped, existing_sigs)
                
                # Log deduplication info
                if len(unique_scraped) < len(scraped):
                    duplicates = len(scraped) - len(unique_scraped)
                    log(f"   🔄 {duplicates} duplicate(s) removed from {location}")
                
                # Extend accumulated jobs
                jobs[job_id]["all_accumulated_jobs"].extend(unique_scraped)
                all_jobs.extend(unique_scraped)
            else:
                # Single state: just add to all_jobs
                all_jobs.extend(scraped)

            jobs[job_id]["progress"] = len(all_jobs)
            
            # Check if cancellation happened during scraping
            if jobs[job_id].get("status") == "cancelled":
                log(f"⚠️  CANCELLATION DETECTED - {len(all_jobs)} jobs scraped before stop")
            else:
                if state_index is not None:
                    total_acc = len(jobs[job_id]["all_accumulated_jobs"])
                    log(f"✅ {location} completed: {len(unique_scraped)} new jobs (total accumulated: {total_acc})")
                else:
                    log(f"✅ Search completed: {len(scraped)} jobs extracted (total: {len(all_jobs)})")
        
        finally:
            log(f"🛑 Closing browser...")
            run_async_close(scraper)
            log(f"✓ Browser closed successfully")

        # Check if job was cancelled - if so, don't try to process more states
        if jobs[job_id].get("status") == "cancelled":
            log(f"💾 Saving final results for cancelled job")
            
            # Use accumulated jobs if multi-state, otherwise use current state
            final_jobs = jobs[job_id].get("all_accumulated_jobs") if state_index is not None else all_jobs
            
            if not final_jobs:
                log("No data to save for cancelled job.")
                jobs[job_id].update({
                    "status":      "done",
                    "total_found": 0,
                    "progress":    0,
                    "output_file": None,
                    "finished_at": datetime.now().isoformat(),
                })
                update_job(job_id, status="done", finished_at=jobs[job_id]["finished_at"])
                return
            
            label = "all" if "ALL" in (jobs[job_id].get("states") or []) else "_".join(
                s.replace(" ", "_").lower() for s in (jobs[job_id].get("states_to_process") or [location])
            )
            filename = f"careerone_{label}"
            output_path = save_to_csv(final_jobs, filename)
            log(f"✅ Results saved: {Path(output_path).name if output_path else 'N/A'} ({len(final_jobs)} unique jobs)")
            
            # Mark job as done
            jobs[job_id].update({
                "status":      "done",
                "total_found": len(final_jobs),
                "progress":    len(final_jobs),
                "output_file": str(output_path),
                "finished_at": datetime.now().isoformat(),
            })
            update_job(
                job_id,
                status="done",
                progress=len(final_jobs),
                total_found=len(final_jobs),
                output_file=str(output_path),
                file_name=Path(output_path).name if output_path else None,
                finished_at=jobs[job_id]["finished_at"],
            )
            log(f"✓ Job marked as complete")
            return

        # ── Check if there are more states to process ──
        if state_index is not None and total_states is not None and state_index < total_states - 1:
            # More states to process - don't save yet
            next_state_index = state_index + 1
            next_location = jobs[job_id]["states_to_process"][next_state_index]
            
            log(f"\n{'='*60}")
            log(f"State {state_index + 1}/{total_states} completed: {location}")
            log(f"Moving to state {next_state_index + 1}/{total_states}: {next_location}")
            log(f"{'='*60}\n")
            
            # Update current state index
            jobs[job_id]["current_state_index"] = next_state_index
            
            # Start scraping next state (without saving file yet)
            start_careerone_job(
                job_id, jobs, keyword, next_location, pages, pause_event,
                date_filter=date_filter,
                state_index=next_state_index, total_states=total_states
            )
        else:
            # All states completed (or single state) - save final file with all accumulated data
            final_jobs = jobs[job_id].get("all_accumulated_jobs") if state_index is not None else all_jobs
            
            if not final_jobs:
                log("No data collected.")
                jobs[job_id].update({
                    "status":      "done",
                    "total_found": 0,
                    "progress":    0,
                    "output_file": None,
                    "finished_at": datetime.now().isoformat(),
                })
                update_job(job_id, status="done", finished_at=jobs[job_id]["finished_at"])
                return
            
            label = "all" if "ALL" in (jobs[job_id].get("states") or []) else "_".join(
                s.replace(" ", "_").lower() for s in (jobs[job_id].get("states_to_process") or [location])
            )
            filename = f"careerone_{label}"
            log(f"💾 Saving FINAL results (all states combined): {filename}...")
            output_path = save_to_csv(final_jobs, filename)
            log(f"✅ Results saved: {Path(output_path).name if output_path else 'N/A'}")
            
            jobs[job_id].update({
                "status":      "done",
                "total_found": len(final_jobs),
                "progress":    len(final_jobs),
                "output_file": str(output_path),
                "finished_at": datetime.now().isoformat(),
            })
            update_job(
                job_id,
                status="done",
                progress=len(final_jobs),
                total_found=len(final_jobs),
                output_file=str(output_path),
                file_name=Path(output_path).name if output_path else None,
                finished_at=jobs[job_id]["finished_at"],
            )
            
            if state_index is not None:
                log(f"\n🎉 ALL {total_states} STATES COMPLETE! {len(final_jobs)} unique jobs saved")
            else:
                log(f"🎉 SCRAPING COMPLETE! {len(final_jobs)} jobs saved")

    except Exception as e:
        # Save whatever data we have on error
        final_jobs = jobs[job_id].get("all_accumulated_jobs") if state_index is not None else all_jobs
        
        if final_jobs:
            label = "all" if "ALL" in (jobs[job_id].get("states") or []) else "_".join(
                s.replace(" ", "_").lower() for s in (jobs[job_id].get("states_to_process") or [location])
            )
            filename = f"careerone_{label}"
            try:
                output_path = save_to_csv(final_jobs, filename)
                log(f"💾 Results saved on error: {Path(output_path).name} ({len(final_jobs)} jobs)")
                jobs[job_id]["output_file"] = str(output_path)
                jobs[job_id]["total_found"] = len(final_jobs)
            except Exception as save_err:
                log(f"⚠️ Failed to save results: {save_err}")
        
        jobs[job_id].update({
            "status":      "error",
            "error":       str(e),
            "finished_at": datetime.now().isoformat(),
        })
        update_job(job_id, status="error", error=str(e), finished_at=jobs[job_id]["finished_at"])
        log(f"❌ ERROR: {e}")
        logger.exception(f"CareerOne error job {job_id}")

    finally:
        # ── Remove handler ──
        for lg in target_loggers:
            lg.removeHandler(handler)


def start_careerone_job(job_id: int, jobs: dict, keyword: str, location: str, pages: int,
                        pause_event=None, date_filter: int = None, state_index: int = None, total_states: int = None):
    """Start CareerOne scraping job in background thread"""
    t = threading.Thread(
        target=run_careerone_scraper,
        args=(job_id, jobs, keyword, location, pages, pause_event, date_filter, state_index, total_states),
        daemon=True
    )
    t.start()
    return t
