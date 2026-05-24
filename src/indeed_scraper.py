"""
Main scraper class for Indeed Australia job listings using Playwright and Camoufox
"""

import asyncio
from bs4 import BeautifulSoup
from typing import List, Dict, Any, Optional
import re

from src.config import (
    MAX_PAGES_PER_SEARCH,
    DELAY_BETWEEN_REQUESTS,
    FETCH_FULL_DESCRIPTION,
    USE_AI_ANALYSIS,
    GEMINI_API_KEYS,
    GEMINI_MODEL,
    AI_RATE_LIMIT_RPM,
)
from src.utils import logger, clean_text, random_delay, get_current_timestamp

INDEED_BASE_URL = "https://au.indeed.com"


class IndeedScraper:
    """Scraper for Indeed Australia job listings using Playwright/Camoufox"""

    def __init__(self, headless: bool = False, use_ai: bool = USE_AI_ANALYSIS):
        self.headless = headless
        self.use_ai = use_ai
        self.jobs_data = []
        self.ai_analyzer = None

        # Initialize AI analyzer if enabled
        if self.use_ai:
            try:
                from src.ai_analyzer import GeminiAnalyzer

                self.ai_analyzer = GeminiAnalyzer(
                    api_keys=GEMINI_API_KEYS,
                    model_name=GEMINI_MODEL,
                    rate_limit_rpm=AI_RATE_LIMIT_RPM,
                )
                logger.info("AI Analyzer initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize AI Analyzer: {str(e)}")
                logger.warning("Continuing without AI analysis")
                self.use_ai = False

    def setup_driver(self):
        """No-op for compatibility with main.py structure.
        Playwright starts instances on demand via get_page_source_playwright.
        """
        pass

    def close(self):
        """No-op for compatibility with main.py structure."""
        pass

    def search_jobs(
        self,
        job_keyword: str = "",
        location: str = "",
        max_pages: int = MAX_PAGES_PER_SEARCH,
        should_cancel: Optional[callable] = None,
        progress_callback: Optional[callable] = None,
        headless: Optional[bool] = None,
        fromage: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        import asyncio
        import sys
        import gc

        # On Windows, ensure the ProactorEventLoop is used as it's required by Playwright
        if sys.platform == 'win32':
            try:
                asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
            except Exception:
                pass

        async def run_and_clean():
            """Wrapper to ensure resources are cleaned up before loop closes"""
            try:
                # Use passed headless parameter, fallback to instance headless, default to False
                headless_mode = headless if headless is not None else self.headless
                res = await self._async_search_jobs(job_keyword, location, max_pages, should_cancel, progress_callback, headless_mode, fromage)
                # Give a small window for background transports and tasks to settle
                await asyncio.sleep(0.5)
                # Explicitly collect garbage to trigger __del__ while loop is still open
                gc.collect()
                return res
            except Exception as e:
                logger.error(f"Error in async search runner: {str(e)}")
                return []

        try:
            # asyncio.run is the recommended way in Modern Python (3.7+)
            # It handles creating the loop, running the task, and closing the loop cleanly.
            return asyncio.run(run_and_clean())
        except RuntimeError:
            # If for some reason a loop is already running in this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(
                    run_and_clean()
                )
            finally:
                # Extra safety cleanup for manual loop management
                loop.run_until_complete(asyncio.sleep(0.5))
                gc.collect()
                loop.close()
        except Exception as e:
            logger.error(f"Critical error in search_jobs: {str(e)}")
            return []

    async def _async_search_jobs(
        self, job_keyword: str, location: str, max_pages: int, should_cancel: Optional[callable] = None, progress_callback: Optional[callable] = None, headless: bool = False, fromage: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        from src.playwright_helper import (
            create_browser_context,
            _wait_for_turnstile,
            _is_cloudflare_page,
        )

        logger.info(
            f"Starting Indeed job search - Keyword: '{job_keyword}', Location: '{location}'"
        )
        jobs = []
        seen_job_urls = set()
        page_num = 1

        print(
            f"\n[INDEED] Starting Camoufox Browser session (Persistent) for search: '{job_keyword}'"
        )
        try:
            cf, browser, _ = await create_browser_context(bypass_cf=True, headless=headless)
        except Exception as e:
            logger.error(f"Failed to initialize Camoufox: {e}")
            return jobs

        try:
            main_page = await browser.new_page()

            while page_num <= max_pages:
                initial_job_count = len(jobs)
                # Check for cancellation
                if should_cancel and should_cancel():
                    logger.info(f"[CANCEL] Indeed scraping stopped by user at page {page_num}")
                    break

                logger.info(f"Scraping Indeed page {page_num}/{max_pages}")

                print(f"[INDEED] Opening Search Page {page_num}/{max_pages}...")

                url = self._build_url(job_keyword, location, page_num, fromage)
                await main_page.goto(url, wait_until="domcontentloaded")
                await asyncio.sleep(2)  # Give time for challenge to render if present

                # Check for CF challenge
                html = await main_page.content()
                if _is_cloudflare_page(html):
                    print("[INDEED] Solving Cloudflare Turnstile on Search Page...")
                    await _wait_for_turnstile(main_page)

                # Try waiting for elements
                try:
                    await main_page.wait_for_selector(".job_seen_beacon", timeout=15000)
                except Exception:
                    pass

                html = await main_page.content()
                soup = BeautifulSoup(html, "lxml")
                job_cards = soup.select(".job_seen_beacon")

                if not job_cards:
                    print(
                        "[INDEED] No data found on first try. Attempting reload to clear stale cached redirects..."
                    )
                    await main_page.reload(wait_until="domcontentloaded")
                    await asyncio.sleep(3)
                    if _is_cloudflare_page(await main_page.content()):
                        await _wait_for_turnstile(main_page)

                    try:
                        await main_page.wait_for_selector(
                            ".job_seen_beacon", timeout=10000
                        )
                    except Exception:
                        pass

                    html = await main_page.content()
                    soup = BeautifulSoup(html, "lxml")
                    job_cards = soup.select(".job_seen_beacon")

                if not job_cards:
                    print(
                        f"[INDEED] Page {page_num} definitively blocked or no data found. Stopping."
                    )
                    break

                print(
                    f"[INDEED] Processing {len(job_cards)} job cards on page {page_num}..."
                )

                locators = await main_page.locator(".job_seen_beacon").all()
                if len(locators) != len(job_cards):
                    logger.warning(
                        "Mismatch between BeautifulSoup cards and Playwright locators."
                    )

                for i, card in enumerate(job_cards):
                    job_data = self._extract_job_data_from_beautifulsoup(card)

                    if not job_data:
                        continue
                        
                    # Inject date_posted based on fromage parameter
                    job_data["date_posted"] = "Last 24 hours" if fromage == 1 else "Anytime"
                    
                    # Deduplicate by jk ID (handles /rc/clk vs /viewjob phantom duplicates)
                    jk_id = self._extract_jk_id(job_data.get("apply_form", "N/A"))
                    if jk_id:
                        if jk_id in seen_job_urls:
                            logger.info(f"Skipping duplicate job (jk={jk_id}): {job_data.get('title')}")
                            continue
                        seen_job_urls.add(jk_id)
                    elif job_data.get("apply_form", "N/A") == "N/A":
                        # No URL at all — skip
                        continue

                    if (
                        FETCH_FULL_DESCRIPTION
                        and job_data["apply_form"] != "N/A"
                        and i < len(locators)
                    ):
                        try:
                            # Click the card to load description (shorter timeout + element check)
                            title_loc = locators[i].locator("a.jcs-JobTitle")
                            if await title_loc.count() > 0:
                                await title_loc.first.evaluate(
                                    "node => { node.scrollIntoView({behavior: 'smooth', block: 'center'}); node.click(); }",
                                    timeout=10000
                                )
                                # Wait for Indeed's SPA panel to update
                                await asyncio.sleep(2)
                            else:
                                logger.warning(f"No clickable title found for card {i} (possible ad or layout difference)")
                                continue

                            # Panel wait is already handled in the if-block above

                            # # Extract description from the panel
                            # desc_loc = main_page.locator("#jobDescriptionText")
                            # if await desc_loc.count() > 0:
                            #     job_data[
                            #         "description"
                            #     ] = await desc_loc.first.inner_text()
                            #     logger.info(f"Successfully scraped full description for: {job_data.get('title', 'Unknown Job')}")
                            # else:
                            #     logger.warning(f"Could not find #jobDescriptionText panel for: {job_data.get('title', 'Unknown Job')}")
                                
                            #     desc_text = job_data["description"]
                            #     # Extract salary type from description
                            #     # if job_data.get("salary_type", "N/A") == "N/A":
                            #     #     desc_lower = desc_text.lower()
                            #     #     if "hourly" in desc_lower:
                            #     #         job_data["salary_type"] = "hourly"
                            #     #     elif "monthly" in desc_lower:
                            #     #         job_data["salary_type"] = "monthly"
                            #     #     elif "yearly" in desc_lower:
                            #     #         job_data["salary_type"] = "yearly"

                            #     salary_pattern = r"\$[\d,]+(?:\.\d+)?\s*[-\u2013]\s*\$[\d,]+(?:\.\d+)?(?:\s*(?:per|an?|/)\s*\w+)?"
                            #     rate_context = re.search(
                            #         r"[^\n]*rates?[^\n]*", desc_text, re.IGNORECASE
                            #     )
                            #     if rate_context:
                            #         salary_match = re.search(
                            #             salary_pattern,
                            #             rate_context.group(0),
                            #             re.IGNORECASE,
                            #         )
                            #         if (
                            #             salary_match
                            #             and job_data.get("_raw_salary", "N/A") == "N/A"
                            #         ):
                            #             job_data["_raw_salary"] = salary_match.group(0)
                            #             logger.info(
                            #                 f"Salary extracted from description: {salary_match.group(0)}"
                            #             )

                            # Extract description from the panel
                            desc_loc = main_page.locator("#jobDescriptionText")
                            if await desc_loc.count() > 0:
                                job_data[
                                    "description"
                                ] = await desc_loc.first.inner_text()
                                logger.info(
                                    f"Successfully scraped full description for: {job_data.get('title', 'Unknown Job')}"
                                )
                            else:
                                logger.warning(
                                    f"Could not find #jobDescriptionText panel for: {job_data.get('title', 'Unknown Job')}. Mencoba deteksi Captcha/Turnstile..."
                                )
                                # Lakukan bypass Turnstile (coba paksa walau bukan 'cloudflare' page explicit)
                                # Tunggu sejenak agar iframe injeksi Turnstile SPA termuat penuh
                                await asyncio.sleep(2.5)
                                from src.playwright_helper import _click_turnstile_checkbox
                                clicked = await _click_turnstile_checkbox(main_page)
                                if clicked:
                                    logger.info("[INDEED] Kotak Captcha/Turnstile diklik pada panel sisi kanan. Menunggu resolusi...")
                                    await asyncio.sleep(5)
                                    # Coba scrap ulang description panelnya setelah di klik
                                    if await desc_loc.count() > 0:
                                        job_data["description"] = await desc_loc.first.inner_text()
                                        logger.info(f"Berhasil memuat dekskripsi #{job_data.get('title')} pasca bypass Cloudflare!")


                            # --- Salary extraction from description text ---
                            # Always runs after description is set (whether from panel or snippet),
                            # but only fills in salary if not already found from card/panel metadata.
                            if job_data.get("_raw_salary", "N/A") == "N/A":
                                desc_text = job_data.get("description", "")
                                if desc_text and desc_text != "N/A":
                                    # Detect salary_type from surrounding words BEFORE the dollar sign
                                    # e.g. "Hourly rates range between $39.89 - $53.67"
                                    salary_type_pattern = re.search(
                                        r"\b(hour(?:ly)?|day(?:ily)?|week(?:ly)?|fortnight(?:ly)?|month(?:ly)?|year(?:ly)?|annual(?:ly)?|p\.a)\b",
                                        desc_text,
                                        re.IGNORECASE,
                                    )
                                    if salary_type_pattern:
                                        st = salary_type_pattern.group(1).lower()
                                        if st.startswith("hour"):
                                            job_data["salary_type"] = "hour"
                                        elif st.startswith("day"):
                                            job_data["salary_type"] = "day"
                                        elif st.startswith("week"):
                                            job_data["salary_type"] = "week"
                                        elif st.startswith("fortnight"):
                                            job_data["salary_type"] = "fortnight"
                                        elif st.startswith("month"):
                                            job_data["salary_type"] = "month"
                                        elif (
                                            st.startswith("year")
                                            or st.startswith("annual")
                                            or st == "p.a"
                                        ):
                                            job_data["salary_type"] = "year"

                                    # Broad salary range pattern: $X - $Y, A$X - A$Y, $X–$Y, $X k - $Y k
                                    salary_range_pattern = r"(?:A?\$|AUD)\s*[\d,]+(?:\.\d+)?\s*[kK]?\s*[-\u2013]\s*(?:A?\$|AUD)\s*[\d,]+(?:\.\d+)?\s*[kK]?"
                                    # Single salary pattern: $X per hour/year, A$X, $Xk etc.
                                    salary_single_pattern = (
                                        r"(?:A?\$|AUD)\s*[\d,]+(?:\.\d+)?\s*[kK]?(?:\s*(?:per|an?|/)\s*\w+)?"
                                    )

                                    salary_match = re.search(
                                        salary_range_pattern, desc_text
                                    ) or re.search(salary_single_pattern, desc_text)
                                    if salary_match:
                                        job_data["_raw_salary"] = salary_match.group(0)
                                        # logger.info(
                                        #     f"Salary extracted from description: {salary_match.group(0)}"
                                        # )
                            # Tunggu #salaryInfoAndJobType muncul sebelum ambil HTML
                            # Elemen ini di-render JS belakangan — tanpa wait, sering kosong
                            try:
                                await main_page.wait_for_selector(
                                    "#salaryInfoAndJobType", timeout=5000
                                )
                            except Exception:
                                pass  # Tidak semua job punya section ini — lanjut saja
                            # Attempt to get Apply Link from panel
                            pane_html = await main_page.content()
                            pane_soup = BeautifulSoup(pane_html, "lxml")

                            # Extract "Apply on company site" strictly for application_url
                            apply_links = pane_soup.find_all("a", href=True)
                            for a in apply_links:
                                text_val = clean_text(a.get_text())
                                if "Apply on company site" in text_val:
                                    if (
                                        "indeed.com" not in a["href"]
                                        or "/rc/clk" in a["href"]
                                        or "/apply" in a["href"]
                                    ):
                                        job_data["application_url"] = a["href"]
                                        break

                            # Extract precise target address from jobLocationText
                            address_container = pane_soup.select_one("#jobLocationText, div[class*='jobLocationText']")
                            if address_container:
                                inner_div = address_container.find("div", attrs={"data-testid": True})
                                if inner_div:
                                    job_data["employer_address"] = clean_text(inner_div.get_text())
                                else:
                                    job_data["employer_address"] = clean_text(address_container.get_text())

                            # Extract Job Type and Salary from #jobDetailsSection
                            job_details_section = pane_soup.select_one(
                                "#salaryInfoAndJobType"
                            )
                            if job_details_section:
                                type_spans = job_details_section.find_all("span")
                                if type_spans:
                                    types = []
                                    salaries = []
                                    for s in type_spans:
                                        t = clean_text(s.get_text())
                                        # Bersihkan prefix " - " yang muncul di span gabungan
                                        # contoh: " -  Full-time, Casual" → "Full-time, Casual"
                                        t = re.sub(r"^[\s\-–—]+", "", t).strip()
                                        if (
                                            t
                                            and len(t) > 2
                                            and t.lower() not in ["job type", "pay"]
                                        ):
                                            if "$" in t:
                                                if t not in salaries:
                                                    salaries.append(t)
                                            else:
                                                if t not in types:
                                                    types.append(t)
                                    if types:
                                        # Map Indeed types to the required enum values
                                        mapped_types = [self._map_job_type(t) for t in types]
                                        job_data["type"] = ", ".join(
                                            dict.fromkeys(mapped_types)
                                        )
                                    # Salary from #jobDetailsSection is the primary source
                                    if salaries:
                                        job_data["_raw_salary"] = ", ".join(
                                            dict.fromkeys(salaries)
                                        )
                                    # If no $ found in #jobDetailsSection, fallback to .salary-snippet-container already set from card

                        except Exception as e:
                            logger.error(f"Error fetch detail inline: {e}")

                    # Finalize mappings
                    if (
                        job_data.get("application_url")
                        and job_data["application_url"] != "N/A"
                    ):
                        job_data["source"] = job_data["application_url"]
                    elif job_data.get("apply_form") and job_data["apply_form"] != "N/A":
                        job_data["source"] = job_data["apply_form"]

                    # Extract phone number from description
                    job_data["employer_phone_number"] = self._extract_phone_numbers(
                        job_data.get("description", "")
                    )

                    # Extract emails from description
                    job_data["employer_email"] = self._extract_emails(
                        job_data.get("description", "")
                    )

                    # Check sponsorship
                    desc_lower = str(job_data.get("description", "")).lower()
                    if any(
                        kw in desc_lower
                        for kw in [
                            "sponsorship",
                            "available sponsorship",
                            "state sponsorship",
                            "state sponsrship",
                        ]
                    ):
                        job_data["sponsorship"] = 1

                    # Process Salary
                    raw_salary = job_data.get("_raw_salary", "N/A")
                    if raw_salary != "N/A":
                        s_lower = raw_salary.lower()
                        if (
                            "year" in s_lower
                            or "annually" in s_lower
                            or "p.a" in s_lower
                        ):
                            job_data["salary_type"] = "year"
                        elif "month" in s_lower:
                            job_data["salary_type"] = "month"
                        elif "week" in s_lower:
                            job_data["salary_type"] = "week"
                        elif "day" in s_lower:
                            job_data["salary_type"] = "day"
                        elif "hour" in s_lower:
                            job_data["salary_type"] = "hour"

                       

                        matches = re.findall(
                            r"(?:A?\$|AUD)?\s*\d{1,3}(?:,\d{3})*(?:\.\d+)?\s*[kK]?", raw_salary
                        )
                        amounts = []
                        for m in matches:
                            val_str = m.strip()
                            # Prepend $ if not present but a numeric was matched
                            if not any(s in val_str.upper() for s in ['$', 'AUD']):
                                val_str = f"${val_str}"
                            amounts.append(val_str)

                        if len(amounts) == 1:
                            job_data["salary_min"] = amounts[0]
                            job_data["salary_max"] = amounts[0]
                        elif len(amounts) >= 2:
                            job_data["salary_min"] = amounts[0]
                            job_data["salary_max"] = amounts[1]

                    # Clean up temporary fields
                    job_data.pop("_raw_salary", None)
                    job_data.pop("apply_form", None)
                    job_data.pop("application_url", None)

                    # Add scraping timestamp
                    job_data["scraping_timestamp"] = get_current_timestamp()

                    jobs.append(job_data)

                extracted_count = len(jobs) - initial_job_count
                msg = f"[INDEED] Page {page_num} extracted successfully! Scraped {extracted_count} jobs."
                logger.info(msg)

                if not self._has_next_page(html):
                    break

                page_num += 1
                random_delay(DELAY_BETWEEN_REQUESTS, DELAY_BETWEEN_REQUESTS + 2)

            if self.use_ai and self.ai_analyzer and jobs:
                jobs = self.ai_analyzer.analyze_batch(jobs)

            self.jobs_data.extend(jobs)
            return jobs

        except Exception as e:
            logger.error(f"Error during Indeed job search: {str(e)}")
            return jobs
        finally:
            await browser.close()
            await cf.__aexit__(None, None, None)

    def _build_url(self, job_keyword: str, location: str, page: int, fromage: Optional[int] = None) -> str:
        """Build Indeed search URL"""
        url = f"{INDEED_BASE_URL}/jobs"
        params = []
        if job_keyword:
            params.append(f"q={job_keyword.replace(' ', '+')}")
        if location:
            params.append(f"l={location.replace(' ', '+')}")
        if page > 1:
            start_index = (page - 1) * 10
            params.append(f"start={start_index}")
        if fromage:
            params.append(f"fromage={fromage}")

        if params:
            url += "?" + "&".join(params)
        return url

    def _extract_job_data_from_beautifulsoup(
        self, job_card
    ) -> Optional[Dict[str, Any]]:
        """Extract data from a single Indeed job HTML card via BeautifulSoup"""
        try:
            job_data = {
                "employer_email": "N/A",
                "employer_first_name": "N/A",
                "employer_last_name": "N/A",
                "employer_phone_number": "N/A",
                "employer_company_name": "N/A",
                "employer_state": "N/A",
                "employer_size": "N/A",
                "employer_address": "N/A",
                "employer_industry": "N/A",
                "employer_website_url": "N/A",
                "employer_description": "N/A",
                "title": "N/A",
                "description": "N/A",
                "level": "N/A",
                "location": "N/A",
                "state": "N/A",
                "type": "N/A",
                "source": "N/A",
                "date_posted": "N/A",
                "sponsorship": 0,
                "salary_min": "N/A",
                "salary_max": "N/A",
                "salary_type": "N/A",
                "job_skills": "N/A",
                # Temp fields
                "_raw_salary": "N/A",
                "apply_form": "N/A",
                "application_url": "N/A",
            }

            # Job Title
            title_elem = job_card.select_one("h2.jobTitle span[title], .jobTitle span")
            if title_elem:
                job_data["title"] = clean_text(title_elem.get_text())

            # Company Name
            comp_elem = job_card.select_one('[data-testid="company-name"]')
            if comp_elem:
                job_data["employer_company_name"] = clean_text(comp_elem.get_text())

            # Location
            loc_elem = job_card.select_one('[data-testid="text-location"]')
            if loc_elem:
                job_data["location"] = clean_text(loc_elem.get_text())
                job_data["state"] = self._extract_state(job_data["location"])
                job_data["employer_state"] = job_data["state"]

            # Salary (fallback from card — will be overridden by #jobDetailsSection if $ found there)
            sal_elem = job_card.select_one(".salary-snippet-container")
            if sal_elem:
                sal_text = clean_text(sal_elem.get_text())
                if "$" in sal_text:
                    job_data["_raw_salary"] = sal_text

            # Job Type
            for type_elem in job_card.select(
                '[data-testid="attribute_snippet_testid"]'
            ):
                text_val = type_elem.get_text().lower()
                if "$" not in text_val and any(
                    kw in text_val
                    for kw in [
                        "full-time",
                        "part-time",
                        "full time",
                        "part time",
                        "contract",
                        "casual",
                    ]
                ):
                    job_data["type"] = self._map_job_type(clean_text(type_elem.get_text()))
                    break

            # Url
            link_elem = job_card.select_one("a.jcs-JobTitle")
            if link_elem and link_elem.get("href"):
                href = link_elem["href"]
                if href.startswith("/rc"):
                    href = INDEED_BASE_URL + href
                elif href.startswith("/viewjob"):
                    # This is a duplicate phantom card for an external job — skip it
                    return False
                job_data["apply_form"] = href

            # Description Snippet
            desc_elem = job_card.select_one(".job-snippet")
            if desc_elem:
                job_data["description"] = clean_text(desc_elem.get_text())

            # Posted Date
            date_elem = job_card.select_one('[data-testid="myJobsStateDate"]')
            if date_elem:
                job_data["posted_date"] = clean_text(date_elem.get_text())
            else:
                date_elem2 = job_card.select_one(".date")
                if date_elem2:
                    job_data["posted_date"] = (
                        clean_text(date_elem2.get_text()).replace("Posted", "").strip()
                    )

            return job_data

        except Exception as e:
            logger.error(f"Error extracting Indeed job data: {str(e)}")
            return None

    def _extract_jk_id(self, url: str) -> Optional[str]:
        """Extract the jk ID from an Indeed job URL (works for both /rc/clk and /viewjob)"""
        if not url or url == "N/A":
            return None
        match = re.search(r'[?&]jk=([a-f0-9]+)', url)
        return match.group(1) if match else None

    def _extract_state(self, location: str) -> str:
        """Extract Australian state from location string"""
        if not location or location == "N/A":
            return "N/A"

        location_upper = location.upper()
        state_map = {
            "NSW": "New South Wales",
            "VIC": "Victoria",
            "QLD": "Queensland",
            "WA": "Western Australia",
            "SA": "South Australia",
            "TAS": "Tasmania",
            "ACT": "Australian Capital Territory",
            "NT": "Northern Territory",
        }
        for abbr, full_name in state_map.items():
            if re.search(rf"\b{abbr}\b", location_upper) or full_name.upper() in location_upper:
                return abbr
        return "N/A"

    def _extract_phone_numbers(self, text: str) -> str:
        """Extract Australian phone numbers from text"""
        if not text or text == "N/A":
            return "N/A"
            
        # Regex for common Australian phone formats:
        # Handles: 04xx xxx xxx, (0x) xxxx xxxx, 0x xxxx xxxx, +61 x xxxx xxxx
        # Supports spaces, hyphens and dots as separators
        phone_pattern = r"((?:\+61|0)[2-478](?:[ \-\.]?[0-9]){8,9}\b)"
        landline_plus_pattern = r"(\([0-9]{2}\)[ \-\.]?[0-9]{4}[ \-\.]?[0-9]{4})"
        
        matches = re.findall(phone_pattern, text)
        matches += re.findall(landline_plus_pattern, text)
        
        if matches:
            # Clean and deduplicate
            unique_phones = []
            for p in matches:
                # Basic cleaning: remove double spaces if any
                clean_p = re.sub(r"\s+", " ", p).strip()
                if clean_p not in unique_phones:
                    unique_phones.append(clean_p)
            return ", ".join(unique_phones)
            
        return "N/A"

    def _extract_emails(self, text: str) -> str:
        """Extract email addresses from text"""
        if not text or text == "N/A":
            return "N/A"
            
        # Regex for common email formats
        email_pattern = r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"
        
        matches = re.findall(email_pattern, text)
        
        if matches:
            # Clean and deduplicate
            unique_emails = []
            for e in matches:
                clean_e = e.strip()
                if clean_e.endswith('.'):
                    clean_e = clean_e[:-1]
                if clean_e not in unique_emails:
                    unique_emails.append(clean_e)
            return ", ".join(unique_emails)
            
        return "N/A"

    def _map_job_type(self, type_str: str) -> str:
        """Map Indeed's job type to standardized enum values"""
        if not type_str or type_str == "N/A":
            return "N/A"
        
        t = type_str.lower()
        if "contract" in t:
            return "contract"
        if "casual" in t or "temporary" in t:
            return "casual_temporary"
        if "part-time" in t or "part time" in t:
            return "part_time"
        if "permanent" in t:
            return "permanent"
        if "full-time" in t or "full time" in t:
            return "full_time"
            
        return type_str

    def _has_next_page(self, html: str) -> bool:
        """Check if there's a next page available on Indeed"""
        soup = BeautifulSoup(html, "lxml")
        next_btn = soup.select_one('[data-testid="pagination-page-next"]')
        if next_btn:
            logger.info("Indeed Next page button found")
            return True
        return False