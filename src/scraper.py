"""
Main scraper class for Jora Australia job listings
"""
import os
import time
import re
import socket
from typing import List, Dict, Any, Optional
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

from config import (
    BASE_URL, HEADLESS_MODE, IMPLICIT_WAIT, PAGE_LOAD_TIMEOUT,
    MAX_PAGES_PER_SEARCH, DELAY_BETWEEN_REQUESTS, SELECTORS, FETCH_FULL_DESCRIPTION,
    USE_AI_ANALYSIS, GEMINI_API_KEYS, GEMINI_MODEL, AI_RATE_LIMIT_RPM, EXTRACT_CONTACT_INFO,
    FULL_DESCRIPTION_TIMEOUT
)
from utils import (
    logger, wait_for_element, safe_find_element, safe_find_elements,
    clean_text, extract_salary, random_delay, get_current_timestamp,
    print_progress, adaptive_delay, detect_cloudflare, get_random_user_agent,
    normalize_state, normalize_job_type, extract_salary_parts,
    detect_job_level, extract_skills, split_contact_name, map_sponsorship,
    extract_website_from_text, extract_phone_from_text
)


class JoraScraper:
    """Scraper for Jora Australia job listings"""
    
    def __init__(self, headless: bool = HEADLESS_MODE, use_ai: bool = USE_AI_ANALYSIS):
        """Initialize the scraper with Selenium WebDriver"""
        self.driver = None
        self.headless = headless
        self.use_ai = use_ai
        self.jobs_data = []
        self.ai_analyzer = None
        self.consecutive_timeouts = 0  # Track consecutive timeouts for smart recovery
        self.max_consecutive_timeouts = 3  # Threshold before disabling full descriptions
        self.skip_full_descriptions = False  # Flag to disable full desc fetching if too many timeouts
        
        # Initialize AI analyzer if enabled
        if self.use_ai:
            try:
                from ai_analyzer import GeminiAnalyzer
                self.ai_analyzer = GeminiAnalyzer(
                    api_keys=GEMINI_API_KEYS,
                    model_name=GEMINI_MODEL,
                    rate_limit_rpm=AI_RATE_LIMIT_RPM
                )
                logger.info("AI Analyzer initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize AI Analyzer: {str(e)}")
                logger.warning("Continuing without AI analysis")
                self.use_ai = False
        
        self.setup_driver()
    
    def setup_driver(self):
        """Setup Chrome WebDriver with options"""
        try:
            chrome_options = Options()
            
            if self.headless:
                chrome_options.add_argument('--headless')
            
            # Get random User-Agent to avoid Cloudflare detection
            user_agent = get_random_user_agent()
            chrome_options.add_argument(f'--user-agent={user_agent}')
            
            # Additional options for Cloudflare bypass and stability
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--no-first-run')
            chrome_options.add_argument('--no-default-browser-check')
            chrome_options.add_experimental_option('excludeSwitches', ['enable-automation'])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            
            # Setup driver - try local driver first, then webdriver-manager
            logger.info("Setting up Chrome WebDriver...")
            
            # Check for local driver first
            local_driver_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "drivers", "chromedriver.exe")
            
            if os.path.exists(local_driver_path):
                logger.info(f"Using local Chrome driver: {local_driver_path}")
                service = Service(local_driver_path)
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
            else:
                # Fall back to webdriver-manager
                logger.info("Local driver not found, using webdriver-manager...")
                try:
                    from webdriver_manager.core.os_manager import ChromeType
                    service = Service(ChromeDriverManager(chrome_type=ChromeType.GOOGLE).install())
                    self.driver = webdriver.Chrome(service=service, options=chrome_options)
                except Exception as e:
                    logger.warning(f"ChromeDriverManager failed: {str(e)}")
                    logger.info("Trying without service (using system PATH)...")
                    self.driver = webdriver.Chrome(options=chrome_options)
            
            # Set timeouts
            self.driver.implicitly_wait(IMPLICIT_WAIT)
            self.driver.set_page_load_timeout(PAGE_LOAD_TIMEOUT)
            
            logger.info("WebDriver initialized successfully")
        except Exception as e:
            logger.error(f"Error setting up WebDriver: {str(e)}")
            logger.error("Please ensure Google Chrome is installed and up to date")
            logger.error("Try running: python fix_chrome_driver.py")
            raise
    
    def search_jobs(self, job_keyword: str = "", location: str = "", max_pages: int = MAX_PAGES_PER_SEARCH, should_cancel: Optional[callable] = None, date_filter: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Search for jobs with given parameters

        Args:
            job_keyword:  Job title or keyword to search
            location:     Location/state to search in
            max_pages:    Maximum number of pages to scrape
            should_cancel: Optional callback that returns True if scraping should stop
            date_filter:  1 = last 24 hours, None = any time

        Returns:
            List of job dictionaries
        """
        logger.info(f"Starting job search - Keyword: '{job_keyword}', Location: '{location}', date_filter={date_filter}")
        self._date_filter = date_filter  # Store for use in _build_url
        
        jobs = []
        page = 1
        cloudflare_wait_attempts = 0
        current_page_url = None  # Track current page URL for recovery
        
        try:
            while page <= max_pages:
                # Check for cancellation
                if should_cancel and should_cancel():
                    logger.info(f"[CANCEL] Jora scraping stopped by user at page {page}")
                    break

                logger.info(f"📄 Scraping page {page}/{max_pages}")

                
                # Build and navigate to URL
                url = self._build_url(job_keyword, location, page)
                current_page_url = url  # Store URL for recovery
                logger.info(f"🔗 Navigating to: {url}")
                self.driver.get(url)
                
                # Use adaptive delay to avoid Cloudflare throttling
                adaptive_delay(page, DELAY_BETWEEN_REQUESTS)
                
                # Check for Cloudflare and wait if needed
                page_source = self.driver.page_source
                if detect_cloudflare(page_source):
                    cloudflare_wait_attempts += 1
                    wait_time = min(60, 10 + (cloudflare_wait_attempts * 5))  # Progressive wait: 10s, 15s, 20s...
                    logger.warning(f"⏳ Cloudflare challenge detected (attempt {cloudflare_wait_attempts}), waiting {wait_time}s...")
                    time.sleep(wait_time)
                    
                    # Refresh page after waiting
                    try:
                        self.driver.refresh()
                        adaptive_delay(page, DELAY_BETWEEN_REQUESTS)
                    except Exception as e:
                        logger.warning(f"Could not refresh after Cloudflare wait: {e}")
                else:
                    cloudflare_wait_attempts = 0  # Reset counter on successful page load
                
                # Extract jobs from current page
                page_jobs = self._extract_jobs_from_page()
                
                # If this page had no jobs but next page exists, don't stop - try next page
                # Empty pages could be temporary issues or page layout issues
                if not page_jobs:
                    logger.warning(f"⚠️  No jobs found on page {page} - checking if next page exists...")
                    # Don't break yet - continue to pagination check below
                else:
                    jobs.extend(page_jobs)
                    logger.info(f"Extracted {len(page_jobs)} jobs from page {page}")
                
                # Check if there's a next page (with smart recovery using saved URL)
                max_retries = 1  # Reduce from 3 - retrying on dead browser doesn't help
                retry_count = 0
                has_next = False
                recovery_after_timeout = False
                
                while retry_count < max_retries:
                    try:
                        has_next = self._has_next_page()
                        break  # Success, exit retry loop
                    except TimeoutException as e:
                        retry_count += 1
                        logger.warning(f"⏱️  Browser timeout checking pagination (attempt {retry_count}/{max_retries}): {str(e)}")
                        
                        if retry_count < max_retries and not recovery_after_timeout:
                            # First timeout: try recovery - return to saved page URL and retry
                            recovery_after_timeout = True
                            try:
                                logger.info(f"🔄 Recovery: returning to page {page} URL...")
                                if current_page_url:
                                    self.driver.get(current_page_url)  # Return to saved page URL
                                    time.sleep(3)
                                    logger.info("✓ Returned to page, retrying pagination check...")
                                else:
                                    logger.warning("No saved URL to recover to")
                            except Exception as recovery_err:
                                logger.error(f"Recovery failed: {recovery_err}")
                                has_next = False
                                break
                        else:
                            # No more recovery attempts - stop pagination gracefully
                            logger.error(f"Browser unresponsive, stopping pagination at page {page}")
                            logger.info(f"✓ Successfully scraped {len(jobs)} jobs before timeout")
                            has_next = False
                            break
                    except Exception as e:
                        logger.error(f"Error checking for next page: {str(e)}")
                        # Try recovery with saved URL
                        try:
                            logger.info(f"🔄 Recovery: returning to page {page} URL...")
                            if current_page_url:
                                self.driver.get(current_page_url)
                                time.sleep(2)
                                has_next = self._has_next_page()
                            else:
                                has_next = False
                        except:
                            has_next = False
                        break
                
                if not has_next:
                    logger.info("✓ No more pages available")
                    break
                
                page += 1
                adaptive_delay(page, DELAY_BETWEEN_REQUESTS)  # Progressive delay for pagination
            
            logger.info(f"Total jobs scraped: {len(jobs)}")
            
            # Apply AI analysis if enabled
            if self.use_ai and self.ai_analyzer and jobs:
                logger.info("Starting AI analysis for scraped jobs...")
                jobs = self.ai_analyzer.analyze_batch(jobs)
                logger.info("AI analysis completed")
            
            self.jobs_data.extend(jobs)
            return jobs
            
        except Exception as e:
            logger.error(f"Error during job search: {str(e)}")
            return jobs
    
    def _build_url(self, job_keyword: str, location: str, page: int) -> str:
        """Build search URL based on actual Jora URL structure"""
        # Format: https://au.jora.com/j?q=keyword&l=location&p=page&tf=1
        url = f"{BASE_URL}/j"

        params = []
        if job_keyword:
            params.append(f"q={job_keyword.replace(' ', '+')}")
        if location:
            params.append(f"l={location.replace(' ', '+')}")
        if page > 1:
            params.append(f"p={page}")
        # Date filter: tf=1 = last 24 hours on Jora
        if getattr(self, '_date_filter', None) == 1:
            params.append("tf=1")

        if params:
            url += "?" + "&".join(params)

        return url
    
    def _extract_jobs_from_page(self) -> List[Dict[str, Any]]:
        """Extract all jobs from current page with retry mechanism
        
        For each job:
        1. Try to extract it
        2. If fails, reload page and retry ONCE
        3. If still fails, skip and move to next job
        4. After all jobs, check for next page
        """
        jobs = []
        failed_jobs = set()  # Track indices of jobs that failed after retry
        
        try:
            # Wait for job listings to load
            time.sleep(2)
            
            # ── ATTEMPT TO FIND JOB CARDS (with retry) ──
            job_cards = None
            max_card_retries = 2
            card_retry_count = 0
            
            while card_retry_count < max_card_retries and not job_cards:
                # Get page source and parse with BeautifulSoup
                soup = BeautifulSoup(self.driver.page_source, 'lxml')
                
                # Try multiple selectors to find job cards
                for selector in SELECTORS['job_card'].split(', '):
                    job_cards = soup.select(selector)
                    if job_cards:
                        logger.info(f"Found {len(job_cards)} job cards using selector: {selector}")
                        break
                
                # If no cards found, try reloading page
                if not job_cards:
                    if card_retry_count == 0:
                        logger.warning(f"No job cards found on page - attempting reload (attempt {card_retry_count + 1}/{max_card_retries})")
                        self.driver.refresh()
                        time.sleep(3)  # Wait longer for page to reload
                    else:
                        logger.error(f"Still no job cards after reload - giving up on this page")
                    
                    card_retry_count += 1
            
            if not job_cards:
                logger.warning("❌ Could not find any job cards on this page after retries - likely page is empty or broken")
                return jobs
            
            logger.info(f"✓ Found job cards - proceeding with extraction")
            
            # Extract data from each job card with retry logic
            for idx, card in enumerate(job_cards):
                # Skip if already failed retry
                if idx in failed_jobs:
                    logger.debug(f"Skipping job {idx} - already failed retry")
                    continue
                
                success = False
                
                # ─── FIRST ATTEMPT ───
                try:
                    job_data = self._extract_job_data(card)
                    if job_data:
                        jobs.append(job_data)
                        logger.debug(f"✓ Successfully extracted job {idx}")
                        success = True
                
                except Exception as first_err:
                    logger.warning(f"✗ First attempt failed for job {idx}: {str(first_err)[:80]}")
                    
                    # ─── RETRY: Reload page and try again ───
                    try:
                        logger.info(f"📄 Reloading page to retry job {idx}...")
                        self.driver.refresh()
                        time.sleep(2)
                        
                        # Get fresh soup and cards
                        soup_retry = BeautifulSoup(self.driver.page_source, 'lxml')
                        job_cards_retry = None
                        for selector in SELECTORS['job_card'].split(', '):
                            job_cards_retry = soup_retry.select(selector)
                            if job_cards_retry and len(job_cards_retry) > idx:
                                break
                        
                        # Try to extract same job index again
                        if job_cards_retry and len(job_cards_retry) > idx:
                            card_retry = job_cards_retry[idx]
                            job_data_retry = self._extract_job_data(card_retry)
                            if job_data_retry:
                                jobs.append(job_data_retry)
                                logger.info(f"✓ RETRY succeeded for job {idx}")
                                success = True
                            else:
                                logger.warning(f"✗ Retry returned no data for job {idx}")
                        else:
                            logger.warning(f"✗ Could not find job {idx} after page reload")
                    
                    except Exception as retry_err:
                        logger.error(f"✗ Retry also failed for job {idx}: {str(retry_err)[:80]}")
                
                # Mark as failed if both attempts failed
                if not success:
                    failed_jobs.add(idx)
                    logger.error(f"⚠️  SKIPPING job {idx} - failed twice, moving to next job")
            
            logger.info(f"📊 Page complete: {len(jobs)} scraped, {len(failed_jobs)} skipped")
            return jobs
            
        except Exception as e:
            logger.error(f"Error extracting jobs from page: {str(e)}")
            return jobs
    
    def _extract_job_data(self, job_card) -> Optional[Dict[str, Any]]:
        """Extract data from a single job card and map to output schema"""
        try:
            # ---- Raw extraction (unchanged selectors) ----
            title = 'N/A'
            title_elem = job_card.select_one('.job-link.-desktop-only') or job_card.select_one('.job-link')
            if title_elem:
                title = clean_text(title_elem.get_text())

            company_name = 'N/A'
            company_elem = job_card.select_one('.job-company')
            if company_elem:
                company_name = clean_text(company_elem.get_text())

            location_raw = 'N/A'
            location_elem = job_card.select_one('.job-location')
            if location_elem:
                location_raw = clean_text(location_elem.get_text())

            salary_raw = 'N/A'
            job_type_raw = 'N/A'
            badge_elements = job_card.select('.badge.-default-badge .content, .badge .content')
            for badge in badge_elements:
                badge_text = clean_text(badge.get_text())
                if badge_text and badge_text != 'N/A':
                    if '$' in badge_text:
                        salary_raw = badge_text
                    elif any(kw in badge_text.lower() for kw in ['full time', 'part time', 'contract', 'casual', 'permanent', 'temporary', 'freelance']):
                        job_type_raw = badge_text

            job_url = 'N/A'
            link_elem = job_card.select_one('.job-link.-desktop-only') or job_card.select_one('.job-link')
            if link_elem and link_elem.get('href'):
                href = link_elem.get('href')
                job_url = BASE_URL + href if href.startswith('/') else href

            description = 'N/A'
            contact_name_raw = None
            phone_number_raw = None
            company_email_raw = None
            apply_url = None
            sponsorship_signal = None

            # ---- Fetch detail page (if enabled) ----
            # Skip full description if too many timeouts have occurred (smart fallback)
            if FETCH_FULL_DESCRIPTION and not self.skip_full_descriptions and job_url != 'N/A':
                try:
                    logger.info(f"Fetching full description for: {title} (timeout count: {self.consecutive_timeouts})")
                    full_desc, apply_method, apply_url_ret, company_contacts = self._get_full_description(job_url)
                    apply_url = apply_url_ret

                    if full_desc and full_desc != 'N/A':
                        description = full_desc
                        self.consecutive_timeouts = 0  # Reset on success
                    else:
                        desc_elem = job_card.select_one('.job-abstract')
                        if desc_elem:
                            description = clean_text(desc_elem.get_text())

                    if company_contacts:
                        contact_name_raw = company_contacts.get('contact_name')
                        phone_number_raw = company_contacts.get('phone_number')
                        company_email_raw = company_contacts.get('company_email')

                    if not contact_name_raw and not phone_number_raw and not company_email_raw:
                        logger.debug(f"No contact info found for: {company_name}")

                except TimeoutException as e:
                    # Increment timeout counter but don't disable full descriptions permanently
                    self.consecutive_timeouts += 1
                    logger.warning(f"Timeout fetching full description ({self.consecutive_timeouts}/{self.max_consecutive_timeouts}): {str(e)}")
                    
                    # Just use abstract description and continue immediately
                    desc_elem = job_card.select_one('.job-abstract')
                    if desc_elem:
                        description = clean_text(desc_elem.get_text())
                    
                    # If too many timeouts in a row, inform user but DON'T disable or restart browser
                    if self.consecutive_timeouts >= self.max_consecutive_timeouts:
                        logger.error(f"⚠️ Frequent timeouts ({self.consecutive_timeouts}) detected. Jora pages loading very slowly. Continuing without full descriptions...")
                        
                except Exception as e:
                    logger.warning(f"Could not fetch full description: {str(e)}")
                    self.consecutive_timeouts += 1
                    desc_elem = job_card.select_one('.job-abstract')
                    if desc_elem:
                        description = clean_text(desc_elem.get_text())
            else:
                if self.skip_full_descriptions:
                    logger.debug(f"Skipping full description for {title} (disabled due to timeouts)")
                desc_elem = job_card.select_one('.job-abstract')
                if desc_elem:
                    description = clean_text(desc_elem.get_text())

            # Fallback: extract phone from description text if not found from company site
            if not phone_number_raw and description and description != 'N/A':
                phone_number_raw = extract_phone_from_text(description)
                if phone_number_raw:
                    logger.debug(f"Phone found in description: {phone_number_raw}")

            # Apply AI sponsorship if enabled
            if self.use_ai:
                sponsorship_signal = 'unknown'  # will be overridden by ai_analyzer later

            # ---- Transform / Map to schema ----
            state_enum = normalize_state(location_raw)
            job_type_enum = normalize_job_type(job_type_raw)
            salary_min, salary_max, salary_type = extract_salary_parts(salary_raw)
            level = detect_job_level(title, description)
            job_skills = extract_skills(description)
            first_name, last_name = split_contact_name(contact_name_raw)
            sponsorship_int = map_sponsorship(sponsorship_signal, description)
            # Extract employer website URL from description text
            employer_website = extract_website_from_text(description)

            job_data = {
                'employer_email':       company_email_raw or None,
                'employer_first_name':  first_name,
                'employer_last_name':   last_name,
                'employer_phone_number': phone_number_raw or None,
                'employer_company_name': company_name if company_name != 'N/A' else None,
                'employer_state':       state_enum,
                'employer_size':        None,
                'employer_address':     location_raw if location_raw != 'N/A' else None,
                'employer_industry':    None,
                'employer_website_url': employer_website,
                'employer_description': None,
                'title':                title if title != 'N/A' else None,
                'description':          description if description != 'N/A' else None,
                'level':                level,
                'location':             location_raw if location_raw != 'N/A' else None,
                'state':                state_enum,
                'type':                 job_type_enum,
                'source':               job_url if job_url != 'N/A' else None,
                'sponsorship':          sponsorship_int,
                'salary_min':           salary_min,
                'salary_max':           salary_max,
                'salary_type':          salary_type,
                'job_skills':           job_skills,
                'scraping_timestamp':   get_current_timestamp(),
            }

            return job_data

        except Exception as e:
            logger.error(f"Error extracting job data: {str(e)}")
            logger.debug(f"Exception type: {type(e).__name__}")
            return None
    
    def _extract_state(self, location: str) -> str:
        """Extract Australian state from location string"""
        if not location or location == "N/A":
            return "N/A"
        
        location_upper = location.upper()
        
        # State abbreviations
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
        
        # Check for abbreviations
        for abbr, full_name in state_map.items():
            if re.search(rf"\b{abbr}\b", location_upper):
                return full_name
        
        # Check for full state names
        for full_name in state_map.values():
            if full_name.upper() in location_upper:
                return full_name
        
        return "N/A"
    
    def _get_full_description(self, job_url: str, search_url: str = None) -> tuple:
        """
        Get full job description and application method from individual job page
        
        Args:
            job_url: URL of the job posting
            search_url: URL of the search results page to return to
            
        Returns:
            Tuple of (description_text, apply_form_text, apply_url, contact_info_dict)
        """
        try:
            # Save current URL if not provided
            if not search_url:
                search_url = self.driver.current_url
            
            # Use configurable timeout for individual job pages (Jora pages load slowly)
            original_timeout = self.driver.timeouts.page_load
            self.driver.set_page_load_timeout(FULL_DESCRIPTION_TIMEOUT)
            
            max_retries = 1
            for attempt in range(max_retries + 1):
                try:
                    # Navigate to job detail page with exception handling
                    self.driver.get(job_url)
                    break  # Success, exit retry loop
                except TimeoutException:
                    if attempt < max_retries:
                        # Retry once before giving up
                        logger.info(f"Page load timeout (attempt {attempt + 1}/{max_retries + 1}), retrying: {job_url}")
                        time.sleep(2)  # Brief wait before retry
                        continue
                    else:
                        # Final attempt failed - reset and raise
                        logger.warning(f"Job detail page took >{FULL_DESCRIPTION_TIMEOUT}s to load after retries, skipping: {job_url}")
                        self.driver.set_page_load_timeout(original_timeout)
                        raise
            
            # Reset to original timeout
            self.driver.set_page_load_timeout(original_timeout)
            time.sleep(1)  # Wait for page content to render
            
            # Parse with BeautifulSoup
            soup = BeautifulSoup(self.driver.page_source, 'lxml')
            
            # Try multiple selectors for job description
            # Priority order based on browser inspection findings
            description_selectors = [
                '.job-description-container',  # Primary - contains full description
                '#job-description-container',  # Alternative ID version
                '.job-description',
                '.jdv-content .job-description',
                'div[class*="description"]',
                'div[class*="job-detail"]'
            ]
            
            full_text = "N/A"
            for selector in description_selectors:
                desc_elem = soup.select_one(selector)
                if desc_elem:
                    # Get ALL text - use get_text with separator to preserve structure
                    # DO NOT use clean_text() as it collapses all whitespace
                    raw_text = desc_elem.get_text(separator='\n', strip=True)
                    # Only remove excessive blank lines
                    full_text = '\n'.join(line.strip() for line in raw_text.split('\n') if line.strip())
                    
                    if full_text and len(full_text) > 50:  # Make sure it's substantial
                        logger.info(f"Fetched full description ({len(full_text)} chars) using selector: {selector}")
                        break
                    else:
                        full_text = "N/A"
            
            # Extract application method/form and URL
            apply_form = "N/A"
            apply_url = None
            
            # Look for apply button with URL - Jora uses data attributes
            # First, try to find the actual apply link from data attributes
            apply_data_selectors = [
                'a[data-bubble-job-apply]',
                'button[data-bubble-job-apply]',
                'div[data-bubble-job-apply]',
                '[data-analytics-apply-pressed]'
            ]
            
            for selector in apply_data_selectors:
                apply_elem = soup.select_one(selector)
                if apply_elem:
                    # Get the apply URL from data attribute or properties
                    if apply_elem.get('data-bubble-job-apply'):
                        # Extract the job ID or path from the data attribute
                        data_attr = apply_elem.get('data-bubble-job-apply')
                        # The data attribute might contain JSON with job info
                        try:
                            import json
                            data_json = json.loads(data_attr)
                            if 'jobId' in data_json:
                                apply_url = f"{BASE_URL}/job/rd/{data_json['jobId']}"
                        except:
                            pass
                    
                    # Also check for href in nested elements
                    if not apply_url:
                        nested_link = apply_elem.find('a', href=True)
                        if nested_link:
                            apply_url = nested_link.get('href')
                    
                    # Get button text for apply_form
                    button_text = clean_text(apply_elem.get_text())
                    if button_text and len(button_text) > 0:
                        apply_form = button_text
                    
                    if apply_url:
                        # Make absolute URL if relative
                        if not apply_url.startswith('http'):
                            from urllib.parse import urljoin
                            apply_url = urljoin(BASE_URL, apply_url)
                        logger.info(f"Found apply method: {apply_form}")
                        logger.info(f"Found apply URL: {apply_url}")
                        break
            
            # Fallback: Look for any link with "apply" in href
            if not apply_url:
                apply_links = soup.select('a[href*="apply"], a[href*="job/rd"]')
                for link in apply_links:
                    href = link.get('href')
                    if href and ('/job/rd/' in href or 'apply' in href.lower()):
                        apply_url = href
                        if not apply_url.startswith('http'):
                            from urllib.parse import urljoin
                            apply_url = urljoin(BASE_URL, apply_url)
                        
                        # Get the button/link text
                        link_text = clean_text(link.get_text())
                        if link_text:
                            apply_form = link_text
                        logger.info(f"Found apply URL (fallback): {apply_url}")
                        break
            
            # If still no apply_form text, check for common patterns
            if apply_form == "N/A":
                # Check page source for common patterns
                if 'company site' in self.driver.page_source.lower():
                    apply_form = "Apply on company site"
                elif 'quick apply' in self.driver.page_source.lower():
                    apply_form = "Quick apply"
                elif 'email' in self.driver.page_source.lower() and 'application' in self.driver.page_source.lower():
                    apply_form = "Email application"
                elif 'online application' in self.driver.page_source.lower():
                    apply_form = "Online application"
            
            # Extract contact info from company site if apply_url is available AND enabled
            contact_info = {'contact_name': None, 'phone_number': None, 'company_email': None}
            
            # Only extract contact info if enabled (disabled by default for faster sponsorship analysis)
            if EXTRACT_CONTACT_INFO and apply_url and apply_url.startswith('http'):
                logger.info(f"Attempting to extract contact info from company site: {apply_url}")
                company_contact_info = self._extract_from_company_site(apply_url)
                if company_contact_info:
                    contact_info.update(company_contact_info)
            elif not EXTRACT_CONTACT_INFO:
                logger.debug("Contact extraction disabled - focusing on sponsorship analysis for speed")
            
            # Return to search results page
            self.driver.get(search_url)
            time.sleep(1)  # Wait for page to load
            
            if full_text == "N/A":
                logger.warning(f"Could not find full description for {job_url}")
            
            return full_text, apply_form, apply_url, contact_info
            
        except (socket.error, socket.timeout, ConnectionResetError) as conn_err:
            # Connection error - log specifically and gracefully fallback
            logger.warning(f"Connection error fetching job details from {job_url}: {type(conn_err).__name__} - Falling back to basic info")
            # Try to return to search results
            if search_url:
                try:
                    self.driver.get(search_url)
                    time.sleep(1)
                except:
                    pass
            return "N/A", "N/A", None, {'contact_name': None, 'phone_number': None, 'company_email': None}
            
        except TimeoutException as timeout_err:
            # Timeout error - log and fallback
            logger.warning(f"Timeout fetching job details from {job_url} - Falling back to basic info")
            # Try to return to search results
            if search_url:
                try:
                    self.driver.get(search_url)
                    time.sleep(1)
                except:
                    pass
            return "N/A", "N/A", None, {'contact_name': None, 'phone_number': None, 'company_email': None}
            
        except Exception as e:
            # Generic error - log and fallback
            logger.error(f"Unexpected error fetching job details from {job_url}: {str(e)}")
            # Try to return to search results
            if search_url:
                try:
                    self.driver.get(search_url)
                    time.sleep(1)
                except:
                    pass
            return "N/A", "N/A", None, {'contact_name': None, 'phone_number': None, 'company_email': None}
    
    def _extract_from_company_site(self, company_url: str) -> Dict[str, Optional[str]]:
        """
        Extract contact information from company application page
        
        Args:
            company_url: URL of the company application page
            
        Returns:
            Dictionary with contact_name, phone_number, company_email
        """
        contact_info = {'contact_name': None, 'phone_number': None, 'company_email': None}
        
        try:
            # Save current URL to return later
            current_url = self.driver.current_url
            
            # Navigate to company site
            logger.info(f"Visiting company site for contact info: {company_url}")
            self.driver.get(company_url)
            time.sleep(3)  # Wait for page to load
            
            # Get page source
            page_source = self.driver.page_source
            soup = BeautifulSoup(page_source, 'lxml')
            page_text = soup.get_text()
            
            # Extract phone numbers (Australian formats - uncensored)
            import re
            phone_patterns = [
                r'\b0[2-9]\d{8}\b',  # 0X XXXXXXXX (10 digits)
                r'\b\+61\s?[2-9]\s?\d{4}\s?\d{4}\b',  # +61 X XXXX XXXX
                r'\(\d{2}\)\s?\d{4}\s?\d{4}',  # (XX) XXXX XXXX
            ]
            
            for pattern in phone_patterns:
                matches = re.findall(pattern, page_text)
                if matches:
                    # Filter out censored numbers (containing *)
                    uncensored = [m for m in matches if '*' not in m]
                    if uncensored:
                        contact_info['phone_number'] = uncensored[0]
                        logger.info(f"[OK] Found uncensored phone: {contact_info['phone_number']}")
                        break
            
            # Extract email addresses
            email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            emails = re.findall(email_pattern, page_text)
            if emails:
                # Filter out common non-contact emails
                filtered_emails = [e for e in emails if not any(x in e.lower() for x in ['noreply', 'no-reply', 'donotreply'])]
                if filtered_emails:
                    contact_info['company_email'] = filtered_emails[0]
                    logger.info(f"[OK] Found email: {contact_info['company_email']}")
            
            # Extract contact names (look for common patterns)
            name_patterns = [
                r'contact\s+([A-Z][a-z]+\s+[A-Z][a-z]+)',  # "contact John Smith"
                r'Contact:\s*([A-Z][a-z]+\s+[A-Z][a-z]+)',  # "Contact: John Smith"
                r'inquiries.*?contact\s+([A-Z][a-z]+\s+[A-Z][a-z]+)',  # "For inquiries contact John Smith"
            ]
            
            for pattern in name_patterns:
                match = re.search(pattern, page_text, re.IGNORECASE)
                if match:
                    contact_info['contact_name'] = match.group(1)
                    logger.info(f"[OK] Found contact name: {contact_info['contact_name']}")
                    break
            
            # Return to previous page
            self.driver.get(current_url)
            time.sleep(1)
            
            return contact_info
            
        except Exception as e:
            logger.error(f"Error searching Google for company contacts: {str(e)}")
            try:
                # Try to return to previous page
                self.driver.get(current_url)
            except:
                pass
            return contact_info
    
    def _has_next_page(self) -> bool:
        """Check if there's a next page available"""
        try:
            # ---- QUICK CHECK FIRST (without scroll) ----
            try:
                # Jora uses .next-page-button for pagination
                next_button = self.driver.find_elements(By.CSS_SELECTOR, '.next-page-button')
                if next_button:
                    logger.info("Next page button found (quick check)")
                    return True
                
                # Alternative: check for page number display (e.g., "Page 1 of 34")
                page_number_elem = self.driver.find_elements(By.CSS_SELECTOR, '.search-results-page-number')
                if page_number_elem:
                    page_text = page_number_elem[0].text
                    if 'of' in page_text.lower():
                        parts = page_text.lower().replace('page', '').strip().split('of')
                        if len(parts) == 2:
                            try:
                                current_page = int(parts[0].strip())
                                total_pages = int(parts[1].strip())
                                has_more = current_page < total_pages
                                logger.info(f"Page {current_page} of {total_pages} - Has more: {has_more}")
                                return has_more
                            except:
                                pass
            except TimeoutException:
                logger.debug(f"Quick check timed out, will skip pagination")
                raise
            except Exception as quick_check_err:
                logger.debug(f"Quick check failed: {quick_check_err}")
            
            # ---- SCROLL-BASED CHECK (if quick check didn't work) ----
            logger.debug("Attempting scroll-based pagination check...")
            try:
                # Use MUCH shorter timeout for script execution (5s instead of 60s)
                self.driver.set_script_timeout(5)
                scroll_script = """
                var serpContent = document.querySelector('.serp-content');
                if (serpContent) {
                    serpContent.scrollTo(0, serpContent.scrollHeight);
                } else {
                    window.scrollTo(0, document.body.scrollHeight);
                }
                """
                self.driver.execute_script(scroll_script)
                self.driver.set_script_timeout(60)  # Reset
            except TimeoutException:
                # Timeout on scroll = browser is unresponsive - don't retry
                logger.warning("Timeout executing scroll script - browser appears unresponsive")
                self.driver.set_script_timeout(60)  # Reset timeout
                raise  # Re-raise to let caller know browser is stuck
            except Exception as script_err:
                logger.debug(f"Scroll script failed, resetting: {script_err}")
                self.driver.set_script_timeout(60)  # Reset
            
            time.sleep(1)  # Wait for any dynamic content to load
            
            # Check again after scroll (with short timeout)
            try:
                next_button = self.driver.find_elements(By.CSS_SELECTOR, '.next-page-button')
                if next_button:
                    logger.info("Next page button found (after scroll)")
                    return True
            except TimeoutException:
                logger.debug("Element check timed out after scroll")
                raise
            
            logger.info("No next page found")
            return False
        except TimeoutException as e:
            logger.error(f"Pagination check timeout: {str(e)}")
            raise  # Re-raise to let caller handle it
        except Exception as e:
            logger.error(f"Error checking for next page: {str(e)}")
            return False
    
    def get_job_details(self, job_url: str) -> Dict[str, Any]:
        """
        Get detailed information from individual job page
        
        Args:
            job_url: URL of the job posting
            
        Returns:
            Dictionary with detailed job information
        """
        try:
            self.driver.get(job_url)
            time.sleep(2)
            
            # Extract detailed information
            # This would need to be customized based on Jora's job detail page structure
            details = {
                'full_description': 'N/A',
                'requirements': 'N/A',
                'benefits': 'N/A'
            }
            
            # Add extraction logic here based on actual page structure
            
            return details
            
        except Exception as e:
            logger.error(f"Error getting job details from {job_url}: {str(e)}")
            return {}
    
    def close(self):
        """Close the WebDriver"""
        if self.driver:
            self.driver.quit()
            logger.info("WebDriver closed")
