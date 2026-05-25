import asyncio
import glob
import os
import signal
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from src.pcgamingwiki_scraper import PCGamingWikiScraper
from src.utils import setup_logging, save_to_csv

# ============================================================
# --- CONFIGURATION ---
# ============================================================
# Alphabets to scrape, comma-separated. e.g. "a,b,c" or "a" or "all"
TARGET_ALPHABETS = "a,b,c"

SKIP_EXISTING   = True   # Skip already-scraped game URLs
MAX_PAGES       = 9999   # 9999 = scrape all pages per alphabet
CHECKPOINT_EVERY = 500   # Auto-save checkpoint every N games (per alphabet)
# ============================================================

cancel_requested = False

def handle_sigint(signum, frame):
    global cancel_requested
    if cancel_requested:
        print("\nForce quitting...")
        sys.exit(1)
    print("\n[Ctrl+C] Stopping gracefully after the current task... (Press Ctrl+C again to force quit)")
    cancel_requested = True


def get_existing_urls() -> set:
    """Scan all existing CSV files and collect already-scraped URLs."""
    existing_urls = set()
    output_dir = ROOT / "data" / "output"
    if not output_dir.exists():
        return existing_urls

    csv_files = glob.glob(str(output_dir / "pcgamingwiki_*.csv"))
    for fpath in csv_files:
        try:
            df = pd.read_csv(fpath, usecols=["URL"], encoding="utf-8-sig")
            existing_urls.update(df["URL"].dropna().tolist())
        except Exception:
            try:
                df = pd.read_csv(fpath, usecols=["URL"])
                existing_urls.update(df["URL"].dropna().tolist())
            except Exception as e:
                print(f"  [WARN] Could not read {fpath}: {e}")
    return existing_urls


def make_checkpoint_callback(alphabet: str, output_dir: Path):
    """
    Returns a callback function that saves a checkpoint CSV every N games.
    Checkpoint files are named: pcgamingwiki_ALPHABET_checkpoint.csv
    They are OVERWRITTEN each time (always the latest full snapshot for that alphabet).
    """
    checkpoint_path = output_dir / f"pcgamingwiki_{alphabet.upper()}_checkpoint.csv"

    def callback(all_games: list, total: int):
        try:
            df = pd.DataFrame(all_games)
            df.to_csv(str(checkpoint_path), index=False, encoding="utf-8-sig")
            print(f"  [CHECKPOINT] {total} games saved → {checkpoint_path.name}")
        except Exception as e:
            print(f"  [CHECKPOINT ERROR] {e}")

    return callback


async def scrape_alphabet(alphabet: str, existing_urls: set):
    """Run the scraper for a single target alphabet and return results."""
    output_dir = ROOT / "data" / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*60}")
    print(f"  Scraping alphabet: [{alphabet.upper()}]")
    print(f"  Existing URLs loaded: {len(existing_urls)}")
    print(f"{'='*60}")

    scraper = PCGamingWikiScraper(headless=True)
    checkpoint_cb = make_checkpoint_callback(alphabet, output_dir)

    scraped_data = await scraper.scrape(
        start_url="https://www.pcgamingwiki.com/wiki/Category:Games",
        max_pages=MAX_PAGES,
        max_games_per_page=0,
        target_alphabet=alphabet,
        existing_urls=existing_urls,
        should_cancel=lambda: cancel_requested,
        checkpoint_callback=checkpoint_cb,
        checkpoint_every=CHECKPOINT_EVERY,
    )

    return scraped_data


async def run_scraper():
    global cancel_requested

    # Parse target alphabets
    raw = TARGET_ALPHABETS.strip().lower()
    if raw == "all":
        # Full A-Z + 0-9
        alphabets = [chr(c) for c in range(ord('a'), ord('z') + 1)] + ["0-9"]
    else:
        alphabets = [a.strip() for a in raw.split(',') if a.strip()]

    print(f"\n{'='*60}")
    print(f"  PCGamingWiki Multi-Alphabet Scraper")
    print(f"  Alphabets: {', '.join(a.upper() for a in alphabets)}")
    print(f"  Checkpoint every: {CHECKPOINT_EVERY} games")
    print(f"  Skip existing: {SKIP_EXISTING}")
    print(f"{'='*60}")

    output_dir = ROOT / "data" / "output"
    total_scraped = 0

    for alphabet in alphabets:
        if cancel_requested:
            print("\n[STOPPED] Cancellation requested. Exiting loop.")
            break

        # Reload existing URLs before each alphabet to include newly saved data
        existing_urls = get_existing_urls() if SKIP_EXISTING else set()

        scraped_data = await scrape_alphabet(alphabet, existing_urls)

        if scraped_data:
            # Save final CSV for this alphabet
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            final_filename = f"pcgamingwiki_{alphabet.upper()}_{timestamp}.csv"
            final_path = output_dir / final_filename

            df = pd.DataFrame(scraped_data)
            df.to_csv(str(final_path), index=False, encoding="utf-8-sig")

            print(f"\n  ✅ Alphabet [{alphabet.upper()}] DONE!")
            print(f"     Games scraped: {len(scraped_data)}")
            print(f"     Saved to     : {final_filename}")

            # Clean up checkpoint file since final is saved
            checkpoint_path = output_dir / f"pcgamingwiki_{alphabet.upper()}_checkpoint.csv"
            if checkpoint_path.exists():
                checkpoint_path.unlink()
                print(f"     Checkpoint   : removed (final file saved)")

            total_scraped += len(scraped_data)
        else:
            print(f"\n  ⚠️  Alphabet [{alphabet.upper()}]: No new games scraped (all skipped or none found).")

    print(f"\n{'='*60}")
    print(f"  All done! Total games scraped this session: {total_scraped}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    signal.signal(signal.SIGINT, handle_sigint)
    setup_logging()
    asyncio.run(run_scraper())
