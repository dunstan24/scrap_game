"""
Seek.com.au Scraper Adapter Class
Standardized interface for Seek scraping to match Jora and Indeed
"""
import os
import sys
from typing import List, Dict, Any, Optional
from pathlib import Path

# Fix for Windows Unicode errors
if sys.platform == 'win32':
    try:
        import codecs
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.detach())
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.detach())
    except:
        pass

# Add src/seek_scraper to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'seek_scraper'))

try:
    from seek_scraper.scraper import SeekScraper as BaseSeekScraper
    from seek_scraper.config import AustralianState
except ImportError:
    # Fallback pathing
    sys.path.append(os.path.dirname(__file__))
    from seek_scraper.scraper import SeekScraper as BaseSeekScraper
    from seek_scraper.config import AustralianState

from utils import logger

class SeekScraper:
    """Standardized Seek.com.au Scraper Class for main.py integration"""
    
    def __init__(self, use_ai: bool = False):
        """Initialize the scraper"""
        self.use_ai = use_ai
        self.base_scraper = None
        self.logger = logger
        self.jobs_data = []

    def search_jobs(self, job_keyword: str, location: str, max_pages: int = 5) -> List[Dict[str, Any]]:
        """
        Search for jobs on Seek using the standard interface
        """
        self.logger.info(f"🚀 Starting Seek search via main.py flow")
        
        # Convert single location string from main.py to list for BaseSeekScraper
        states = []
        if not location or location.lower() == 'australia' or location.lower() == 'all':
            states = ["all"]
        else:
            # Check if it's a known state abbreviation
            loc_upper = location.upper()
            all_states = AustralianState.get_all_states()
            if loc_upper in all_states:
                states = [loc_upper]
            else:
                # Custom location string
                states = [location]

        # Initialize the underlying Seek scraper with inputs from main.py
        self.base_scraper = BaseSeekScraper(
            keyword=job_keyword,
            states=states,
            page_limit=max_pages
        )
        
        try:
            # Run the process
            output_path = self.base_scraper.scrape()
            
            if output_path and os.path.exists(output_path):
                # Format data to ensure it has all fields expected by main.py
                self.jobs_data = self._format_results(self.base_scraper.jobs_data)
                return self.jobs_data
            return []
                
        except Exception as e:
            self.logger.error(f"❌ Seek search error: {str(e)}")
            return []

    def _format_results(self, raw_jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Ensure Seek results match the common schema used in main.py"""
        formatted = []
        for job in raw_jobs:
            # Indeed/Jora use 'application_form' for the link, Seek uses 'job_source'
            if 'application_form' not in job:
                job['application_form'] = job.get('job_source', 'N/A')
            formatted.append(job)
        return formatted

    def close(self):
        """Cleanup driver"""
        if self.base_scraper:
            self.base_scraper._close_driver()
