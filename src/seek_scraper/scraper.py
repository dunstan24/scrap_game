"""
Main Scraper for Seek.com.au Job Listings
Menggunakan Playwright (sync) + playwright-stealth untuk bypass bot detection.
"""

import logging
import time
import random
from typing import List, Optional, Dict, Any
from pathlib import Path
from datetime import datetime
import csv

from playwright.sync_api import sync_playwright, Browser, BrowserContext, Page, TimeoutError as PlaywrightTimeout
from playwright_stealth import Stealth
from bs4 import BeautifulSoup

from .config import SeekScraperConfig, AustralianState
from .utils import (
    setup_logger,
    parse_job_data,
    generate_output_path,
    ensure_output_directory,
    clean_text,
    extract_salary_type_from_text
)


class SeekScraper:
    """Main scraper class for Seek.com.au"""
    
    def __init__(self, use_ai: bool = False):
        """
        Initialize Seek Scraper (Playwright + stealth)
        """
        self.keyword     = None
        self.states      = []
        self.page_limit  = 1
        self.date_filter = None   # None=any time, 1=today, 3/7/14/30=last N days
        self.use_ai      = use_ai
        self.logger      = setup_logger("SeekScraper")
        self.jobs_data   = []

        # Playwright instances
        self._playwright: Optional[Any] = None
        self.browser:     Optional[Browser]        = None
        self.context:     Optional[BrowserContext]  = None
        self.page:        Optional[Page]            = None   # satu-satunya tab
        self.output_path: Optional[Path]            = None
    
    def _setup_driver(self) -> None:
        """Launch Playwright browser dengan stealth patches."""
        self.logger.info("Setting up Playwright (Chromium + stealth)...")

        self._playwright = sync_playwright().start()
        self.browser = self._playwright.chromium.launch(
            headless=SeekScraperConfig.HEADLESS_MODE,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-extensions",
            ]
        )
        self.context = self.browser.new_context(
            user_agent=SeekScraperConfig.USER_AGENT,
            viewport={"width": 1920, "height": 1080},
            locale="en-AU",
            timezone_id="Australia/Sydney",
            extra_http_headers={
                "Accept-Language": "en-AU,en;q=0.9",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            },
        )
        # Hanya 1 tab — listing DAN detail pakai tab yang sama
        # (2 tab = lebih bot-like; 1 tab = natural seperti manusia browse)
        self.page = self.context.new_page()
        Stealth().apply_stealth_sync(self.page)

        self.logger.info("[OK] Playwright + stealth initialized (1 tab)")

    def _close_driver(self) -> None:
        """Close Playwright browser."""
        try:
            if self.context:
                self.context.close()
            if self.browser:
                self.browser.close()
            if self._playwright:
                self._playwright.stop()
            self.logger.info("[OK] Playwright browser closed")
        except Exception as e:
            self.logger.debug(f"Error closing browser: {e}")
    
    def _build_search_url(self, keyword: str, state: str, page: int) -> str:
        """
        Build Seek search URL dengan optional date filter.

        Args:
            keyword: Search keyword
            state:   Australian state (full name, e.g. 'New South Wales')
            page:    Page number (1-indexed)

        Returns:
            Search URL string
        """
        from urllib.parse import quote_plus
        encoded_keyword = quote_plus(keyword)
        encoded_state   = quote_plus(state)
        params = f"keywords={encoded_keyword}&where={encoded_state}"
        if page > 1:
            params += f"&page={page}"
        # Date filter — Seek parameter: dateRange=1 (today), 3, 7, 14, 30
        if self.date_filter and self.date_filter in (1, 3, 7, 14, 30):
            params += f"&dateRange={self.date_filter}"
        url = f"{SeekScraperConfig.SEARCH_URL}?{params}"
        self.logger.debug(f"[URL] {url}")
        return url
    
    def _parse_job_listings(self, html_content: str, state: str, source_url: str) -> List[Dict[str, Any]]:
        """
        Parse job listings from HTML
        
        Args:
            html_content: HTML content
            state: State for the jobs
            source_url: Source URL
            
        Returns:
            List of job dictionaries
        """
        jobs = []
        
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Find all job listings - adjust selectors based on Seek's structure
            job_listings = soup.find_all('article', {'data-card-type': 'JobCard'})
            
            self.logger.debug(f"Found {len(job_listings)} job listings")
            
            for idx, job_card in enumerate(job_listings, 1):
                try:
                    # Extract job information
                    job_info = self._extract_job_info(job_card, state, source_url)
                    
                    if job_info:
                        jobs.append(job_info)
                        self.logger.debug(f"  [OK] Parsed job {idx}: {job_info.get('title', 'N/A')}")
                    
                except Exception as e:
                    self.logger.debug(f"  ✗ Error parsing job {idx}: {str(e)}")
                    continue
            
        except Exception as e:
            self.logger.error(f"Error parsing job listings: {str(e)}")
        
        return jobs
    
    def _extract_job_info(self, job_card, state: str, source_url: str) -> Optional[Dict[str, Any]]:
        """
        Extract individual job information
        
        Args:
            job_card: BeautifulSoup job card element
            state: State for the job
            source_url: Source URL
            
        Returns:
            Job information dictionary or None
        """
        try:
            # Job title (fixed selector for current Seek structure)
            title_element = job_card.find('a', {'data-testid': 'job-card-title'})
            title = clean_text(title_element.get_text(strip=True)) if title_element else ""
            
            if not title:
                return None
            
            # Job link/source
            job_link = title_element.get('href', '') if title_element else ""
            full_source = f"{SeekScraperConfig.BASE_URL}{job_link}" if job_link and not job_link.startswith('http') else job_link
            
            # ── Company name extraction (card) ──────────────────────────
            company_name = ""

            # Selector 1: a[data-automation="jobCompany"] — paling reliable di Seek
            elem = job_card.find('a', {'data-automation': 'jobCompany'})
            if elem:
                company_name = clean_text(elem.get_text(strip=True))

            # Selector 2: span[data-automation="jobCompany"]
            if not company_name:
                elem = job_card.find('span', {'data-automation': 'jobCompany'})
                if elem:
                    company_name = clean_text(elem.get_text(strip=True))

            # Selector 3: data-testid="advertiser-name"
            if not company_name:
                elem = job_card.find(attrs={'data-testid': 'advertiser-name'})
                if elem:
                    company_name = clean_text(elem.get_text(strip=True))

            # Selector 4: data-automation="advertiserName"
            if not company_name:
                elem = job_card.find(attrs={'data-automation': 'advertiserName'})
                if elem:
                    company_name = clean_text(elem.get_text(strip=True))

            # Selector 5: link ke halaman company (/companies/...)
            if not company_name:
                for link in job_card.find_all('a', href=True):
                    href = link.get('href', '')
                    text = link.get_text(strip=True)
                    if '/companies/' in href and text and len(text) > 2:
                        company_name = clean_text(text)
                        break

            # Selector 6 (lama): link href ending dengan '-jobs' — fallback
            if not company_name:
                for link in job_card.find_all('a', href=True):
                    href = link.get('href', '')
                    text = link.get_text(strip=True)
                    if href.endswith('-jobs') and text and len(text) > 2:
                        company_name = clean_text(text)
                        break

            # Selector 7: span[data-automation="advertiser-name"]
            if not company_name:
                elem = job_card.find('span', {'data-automation': 'advertiser-name'})
                if elem:
                    company_name = clean_text(elem.get_text(strip=True))

            # Simpan sumber link untuk dipakai nanti
            all_links = job_card.find_all('a')

            # Location - Look for span with data-automation="jobCardLocation"
            location = ""
            location_element = job_card.find('span', {'data-automation': 'jobCardLocation'})
            if location_element:
                location_text = location_element.get_text(strip=True)
                # Clean up the text (remove leading/trailing commas and spaces)
                location = clean_text(location_text).lstrip(', ').rstrip(', ')
            
            # Fallback: if location not found, try to find links pointing to location pages
            if not location:
                all_links = job_card.find_all('a')
                for link in all_links:
                    href = link.get('href', '')
                    link_text = link.get_text(strip=True)
                    # Location links typically have href patterns like "/python-jobs/in-Sydney-NSW"
                    if '/jobs/in-' in href and link_text and len(link_text) > 2:
                        location = clean_text(link_text)
                        break
            
            # Salary: Only extract from detail page (job-salary-detail)
            salary = ""
            salary_min = None
            salary_max = None
            salary_type = None
            
            # Job classification (type) - try multiple selectors
            classification = "full_time"
            classification_selectors = [
                ('span', {'data-testid': 'job-classification'}),
                ('span', {'data-testid': 'job-type'}),
            ]
            
            for tag, attrs in classification_selectors:
                classification_element = job_card.find(tag, attrs)
                if classification_element:
                    class_text = classification_element.get_text(strip=True)
                    if class_text:
                        classification = clean_text(class_text)
                        break
            
            # Description preview - try multiple selectors
            description = ""
            description_selectors = [
                ('div', {'data-testid': 'job-summary'}),
                ('span', {'data-testid': 'job-card-teaser'}),
                ('span', {'data-testid': 'job-teaser'}),
            ]
            
            for tag, attrs in description_selectors:
                description_element = job_card.find(tag, attrs)
                if description_element:
                    desc_text = description_element.get_text(separator=" ", strip=True)
                    if desc_text:
                        description = clean_text(desc_text)
                        break
            



            # --- Visit job detail page for salary, email, phone, description ---
            detail_email       = None
            detail_description = None
            detail_phone       = None
            detail_company     = None
            try:
                if full_source and self.page:
                    # Navigasi di tab yang SAMA (1 tab saja, seperti manusia)
                    # Listing page HTML sudah di-capture sebelumnya di _fetch_page,
                    # jadi aman untuk navigate ke detail sekarang.
                    self.page.goto(full_source, wait_until="domcontentloaded", timeout=30_000)
                    time.sleep(random.uniform(1.5, 3.0))
                    detail_html = self.page.content()
                    detail_soup = BeautifulSoup(detail_html, 'html.parser')

                    # Cari email dari mailto:
                    mailto_link = detail_soup.find('a', href=lambda x: x and x.startswith('mailto:'))
                    if mailto_link:
                        detail_email = mailto_link['href'][7:].split('?')[0].strip()

                    # Cari nomor telepon
                    from .utils import extract_phone_from_soup, extract_salary_range, extract_salary_type_from_text
                    detail_phone = extract_phone_from_soup(detail_soup)

                    # Cari salary dari detail page
                    salary_detail_elem = detail_soup.find('span', {'data-automation': 'job-detail-salary'})
                    if salary_detail_elem:
                        salary_detail_text = salary_detail_elem.get_text(strip=True)
                        self.logger.debug(f"[SALARY_DETAIL_FOUND] salary_text: '{salary_detail_text}'")
                        if salary_detail_text:
                            salary = salary_detail_text
                            salary_min, salary_max = extract_salary_range(salary_detail_text)
                            salary_type = extract_salary_type_from_text(salary_detail_text)
                        else:
                            self.logger.debug("[SALARY_DETAIL_EMPTY] salary_detail_elem found but text is empty.")
                    else:
                        self.logger.debug("[SALARY_DETAIL_NOT_FOUND] No element with data-automation='job-salary-detail' found on detail page.")

                    # ── Company name dari detail page (fallback jika card gagal) ──
                    company_selectors_detail = [
                        ('a',    {'data-automation': 'jobCompany'}),
                        ('span', {'data-automation': 'jobCompany'}),
                        ('a',    {'data-automation': 'advertiser-name'}),
                        ('span', {'data-automation': 'advertiser-name'}),
                        ('span', {'data-testid':     'advertiser-name'}),
                    ]
                    for tag, attrs in company_selectors_detail:
                        el = detail_soup.find(tag, attrs)
                        if el:
                            txt = clean_text(el.get_text(strip=True))
                            if txt:
                                detail_company = txt
                                break
                    # Fallback: company link di detail page (/companies/...)
                    if not detail_company:
                        for link in detail_soup.find_all('a', href=True):
                            href = link.get('href', '')
                            text = link.get_text(strip=True)
                            if '/companies/' in href and text and len(text) > 2:
                                detail_company = clean_text(text)
                                break

                    # Cari deskripsi lengkap
                    detail_description = None
                    desc_selectors = [
                        ('div', {'data-automation': 'jobAdDetails'}),
                        ('div', {'data-testid': 'job-details-tab'}),
                        ('div', {'data-automation': 'job-detail-content'}),
                        ('div', {'class': 'jobAdDetails'}),
                        ('div', {'id': 'job-details'}),
                        ('section', {'data-automation': 'job-section-details'}),
                    ]
                    for d_tag, d_attrs in desc_selectors:
                        desc_div = detail_soup.find(d_tag, d_attrs)
                        if desc_div:
                            raw_text = desc_div.get_text(separator='\n', strip=True)
                            if raw_text and len(raw_text) > 100:
                                detail_description = raw_text
                                self.logger.debug(f"[DESC_FOUND] selector={d_attrs}, len={len(raw_text)}")
                                break

                    if not detail_description:
                        paragraphs = detail_soup.find_all(['p', 'li'])
                        if paragraphs:
                            raw_text = '\n'.join(
                                p.get_text(strip=True) for p in paragraphs
                                if len(p.get_text(strip=True)) > 20
                            )
                            if len(raw_text) > 100:
                                detail_description = raw_text
                                self.logger.debug(f"[DESC_FALLBACK_P_LI] len={len(raw_text)}")

                    # Tab detail TIDAK ditutup — dipakai ulang untuk job berikutnya
            except Exception as e:
                self.logger.debug(f"Error extracting detail page: {str(e)}")

            # ── Tentukan company name final ──────────────────────────────
            # Prioritas: card extraction → detail page extraction → "Unknown"
            final_company = company_name or detail_company or "Unknown"
            if not company_name and detail_company:
                self.logger.debug(f"[COMPANY_FROM_DETAIL] '{detail_company}'")
            elif not company_name and not detail_company:
                self.logger.info(f"[COMPANY_NOT_FOUND] title='{title}' source='{full_source}'")

            # Pilih email: prioritas dari detail page, lalu dari card
            employer_email = detail_email
            if not employer_email:
                for link in all_links:
                    href = link.get('href', '')
                    if href.startswith('mailto:'):
                        email = href[7:].split('?')[0].strip()
                        if email:
                            employer_email = email
                            break

            final_salary_type = salary_type
            final_salary_min  = salary_min
            final_salary_max  = salary_max

            # Pilih deskripsi: prioritas dari detail page, lalu dari card
            final_description = detail_description if detail_description else description

            job_data_raw = {
                'title':                 title,
                'company_name':          final_company,
                'location':              location,
                'salary':                salary,
                'salary_min':            final_salary_min,
                'salary_max':            final_salary_max,
                'salary_type':           final_salary_type,
                'type':                  classification,
                'description':           final_description,
                'employer_email':        employer_email,
                'employer_first_name':   None,
                'employer_last_name':    None,
                'employer_phone_number': detail_phone,
                'company_size':          None,
                'company_address':       location,
                'company_industry':      None,
                'company_website':       None,
                'company_description':   final_description,
            }

            # Parse the job data
            parsed_job = parse_job_data(job_data_raw, full_source or source_url, state)

            return parsed_job
            
        except Exception as e:
            self.logger.debug(f"Error extracting job info: {str(e)}")
            return None
    
    def _fetch_page(self, url: str, page_num: int, state: str) -> List[Dict[str, Any]]:
        """
        Fetch dan parse satu halaman dengan retry.
        Menggunakan Playwright — stealth sudah aktif dari context.

        Adaptive timeout:
          - page <= 10: 10s
          - page <= 20: 20s
          - page  > 20: 30s
        """
        MAX_RETRIES = 3

        # Adaptive timeout (ms untuk Playwright)
        if page_num <= 10:
            wait_ms = SeekScraperConfig.ELEMENT_WAIT_TIMEOUT * 1000
        elif page_num <= 20:
            wait_ms = 20_000
        else:
            wait_ms = 30_000

        # Extra delay untuk page tinggi (human-like pacing)
        if page_num > 10:
            extra = random.uniform(2.0, 5.0)
            self.logger.debug(f"[ANTI-BOT] Extra delay {extra:.1f}s before page {page_num}...")
            time.sleep(extra)

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                if attempt > 1:
                    backoff = (2 ** (attempt - 1)) * 3 + random.uniform(0, 2)
                    self.logger.warning(
                        f"  [RETRY {attempt}/{MAX_RETRIES}] Waiting {backoff:.1f}s "
                        f"(page {page_num}, {state})..."
                    )
                    time.sleep(backoff)

                self.logger.info(f"Fetching page {page_num} ({state})..."
                                 + (f" [attempt {attempt}]" if attempt > 1 else ""))

                # Navigasi ke halaman
                self.page.goto(url, wait_until="domcontentloaded", timeout=60_000)

                # Tunggu job cards muncul (TANPA SCROLL — Seek infinite-scroll
                # akan load job extra dari next-page jika di-scroll)
                success = True
                try:
                    self.page.wait_for_selector(
                        'article[data-card-type="JobCard"]',
                        timeout=wait_ms
                    )
                except PlaywrightTimeout:
                    success = False

                # Fallback: scroll minimal (200px) — hanya jika belum ada card
                if not success:
                    self.logger.debug("  [FALLBACK] Cards not found, minimal scroll...")
                    self.page.evaluate("window.scrollTo(0, 200)")
                    time.sleep(1.5)
                    self.page.evaluate("window.scrollTo(0, 0)")
                    try:
                        self.page.wait_for_selector(
                            'article[data-card-type="JobCard"]',
                            timeout=8_000
                        )
                        success = True
                    except PlaywrightTimeout:
                        success = False

                if not success:
                    # Deteksi REAL CAPTCHA / bot block
                    # PENTING: hindari false positive!
                    # - 'captcha' saja TIDAK cukup — Google reCAPTCHA dimuat
                    #   sebagai background script di hampir semua web modern
                    # - Cek hanya pattern yang spesifik menandakan REAL block
                    page_src = self.page.content().lower()
                    real_block_patterns = [
                        'cf-challenge-body',            # Cloudflare challenge
                        'challenge-form',               # Cloudflare form
                        'please verify you are a human',# Text CAPTCHA eksplisit
                        'ray id',                       # Cloudflare ray ID (block page)
                        'ddos-guard',                   # DDoS-Guard protection
                        'access denied',                # Hard ban
                    ]
                    is_real_block = any(k in page_src for k in real_block_patterns)
                    if is_real_block:
                        raise Exception("[BOT-BLOCK] Real bot block detected")
                    # Bukan CAPTCHA — kemungkinan end-of-results atau halaman kosong
                    raise Exception("Job listings element not found (end of results or empty page)")

                # Log URL aktual
                actual_url = self.page.url
                self.logger.info(f"  [PAGE_URL] {actual_url}")
                if page_num > 1 and f"page={page_num}" not in actual_url:
                    self.logger.warning(
                        f"  [WARN] Redirect? Target page={page_num}, Actual: {actual_url}"
                    )

                # Adaptive wait setelah load
                wait_after = random.uniform(1.5, 3.5) if page_num <= 15 else random.uniform(3.0, 6.0)
                time.sleep(wait_after)

                html_content = self.page.content()
                parsed_jobs  = self._parse_job_listings(html_content, state, actual_url)

                self.logger.info(f"  [OK] Parsed {len(parsed_jobs)} jobs from page {page_num}")
                return parsed_jobs

            except Exception as e:
                err_msg = str(e)
                self.logger.warning(f"  [WARN] Attempt {attempt}/{MAX_RETRIES} failed for page {page_num}: {err_msg}")
                if "[BOT-BLOCK]" in err_msg:
                    self.logger.error(f"  [FAIL] Bot block pada page {page_num}. Menghentikan scraping state ini.")
                    return []
                if attempt == MAX_RETRIES:
                    self.logger.error(f"  [FAIL] All {MAX_RETRIES} attempts failed for page {page_num} ({state}). Skipping.")

        return []

    
    def _save_to_csv(self, output_path: Path) -> None:
        """
        Save scraped data to CSV file
        
        Args:
            output_path: Path to save CSV file
        """
        try:
            self.logger.info("Saving results to CSV...")
            
            if not self.jobs_data:
                self.logger.warning("  [WARN] No job data to save")
                return
            
            with open(output_path, 'w', newline='', encoding='utf-8-sig') as csvfile:
                # extrasaction='ignore': abaikan key di job dict yang tidak ada di CSV_COLUMNS
                writer = csv.DictWriter(
                    csvfile,
                    fieldnames=SeekScraperConfig.CSV_COLUMNS,
                    extrasaction='ignore'
                )
                
                # Write header
                writer.writeheader()
                
                # Write data rows
                for job in self.jobs_data:
                    # Compatibility fix: ensure 'application_form' exists for main.py
                    if 'application_form' not in job:
                        job['application_form'] = job.get('job_source', 'N/A')
                    writer.writerow(job)
            
            self.logger.info(f"  [OK] Saved {len(self.jobs_data)} jobs to {output_path}")
            
        except Exception as e:
            self.logger.error(f"  [ERR] Error saving to CSV: {str(e)}")

    def search_jobs(self, job_keyword: str, location: str, max_pages: int = 5) -> List[Dict[str, Any]]:
        """Standardized search method for main.py integration"""
        self.keyword = job_keyword
        self.page_limit = max_pages
        
        # Normalize location string to states list
        if not location or location.lower() in ['australia', 'all']:
            self.states = AustralianState.get_all_states()
        else:
            loc_upper = location.upper()
            if loc_upper in AustralianState.get_all_states():
                self.states = [loc_upper]
            else:
                self.states = [location]
        
        # Execute scraping
        self.scrape()
        
        # Ensure application_form exists in all results for main.py compatibility
        for job in self.jobs_data:
            if 'application_form' not in job:
                job['application_form'] = job.get('job_source', 'N/A')
                
        return self.jobs_data

    def close(self):
        """Standardized close method for main.py integration"""
        self._close_driver()
    
    def scrape(self, should_cancel: Optional[callable] = None,
               pause_event=None) -> Optional[Path]:
        """
        Main scraping method

        Args:
            should_cancel: Optional callback that returns True if scraping should stop
            pause_event:   threading.Event — clear=paused, set=running

        Returns:
            Path to output CSV file or None if error
        """
        try:
            self.logger.info("=" * 60)
            self.logger.info("[START] Scrapping started...")
            self.logger.info(f"   Keyword: {self.keyword}")
            self.logger.info(f"   States: {', '.join(self.states)}")
            self.logger.info(f"   Pages per state: {self.page_limit}")
            self.logger.info("=" * 60)
            
            # Setup output file
            self.output_path = generate_output_path()
            
            # Setup WebDriver
            self._setup_driver()
            
            total_jobs_scraped = 0
            aborted = False  # flag untuk early-exit (cancel/error dalam loop)

            # Scrape each state
            seen_keys = set()   # deduplication: URL + fallback title|company

            for state in self.states:
                # Check for cancellation
                if should_cancel and should_cancel():
                    self.logger.info(f"[CANCEL] Scraping stopped by user before {state}")
                    aborted = True
                    break

                self.logger.info(f"\n--- Scraping {state} ---")
                consecutive_empty = 0  # reset per-state

                for page in range(1, self.page_limit + 1):
                    # Check for cancellation
                    if should_cancel and should_cancel():
                        self.logger.info(f"[CANCEL] Scraping stopped by user at page {page} of {state}")
                        aborted = True
                        break

                    # Check for pause — blocks here until resumed
                    if pause_event and not pause_event.is_set():
                        self.logger.info(f"[PAUSE] Waiting for resume... (page {page} of {state})")
                        pause_event.wait()   # blocks until event.set() dipanggil
                        self.logger.info("[RESUME] Scraping resumed.")
                        # Cek cancel sekali lagi setelah resume
                        if should_cancel and should_cancel():
                            self.logger.info(f"[CANCEL] Scraping stopped after resume at page {page}")
                            aborted = True
                            break

                    url = self._build_search_url(self.keyword, state, page)

                    jobs = self._fetch_page(url, page, state)

                    # ── Auto-stop state jika end-of-results ─────────────────
                    # Seek memiliki hard limit ~520 jobs (~26 page × 22 jobs).
                    # Jika sudah 2 page berturut-turut kosong, berarti sudah
                    # habis hasilnya — tidak perlu lanjut sampai page_limit.
                    if not jobs:
                        consecutive_empty += 1
                        if consecutive_empty >= 2:
                            self.logger.info(
                                f"[END-OF-RESULTS] {consecutive_empty} halaman kosong berturut-turut "
                                f"di {state} (page {page}). Melanjutkan ke state berikutnya."
                            )
                            break
                        self.logger.debug(f"  [EMPTY] Page {page} kosong ({consecutive_empty}/2).")
                    else:
                        consecutive_empty = 0  # reset counter jika ada data

                    # Deduplication: buang job yang sudah ada
                    new_jobs = []
                    for job in jobs:
                        raw_url  = (job.get("source") or "").strip()
                        # Strip query params — Seek menambah ?tracking=...&sr=N yang beda
                        # tapi job ID di path-nya sama (/job/80737940)
                        clean_url = raw_url.split("?")[0].rstrip("/")

                        job_title = (job.get("title")  or "").strip().lower()
                        job_co    = (job.get("employer_company_name") or "").strip().lower()

                        # Key utama: path URL tanpa query; fallback: title+company
                        dedup_key = clean_url if clean_url else f"{job_title}||{job_co}"

                        if dedup_key and dedup_key in seen_keys:
                            self.logger.debug(f"[SKIP DUPLICATE] {dedup_key[:80]}")
                            continue
                        if dedup_key:
                            seen_keys.add(dedup_key)
                        new_jobs.append(job)

                    dup_count = len(jobs) - len(new_jobs)
                    if dup_count:
                        self.logger.info(f"  [DEDUP] {dup_count} duplicate(s) removed on page {page}")

                    self.jobs_data.extend(new_jobs)
                    total_jobs_scraped += len(new_jobs)

                    if page < self.page_limit:
                        delay = random.uniform(1.5, 4.0)
                        self.logger.debug(f"[DELAY] Waiting {delay:.1f}s before next page...")
                        time.sleep(delay)

                # Propagate inner break ke outer loop
                if aborted:
                    break

                # Delay between states
                delay = random.uniform(2.0, 5.0)
                self.logger.debug(f"[DELAY] Waiting {delay:.1f}s before next state...")
                time.sleep(delay)
            
            # ── Simpan data (penuh atau parsial) ──────────────────────────────
            self.logger.info("\n" + "=" * 60)
            if self.jobs_data:
                if aborted:
                    self.logger.info(f"[PARTIAL SAVE] Menyimpan {len(self.jobs_data)} jobs (partial)...")
                else:
                    self.logger.info(f"Scraping selesai. Total: {total_jobs_scraped} jobs")

                self._save_to_csv(self.output_path)

                if aborted:
                    self.logger.info(f"[OK] Data parsial tersimpan → {self.output_path}")
                else:
                    self.logger.info("[OK] Scrapping completed successfully!")
                    self.logger.info(f"[FILE] Output file: {self.output_path}")
            else:
                self.logger.info("[INFO] Tidak ada data yang berhasil dikumpulkan.")
            self.logger.info("=" * 60)
            
            return self.output_path
            
        except Exception as e:
            self.logger.error(f"✗ Scrapping failed: {str(e)}")
            # Coba simpan data parsial jika sempat terkumpul
            if self.jobs_data:
                try:
                    self.logger.info(f"[PARTIAL SAVE] Error terjadi, menyimpan {len(self.jobs_data)} jobs parsial...")
                    self._save_to_csv(self.output_path)
                    self.logger.info(f"[OK] Data parsial tersimpan → {self.output_path}")
                except Exception as save_err:
                    self.logger.error(f"[SAVE ERROR] Gagal menyimpan parsial: {save_err}")
            return self.output_path if self.jobs_data else None
            
        finally:
            self._close_driver()
    
    def get_job_summary(self) -> Dict[str, Any]:
        """
        Get summary of scraped jobs
        
        Returns:
            Summary dictionary
        """
        summary = {
            'total_jobs': len(self.jobs_data),
            'states': len(self.states),
            'pages_per_state': self.page_limit,
            'output_file': str(self.output_path) if self.output_path else None,
            'timestamp': datetime.now().isoformat()
        }
        
        return summary


def scrape_seek_jobs(keyword: str, states: List[str], page_limit: int = 1) -> Optional[Path]:
    """
    Convenient function to scrape Seek jobs
    
    Args:
        keyword: Search keyword
        states: List of states or ["all"] for all states
        page_limit: Number of pages to scrape per state
        
    Returns:
        Path to output CSV file
        
    Example:
        >>> scrape_seek_jobs("Python Developer", ["NSW", "VIC"], page_limit=2)
        >>> scrape_seek_jobs("Data Scientist", ["all"], page_limit=3)
    """
    scraper = SeekScraper(keyword, states, page_limit)
    return scraper.scrape()
