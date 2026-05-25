import asyncio
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
import urllib.parse
from datetime import datetime

from src.config import (
    HEADLESS_MODE, PAGE_LOAD_TIMEOUT, DELAY_BETWEEN_REQUESTS
)
from src.utils import logger, clean_text, adaptive_delay
from src.playwright_helper import create_browser_context

class PCGamingWikiScraper:
    """Scraper for PCGamingWiki games and system requirements using Camoufox"""
    
    BASE_URL = "https://www.pcgamingwiki.com"
    START_URL = "https://www.pcgamingwiki.com/wiki/Category:Games"
    
    def __init__(self, headless: bool = HEADLESS_MODE):
        self.headless = headless
        self.camoufox_cm = None
        self.browser = None
        self.page = None
        self.games_data = []

    async def setup_browser(self):
        """Setup Camoufox browser"""
        try:
            logger.info("Initializing Camoufox browser for PCGamingWiki...")
            self.camoufox_cm, self.browser, _ = await create_browser_context(bypass_cf=True, headless=self.headless)
            self.page = await self.browser.new_page()
            self.page.set_default_timeout(PAGE_LOAD_TIMEOUT * 1000)
            self.page.set_default_navigation_timeout(PAGE_LOAD_TIMEOUT * 1000)
            logger.info("Browser initialized successfully")
        except Exception as e:
            logger.error(f"Failed to setup browser: {str(e)}")
            raise

    async def close(self):
        """Close browser resources safely"""
        if self.page:
            try:
                await self.page.close()
            except:
                pass
        if self.browser:
            try:
                await self.browser.close()
            except:
                pass
        if self.camoufox_cm:
            try:
                await self.camoufox_cm.__aexit__(None, None, None)
            except:
                pass

    async def scrape(self, start_url: str = START_URL, max_pages: int = 1, max_games_per_page: int = 0,
                     should_cancel=None, target_alphabet: str = None, existing_urls: set = None,
                     checkpoint_callback=None, checkpoint_every: int = 500) -> List[Dict[str, Any]]:
        """
        Main scraping loop:
        1. Navigate to List Page
        2. Extract game links
        3. Visit each game link and extract system requirements
        4. Go to Next Page

        checkpoint_callback: called every `checkpoint_every` games with (list_of_new_games, total_so_far)
        """
        if existing_urls is None:
            existing_urls = set()

        if target_alphabet:
            separator = "&" if "?" in start_url else "?"
            start_url = f"{start_url}{separator}from={target_alphabet.upper()}"

        all_scraped_games = []
        current_url = start_url
        current_page_num = 1
        games_since_last_checkpoint = 0

        try:
            if not self.page:
                await self.setup_browser()

            while current_page_num <= max_pages and current_url:
                if should_cancel and should_cancel():
                    logger.info("Cancellation detected! Stopping pagination.")
                    break

                logger.info(f"\n{'='*60}")
                logger.info(f" PAGE {current_page_num} of {max_pages}")
                logger.info(f" URL: {current_url}")
                logger.info(f"{'='*60}")

                # 1. Load the list page
                logger.info("Loading list page...")
                await self.page.goto(current_url, wait_until='domcontentloaded')
                await asyncio.sleep(2)

                # 2. Extract game URLs
                html_content = await self.page.content()
                soup = BeautifulSoup(html_content, 'lxml')
                game_links = []
                
                # Target specifically #mw-pages to avoid scraping subcategories
                category_groups = soup.select('#mw-pages .mw-category-group')
                game_links = []
                finished_target_alphabet = False
                
                for group in category_groups:
                    if finished_target_alphabet:
                        break
                        
                    h3 = group.find('h3')
                    if h3 and target_alphabet:
                        current_letter = clean_text(h3.get_text()).upper()
                        if current_letter != target_alphabet.upper():
                            logger.info(f"Reached alphabet '{current_letter}'. Finished scraping target alphabet '{target_alphabet.upper()}'.")
                            finished_target_alphabet = True
                            break
                            
                    a_tags = group.select('ul li a')
                    for a_tag in a_tags:
                        href = a_tag.get('href')
                        title = clean_text(a_tag.get_text())
                        if href:
                            full_url = urllib.parse.urljoin(self.BASE_URL, href)
                            if full_url in existing_urls:
                                logger.info(f"Skipping already scraped game: {title}")
                                continue
                            game_links.append({"title": title, "url": full_url})

                if max_games_per_page > 0:
                    game_links = game_links[:max_games_per_page]
                    logger.info(f"Test mode: Limited to {len(game_links)} games on this page.")
                else:
                    logger.info(f"Found {len(game_links)} games on page {current_page_num}.")

                if len(game_links) == 0:
                    logger.warning("0 games found! Dumping HTML and taking screenshot for debugging.")
                    import os
                    os.makedirs("debug", exist_ok=True)
                    with open("debug/page_source.html", "w", encoding="utf-8") as f:
                        f.write(html_content)
                    await self.page.screenshot(path="debug/page_screenshot.png")
                    logger.warning("Debug files saved to debug/ directory.")

                # 3. Visit each game and extract details
                for idx, game_info in enumerate(game_links):
                    if should_cancel and should_cancel():
                        logger.info("Cancellation detected! Stopping game extraction.")
                        # Trigger final checkpoint before stopping
                        if checkpoint_callback and games_since_last_checkpoint > 0:
                            checkpoint_callback(all_scraped_games, len(all_scraped_games))
                        return all_scraped_games

                    logger.info(f"  [{idx+1}/{len(game_links)}] Scraping: {game_info['title']}")
                    game_data = await self._extract_game_details(game_info['url'], game_info['title'])
                    if game_data:
                        all_scraped_games.append(game_data)
                        games_since_last_checkpoint += 1

                        # --- Checkpoint save every N games ---
                        if checkpoint_callback and games_since_last_checkpoint >= checkpoint_every:
                            logger.info(f"  [CHECKPOINT] {len(all_scraped_games)} games scraped. Saving checkpoint...")
                            checkpoint_callback(all_scraped_games, len(all_scraped_games))
                            games_since_last_checkpoint = 0
                    
                    # Be polite to the wiki
                    adaptive_delay(1, DELAY_BETWEEN_REQUESTS)

                if finished_target_alphabet:
                    break

                # 4. Find the "Next Page" link
                next_page_tag = soup.find('a', string=lambda text: text and 'next page' in text.lower())
                if next_page_tag and next_page_tag.get('href'):
                    current_url = urllib.parse.urljoin(self.BASE_URL, next_page_tag.get('href'))
                    logger.info(f"Found next page link. Moving to page {current_page_num + 1}...")
                    current_page_num += 1
                else:
                    logger.info("No 'next page' link found. Reached the end.")
                    break

            return all_scraped_games

        except Exception as e:
            logger.error(f"Error during overall scraping: {str(e)}")
            return all_scraped_games
        finally:
            await self.close()


    async def _extract_game_details(self, url: str, title: str) -> Optional[Dict[str, Any]]:
        """Extract System Requirements and other details from a single game page"""
        try:
            await self.page.goto(url, wait_until='domcontentloaded')
            # Wait a short bit for tables to render if they are dynamic
            await asyncio.sleep(1.5)

            html_content = await self.page.content()
            soup = BeautifulSoup(html_content, 'lxml')

            # Base data
            data = {
                "Title": title,
                "URL": url,
                "Scraped_At": datetime.now().isoformat(),
                "Description": "N/A",
                "Cover_Image_URL": "N/A",
                "OS_Minimum": "N/A",
                "CPU_Minimum": "N/A",
                "RAM_Minimum": "N/A",
                "GPU_Minimum": "N/A",
                "Storage_Minimum": "N/A",
                "OS_Recommended": "N/A",
                "CPU_Recommended": "N/A",
                "RAM_Recommended": "N/A",
                "GPU_Recommended": "N/A",
                "Storage_Recommended": "N/A"
            }

            # --- Extract Cover Image URL ---
            # Image is inside: td.template-infobox-cover > a > img
            cover_img = soup.select_one('td.template-infobox-cover img')
            if cover_img:
                # Try to get the full-size image from srcset (format: "url 1.5x, url_full 2x")
                srcset = cover_img.get('srcset', '')
                if srcset:
                    # The last entry in srcset is the highest resolution (2x = full size)
                    last_entry = srcset.strip().split(',')[-1].strip()
                    full_url = last_entry.split(' ')[0].strip()
                    if full_url.startswith('http'):
                        data["Cover_Image_URL"] = full_url
                    else:
                        data["Cover_Image_URL"] = cover_img.get('src', 'N/A')
                else:
                    data["Cover_Image_URL"] = cover_img.get('src', 'N/A')

            # --- Extract Game Description ---
            # Description is inside: div.introduction (class, not id!)
            intro_div = soup.find('div', class_='introduction')
            if intro_div:
                # Get all paragraph text, skipping empty paragraphs (class="mw-empty-elt")
                paragraphs = intro_div.find_all('p')
                description_parts = []
                for p in paragraphs:
                    # Skip empty paragraphs
                    if 'mw-empty-elt' in p.get('class', []):
                        continue
                    text = clean_text(p.get_text())
                    # Remove citation markers like [Note 1], [2], [3]
                    import re
                    text = re.sub(r'\[.*?\]', '', text).strip()
                    if text:
                        description_parts.append(text)
                if description_parts:
                    data["Description"] = ' '.join(description_parts)

            # Based on user's HTML: <table class="pcgwikitable template-infotable" id="table-sysreqs-windows">
            sysreq_table = soup.find('table', id='table-sysreqs-windows')
            
            # Fallback check if it has a generic sysreq table without the specific id
            if not sysreq_table:
                sysreq_table = soup.find('table', class_='sysreq') or soup.find('table', class_='template-infotable')

            if sysreq_table:
                rows = sysreq_table.find_all('tr', class_='table-sysreqs-body-row')
                for row in rows:
                    param_th = row.find('th', class_='table-sysreqs-body-parameter')
                    min_td = row.find('td', class_='table-sysreqs-body-minimum')
                    
                    if param_th:
                        param_name = clean_text(param_th.get_text()).lower()
                        import re

                        if min_td:
                            min_val = clean_text(min_td.get_text())
                            
                            # Clean up citations like [Note 3] or [8] 
                            # This removes standard bracketed citations
                            min_val = re.sub(r'\[.*?\]', '', min_val).strip()

                            if 'operating system' in param_name or 'os' in param_name:
                                data["OS_Minimum"] = min_val
                            elif 'processor' in param_name or 'cpu' in param_name:
                                data["CPU_Minimum"] = min_val
                            elif 'memory' in param_name or 'ram' in param_name:
                                data["RAM_Minimum"] = min_val
                            elif 'video card' in param_name or 'gpu' in param_name:
                                data["GPU_Minimum"] = min_val
                            elif 'storage' in param_name or 'hdd' in param_name or 'ssd' in param_name:
                                data["Storage_Minimum"] = min_val
                                
                        rec_td = row.find('td', class_='table-sysreqs-body-recommended')
                        
                        rec_val = None
                        if rec_td:
                            rec_val = clean_text(rec_td.get_text())
                            rec_val = re.sub(r'\[.*?\]', '', rec_val).strip()

                        if rec_val and rec_val != "N/A":
                            if 'operating system' in param_name or 'os' in param_name:
                                data["OS_Recommended"] = rec_val
                            elif 'processor' in param_name or 'cpu' in param_name:
                                data["CPU_Recommended"] = rec_val
                            elif 'memory' in param_name or 'ram' in param_name:
                                data["RAM_Recommended"] = rec_val
                            elif 'video card' in param_name or 'gpu' in param_name:
                                data["GPU_Recommended"] = rec_val
                            elif 'storage' in param_name or 'hdd' in param_name or 'ssd' in param_name:
                                data["Storage_Recommended"] = rec_val
            else:
                logger.warning(f"    No Windows System Requirements table found for {title}")

            return data

        except Exception as e:
            logger.error(f"  Error extracting details for {title}: {str(e)}")
            return None
