
"""
Utility functions for Seek Scraper
"""

import logging
import sys
import re
from datetime import datetime
from typing import Optional, Dict, List, Tuple, Any
from bs4 import BeautifulSoup

# ==================== SALARY TYPE EXTRACTION ====================
def extract_salary_type_from_text(salary_text: str) -> Optional[str]:
    """
    Extract salary type (e.g., 'per hour', 'per annum', 'per day') from salary string.
    Returns the type as string, or None if not found.
    """
    if not salary_text:
        return None
    # Bersihkan karakter non-ASCII dan whitespace aneh
    cleaned = salary_text.encode('ascii', 'ignore').decode('ascii')
    cleaned = re.sub(r'[\u00A0\t\r\n]+', ' ', cleaned)
    text = cleaned.lower().strip()
    # Ordered by specificity, mapping all to enum: hour, week, month, year
    patterns = [
        (r'(per[\s\-]*)?hour(s)?|/hour(s)?|hourly|hr(s)?(?![a-z])', 'hour'),
        (r'(per[\s\-]*)?day(s)?|/day(s)?|daily|pd(?![a-z])', 'day'),
        (r'(per[\s\-]*)?week(s)?|/week(s)?|weekly|wk(s)?(?![a-z])', 'week'),
        (r'(per[\s\-]*)?month(s)?|/month(s)?|monthly|mo(s)?(?![a-z])', 'month'),
        (r'(per[\s\-]*)?annum|/annum|annually|annum(?![a-z])|(per[\s\-]*)?year(s)?|/year(s)?|yearly|yr(s)?(?![a-z])', 'year'),
        (r'p\.?a\.?', 'year'),
    ]
    for pattern, label in patterns:
        if re.search(pattern, text):
            return label
    # Heuristic: jika salary text mengandung angka besar (>=10000) tanpa periode eksplisit, anggap per year
    # Contoh: 'Salary from $148,213 plus 16% superannuation', '$69,160 + Uniforms...'
    big_number = re.search(r'\$?\s?([0-9]{2,3},[0-9]{3}|[0-9]{5,})', salary_text)
    if big_number:
        num_str = big_number.group(1).replace(',', '')
        if int(num_str) >= 10000:
            return 'year'
    # Debug log jika gagal deteksi
    import logging
    logging.getLogger("SeekScraper").debug(f"[SALARY_TYPE_NOT_FOUND] salary_text: '{salary_text}' cleaned: '{text}'")
    return None
# ==================== PHONE EXTRACTION ====================
def extract_phone_from_soup(soup: 'BeautifulSoup') -> Optional[str]:
    """
    Extract the first phone number found in <a href="tel:..."> tag.
    Returns the phone number as string, or None if not found.
    """
    if not soup:
        return None
    tel_link = soup.find('a', href=lambda x: x and x.startswith('tel:'))
    if tel_link:
        # Ambil nomor setelah 'tel:' dan strip spasi
        phone = tel_link['href'][4:].replace('%20', ' ').strip()
        # Normalisasi: hapus karakter non-digit kecuali spasi
        import re
        phone = re.sub(r'[^0-9 ]', '', phone)
        return phone
    return None
import os
from pathlib import Path

from .config import (
    SeekScraperConfig,
    AustralianState,
    JobType,
    SalaryType,
    EmployerSize,
    JobLevel,
    Sponsorship
)

# ==================== EMAIL EXTRACTION ====================
def extract_email_from_text(text: str) -> Optional[str]:
    """
    Extract the first email address found in the given text.
    Returns None if not found.
    Handles emails with spaces, [at], (at), etc.
    """
    if not text:
        return None
    # Normalisasi: ganti [at], (at), {at}, spasi di sekitar @ menjadi @
    norm = text
    norm = re.sub(r"\s*\[at\]\s*|\s*\(at\)\s*|\s*\{at\}\s*|\s+at\s+|\s*@\s*", "@", norm, flags=re.IGNORECASE)
    # Hilangkan spasi di sekitar titik
    norm = re.sub(r"\s*\.\s*", ".", norm)
    # Cari email
    match = re.search(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", norm)
    if match:
        email = match.group(0).strip().rstrip('.;,')
        return email
    return None
def extract_employer_description(description: str) -> str:
    """
    Extract employer description from job description text.
    Only returns a paragraph if it looks like it describes the employer/company.
    Otherwise returns empty string.
    """
    if not description:
        return ""
    desc = description.lower()
    employer_headers = [
        "about the company", "about us", "about our company", "who we are", "about employer", "about the organisation", "about the organization", "company overview", "company profile", "about your new company"
    ]
    paragraphs = [p.strip() for p in description.split("\n") if p.strip()]
    if len(paragraphs) == 1:
        paragraphs = [p.strip() for p in description.split(".") if len(p.strip()) > 30]
    for para in paragraphs:
        para_l = para.lower()
        for header in employer_headers:
            if header in para_l:
                return para.strip()
    for para in paragraphs:
        para_l = para.lower()
        if para_l.startswith("about ") or para_l.startswith("who we are") or para_l.startswith("company "):
            return para.strip()
    return ""
# ==================== LOGGING SETUP ====================

class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors for terminal output"""
    
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[92m',       # Green
        'WARNING': '\033[93m',    # Yellow
        'ERROR': '\033[91m',      # Red
        'CRITICAL': '\033[95m',   # Magenta
        'RESET': '\033[0m'        # Reset
    }
    
    # Unicode to ASCII replacement map for Windows compatibility
    UNICODE_MAP = {
        '✓': '[OK]',
        '✗': '[FAIL]',
        '⚠': '[WARN]',
        '✉': '[MSG]',
        '◆': '*',
        '★': '*',
        '→': '->',
        '←': '<-',
        '↑': '^',
        '↓': 'v',
    }
    
    def format(self, record):
        try:
            # Replace unicode characters with ASCII-safe alternatives
            msg_str = str(record.msg)
            for unicode_char, ascii_char in self.UNICODE_MAP.items():
                msg_str = msg_str.replace(unicode_char, ascii_char)
            record.msg = msg_str
            
            log_color = self.COLORS.get(record.levelname, self.COLORS['INFO'])
            record.msg = f"{log_color}{record.msg}{self.COLORS['RESET']}"
        except (UnicodeEncodeError, UnicodeDecodeError, AttributeError):
            # Fallback for terminals that don't support colors/unicode
            pass
        return super().format(record)


def setup_logger(name: str = "SeekScraper") -> logging.Logger:
    """
    Setup logger with colored console output and file output
    
    Args:
        name: Logger name
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    
    # Remove existing handlers
    if logger.handlers:
        logger.handlers.clear()
    
    # Console Handler with colors - force UTF-8 encoding
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    
    # Set UTF-8 encoding for Windows compatibility
    if hasattr(console_handler, 'stream'):
        import io
        if hasattr(console_handler.stream, 'reconfigure'):
            try:
                console_handler.stream.reconfigure(encoding='utf-8', errors='replace')
            except (AttributeError, ValueError):
                pass
    
    console_formatter = ColoredFormatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # File Handler
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / f"seek_scraper_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
    
    return logger


# ==================== DATA VALIDATION ====================

# Mapping nama lengkap → singkatan negara bagian Australia
_STATE_FULL_TO_ABBR: Dict[str, str] = {
    "new south wales":              "NSW",
    "victoria":                     "VIC",
    "queensland":                   "QLD",
    "western australia":            "WA",
    "south australia":              "SA",
    "tasmania":                     "TAS",
    "australian capital territory": "ACT",
    "northern territory":           "NT",
}


def validate_state(state: str) -> Optional[str]:
    """
    Validate dan normalise state value.
    Menerima singkatan (NSW) MAUPUN nama lengkap (New South Wales).
    Selalu mengembalikan singkatan 2-3 huruf.

    Args:
        state: State value to validate (abbreviation or full name)

    Returns:
        State abbreviation (e.g. 'NSW') or None if unrecognized
    """
    if not state:
        return None
    # Cek apakah sudah singkatan (ACT, NSW, VIC, ...)
    if state.strip().upper() in [s.value for s in AustralianState]:
        return state.strip().upper()
    # Coba konversi nama lengkap → singkatan
    abbr = _STATE_FULL_TO_ABBR.get(state.strip().lower())
    if abbr:
        return abbr
    return None


def validate_job_type(job_type: str) -> Optional[str]:
    """Validate job type"""
    try:
        if job_type.lower() in JobType.get_all_types():
            return job_type.lower()
    except (AttributeError, TypeError):
        pass
    return None


def validate_salary_type(salary_type: str) -> Optional[str]:
    """Validate salary type"""
    try:
        if salary_type.lower() in SalaryType.get_all_salary_types():
            return salary_type.lower()
    except (AttributeError, TypeError):
        pass
    return None


def validate_employer_size(size: str) -> Optional[str]:
    """Validate employer size"""
    try:
        if size.lower() in EmployerSize.get_all_sizes():
            return size.lower()
    except (AttributeError, TypeError):
        pass
    return None


def validate_job_level(level: str) -> Optional[str]:
    """Validate job level"""
    try:
        if level.lower() in JobLevel.get_all_levels():
            return level.lower()
    except (AttributeError, TypeError):
        pass
    return None


# ==================== DATA EXTRACTION ====================

def extract_salary_range(salary_text: str) -> Tuple[Optional[float], Optional[float]]:
    """
    Extract salary min and max from salary text
    
    Args:
        salary_text: Text containing salary information (e.g., "$50k - $60k")
        
    Returns:
        Tuple of (salary_min, salary_max) or (None, None) if not found
    """
    if not salary_text:
        return None, None
    
    try:
        # Tangkap format $85,000 atau $85,000.50 (dengan tanda $)
        matches = re.findall(r'\$\d{1,3}(?:,\d{3})*(?:\.\d+)?', salary_text)

        if len(matches) >= 2:
            return matches[0], matches[1]
        elif len(matches) == 1:
            return matches[0], matches[0]

        # Fallback: angka tanpa $ (mis. "85000 - 95000")
        nums = re.findall(r'\d{1,3}(?:,\d{3})*(?:\.\d+)?', salary_text)
        if len(nums) >= 2:
            return nums[0], nums[1]
        elif len(nums) == 1:
            return nums[0], nums[0]

    except (ValueError, IndexError):
        pass

    return None, None


def detect_salary_type(salary_text: str) -> Optional[str]:
    """
    Detect salary type from text
    
    Args:
        salary_text: Text containing salary information
        
    Returns:
        Salary type (hour, week, month, year) or None if not detected
    """
    if not salary_text:
        return None
    
    salary_lower = salary_text.lower()
    
    if "/hour" in salary_lower or "hourly" in salary_lower:
        return SalaryType.HOUR.value
    elif "/week" in salary_lower or "weekly" in salary_lower:
        return SalaryType.WEEK.value
    elif "/month" in salary_lower or "monthly" in salary_lower or "pcm" in salary_lower:
        return SalaryType.MONTH.value
    elif "p.a." in salary_lower or "per annum" in salary_lower or "year" in salary_lower:
        return SalaryType.YEAR.value
    
    return None


def detect_sponsorship(description: str) -> int:
    """
    Detect if job offers sponsorship
    
    Args:
        description: Job description text
        
    Returns:
        1 if sponsorship is mentioned, 0 otherwise
    """
    if not description:
        return 0
    
    description_lower = description.lower()
    
    for keyword in SeekScraperConfig.SPONSORSHIP_KEYWORDS:
        if keyword.lower() in description_lower:
            return 1
    
    return 0


def extract_skills_from_text(text: str) -> str:
    """
    Extract skills from job description
    
    Args:
        text: Job description text
        
    Returns:
        Comma-separated skills string
    """
    # Common skills patterns
    skills_patterns = [
        r'(?:skills?|required|must\s+have|preferred):?\s*([^.]+)',
        r'([a-zA-Z\+\#]+[\s\+\#]*(?:[a-zA-Z\+\#]+)?(?:\s*[,&]\s*[a-zA-Z\+\#]+)*)'
    ]
    
    if not text:
        return ""
    
    text_lower = text.lower()
    found_skills = []
    
    # Common tech skills to look for
    common_skills = [
        'python', 'java', 'javascript', 'c#', 'sql', 'html', 'css',
        'react', 'angular', 'node.js', 'express', 'mongodb', 'postgresql',
        'aws', 'azure', 'gcp', 'docker', 'kubernetes', 'git',
        'agile', 'scrum', 'leadership', 'communication', 'problem solving',
        'data analysis', 'machine learning', 'api', 'rest', 'graphql',
        'cloud', 'devops', 'testing', 'linux', 'window'
    ]
    
    for skill in common_skills:
        if skill in text_lower:
            found_skills.append(skill.title())
    
    return ", ".join(found_skills) if found_skills else "Not Specified"


def detect_job_level(description: str, title: str) -> str:
    """
    Detect job level from description and title
    
    Args:
        description: Job description
        title: Job title
        
    Returns:
        Job level: beginer, medior, senior, or enterprise
    """
    combined_text = f"{title} {description}".lower()
    
    # Enterprise patterns
    enterprise_patterns = [
        r'executive', r'director', r'c-?suite', r'vp\b', r'vice\s+president',
        r'chief\s+', r'board', r'ceo', r'cto', r'cfo'
    ]
    
    # Senior patterns
    senior_patterns = [
        r'senior', r'lead', r'principal', r'architect', r'manager',
        r'\b10\+\s+years', r'expertise', r'advanced'
    ]
    
    # Medior patterns
    medior_patterns = [
        r'mid[\s\-]?level', r'intermediate', r'medior',
        r'\b3[\s\-]?5\s+years', r'proficiency'
    ]
    
    # Check enterprise
    for pattern in enterprise_patterns:
        if re.search(pattern, combined_text):
            return JobLevel.ENTERPRISE.value
    
    # Check senior
    for pattern in senior_patterns:
        if re.search(pattern, combined_text):
            return JobLevel.SENIOR.value
    
    # Check medior
    for pattern in medior_patterns:
        if re.search(pattern, combined_text):
            return JobLevel.MEDIOR.value
    
    # Default to beginer
    return JobLevel.BEGINER.value


def parse_job_data(job_element: Dict[str, Any], source_url: str, state: str) -> Dict[str, Any]:
    """
    Parse job element data into standardized format
    
    Args:
        job_element: Dictionary containing job information
        source_url: Source URL for the job posting
        state: State where job is located
        
    Returns:
        Standardized job data dictionary
    """
    
    # Validate state
    validated_state = validate_state(state) or state.upper()
    
    # Extract salary information
    salary_text = job_element.get('salary', '')
    salary_min, salary_max = extract_salary_range(salary_text)
    salary_type = extract_salary_type_from_text(salary_text)
    
    # Detect sponsorship
    description = job_element.get('description', '')
    sponsorship = detect_sponsorship(description)
    
    # Detect job level
    title = job_element.get('title', '')
    level = detect_job_level(description, title)
    
    # Extract skills
    skills = extract_skills_from_text(description)
    
    # Detect job type
    job_type_text = job_element.get('type', 'full_time')
    validated_job_type = validate_job_type(job_type_text) or JobType.FULL_TIME.value
    
    # Build job data dictionary
    employer_description = extract_employer_description(job_element.get('company_description', ''))
    # Try to extract email from description if not already present
    employer_email = job_element.get('employer_email', '')
    if not employer_email:
        employer_email = extract_email_from_text(description)
    job_data = {
        'employer_email': employer_email or None,
        'employer_first_name': job_element.get('employer_first_name', '') or None,
        'employer_last_name': job_element.get('employer_last_name', '') or None,
        'employer_phone_number': job_element.get('employer_phone_number', '') or None,
        'employer_company_name': job_element.get('company_name', ''),
        'employer_state': validated_state,
        'employer_size': job_element.get('company_size', '') or None,
        'employer_address': job_element.get('company_address', '') or None,
        'employer_industry': job_element.get('company_industry', '') or None,
        'employer_website_url': job_element.get('company_website', '') or None,
        'employer_description': employer_description or None,
        'title': title,
        'description': description,
        'level': level,
        'location': job_element.get('location', ''),
        'state': validated_state,
        'type': validated_job_type,
        'source': source_url,
        'sponsorship': sponsorship,
        'salary_min': salary_min,
        'salary_max': salary_max,
        'salary_type': salary_type,
        'job_skills': None,
        'scraping_timestamp': datetime.now().isoformat()
    }
    return job_data


# ==================== DATA EXPORT ====================

def ensure_output_directory() -> Path:
    """
    Ensure output directory exists
    
    Returns:
        Path to output directory
    """
    output_dir = Path(SeekScraperConfig.CSV_OUTPUT_DIR)
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def generate_csv_filename() -> str:
    """
    Generate CSV filename with timestamp
    
    Returns:
        CSV filename
    """
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    return f"{SeekScraperConfig.CSV_PREFIX}_{timestamp}.csv"


def generate_output_path() -> Path:
    """
    Generate full output path for CSV file
    
    Returns:
        Full path to output CSV file
    """
    output_dir = ensure_output_directory()
    filename = generate_csv_filename()
    return output_dir / filename


# ==================== TEXT CLEANING ====================

def clean_text(text: str, max_length: int = None) -> str:
    """
    Clean and normalize text
    
    Args:
        text: Text to clean
        max_length: Maximum length to truncate to
        
    Returns:
        Cleaned text
    """
    if not text:
        return ""
    
    # Remove extra whitespace
    text = " ".join(text.split())
    
    # Remove special characters but keep basic punctuation
    text = re.sub(r'[^\w\s\-.,;:\'\"()&@]', '', text)
    
    # Truncate if needed
    if max_length and len(text) > max_length:
        text = text[:max_length] + "..."
    
    return text


def format_salary_display(salary_min: float, salary_max: float, salary_type: str) -> str:
    """
    Format salary for display
    
    Args:
        salary_min: Minimum salary
        salary_max: Maximum salary
        salary_type: Type of salary
        
    Returns:
        Formatted salary string
    """
    if salary_min == 0 and salary_max == 0:
        return "Not Specified"
    
    return f"${salary_min:,.0f} - ${salary_max:,.0f} {salary_type}"
