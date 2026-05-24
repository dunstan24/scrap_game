"""
Configuration and Enum Definitions for Seek.com.au Scraper
"""

from enum import Enum
from typing import List

# ==================== ENUMS ====================

class AustralianState(str, Enum):
    """Australian States Enum"""
    ACT = "ACT"
    NSW = "NSW"
    NT = "NT"
    QLD = "QLD"
    SA = "SA"
    TAS = "TAS"
    VIC = "VIC"
    WA = "WA"

    @classmethod
    def get_all_states(cls) -> List[str]:
        """Get all state values"""
        return [state.value for state in cls]

    @classmethod
    def get_all_codes(cls) -> List[str]:
        """Get all state codes"""
        return [state.name for state in cls]


class EmployerSize(str, Enum):
    """Employer Size Enum"""
    SIZE_1_10 = "size_1_10"
    SIZE_11_50 = "size_11_50"
    SIZE_51_200 = "size_51_200"
    SIZE_201_500 = "size_201_500"
    SIZE_501_1000 = "size_501_1000"
    SIZE_1001_5000 = "size_1001_5000"
    SIZE_5001_10000 = "size_5001_10000"
    SIZE_10001_PLUS = "size_10001_plus"

    @classmethod
    def get_all_sizes(cls) -> List[str]:
        """Get all employer size values"""
        return [size.value for size in cls]


class JobLevel(str, Enum):
    """Job Level Enum"""
    BEGINER = "beginer"
    MEDIOR = "medior"
    SENIOR = "senior"
    ENTERPRISE = "enterprise"

    @classmethod
    def get_all_levels(cls) -> List[str]:
        """Get all job level values"""
        return [level.value for level in cls]


class JobType(str, Enum):
    """Job Type Enum"""
    FULL_TIME = "full_time"
    PART_TIME = "part_time"
    PERMANENT = "permanent"
    CASUAL_TEMPORARY = "casual_temporary"
    CONTRACT = "contract"

    @classmethod
    def get_all_types(cls) -> List[str]:
        """Get all job type values"""
        return [job_type.value for job_type in cls]


class SalaryType(str, Enum):
    """Salary Type Enum"""
    HOUR = "hour"
    WEEK = "week"
    MONTH = "month"
    YEAR = "year"

    @classmethod
    def get_all_salary_types(cls) -> List[str]:
        """Get all salary type values"""
        return [salary_type.value for salary_type in cls]


class Sponsorship(str, Enum):
    """Sponsorship Enum"""
    YES = 1
    NO = 0


# ==================== CONFIGURATION ====================

class SeekScraperConfig:
    """Configuration for Seek Scraper"""
    
    # Base URL
    BASE_URL = "https://www.seek.com.au"
    SEARCH_URL = "https://www.seek.com.au/jobs"
    
    # Timeouts (in seconds)
    PAGE_LOAD_TIMEOUT = 15
    ELEMENT_WAIT_TIMEOUT = 10
    
    # CSV Settings
    CSV_OUTPUT_DIR = "data/output"
    CSV_PREFIX = "jobs_seek"
    
    # Browser Settings
    HEADLESS_MODE = True    # True = background (tidak terlihat), False = tampilkan browser
    USER_AGENT = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
    
    # Pagination
    DEFAULT_PAGE_SIZE = 20
    
    # State to Seek URL mapping
    STATE_URL_MAPPING = {
        "ACT": "Australian%20Capital%20Territory",
        "NSW": "New%20South%20Wales",
        "NT": "Northern%20Territory",
        "QLD": "Queensland",
        "SA": "South%20Australia",
        "TAS": "Tasmania",
        "VIC": "Victoria",
        "WA": "Western%20Australia",
    }
    
    # Sponsorship Keywords
    SPONSORSHIP_KEYWORDS = [
        "sponsorship",
        "available sponsorship",
        "state sponsorship",
        "visa sponsorship",
        "employer sponsorship",
        "eligible for sponsorship",
        "migration",
        "visa support"
    ]
    
    # Default Values (use None for nullable fields)
    DEFAULT_SALARY_MIN = None
    DEFAULT_SALARY_MAX = None
    DEFAULT_SALARY_TYPE = None
    
    # Csv columns
    CSV_COLUMNS = [
        "employer_email",
        "employer_first_name",
        "employer_last_name",
        "employer_phone_number",
        "employer_company_name",
        "employer_state",
        "employer_size",
        "employer_address",
        "employer_industry",
        "employer_website_url",
        "employer_description",
        "title",
        "description",
        "level",
        "location",
        "state",
        "type",
        "source",
        "sponsorship",
        "salary_min",
        "salary_max",
        "salary_type",
        "job_skills",
        "scraping_timestamp"
    ]
