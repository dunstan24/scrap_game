"""
Configuration settings for Jora Australia scraper
"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Base URLs
BASE_URL = os.getenv('BASE_URL', 'https://au.jora.com')

# Selenium Settings
HEADLESS_MODE = os.getenv('HEADLESS_MODE', 'True').lower() == 'true'
IMPLICIT_WAIT = int(os.getenv('IMPLICIT_WAIT', 10))
PAGE_LOAD_TIMEOUT = int(os.getenv('PAGE_LOAD_TIMEOUT', 60))

# Scraping Settings
MAX_PAGES_PER_SEARCH = int(os.getenv('MAX_PAGES_PER_SEARCH', 50))
DELAY_BETWEEN_REQUESTS = int(os.getenv('DELAY_BETWEEN_REQUESTS', 2))
FETCH_FULL_DESCRIPTION = os.getenv('FETCH_FULL_DESCRIPTION', 'True').lower() == 'true'
FULL_DESCRIPTION_TIMEOUT = int(os.getenv('FULL_DESCRIPTION_TIMEOUT', 90))  # Seconds to wait for job detail page

# Cloudflare Detection & Handling
CLOUDFLARE_MARKERS = [
    'just a moment',
    'cloudflare',
    'security verification',
    'performing security',
    'enable javascript and cookies',
    'ray id:',
    'checking your browser',
    'turnstile',
]

# User-Agent rotation for bypassing Cloudflare detection
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0',
    'Mozilla/5.0 (X11; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0',
]

# Progressive delay multiplier for pagination (after X pages, multiply delays)
DELAY_MULTIPLIER_THRESHOLD = 15  # After 15 pages, start increasing delays
DELAY_MULTIPLIER = 1.5  # Multiply delays by this factor

# Output Settings
OUTPUT_DIRECTORY = os.getenv('OUTPUT_DIRECTORY', 'data/output')

# Australian States and Territories
AUSTRALIAN_STATES = [
    'New South Wales',
    'Victoria',
    'Queensland',
    'Western Australia',
    'South Australia',
    'Tasmania',
    'Australian Capital Territory',
    'Northern Territory',
]

# State enum: maps various text forms -> canonical abbreviation
STATE_ABBR_MAP = {
    'new south wales': 'NSW',
    'nsw': 'NSW',
    'victoria': 'VIC',
    'vic': 'VIC',
    'queensland': 'QLD',
    'qld': 'QLD',
    'western australia': 'WA',
    'wa': 'WA',
    'south australia': 'SA',
    'sa': 'SA',
    'tasmania': 'TAS',
    'tas': 'TAS',
    'australian capital territory': 'ACT',
    'act': 'ACT',
    'northern territory': 'NT',
    'nt': 'NT',
}

# Job type enum mapping
JOB_TYPE_MAP = {
    'full time': 'full_time',
    'full-time': 'full_time',
    'fulltime': 'full_time',
    'part time': 'part_time',
    'part-time': 'part_time',
    'parttime': 'part_time',
    'permanent': 'permanent',
    'casual': 'casual_temporary',
    'temporary': 'casual_temporary',
    'casual/temporary': 'casual_temporary',
    'contract': 'contract',
    'contractor': 'contract',
    'freelance': 'contract',
}

# Salary type patterns (ordered by specificity)
SALARY_TYPE_PATTERNS = [
    (r'(per[\s\-]*)?hour(s)?|/hour(s)?|hourly|hr(s)?(?![a-z])', 'hour'),
    (r'(per[\s\-]*)?day(s)?|/day(s)?|daily', 'day'),
    (r'(per[\s\-]*)?week(s)?|/week(s)?|weekly|wk(s)?(?![a-z])', 'week'),
    (r'(per[\s\-]*)?month(s)?|/month(s)?|monthly|pcm', 'month'),
    (r'(per[\s\-]*)?annum|/annum|annually|p\.?a\.?|(per[\s\-]*)?year(s)?|/year(s)?|yearly|yr(s)?(?![a-z])', 'year'),
]

# Sponsorship keywords to detect in description
SPONSORSHIP_KEYWORDS = [
    'sponsorship', 'visa sponsorship', 'work visa', 'employer sponsored',
    'skilled migration', '482 visa', '186 visa', '187 visa',
    'temporary skill shortage', 'available sponsorship', 'state sponsorship',
    'sponsor', 'sponsoring', 'will sponsor',
]

# Job level detection patterns
JOB_LEVEL_PATTERNS = {
    'enterprise': [r'executive', r'director', r'c-?suite', r'\bvp\b', r'vice\s+president', r'chief\s+', r'board', r'ceo', r'cto', r'cfo'],
    'senior': [r'senior', r'lead', r'principal', r'architect', r'manager', r'\b10\+\s+years', r'expertise', r'advanced'],
    'medior': [r'mid[\s\-]?level', r'intermediate', r'medior', r'\b3[\s\-]?5\s+years', r'proficiency'],
}

# Common tech/professional skills to detect
COMMON_SKILLS = [
    'python', 'java', 'javascript', 'c#', 'sql', 'html', 'css',
    'react', 'angular', 'node.js', 'express', 'mongodb', 'postgresql',
    'aws', 'azure', 'gcp', 'docker', 'kubernetes', 'git',
    'agile', 'scrum', 'leadership', 'communication', 'problem solving',
    'data analysis', 'machine learning', 'api', 'rest', 'graphql',
    'cloud', 'devops', 'testing', 'linux', 'excel', 'powerbi',
]

# Common Job Categories (can be customized)
JOB_CATEGORIES = [
    'Accounting',
    'Administration',
    'Agriculture',
    'Architecture',
    'Banking & Finance',
    'Construction',
    'Customer Service',
    'Education',
    'Engineering',
    'Healthcare & Medical',
    'Hospitality & Tourism',
    'Human Resources',
    'Information Technology',
    'Legal',
    'Manufacturing',
    'Marketing & Communications',
    'Mining & Resources',
    'Real Estate',
    'Retail',
    'Sales',
    'Science & Technology',
    'Trades & Services',
    'Transport & Logistics'
]

# CSS Selectors (Updated based on actual Jora website structure)
SELECTORS = {
    'job_card': '.job-card',  # Changed: Use .job-card instead of .job-card.result for more coverage
    'job_title': '.job-link.-desktop-only, .job-link',
    'company_name': '.job-company',
    'location': '.job-location',
    'salary': '.badge.-default-badge .content',  # Filter for $ sign
    'job_type': '.badge.-default-badge .content',  # Filter for job types
    'description': '.job-abstract',
    'posted_date': '.job-listed-date',
    'next_button': 'a[rel="next"], .pagination-next, button.next-page',
    'job_link': '.job-link.-desktop-only, .job-link',
    # Additional selectors for job detail view
    'jdv_description': '.job-description-container, .job-description',
    'jdv_company': '.jdv-content .company',
    'jdv_location': '.jdv-content .location'
}

# Gemini AI Configuration
GEMINI_API_KEYS = [
    os.getenv('GEMINI_API_KEY_1', 'AIzaSyAhdu8XFz74gRfzlItUB-KndYPsYi0hZio'),  # scraping-mechine-1
    os.getenv('GEMINI_API_KEY_2', 'AIzaSyA2lVvQ3wgPHCabFJiiPezNzIVC0TLhAZ4'),  # scraping-mechine-2
    os.getenv('GEMINI_API_KEY_3', 'AIzaSyBhJUGEKcIA9HeP29wdCnI6xS82gn8hCMg'),  # scraping-mechine-3
    os.getenv('GEMINI_API_KEY_4', 'AIzaSyDxNdTxrzU2DrxCLdCO1LQ-50KEIYF0eOs'),  # scraping-mechine-4
    os.getenv('GEMINI_API_KEY_5', 'AIzaSyDVTjRTleQuSWfV2vSZWQJPSyBmJS50qkk'),  # scraping-mechine-5
    os.getenv('GEMINI_API_KEY_6', 'AIzaSyCLhGvGlV9jV-iRTzQFV3CpDY1P-iaSvfU'),  # scraping-mechine-6
]

# Filter out None values (uncommented keys only)
GEMINI_API_KEYS = [key for key in GEMINI_API_KEYS if key and key != 'YOUR_KEY_X_HERE']

# AI Analysis Settings
USE_AI_ANALYSIS = os.getenv('USE_AI_ANALYSIS', 'False').lower() == 'true'
GEMINI_MODEL = os.getenv('GEMINI_MODEL', 'gemini-2.5-flash')  # Options: gemini-2.5-flash, gemini-3-flash
AI_RATE_LIMIT_RPM = int(os.getenv('AI_RATE_LIMIT_RPM', 15))  # Requests per minute for free tier
AI_BATCH_SIZE = int(os.getenv('AI_BATCH_SIZE', 10))  # Process jobs in batches

# Contact Extraction Settings (DISABLE for faster sponsorship-focused scraping)
EXTRACT_CONTACT_INFO = os.getenv('EXTRACT_CONTACT_INFO', 'False').lower() == 'true'  # Set to False for speed

# Output columns - sesuai schema field yang diminta
DATA_FIELDS = [
    'employer_email',
    'employer_first_name',
    'employer_last_name',
    'employer_phone_number',
    'employer_company_name',
    'employer_state',
    'employer_size',
    'employer_address',
    'employer_industry',
    'employer_website_url',
    'employer_description',
    'title',
    'description',
    'level',
    'location',
    'state',
    'type',
    'source',
    'sponsorship',
    'salary_min',
    'salary_max',
    'salary_type',
    'job_skills',
]