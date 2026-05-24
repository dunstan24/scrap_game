"""
Main scraper class for CareerOne Australia job listings using Camoufox
Uses same Cloudflare bypass approach as Jora, Seek, Indeed scrapers
"""
import asyncio
import time
from typing import List, Dict, Any, Optional
from datetime import datetime
from bs4 import BeautifulSoup

from src.config import (
    HEADLESS_MODE, PAGE_LOAD_TIMEOUT,
    DELAY_BETWEEN_REQUESTS, FETCH_FULL_DESCRIPTION,
    USE_AI_ANALYSIS, GEMINI_API_KEYS, GEMINI_MODEL, AI_RATE_LIMIT_RPM,
    FULL_DESCRIPTION_TIMEOUT
)
from src.utils import (
    logger, clean_text, get_random_user_agent,
    normalize_state, normalize_job_type, extract_salary_parts,
    detect_job_level, extract_skills, split_contact_name, map_sponsorship,
    extract_website_from_text, extract_phone_from_text, adaptive_delay,
    detect_cloudflare
)
from src.playwright_helper import create_browser_context, _wait_for_turnstile, _is_cloudflare_page


class CareerOneScraper:
    """Scraper for CareerOne Australia job listings using Playwright"""
    
    BASE_URL = "https://www.careerone.com.au"
    SEARCH_URL = "https://www.careerone.com.au/jobs/in-australia"
    
    # CSS Selectors based on CareerOne HTML structure from CAREERONE_INFO.txt
    # Verified against actual HTML structure on website
    SELECTORS = {
        'job_card': '.job-card-detailed',  # Main container for each job listing
        'job_title': 'h2.text-title-1 a',  # Job title link inside h2
        'company_name': 'a.text-title-3.text-black',  # Company name link (under .job-card-brand)
        'salary': '.job-card-detailed-pay-info .text-title-4.text-black',  # Salary in pay-info section
        'job_type': 'span.text-body-4.text-black',  # "Full time", "Permanent", etc.
        'location': 'div.d-inline-block.text-body-4.text-black a',  # Location links
        'posted_date': '.job-date',  # Posted date (e.g., "Posted 15d ago")
        'description': 'div#jvDescription .job-text p',  # Full description paragraphs on detail page
        'apply_button': 'button.btn.jv-cta-btn',  # Apply button on detail page
        'next_page_button': 'li.page-item button[aria-label="Go to next page"]',  # Next page button in pagination list
        'next_page_button_alt': 'button[aria-label="Go to next page"].page-link',  # Alternative selector
        'prev_page_button': 'span[aria-label="Go to previous page"]',  # Previous page (disabled when on page 1)
        'search_input': '#inputKeywordSearch',  # Keyword search input
        'location_input': 'input[placeholder="All Australia"]',  # Location input
        'search_button': 'button.searchbar-btn-search.btn-theme-primary',  # Search button with magnifying glass icon
    }
    
    def __init__(self, headless: bool = False, use_ai: bool = USE_AI_ANALYSIS):
        """Initialize the scraper with Camoufox (non-headless by default)"""
        self.headless = headless
        self.camoufox_cm = None
        self.browser = None
        self.page = None
        self.use_ai = use_ai
        self.jobs_data = []
        self.ai_analyzer = None
        self.consecutive_timeouts = 0
        self.max_consecutive_timeouts = 3
        self.skip_full_descriptions = False
        
        # Initialize AI analyzer if enabled
        if self.use_ai:
            try:
                from ai_analyzer import GeminiAnalyzer
                self.ai_analyzer = GeminiAnalyzer(
                    api_keys=GEMINI_API_KEYS,
                    model_name=GEMINI_MODEL,
                    rate_limit_rpm=AI_RATE_LIMIT_RPM
                )
                logger.info(" AI Analyzer initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize AI Analyzer: {str(e)}")
                logger.warning("Continuing without AI analysis")
                self.use_ai = False
    
    async def setup_browser(self):
        """Setup Camoufox browser with Cloudflare Turnstile bypass (same as Jora/Seek/Indeed)"""
        try:
            logger.info("Initializing Camoufox browser with Cloudflare bypass...")
            logger.info(f"   Mode: {'Browser Visible' if not self.headless else 'Headless'}")
            
            # Use Camoufox for Cloudflare Turnstile support (like Indeed scraper does)
            self.camoufox_cm, self.browser, _ = await create_browser_context(bypass_cf=True, headless=self.headless)
            
            # Create page
            self.page = await self.browser.new_page()
            
            # Set navigation timeout
            self.page.set_default_timeout(PAGE_LOAD_TIMEOUT * 1000)
            self.page.set_default_navigation_timeout(PAGE_LOAD_TIMEOUT * 1000)
            
            logger.info(" Camoufox browser initialized successfully (CF-safe headless)")
            
        except Exception as e:
            logger.error(f" Failed to setup Camoufox: {str(e)}")
            logger.error("Make sure camoufox is installed: pip install camoufox[geoip] && python -m camoufox fetch")
            raise
    
    async def wait_for_cloudflare(self, retry_count=0, max_retries=3):
        """
        Wait for Cloudflare Turnstile challenge using Camoufox
        Uses the exact same _wait_for_turnstile approach as Indeed/Jora/Seek
        With retry logic for robust bypass
        """
        try:
            html = await self.page.content()
            if _is_cloudflare_page(html):
                logger.info(" Cloudflare challenge detected - using Camoufox Turnstile handler...")
                resolved = await _wait_for_turnstile(self.page, timeout_ms=90000)  # 90s timeout
                if resolved:
                    logger.info(" Cloudflare challenge resolved")
                    # Verify it's actually resolved
                    await asyncio.sleep(1)
                    html_check = await self.page.content()
                    if _is_cloudflare_page(html_check):
                        # Still showing CF, retry if we haven't exceeded max
                        if retry_count < max_retries:
                            logger.warning(f" CF still visible after resolution, retrying ({retry_count + 1}/{max_retries})...")
                            await asyncio.sleep(2)
                            return await self.wait_for_cloudflare(retry_count + 1, max_retries)
                        else:
                            logger.warning(" CF bypass failed after max retries - continuing anyway")
                    return True
                else:
                    # Resolution failed, retry if possible
                    if retry_count < max_retries:
                        logger.warning(f" Cloudflare timeout, retrying ({retry_count + 1}/{max_retries})...")
                        await asyncio.sleep(2)
                        return await self.wait_for_cloudflare(retry_count + 1, max_retries)
                    else:
                        logger.warning("  Cloudflare timeout after max retries - continuing anyway")
                        return True
            else:
                logger.info(" No Cloudflare challenge detected")
                return True
                
        except Exception as e:
            logger.warning(f"  Error handling Cloudflare: {e}")
            if retry_count < max_retries:
                logger.info(f" Retrying CF bypass ({retry_count + 1}/{max_retries})...")
                await asyncio.sleep(2)
                return await self.wait_for_cloudflare(retry_count + 1, max_retries)
            return True  # Continue anyway
    
    async def search_jobs(self, keyword: str, location: str = "All Australia", pages: int = 1,
                         should_cancel=None, date_filter: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Search for jobs on CareerOne
        
        Args:
            keyword: Job keyword to search
            location: Location to search (default: "All Australia")
            pages: Number of pages to scrape
            should_cancel: Callback function to check if scraping should be cancelled
            date_filter: 1 = last 24 hours, None = any time
            
        Returns:
            List of job dictionaries
        """
        jobs = []
        self._date_filter = date_filter  # Store for use in date filter selection
        
        try:
            # Setup browser if not already done
            if not self.page:
                await self.setup_browser()
            
            # Navigate to CareerOne
            logger.info(f" Navigating to CareerOne search page...")
            logger.info(f" URL: {self.SEARCH_URL}")
            await self.page.goto(self.SEARCH_URL, wait_until='domcontentloaded')
            
            # Wait for Cloudflare challenge
            await self.wait_for_cloudflare()
            
            logger.info(f" CareerOne page loaded successfully")
            
            # STEP 1: Click "Posted within" button, then "Posted today" in dropdown (FIRST!)
            if date_filter == 1:
                try:
                    logger.info(f"\n{'='*60}")
                    logger.info(f" 📝 STEP 1️⃣ : CLICK 'POSTED TODAY' FILTER FIRST")
                    logger.info(f"{'='*60}")
                    logger.info(f" Clicking 'Posted within' -> 'Posted today'")
                    await self._click_posted_today_on_search_form()
                    logger.info(f" ✓ STEP 1 COMPLETE: 'Posted today' filter applied")
                    
                    await asyncio.sleep(1)
                        
                except Exception as step1_error:
                    logger.error(f" ⚠️  Could not apply 'Posted today' filter: {str(step1_error)}")
                    logger.info(f" Continuing anyway...")
            else:
                logger.info(f"\n{'='*60}")
                logger.info(f" ℹ️  STEP 1️⃣ : No date filter requested")
                logger.info(f"{'='*60}")
            
            # STEP 2: Type occupation (ONLY if keyword exists)
            if keyword and keyword.strip():
                try:
                    logger.info(f"\n{'='*60}")
                    logger.info(f" 📝 STEP 2️⃣ : TYPE OCCUPATION")
                    logger.info(f"{'='*60}")
                    logger.info(f" Keyword: '{keyword}'")
                    await self._type_occupation(keyword)
                    logger.info(f" ✓ STEP 2 COMPLETE: Occupation typed")
                except Exception as step2_error:
                    logger.error(f" ❌ CRITICAL ERROR IN STEP 2: {str(step2_error)}")
                    import traceback
                    logger.error(traceback.format_exc())
                    raise
            else:
                logger.info(f"\n{'='*60}")
                logger.info(f" ℹ️  STEP 2️⃣ : SKIPPING OCCUPATION (keyword is empty)")
                logger.info(f"{'='*60}")
            
            # STEP 3: Type state
            try:
                logger.info(f"\n{'='*60}")
                logger.info(f" 📝 STEP 3️⃣ : TYPE STATE")
                logger.info(f"{'='*60}")
                logger.info(f" Location: '{location}'")
                await self._type_state(location)
                logger.info(f" ✓ STEP 3 COMPLETE: State typed")
            except Exception as step3_error:
                logger.error(f" ❌ CRITICAL ERROR IN STEP 3: {str(step3_error)}")
                import traceback
                logger.error(traceback.format_exc())
                raise
            
            # NO SEARCH BUTTON CLICK - Already submitted by state+Enter
            logger.info(f"\n{'='*60}")
            logger.info(f" ✅ FORM SUBMISSION COMPLETE via state+Enter")
            logger.info(f" Now extracting jobs and navigating pages...")
            logger.info(f"{'='*60}")
            
            # Scrape pages
            page = 1
            is_infinite = pages == 999  # Special value for "Infinite" pages
            max_pages = pages if not is_infinite else float('inf')
            
            if is_infinite:
                logger.info(f" 🔄 INFINITE MODE: Will scrape all available pages")
            else:
                logger.info(f" 📄 PAGE LIMIT: {pages} pages")
            
            while page <= max_pages:
                if should_cancel and should_cancel():
                    logger.info(" ❌ CANCELLATION DETECTED - stopping scraping immediately")
                    logger.info(f" 💾 Saving {len(jobs)} jobs scraped so far...")
                    break
                
                logger.info(f"\n{'='*60}")
                if is_infinite:
                    logger.info(f" PAGE {page} (INFINITE MODE - showing all pages)")
                else:
                    logger.info(f" PAGE {page} of {pages}")
                logger.info(f"{'='*60}")
                
                # Wait for Cloudflare before scraping
                await self.wait_for_cloudflare()
                
                # Extract jobs from current page
                logger.info(f" Extracting job listings from page {page}...")
                page_jobs = await self._extract_jobs_from_page(should_cancel)
                jobs.extend(page_jobs)
                logger.info(f" Page {page} complete: {len(page_jobs)} jobs extracted (total: {len(jobs)})")
                
                # Check cancellation again after each page
                if should_cancel and should_cancel():
                    logger.info(" ❌ CANCELLATION DETECTED - stopping after this page")
                    logger.info(f" 💾 Saving {len(jobs)} jobs scraped so far...")
                    break
                
                # Check if there's a next page and navigate to it
                if is_infinite or page < pages:
                    # Check cancel before moving to next page
                    if should_cancel and should_cancel():
                        logger.info(" ❌ CANCEL DETECTED before navigation - stopping pagination")
                        break
                    
                    logger.info(f"  Preparing to navigate to page {page + 1}...")
                    if await self._navigate_next_page():
                        logger.info(f" Successfully navigated to page {page + 1}")
                        await asyncio.sleep(2)
                        page += 1
                        adaptive_delay(page, DELAY_BETWEEN_REQUESTS)
                    else:
                        logger.info("  No next page available - stopping pagination")
                        break
                else:
                    break
            
            logger.info(f"\n{'='*60}")
            logger.info(f" SCRAPING COMPLETE!")
            logger.info(f" Total jobs scraped: {len(jobs)}")
            logger.info(f"{'='*60}")
            
            # Apply AI analysis if enabled
            if self.use_ai and self.ai_analyzer and jobs:
                logger.info(" Starting AI analysis for scraped jobs...")
                jobs = self.ai_analyzer.analyze_batch(jobs)
                logger.info(" AI analysis completed")
            
            self.jobs_data.extend(jobs)
            return jobs
            
        except Exception as e:
            logger.error(f" Error during job search: {str(e)}")
            return jobs
    
    async def _type_occupation(self, keyword: str):
        """Click occupation field, type keyword, move on (NO Enter)"""
        try:
            logger.info(f"    🔹 Entering occupation: '{keyword}'")
            
            # Click the search input field
            await self.page.click(self.SELECTORS['search_input'])
            await asyncio.sleep(0.3)
            
            # Clear any existing text
            await self.page.fill(self.SELECTORS['search_input'], '')
            await asyncio.sleep(0.2)
            
            # Type the keyword
            await self.page.keyboard.type(keyword)
            await asyncio.sleep(0.3)
            
            logger.info(f"   ✓ Occupation typed: '{keyword}'")
            
        except Exception as e:
            logger.warning(f"    Could not type occupation: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            raise

    async def _click_posted_today_on_search_form(self):
        """Click 'Posted within' button, then 'Posted today' in dropdown (NO form submission!)"""
        try:
            logger.info(f"    🔹 Step 1: Looking for 'Posted within' button...")
            await asyncio.sleep(0.5)
            
            # Step 1: Find and click "Posted within" button
            posted_within_clicked = False
            
            # Use JavaScript to click it safely without triggering form submission
            result = await self.page.evaluate("""
                () => {
                    const buttons = Array.from(document.querySelectorAll('button'))
                        .filter(btn => btn.textContent.includes('Posted within'));
                    if (buttons.length > 0) {
                        buttons[0].click();
                        return true;
                    }
                    return false;
                }
            """)
            if result:
                logger.info(f"   ✓ Clicked 'Posted within' button via JavaScript")
                posted_within_clicked = True
                await asyncio.sleep(1)  # Wait for dropdown to appear
            
            if not posted_within_clicked:
                logger.warning(f"    Could not click 'Posted within' - continuing anyway")
                return
            
            # Step 2: Click "Posted today" in dropdown with event.preventDefault() to stop form submission
            logger.info(f"    🔹 Step 2: Looking for 'Posted today' in dropdown...")
            
            result = await self.page.evaluate("""
                () => {
                    const divs = Array.from(document.querySelectorAll('div.c1-tag__text'))
                        .filter(div => div.textContent.includes('Posted today'));
                    if (divs.length > 0) {
                        // Find parent element that might be clickable
                        let elem = divs[0];
                        // Try clicking the element itself or its parent
                        if (elem) {
                            elem.click();
                            return true;
                        }
                    }
                    return false;
                }
            """)
            if result:
                logger.info(f"   ✓ Clicked 'Posted today' via JavaScript")
                await asyncio.sleep(1)
                return
            
            logger.warning(f"    Could not find 'Posted today' in dropdown - continuing anyway")
            
        except Exception as e:
            logger.warning(f"    Error clicking 'Posted today': {e}")
            import traceback
            logger.debug(traceback.format_exc())

    async def _type_state(self, location: str):
        """Click location field, type state, press Enter (NO dropdown navigation)"""
        try:
            logger.info(f"    🔹 Entering location (state): '{location}'")
            
            # Click the location input field
            await self.page.click(self.SELECTORS['location_input'])
            await asyncio.sleep(0.3)
            
            # Clear any existing text
            await self.page.fill(self.SELECTORS['location_input'], '')
            await asyncio.sleep(0.2)
            
            # Type the location
            logger.info(f"    Typing: '{location}'")
            await self.page.keyboard.type(location)
            await asyncio.sleep(0.5)
            logger.info(f"   ✓ State typed: '{location}'")
            
            # Press Enter to submit
            logger.info(f"    Pressing Enter to submit...")
            await self.page.keyboard.press('Enter')
            await asyncio.sleep(3)  # Wait for results to load
            logger.info(f"   ✓ Results loaded")
                
        except Exception as e:
            logger.warning(f"    Could not type state: {str(e)[:100]}")
            import traceback
            logger.debug(traceback.format_exc())
            raise
    
    async def _input_search_params(self, keyword: str, location: str):
        """Input search keyword and location
        
        CRITICAL: Type values but DO NOT interact with dropdowns or press Enter!
        Just type and move on - no submission!
        
        ORDER:
        1. Type keyword (occupation) 
        2. Type location (state)
        3. Return (NO Enter key, NO dropdown selection)
        4. Search button will be clicked in main function
        """
        try:
            # INPUT 1️⃣: KEYWORD (OCCUPATION)
            logger.info(f"    🔹 INPUT 1️⃣ : Entering keyword: '{keyword}'")
            await self.page.fill(self.SELECTORS['search_input'], keyword)
            logger.info(f"   ✓ Keyword typed (NO Enter): '{keyword}'")
            await asyncio.sleep(0.5)
            
        except Exception as e:
            logger.warning(f"    Could not input keyword: {e}")
        
        try:
            # INPUT 2️⃣: LOCATION (STATE)
            logger.info(f"    🔹 INPUT 2️⃣ : Entering location (state): '{location}'")
            
            # Find location input
            location_input = await self.page.query_selector(self.SELECTORS['location_input'])
            
            if not location_input:
                # Try alternatives
                location_input = await self.page.query_selector('input[placeholder*="Australia"]')
                if not location_input:
                    location_input = await self.page.query_selector('div.c1-typeahead-single-select__search__input input')
            
            if location_input:
                # Click to focus
                await location_input.click()
                await asyncio.sleep(0.3)
                
                # Clear any existing text
                await self.page.keyboard.press('Control+A')
                await asyncio.sleep(0.1)
                await self.page.keyboard.press('Backspace')
                await asyncio.sleep(0.3)
                
                # Type location WITHOUT pressing Enter or clicking dropdown
                logger.info(f"    Typing location: '{location}'")
                await self.page.keyboard.type(location)
                logger.info(f"   ✓ Location typed (NO Enter, NO selection): '{location}'")
                
                # IMPORTANT: Just wait, don't interact with dropdown
                await asyncio.sleep(0.5)
                logger.info(f"   ✓ INPUT STEP COMPLETE - Ready for search button click")
            else:
                logger.warning(f"    Location input not found - continuing anyway")
                
        except Exception as e:
            logger.warning(f"    Could not input location: {str(e)[:100]}")
            logger.warning(f"    Continuing anyway...")
    
    async def _select_date_filter(self, date_filter: Optional[int]) -> bool:
        """Select date filter option - MUST be called BEFORE search button click!
        
        Per user requirement: STOP if "Posted today" not found - don't try fallbacks!
        
        Args:
            date_filter: 1 = last 24 hours, None = any time
            
        Returns:
            True if successful, False otherwise
        """
        if date_filter is None:
            logger.info(f"    ✓ Date filter is 'Any time' - no action needed")
            return True
        
        try:
            logger.info(f"    🔍 [CRITICAL] Applying date filter BEFORE search...")
            await asyncio.sleep(0.5)
            
            logger.info(f"    🔍 Looking for 'Posted within' button with 'Posted today' option...")
            
            # FIND THE EXACT BUTTON WITH "Posted within" TEXT
            # List all toggleBtn buttons to see which ones exist
            all_buttons = await self.page.query_selector_all('button.toggleBtn')
            logger.info(f"    Found {len(all_buttons)} total button.toggleBtn elements")
            
            # Find the one with "Posted within" text
            toggle_button = None
            for idx, btn in enumerate(all_buttons):
                btn_text = await btn.text_content()
                btn_text_clean = btn_text.strip() if btn_text else ""
                logger.info(f"      Button {idx}: '{btn_text_clean[:40]}...'")
                
                if 'Posted within' in btn_text:
                    toggle_button = btn
                    logger.info(f"    ✓✓✓ FOUND 'Posted within' button at index {idx}")
                    break
            
            if not toggle_button:
                logger.error(f"    ❌ FATAL: 'Posted within' button NOT FOUND!")
                logger.error(f"    ❌ STOP: Cannot apply date filter. Aborting search.")
                return False
            
            logger.info(f"    Clicking 'Posted within' button...")
            await toggle_button.click()
            
            # Wait for dropdown to open
            logger.info(f"    Waiting for dropdown to open...")
            await asyncio.sleep(1.5)
            
            # Look for "Posted today" option
            if date_filter == 1:
                option_text = "Posted today"
            else:
                logger.error(f"    ❌ FATAL: Unknown date_filter value: {date_filter}")
                return False
            
            logger.info(f"    Looking for '{option_text}' option...")
            
            # Find the option - using the exact selector from HTML
            options = await self.page.query_selector_all('div.c1-tag__text')
            logger.info(f"    Found {len(options)} div.c1-tag__text element(s)")
            
            # List all options found
            found_texts = []
            for idx, opt in enumerate(options):
                opt_text = await opt.text_content()
                opt_text_clean = opt_text.strip() if opt_text else ""
                found_texts.append(opt_text_clean)
                logger.info(f"      Option {idx}: '{opt_text_clean}'")
            
            # Search for exact match
            date_option = None
            for opt in options:
                opt_text = await opt.text_content()
                opt_text_clean = opt_text.strip() if opt_text else ""
                
                if opt_text_clean == option_text:  # Exact match
                    date_option = opt
                    logger.info(f"    ✓✓✓ FOUND '{option_text}'")
                    break
            
            if not date_option:
                logger.error(f"    ❌ FATAL: '{option_text}' option NOT FOUND!")
                logger.error(f"    ❌ Available options were: {found_texts}")
                logger.error(f"    ❌ STOP: Cannot proceed without correct date filter.")
                return False
            
            logger.info(f"    Clicking '{option_text}'...")
            await date_option.click()
            
            # Wait for click to register and dropdown to close
            await asyncio.sleep(1.5)
            
            logger.info(f"    ✅ [SUCCESS] Date filter '{option_text}' applied!")
            logger.info(f"    ⚠️  IMPORTANT: Do NOT search here - search button will be clicked in main flow!")
            return True
            
        except Exception as e:
            logger.error(f"    ❌ FATAL ERROR in date filter: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            logger.error(f"    ❌ STOP: Aborting search due to error.")
            return False
    
    
    async def _navigate_next_page(self) -> bool:
        """Navigate to next page using click only
        
        Simple approach: try to click next button, if fails then stop
        """
        try:
            logger.info(f"   Looking for next page button...")
            
            # Wait for page to be calm before attempting click
            await asyncio.sleep(1)
            
            # Try to find NEXT button
            button_selectors = [
                'button:has-text("NEXT")',
                'button.page-link[aria-label="Go to next page"]',
                'button[role="menuitem"][aria-label="Go to next page"]',
                'li.page-item button.page-link',
            ]
            
            next_button = None
            for selector in button_selectors:
                try:
                    next_button = await self.page.query_selector(selector)
                    if next_button:
                        logger.info(f"    ✓ Found next button with selector: {selector}")
                        break
                except:
                    pass
            
            if not next_button:
                logger.info("    ❌ Next page button not found - this appears to be the last page")
                return False
            
            logger.info(f"    Attempting to click next page button...")
            
            # Use JavaScript to click - bypasses Playwright click validation
            try:
                result = await self.page.evaluate("""
                    () => {
                        const buttons = Array.from(document.querySelectorAll('button'))
                            .filter(btn => btn.getAttribute('aria-label') === 'Go to next page');
                        if (buttons.length > 0) {
                            buttons[0].click();
                            return true;
                        }
                        return false;
                    }
                """)
                
                if result:
                    logger.info("    ✓ Successfully clicked next page button via JavaScript")
                    
                    # Wait for page to load
                    try:
                        await self.page.wait_for_load_state('networkidle', timeout=10000)
                    except:
                        await asyncio.sleep(2)
                    
                    logger.info("   ✓ Successfully navigated to next page")
                    return True
                else:
                    logger.warning(f"    ❌ Next button not found via JavaScript")
                    return False
                
            except Exception as click_err:
                # Click failed - stop, don't try other strategies
                logger.warning(f"    ❌ Click failed: {str(click_err)[:80]}")
                logger.info(f"    Stopping navigation - could not click next page button")
                return False
            
        except Exception as e:
            logger.warning(f"    ❌ Error in navigation: {e}")
            return False
    
    async def _extract_jobs_from_page(self, should_cancel=None) -> List[Dict[str, Any]]:
        """Extract all jobs from current page
        
        If date_filter=1 (Last 24 hours), only include jobs with "Posted today" or "Posted 1d ago"
        """
        jobs = []
        failed_jobs = set()
        skipped_by_date_filter = 0
        
        try:
            await asyncio.sleep(1)
            
            # Get job cards
            logger.info(f"   Scanning page for job cards...")
            page_content = await self.page.content()
            soup = BeautifulSoup(page_content, 'lxml')
            job_cards = soup.select(self.SELECTORS['job_card'])
            
            if not job_cards:
                logger.warning(f"   Could not find any job cards on this page")
                return jobs
            
            # If less than 5 jobs, wait 5-10 seconds for more jobs to load
            if len(job_cards) < 5:
                logger.info(f"   Found only {len(job_cards)} job card(s). Waiting 5-10 seconds for more jobs to load...")
                wait_time = 5 + (await self.page.evaluate("() => Math.random() * 5"))  # Random 5-10 seconds
                await asyncio.sleep(wait_time)
                
                # Reload and check again
                logger.info(f"   Rechecking page for additional jobs...")
                page_content = await self.page.content()
                soup = BeautifulSoup(page_content, 'lxml')
                job_cards_updated = soup.select(self.SELECTORS['job_card'])
                if len(job_cards_updated) > len(job_cards):
                    logger.info(f"   Job count increased from {len(job_cards)} to {len(job_cards_updated)}")
                    job_cards = job_cards_updated
                else:
                    logger.info(f"   Job count unchanged ({len(job_cards)}). Proceeding with extraction.")
            
            logger.info(f"   Found {len(job_cards)} job card(s) on this page")
            
            # Log date filter status
            if self._date_filter == 1:
                logger.info(f"   🔥 DATE FILTER ACTIVE: Only accepting 'Posted today' or 'Posted 1d ago'")
            
            # Extract data from each job card
            logger.info(f"   Processing {len(job_cards)} job(s)...")
            for idx, card in enumerate(job_cards):
                # CHECK CANCEL before processing each job
                if should_cancel and should_cancel():
                    logger.info(f" ❌ CANCEL DETECTED during extraction - stopping at job {idx + 1}/{len(job_cards)}")
                    break
                
                if idx in failed_jobs:
                    continue
                
                # CHECK DATE FILTER before extracting full data (save time!)
                if self._date_filter == 1:
                    posted_date_elem = card.select_one(self.SELECTORS['posted_date'])
                    if posted_date_elem:
                        posted_text = clean_text(posted_date_elem.get_text())
                    else:
                        posted_text = "N/A"
                    
                    # Only accept "Posted today" or "Posted 1d ago"
                    if posted_text not in ["Posted today", "Posted 1d ago"]:
                        logger.info(f"     Job {idx + 1}: SKIPPED - posted '{posted_text}' (not within 24h)")
                        skipped_by_date_filter += 1
                        continue
                    else:
                        logger.info(f"     Job {idx + 1}: ✓ Posted '{posted_text}' - MATCHES date filter")
                
                success = False
                
                try:
                    logger.info(f"     Extracting job {idx + 1}/{len(job_cards)}...")
                    job_data = await self._extract_job_data(card)
                    if job_data:
                        jobs.append(job_data)
                        title = job_data.get('title', 'Unknown')
                        company = job_data.get('employer_company_name', 'Unknown')
                        logger.info(f"     Job {idx + 1}: '{title}' at {company}")
                        success = True
                
                except Exception as first_err:
                    logger.warning(f"    ✗ Failed to extract job {idx + 1}: {str(first_err)[:60]}")
                    logger.info(f"     SKIPPING job {idx + 1} - could not extract data")
                    failed_jobs.add(idx)
            
            # Log final counts
            if self._date_filter == 1:
                logger.info(f"   [DATE FILTER] Scraped: {len(jobs)}, Skipped by date filter: {skipped_by_date_filter}, Failed: {len(failed_jobs)}")
            else:
                logger.info(f"   Page extraction complete: {len(jobs)} scraped, {len(failed_jobs)} skipped")
            
            return jobs
            
        except Exception as e:
            logger.error(f" Error extracting jobs from page: {str(e)}")
            return jobs
    
    async def _extract_job_data(self, job_card) -> Optional[Dict[str, Any]]:
        """Extract data from a single job card - async to support full description extraction"""
        try:
            # Extract title
            title = 'N/A'
            job_url = 'N/A'
            title_elem = job_card.select_one(self.SELECTORS['job_title'])
            if title_elem:
                title = clean_text(title_elem.get_text())
                job_url = title_elem.get('href', 'N/A')
            
            # Extract company name
            company_name = 'N/A'
            company_elem = job_card.select_one(self.SELECTORS['company_name'])
            if company_elem:
                company_name = clean_text(company_elem.get_text())
            
            # Extract salary
            salary_raw = 'N/A'
            salary_elem = job_card.select_one(self.SELECTORS['salary'])
            if salary_elem:
                salary_raw = clean_text(salary_elem.get_text())
            
            # Extract job type (format: "Full time · Permanent")
            job_type_raw = 'N/A'
            type_elements = job_card.select(self.SELECTORS['job_type'])
            
            # Collect all text from job type elements
            type_texts = []
            for elem in type_elements:
                elem_text = clean_text(elem.get_text()).lower()
                type_texts.append(elem_text)
                
                # Check first element for job type keywords (Full time, Part time, Contract, Casual)
                if any(kw in elem_text for kw in ['full time', 'full-time', 'fulltime', 
                                                      'part time', 'part-time', 'parttime',
                                                      'contract', 'casual', 'temporary']):
                    job_type_raw = clean_text(elem.get_text())
                    break
            
            # If not found, look for employment type (Permanent, Temporary)
            if job_type_raw == 'N/A' and type_texts:
                for text in type_texts:
                    if any(kw in text for kw in ['permanent', 'temporary']):
                        job_type_raw = clean_text(text)
                        break
            
            # Extract location (may include multiple location elements)
            location_raw = 'N/A'
            location_elements = job_card.select(self.SELECTORS['location'])
            if location_elements:
                location_parts = []
                for elem in location_elements:
                    loc_text = clean_text(elem.get_text())
                    # Remove trailing comma if present
                    loc_text = loc_text.rstrip(',').strip()
                    if loc_text:
                        location_parts.append(loc_text)
                
                # Join locations with comma separator
                if location_parts:
                    location_raw = ', '.join(location_parts)
            
            # Extract posted date
            posted_date = 'N/A'
            try:
                posted_elem = job_card.select_one(self.SELECTORS['posted_date'])
                if posted_elem:
                    posted_date = clean_text(posted_elem.get_text())
            except Exception:
                pass
            
            # Description - fetch from detail page
            description = 'N/A'
            contact_name_raw = None
            phone_number_raw = None
            company_email_raw = None
            apply_url = None
            sponsorship_signal = None
            
            # Try to fetch full description from job detail page
            try:
                if job_url and job_url != 'N/A':
                    # Open job detail page in new tab
                    job_page = await self.browser.new_page()
                    job_page.set_default_timeout(PAGE_LOAD_TIMEOUT * 1000)
                    
                    # Navigate to job detail
                    full_url = self.BASE_URL + job_url if job_url.startswith('/') else job_url
                    await job_page.goto(full_url, wait_until='domcontentloaded')
                    
                    # Wait for potential CF on job detail page
                    job_html = await job_page.content()
                    if _is_cloudflare_page(job_html):
                        await _wait_for_turnstile(job_page, timeout_ms=60000)
                    
                    # Wait for description to load
                    try:
                        await job_page.wait_for_selector('div#jvDescription .job-text p', timeout=10000)
                    except:
                        pass  # Description might not be there
                    
                    # Extract description from all <p> tags in job-text div
                    job_html = await job_page.content()
                    soup_job = BeautifulSoup(job_html, 'lxml')
                    
                    # Find all p tags in the job description div
                    desc_div = soup_job.select_one('div#jvDescription .job-text')
                    if desc_div:
                        p_tags = desc_div.select('p')
                        if p_tags:
                            desc_parts = []
                            for p in p_tags:
                                p_text = clean_text(p.get_text())
                                if p_text:
                                    desc_parts.append(p_text)
                            
                            if desc_parts:
                                description = '\n\n'.join(desc_parts)
                                logger.info(f"    Extracted description: {len(description)} chars")
                    
                    await job_page.close()
            except Exception as e:
                logger.warning(f"    Could not fetch full description: {str(e)[:60]}")
                description = 'N/A'
            
            # Transform data
            state_enum = normalize_state(location_raw)
            job_type_enum = normalize_job_type(job_type_raw)
            salary_min, salary_max, salary_type = extract_salary_parts(salary_raw)
            level = detect_job_level(title, description)
            job_skills = extract_skills(description)
            first_name, last_name = split_contact_name(contact_name_raw)
            sponsorship_int = map_sponsorship(sponsorship_signal, description)
            employer_website = extract_website_from_text(description)
            
            if not phone_number_raw and description and description != 'N/A':
                phone_number_raw = extract_phone_from_text(description)
            
            if self.use_ai:
                sponsorship_signal = 'unknown'
            
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
                'source':               self.BASE_URL + job_url if job_url.startswith('/') else job_url,
                'sponsorship':          sponsorship_int,
                'salary_min':           salary_min,
                'salary_max':           salary_max,
                'salary_type':          salary_type,
                'job_skills':           job_skills,
            }
            
            return job_data
        
        except Exception as e:
            logger.error(f"Error extracting job data: {str(e)}")
            return None
    
    async def close(self):
        """Close the Camoufox browser"""
        try:
            if self.page:
                await self.page.close()
            if self.browser:
                await self.browser.close()
            # For Camoufox, use the context manager exit
            if hasattr(self, 'camoufox_cm') and self.camoufox_cm:
                await self.camoufox_cm.__aexit__(None, None, None)
            logger.info(" Camoufox browser closed")
        except Exception as e:
            logger.error(f"Error closing browser: {e}")


# Wrapper function for async execution (for compatibility with sync code)
def run_async_search(scraper, keyword: str, location: str, pages: int, should_cancel=None, date_filter: Optional[int] = None):
    """Run async search in sync context"""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    return loop.run_until_complete(scraper.search_jobs(keyword, location, pages, should_cancel, date_filter))


def run_async_close(scraper):
    """Run async close in sync context"""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    return loop.run_until_complete(scraper.close())
