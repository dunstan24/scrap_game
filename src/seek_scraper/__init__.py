"""
Seek Scraper Package
Job scraping tool for Seek.com.au
"""

from .scraper import SeekScraper, scrape_seek_jobs
from .config import (
    SeekScraperConfig,
    AustralianState,
    EmployerSize,
    JobLevel,
    JobType,
    SalaryType,
    Sponsorship
)
from .utils import (
    setup_logger,
    parse_job_data,
    generate_output_path,
    extract_salary_range,
    detect_sponsorship,
    extract_skills_from_text,
    detect_job_level
)

__version__ = "1.0.0"
__author__ = "Job Scraper Team"

__all__ = [
    # Main classes
    'SeekScraper',
    'SeekScraperConfig',
    
    # Enums
    'AustralianState',
    'EmployerSize',
    'JobLevel',
    'JobType',
    'SalaryType',
    'Sponsorship',
    
    # Functions
    'scrape_seek_jobs',
    'setup_logger',
    'parse_job_data',
    'generate_output_path',
    'extract_salary_range',
    'detect_sponsorship',
    'extract_skills_from_text',
    'detect_job_level',
]
