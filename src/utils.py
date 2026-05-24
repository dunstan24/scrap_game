"""
Utility functions for the Jora scraper
"""
import os
import time
import logging
from datetime import datetime
from typing import List, Dict, Any
import pandas as pd
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import re

# Setup logging
def setup_logging(log_file: str = 'scraper.log'):
    """Setup logging configuration"""
    log_dir = 'logs'
    os.makedirs(log_dir, exist_ok=True)
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%dT%H:%M:%S%z',
        handlers=[
            logging.FileHandler(os.path.join(log_dir, log_file)),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

logger = setup_logging()

def create_directories():
    """Create necessary directories for data storage"""
    directories = [
        'data/raw',
        'data/processed',
        'data/output',
        'logs'
    ]
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        # Create .gitkeep file
        gitkeep_path = os.path.join(directory, '.gitkeep')
        if not os.path.exists(gitkeep_path):
            open(gitkeep_path, 'a').close()
    logger.info("Directories created successfully")

def wait_for_element(driver, by, value, timeout=10):
    """Wait for an element to be present"""
    try:
        element = WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((by, value))
        )
        return element
    except TimeoutException:
        logger.warning(f"Timeout waiting for element: {value}")
        return None

def safe_find_element(driver, by, value, default="N/A"):
    """Safely find an element and return its text or default value"""
    try:
        element = driver.find_element(by, value)
        return element.text.strip() if element.text else default
    except NoSuchElementException:
        return default

def safe_find_elements(driver, by, value):
    """Safely find multiple elements"""
    try:
        return driver.find_elements(by, value)
    except NoSuchElementException:
        return []

def clean_text(text: str) -> str:
    """Clean and normalize text"""
    if not text or text == "N/A":
        return "N/A"
    return ' '.join(text.split()).strip()

def extract_salary(salary_text: str) -> str:
    """Extract and normalize salary information"""
    if not salary_text or salary_text == "N/A":
        return "N/A"
    # Remove extra whitespace and normalize
    return clean_text(salary_text)

# def save_to_excel(data: List[Dict[str, Any]], filename: str, output_dir: str = 'data/output'):
#     """Save scraped data to Excel file (kept name for backward compat)"""
#     try:
#         os.makedirs(output_dir, exist_ok=True)

#         # Create DataFrame
#         df = pd.DataFrame(data)

#         # Generate filename with timestamp
#         timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
#         filepath = os.path.join(output_dir, f"{filename}_{timestamp}.csv")

#         # Save to CSV (utf-8-sig so Excel opens correctly on Windows)
#         df.to_csv(filepath, index=False, encoding='utf-8-sig')
#         logger.info(f"Data saved to {filepath}")
#         logger.info(f"Total records: {len(data)}")

#         return filepath
#     except Exception as e:
#         logger.error(f"Error saving to CSV: {str(e)}")
#         raise

# def append_to_excel(data: List[Dict[str, Any]], filepath: str):
#     """Append data to existing Excel (.xlsx) or CSV file"""
#     try:
#         is_excel = filepath.endswith('.xlsx')

#         if os.path.exists(filepath):
#             # Read existing data based on file type
#             if is_excel:
#                 existing_df = pd.read_excel(filepath, engine='openpyxl')
#             else:
#                 existing_df = pd.read_csv(filepath, encoding='utf-8-sig')

#             # Append new data
#             new_df = pd.DataFrame(data)
#             combined_df = pd.concat([existing_df, new_df], ignore_index=True)
#             # Remove duplicates based on source URL, company name, and location
#             combined_df = combined_df.drop_duplicates(
#                 subset=['source', 'employer_company_name', 'location'],
#                 keep='last'
#             )

#             # Save back in the correct format
#             if is_excel:
#                 combined_df.to_excel(filepath, index=False, engine='openpyxl')
#             else:
#                 logger.info("File is not Excel, skipping append")

#             logger.info(f"Data appended to {filepath}")
#             logger.info(f"Total records after append: {len(combined_df)}")
#         else:
#             # File doesn't exist, create new
#             df = pd.DataFrame(data)
#             if is_excel:
#                 df.to_excel(filepath, index=False, engine='openpyxl')
#             else:
#                 logger.info("File is not Excel, skipping append")
#             logger.info(f"Created new file: {filepath}")
#             logger.info(f"Total records: {len(data)}")
#     except Exception as e:
#         logger.error(f"Error appending data: {str(e)}")
#         raise

def build_search_url(base_url: str, job_keyword: str = "", location: str = "", page: int = 1) -> str:
    """Build Jora search URL with parameters"""
    # This is a generic structure - adjust based on actual Jora URL pattern
    url = f"{base_url}/jobs"
    
    params = []
    if job_keyword:
        params.append(f"q={job_keyword.replace(' ', '+')}")
    if location:
        params.append(f"l={location.replace(' ', '+')}")
    if page > 1:
        params.append(f"page={page}")
    
    if params:
        url += "?" + "&".join(params)
    
    return url

def random_delay(min_seconds: int = 1, max_seconds: int = 3):
    """Add random delay to mimic human behavior"""
    import random
    delay = random.uniform(min_seconds, max_seconds)
    time.sleep(delay)

def adaptive_delay(page_number: int, base_delay: int = 2):
    """
    Adaptive delay that increases with page number to avoid Cloudflare throttling.
    After every 15 pages, delays are progressively increased.
    """
    import random
    from config import DELAY_MULTIPLIER_THRESHOLD, DELAY_MULTIPLIER
    
    # Calculate multiplier based on pages reached
    pages_over_threshold = max(0, page_number - DELAY_MULTIPLIER_THRESHOLD)
    multiplier = (DELAY_MULTIPLIER ** (pages_over_threshold // 5)) if pages_over_threshold > 0 else 1
    
    # Apply multiplier to delays
    min_delay = base_delay * multiplier
    max_delay = (base_delay + 2) * multiplier
    
    delay = random.uniform(min_delay, max_delay)
    logger.debug(f"Page {page_number}: adaptive delay = {delay:.2f}s (multiplier: {multiplier:.2f})")
    time.sleep(delay)

def detect_cloudflare(page_source: str) -> bool:
    """
    Detect if page is showing Cloudflare challenge or protection.
    
    Args:
        page_source: HTML content from the page
        
    Returns:
        True if Cloudflare detected, False otherwise
    """
    from config import CLOUDFLARE_MARKERS
    
    if not page_source:
        return False
    
    # Check first 5000 chars for markers (usually near top)
    snippet = page_source[:5000].lower()
    for marker in CLOUDFLARE_MARKERS:
        if marker.lower() in snippet:
            logger.warning(f"🔒 Cloudflare detected: '{marker}'")
            return True
    
    return False

def get_random_user_agent() -> str:
    """Get a random User-Agent to bypass detection."""
    import random
    from config import USER_AGENTS
    
    agent = random.choice(USER_AGENTS)
    logger.debug(f"Using User-Agent: {agent[:80]}...")
    return agent

def get_current_timestamp() -> str:
    """Get current timestamp as string in ISO 8601 format"""
    return datetime.now().astimezone().replace(microsecond=0).isoformat()

def print_progress(current: int, total: int, prefix: str = 'Progress'):
    """Print progress bar"""
    bar_length = 50
    filled_length = int(bar_length * current / total)
    bar = '█' * filled_length + '-' * (bar_length - filled_length)
    percent = f"{100 * (current / total):.1f}"
    print(f'\r{prefix}: |{bar}| {percent}% ({current}/{total})', end='')
    if current == total:
        print()


def save_to_csv(
    data: List[Dict[str, Any]], filename: str, output_dir: str = "data/output"
):
    """Save scraped data to CSV file"""
    try:
        os.makedirs(output_dir, exist_ok=True)

        # Create DataFrame
        df = pd.DataFrame(data)
        
        # Inject ISO 8601 scraping_timestamp if not present
        if 'scraping_timestamp' not in df.columns:
            df['scraping_timestamp'] = get_current_timestamp()

        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = os.path.join(output_dir, f"{filename}_{timestamp}.csv")

        # Save to CSV
        df.to_csv(filepath, index=False, encoding='utf-8-sig')
        logger.info(f"Data saved to {filepath}")
        logger.info(f"Total records: {len(data)}")

        return filepath
    except Exception as e:
        logger.error(f"Error saving to CSV: {str(e)}")
        raise

def append_to_csv(data: List[Dict[str, Any]], filepath: str):
    """Append data to existing CSV file"""
    try:
        if os.path.exists(filepath):
            # Read existing data
            existing_df = pd.read_csv(filepath)
            # Append new data
            new_df = pd.DataFrame(data)
            
            # Inject ISO 8601 scraping_timestamp if not present
            if 'scraping_timestamp' not in new_df.columns:
                new_df['scraping_timestamp'] = get_current_timestamp()
                
            combined_df = pd.concat([existing_df, new_df], ignore_index=True)
            # Remove duplicates based on title, employer_company_name, and location
            combined_df = combined_df.drop_duplicates(
                subset=["source", "employer_company_name", "location"], keep="last"
            )
            # Save back
            combined_df.to_csv(filepath, index=False, encoding='utf-8-sig')
            logger.info(f"Data appended to {filepath}")
            logger.info(f"Total records after append: {len(combined_df)}")
        else:
            # File doesn't exist, create new
            save_to_csv(data, os.path.basename(filepath).replace('.csv', ''))
    except Exception as e:
        logger.error(f"Error appending to CSV: {str(e)}")
        raise

def normalize_state(location: str) -> str:
    """Normalize Australian state from location string"""
    if not location or location == "N/A":
        return "N/A"
    
    loc = location.upper()
    state_map = {
        'NSW': 'New South Wales',
        'VIC': 'Victoria',
        'QLD': 'Queensland',
        'WA': 'Western Australia',
        'SA': 'South Australia',
        'TAS': 'Tasmania',
        'ACT': 'Australian Capital Territory',
        'NT': 'Northern Territory'
    }
    
    for abbr, full in state_map.items():
        if abbr in loc or full.upper() in loc:
            return abbr
    return "N/A"

def normalize_job_type(job_type: str) -> str:
    """Normalize job type to standardized enum values"""
    if not job_type or job_type == "N/A":
        return "full_time"  # Default
    
    jt = job_type.lower()
    if 'part' in jt:
        return 'part_time'
    if 'contract' in jt:
        return 'contract'
    if 'casual' in jt or 'temp' in jt:
        return 'casual_temporary'
    if 'permanent' in jt:
        return 'permanent'
    return 'full_time'

def extract_salary_parts(salary_text: str) -> tuple:
    """Extract min, max dan type dari salary string.
    Mengembalikan string raw dengan tanda $ dan koma, bukan float.
    Contoh: "$85,000", "$95,000", "year"
    """
    if not salary_text or salary_text == "N/A":
        return "N/A", "N/A", "N/A"

    # Coba tangkap format $85,000 atau $85,000.50 (dengan tanda $)
    matches = re.findall(r'\$\d{1,3}(?:,\d{3})*(?:\.\d+)?', salary_text)

    if len(matches) >= 2:
        s_min, s_max = matches[0], matches[1]
    elif len(matches) == 1:
        s_min = s_max = matches[0]
    else:
        # Fallback: angka tanpa $ (misal "85000 - 95000")
        nums = re.findall(r'\d{1,3}(?:,\d{3})*(?:\.\d+)?', salary_text)
        if len(nums) >= 2:
            s_min, s_max = nums[0], nums[1]
        elif len(nums) == 1:
            s_min = s_max = nums[0]
        else:
            s_min = s_max = "N/A"

    # Detect type - check for /hr first, then hour, then others
    s_lower = salary_text.lower()
    s_type = "year"
    if '/hr' in s_lower or 'hour' in s_lower:
        s_type = "hour"
    elif 'day' in s_lower:
        s_type = "day"
    elif 'week' in s_lower:
        s_type = "week"
    elif 'month' in s_lower:
        s_type = "month"

    return s_min, s_max, s_type

def detect_job_level(title: str, description: str) -> str:
    """Detect job seniority level"""
    combined = (str(title) + " " + str(description)).lower()
    if any(x in combined for x in ['senior', 'lead', 'principal', 'head', 'manager']):
        return 'senior'
    if any(x in combined for x in ['junior', 'graduate', 'entry', 'trainee']):
        return 'beginer'
    if any(x in combined for x in ['director', 'executive', 'vp', 'ceo', 'cto']):
        return 'enterprise'
    return 'medior'

def extract_skills(description: str) -> str:
    """Extract key skills from description"""
    if not description or description == "N/A":
        return "N/A"
    # Simplified version
    common_skills = ['Python', 'Java', 'SQL', 'React', 'Project Management', 'Communication', 'AWS', 'Azure', 'Docker']
    found = [skill for skill in common_skills if skill.lower() in str(description).lower()]
    return ", ".join(found) if found else "N/A"

def split_contact_name(name_raw: str) -> tuple:
    """Split full name into first and last name"""
    if not name_raw:
        return "N/A", "N/A"
    parts = str(name_raw).strip().split()
    if len(parts) >= 2:
        return parts[0], " ".join(parts[1:])
    return name_raw, "N/A"

def map_sponsorship(signal: str, description: str) -> int:
    """Map sponsorship signal/description to integer (0 or 1)"""
    if signal == 'yes':
        return 1
    desc = str(description).lower()
    if any(kw in desc for kw in ['sponsorship available', 'visa sponsorship']):
        return 1
    return 0

def extract_website_from_text(text: str) -> str:
    """Extract URL from text"""
    if not text:
        return "N/A"
    match = re.search(r'https?://[^\s<>"]+|www\.[^\s<>"]+', str(text))
    return match.group(0) if match else "N/A"

def extract_phone_from_text(text: str) -> str:
    """Extract Australian phone numbers from text"""
    if not text:
        return "N/A"
    # Simple regex for AU phone numbers
    match = re.search(r'(\+61|0)[2-478](?:[ -]?[0-9]){8}', str(text))
    return match.group(0) if match else "N/A"
