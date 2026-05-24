import asyncio
import sys
import glob
from pathlib import Path
import pandas as pd
import signal

# Add src to python path so we can import scraper
ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from src.pcgamingwiki_scraper import PCGamingWikiScraper
from src.utils import setup_logging, save_to_csv

# --- CONFIGURATION ---
SCRAPE_MODE = "alphabet"      # Options: "all" or "alphabet"
TARGET_ALPHABET = "a"         # e.g., "A", "B", "0-9" (Only used if SCRAPE_MODE="alphabet")
SKIP_EXISTING = True          # Skip already scraped games from data/output folder
MAX_PAGES = 9999              # Set to 9999 to scrape all pages
MAX_GAMES_PER_PAGE = 0        # Set to 0 to scrape all games on each page
# ---------------------

def get_existing_urls() -> set:
    existing_urls = set()
    output_dir = ROOT / "data" / "output"
    if not output_dir.exists():
        return existing_urls
        
    csv_files = glob.glob(str(output_dir / "pcgamingwiki_export*.csv"))
    for fpath in csv_files:
        try:
            df = pd.read_csv(fpath)
            if "URL" in df.columns:
                existing_urls.update(df["URL"].dropna().tolist())
        except Exception as e:
            print(f"Warning: Failed to read {fpath}: {e}")
            
    if existing_urls:
        print(f"Loaded {len(existing_urls)} existing URLs to skip.")
    return existing_urls

cancel_requested = False

def handle_sigint(signum, frame):
    global cancel_requested
    if cancel_requested:
        print("\nForce quitting...")
        sys.exit(1)
    print("\n[Ctrl+C] Stopping gracefully after the current task... (Press Ctrl+C again to force quit)")
    cancel_requested = True

async def run_scraper():
    print("="*60)
    print(f"Starting PCGamingWiki Scraper")
    print(f"Mode: {SCRAPE_MODE}")
    if SCRAPE_MODE == "alphabet":
        print(f"Target Alphabet: {TARGET_ALPHABET}")
    print("="*60)
    
    existing_urls = get_existing_urls() if SKIP_EXISTING else set()
    
    scraper = PCGamingWikiScraper(headless=True)
    
    scraper_target_alphabet = TARGET_ALPHABET if SCRAPE_MODE == "alphabet" else None
    
    print("Initializing browser and navigating to Category:Games...")
    scraped_data = await scraper.scrape(
        start_url="https://www.pcgamingwiki.com/wiki/Category:Games",
        max_pages=MAX_PAGES,
        max_games_per_page=MAX_GAMES_PER_PAGE,
        target_alphabet=scraper_target_alphabet,
        existing_urls=existing_urls,
        should_cancel=lambda: cancel_requested
    )
    
    print("\n" + "="*60)
    print(f"Scraping Complete! Extracted {len(scraped_data)} games.")
    print("="*60)
    
    if scraped_data:
        # Save to CSV
        filename = f"pcgamingwiki_export_script_run"
        output_path = save_to_csv(scraped_data, filename)
        print(f"Saved {len(scraped_data)} games to {output_path}")

        # Print the first 2 games as a sample
        print("\nSample Data (First 2 games):")
        for i, game in enumerate(scraped_data[:2]):
            print(f"\nGame {i+1}: {game['Title']}")
            print(f"  URL: {game['URL']}")
            print(f"  OS Minimum: {game['OS_Minimum']}")
            print(f"  CPU Minimum: {game['CPU_Minimum']}")
            print(f"  RAM Minimum: {game['RAM_Minimum']}")
            print(f"  GPU Minimum: {game['GPU_Minimum']}")
            print(f"  Storage: {game['Storage_Minimum']}")
            print(f"  OS Recommended: {game['OS_Recommended']}")
            print(f"  CPU Recommended: {game['CPU_Recommended']}")
            print(f"  RAM Recommended: {game['RAM_Recommended']}")
            print(f"  GPU Recommended: {game['GPU_Recommended']}")
            print(f"  Storage Recommended: {game['Storage_Recommended']}")
    
if __name__ == "__main__":
    signal.signal(signal.SIGINT, handle_sigint)
    setup_logging()
    asyncio.run(run_scraper())
