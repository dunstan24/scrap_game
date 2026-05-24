"""
playwright_helper.py — Single fetch engine untuk semua state scraper.

Dua mode operasi:
  - bypass_cf=False (default) : headless biasa (Playwright), untuk state tanpa proteksi CF
  - bypass_cf=True            : headless CF-safe (Camoufox), khusus ACT (Cloudflare Turnstile)

Instalasi (jalankan sekali):
    pip install playwright camoufox[geoip]
    playwright install chromium
    python -m camoufox fetch
"""

import asyncio
import logging
import time
from typing import Optional

logger = logging.getLogger(__name__)


# ── Cek dependensi ─────────────────────────────────────────────────────────────

try:
    from playwright.async_api import async_playwright, Page, TimeoutError as PWTimeout

    _PLAYWRIGHT_AVAILABLE = True
except ImportError:
    _PLAYWRIGHT_AVAILABLE = False
    logger.error(
        "[Playwright] 'playwright' belum diinstall.\n"
        "Jalankan: pip install playwright && playwright install chromium"
    )

try:
    from camoufox.async_api import AsyncCamoufox

    _CAMOUFOX_AVAILABLE = True
except ImportError:
    _CAMOUFOX_AVAILABLE = False
    logger.warning(
        "[Camoufox] 'camoufox' belum diinstall.\n"
        "Jalankan: pip install camoufox[geoip] && python -m camoufox fetch\n"
        "bypass_cf=True tidak akan berfungsi tanpa camoufox."
    )


# ── Konstanta ──────────────────────────────────────────────────────────────────

_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)

_CLOUDFLARE_MARKERS = (
    "just a moment",
    "cloudflare",
    "security verification",
    "performing security",
    "enable javascript and cookies",
    "ray id:",
    "verify you are human",  # Explicit challenge text
)

_CLOUDFLARE_LOADING_MARKERS = (
    "cloudflare is evaluating your browser",
    "cloudflare is loading",
    "checking your browser",
    "please wait",
)

# Timeout dalam milidetik
_CF_TURNSTILE_TIMEOUT_MS = 90_000  # 90s — tunggu Turnstile auto-resolve (extended from 60s)
_PAGE_LOAD_TIMEOUT_MS = 90_000  # 90s — max load halaman (CF mode)
_SELECTOR_WAIT_MS = 30_000  # 30s — tunggu selector muncul
_HEADLESS_LOAD_TIMEOUT_MS = 30_000  # 30s — cukup untuk non-CF sites


# ── Helpers ────────────────────────────────────────────────────────────────────


def _is_cloudflare_page(html: str) -> bool:
    """Check if page shows Cloudflare challenge."""
    if not html:
        return False
    snippet = html[:5000].lower()
    return any(marker in snippet for marker in _CLOUDFLARE_MARKERS)


def _is_cloudflare_loading(html: str) -> bool:
    """Check if Cloudflare is in loading state (not fully rendered yet)."""
    if not html:
        return False
    snippet = html[:5000].lower()
    return any(marker in snippet for marker in _CLOUDFLARE_LOADING_MARKERS)


def _has_verify_human_text(html: str) -> bool:
    """Check if 'verify you are human' text is present (challenge fully loaded)."""
    if not html:
        return False
    snippet = html[:5000].lower()
    return "verify you are human" in snippet


async def _click_turnstile_checkbox(page) -> bool:
    """Coba klik checkbox Turnstile di dalam iframe. Return True jika berhasil klik."""
    import random

    # --- Strategi 1: Akses iframe Turnstile langsung via Playwright frame API ---
    try:
        frames = page.frames
        for frame in frames:
            if "challenges.cloudflare.com" in (frame.url or ""):
                logger.info(f"[Camoufox] Turnstile iframe ditemukan: {frame.url}")
                # Cari checkbox di dalam iframe
                try:
                    checkbox = frame.locator('input[type="checkbox"]')
                    if await checkbox.count() > 0:
                        await checkbox.first.click(timeout=5000)
                        logger.info("[Camoufox] Turnstile checkbox di-klik via frame API")
                        return True
                except Exception as e:
                    logger.debug(f"[Camoufox] Gagal klik checkbox di frame: {e}")

                # Fallback: klik area tengah dari iframe
                try:
                    # Cari elemen body di dalam frame dan klik
                    body = frame.locator("body")
                    if await body.count() > 0:
                        await body.first.click(position={"x": 28, "y": 28}, timeout=5000)
                        logger.info("[Camoufox] Klik body iframe Turnstile (posisi checkbox)")
                        return True
                except Exception as e:
                    logger.debug(f"[Camoufox] Gagal klik body frame: {e}")
    except Exception as e:
        logger.debug(f"[Camoufox] Error akses frames: {e}")

    # --- Strategi 2: Cari iframe element di main page dan klik berdasarkan bounding box ---
    try:
        # Cloudflare Turnstile iframe selectors
        iframe_selectors = [
            'iframe[src*="challenges.cloudflare.com"]',
            'iframe[src*="turnstile"]',
            '.cf-turnstile iframe',
            '#cf-turnstile iframe',
            'iframe[title*="Cloudflare"]',
            'iframe[title*="challenge"]',
        ]
        for selector in iframe_selectors:
            iframe_loc = page.locator(selector)
            if await iframe_loc.count() > 0:
                await iframe_loc.first.scroll_into_view_if_needed()
                await asyncio.sleep(0.5)
                bbox = await iframe_loc.first.bounding_box()
                if bbox:
                    click_x = bbox["x"] + 30 + random.uniform(-3, 3)
                    click_y = bbox["y"] + (bbox["height"] / 2) + random.uniform(-3, 3)
                    await page.mouse.move(click_x, click_y, steps=5)
                    await asyncio.sleep(random.uniform(0.1, 0.3))
                    await page.mouse.click(click_x, click_y, delay=random.randint(50, 150))
                    logger.info(f"[Camoufox] Native Mouse Klik internal Turnstile iframe selector: {selector} di posisi ({click_x:.1f}, {click_y:.1f})")
                    return True
    except Exception as e:
        logger.debug(f"[Camoufox] Error bounding box click: {e}")

    # --- Strategi 2.5: Cari berdasarkan dimensi widget Turnstile (Robust terhadap nama acak) ---
    try:
        iframes = await page.locator("iframe").all()
        for iframe_loc in iframes:
            try:
                await iframe_loc.scroll_into_view_if_needed(timeout=2000)
                await asyncio.sleep(0.2)
            except Exception:
                pass
            
            bbox = await iframe_loc.bounding_box()
            if bbox:
                # Dimensi Turnstile standar: ~300x65 pixels
                height = bbox["height"]
                width = bbox["width"]
                if 50 < height < 80 and 280 < width < 320:
                    click_x = bbox["x"] + 30 + random.uniform(-3, 3)
                    click_y = bbox["y"] + (height / 2) + random.uniform(-3, 3)
                    await page.mouse.move(click_x, click_y, steps=5)
                    await asyncio.sleep(random.uniform(0.1, 0.3))
                    await page.mouse.click(click_x, click_y, delay=random.randint(50, 150))
                    logger.info(f"[Camoufox] Native Mouse Klik Turnstile iframe via deteksi dimensi ({width}x{height}) di posisi ({click_x:.1f}, {click_y:.1f})")
                    return True
    except Exception as e:
        logger.debug(f"[Camoufox] Error dimension detect: {e}")

    # --- Strategi 3: Klik berdasarkan koordinat umum (last resort) ---
    try:
        # Turnstile widget biasanya di tengah halaman vertikal, 300px dari kiri
        viewport = page.viewport_size or {"width": 1280, "height": 720}
        click_x = viewport["width"] // 2 - 100 + random.randint(-10, 10)
        click_y = viewport["height"] // 2 + random.randint(-20, 20)
        await page.mouse.move(click_x, click_y)
        await asyncio.sleep(random.uniform(0.3, 0.7))
        await page.mouse.click(click_x, click_y)
        logger.info(f"[Camoufox] Fallback klik koordinat ({click_x}, {click_y})")
        return True
    except Exception as e:
        logger.debug(f"[Camoufox] Error fallback click: {e}")

    return False


async def _wait_for_turnstile(page, timeout_ms: int = _CF_TURNSTILE_TIMEOUT_MS) -> bool:
    """Klik checkbox Turnstile lalu poll sampai halaman CF challenge hilang.
    
    Improved logic:
    1. Wait up to 30s for "verify you are human" text to appear (challenge loading)
    2. When text appears, look for checkbox and click it
    3. Poll until challenge is gone
    
    Return True jika berhasil."""
    import random

    logger.info("[Camoufox] Menunggu Cloudflare Turnstile selesai...")
    start = time.time()
    deadline = timeout_ms / 1000
    verify_human_detected = False
    verify_human_time = None
    click_attempted = False
    click_count = 0
    max_click_attempts = 5

    # Phase 1: Tunggu sebentar agar iframe Turnstile ter-render
    await asyncio.sleep(2)

    # Phase 1: Wait for "verify you are human" text to appear (20-30 seconds)
    logger.info("[Camoufox] Phase 1: Menunggu challenge 'verify you are human' muncul (max 30s)...")
    while (time.time() - start) < min(deadline, 30):
        try:
            html = await page.content()
            
            # Check if challenge is already resolved
            if not _is_cloudflare_page(html):
                logger.info(
                    f"[Camoufox] Challenge sudah resolved dalam {time.time() - start:.1f}s (Phase 1)"
                )
                return True
            
            # Check if loading
            is_loading = _is_cloudflare_loading(html)
            if is_loading:
                logger.info(f"[Camoufox] Cloudflare sedang loading... ({time.time() - start:.1f}s)")
            
            # Check if "verify you are human" text is present
            if _has_verify_human_text(html):
                if not verify_human_detected:
                    verify_human_detected = True
                    verify_human_time = time.time() - start
                    logger.info(
                        f"[Camoufox] 'Verify you are human' terdeteksi setelah {verify_human_time:.1f}s. "
                        f"Checkbox seharusnya ada di sebelah kiri."
                    )
                break  # Exit Phase 1, proceed to Phase 2
            
            # Wait before next check
            await asyncio.sleep(2)
        
        except Exception as e:
            logger.debug(f"[Camoufox] Error dalam Phase 1: {e}")
            await asyncio.sleep(2)
    
    # Phase 2: Klik checkbox dan tunggu challenge selesai
    logger.info("[Camoufox] Phase 2: Mencoba klik checkbox dan tunggu selesai...")
    
    while (time.time() - start) < deadline:
        try:
            html = await page.content()
            
            # Check if challenge is resolved
            if not _is_cloudflare_page(html):
                elapsed = time.time() - start
                logger.info(f"[Camoufox] Turnstile resolved dalam {elapsed:.1f}s")
                if verify_human_detected:
                    logger.info(f"[Camoufox] Challenge fully loaded at {verify_human_time:.1f}s, clicked at ~{elapsed:.1f}s")
                return True

            # Coba klik checkbox (beberapa kali jika perlu, dengan jeda)
            if click_count < max_click_attempts:
                logger.info(
                    f"[Camoufox] Attempt {click_count + 1}/{max_click_attempts}: "
                    f"Mencoba klik Turnstile checkbox..."
                )
                clicked = await _click_turnstile_checkbox(page)
                click_count += 1
                if clicked:
                    click_attempted = True
                    logger.info("[Camoufox] Checkbox diklik. Menunggu verifikasi...")
                    # Beri waktu untuk proses verifikasi setelah klik
                    await asyncio.sleep(random.uniform(4, 6))
                else:
                    # Gerak mouse random sebelum retry
                    logger.info("[Camoufox] Klik gagal, retry...")
                    await page.mouse.move(
                        random.randint(100, 700), random.randint(100, 500)
                    )
                    await asyncio.sleep(random.uniform(2, 4))
            else:
                # Semua attempts habis — hanya poll
                if not click_attempted:
                    logger.warning(
                        "[Camoufox] Semua click attempts gagal. Menunggu auto-resolve..."
                    )
                await page.mouse.move(
                    random.randint(100, 700), random.randint(100, 500)
                )
                await asyncio.sleep(3)

        except Exception as e:
            logger.debug(f"[Camoufox] Error dalam Phase 2: {e}")
            await asyncio.sleep(2)

    elapsed = time.time() - start
    logger.warning(f"[Camoufox] Turnstile TIMEOUT setelah {elapsed:.1f}s/{deadline:.0f}s")
    if verify_human_detected:
        logger.warning(f"[Camoufox] Challenge terdeteksi di {verify_human_time:.1f}s tapi tidak terselesaikan dalam timeout.")
    return False


# ── Core async fetchers ────────────────────────────────────────────────────────


async def _fetch_with_camoufox(
    url: str,
    wait_for_selector: Optional[str],
    extra_wait_seconds: int,
) -> Optional[str]:
    """Fetch menggunakan Camoufox — headless, bypass Cloudflare Turnstile."""
    if not _CAMOUFOX_AVAILABLE:
        logger.error(
            "[Camoufox] Module tidak tersedia. "
            "Jalankan: pip install camoufox[geoip] && python -m camoufox fetch"
        )
        return None

    try:
        async with AsyncCamoufox(
            headless=True,
            geoip=True,
            locale="en-AU",
            os="windows",
            disable_coop=True,
        ) as browser:
            page = await browser.new_page()

            logger.info(f"[Camoufox] Membuka: {url}")
            await page.goto(
                url, timeout=_PAGE_LOAD_TIMEOUT_MS, wait_until="domcontentloaded"
            )

            # Tunggu sampai CF challenge selesai jika ada
            page_html = await page.content()
            if _is_cloudflare_page(page_html):
                logger.info(
                    "[Camoufox] CF challenge terdeteksi. "
                    "Tunggu 20-30s untuk 'verify you are human' muncul..."
                )
                if _is_cloudflare_loading(page_html):
                    logger.info("[Camoufox] Status: Sedang loading...")
                if _has_verify_human_text(page_html):
                    logger.info("[Camoufox] Status: 'Verify you are human' sudah visible")
                
                resolved = await _wait_for_turnstile(page)
                if not resolved:
                    logger.error("[Camoufox] Gagal melewati Cloudflare Turnstile.")
                    with open("debug_cf_blocked.html", "w", encoding="utf-8") as f:
                        f.write(await page.content())
                    return None

            # Tunggu selector konten muncul
            if wait_for_selector:
                try:
                    await page.wait_for_selector(
                        wait_for_selector, timeout=_SELECTOR_WAIT_MS
                    )
                    logger.info(f"[Camoufox] Selector '{wait_for_selector}' ditemukan.")
                except Exception:
                    logger.warning(
                        f"[Camoufox] Selector '{wait_for_selector}' tidak muncul "
                        f"dalam {_SELECTOR_WAIT_MS / 1000:.0f}s — lanjut ambil HTML."
                    )

            if extra_wait_seconds > 0:
                await asyncio.sleep(extra_wait_seconds)

            html = await page.content()
            logger.info(f"[Camoufox] HTML didapat ({len(html):,} chars)")
            return html

    except Exception as e:
        logger.error(f"[Camoufox] Error: {e}", exc_info=True)
        return None


async def _fetch_with_playwright(
    url: str,
    wait_for_selector: Optional[str],
    extra_wait_seconds: int,
) -> Optional[str]:
    """Fetch menggunakan Playwright headless biasa — untuk site tanpa CF."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
            ],
        )
        context = await browser.new_context(
            user_agent=_UA,
            locale="en-AU",
            timezone_id="Australia/Sydney",
        )
        page = await context.new_page()

        await page.set_extra_http_headers(
            {
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                "Accept-Language": "en-AU,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "Upgrade-Insecure-Requests": "1",
            }
        )

        try:
            logger.info(f"[Playwright] Membuka: {url}")
            await page.goto(
                url, timeout=_HEADLESS_LOAD_TIMEOUT_MS, wait_until="domcontentloaded"
            )

            if wait_for_selector:
                try:
                    await page.wait_for_selector(
                        wait_for_selector, timeout=_SELECTOR_WAIT_MS
                    )
                    logger.info(
                        f"[Playwright] Selector '{wait_for_selector}' ditemukan."
                    )
                except PWTimeout:
                    logger.warning(
                        f"[Playwright] Selector '{wait_for_selector}' tidak muncul "
                        f"dalam {_SELECTOR_WAIT_MS / 1000:.0f}s — lanjut ambil HTML."
                    )

            if extra_wait_seconds > 0:
                await asyncio.sleep(extra_wait_seconds)

            html = await page.content()
            logger.info(f"[Playwright] HTML didapat ({len(html):,} chars)")
            return html

        except Exception as e:
            logger.error(f"[Playwright] Error: {e}", exc_info=True)
            return None
        finally:
            await browser.close()


async def _fetch_async(
    url: str,
    bypass_cf: bool,
    wait_for_selector: Optional[str],
    extra_wait_seconds: int,
) -> Optional[str]:
    """Router: pilih engine berdasarkan bypass_cf flag."""
    if bypass_cf:
        return await _fetch_with_camoufox(url, wait_for_selector, extra_wait_seconds)
    else:
        return await _fetch_with_playwright(url, wait_for_selector, extra_wait_seconds)


# ── Public API ─────────────────────────────────────────────────────────────────

# Konstanta publik — bisa diimport scraper lain yang butuh nilai timeout
PAGE_LOAD_TIMEOUT_MS = _HEADLESS_LOAD_TIMEOUT_MS  # 30s, untuk non-CF sites
SELECTOR_TIMEOUT_MS = _SELECTOR_WAIT_MS  # 30s, tunggu selector


def get_page_source_playwright(
    url: str,
    wait_for_selector: Optional[str] = "table",
    extra_wait_seconds: int = 3,
    bypass_cf: bool = False,
) -> Optional[str]:
    """
    Synchronous entry point — dipanggil dari semua state scraper.

    Parameters
    ----------
    url               : URL yang akan di-fetch.
    wait_for_selector : CSS selector yang ditunggu sebelum ambil HTML.
                        Default 'table'. Set None jika tidak perlu tunggu.
    extra_wait_seconds: Detik tambahan setelah selector muncul (render JS).
    bypass_cf         : False (default) → headless Playwright untuk state normal.
                        True  → headless Camoufox khusus ACT (Cloudflare Turnstile).

    Returns
    -------
    HTML string atau None jika gagal.
    """
    if not _PLAYWRIGHT_AVAILABLE:
        logger.error("[Playwright] Module tidak tersedia.")
        return None

    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(
            _fetch_async(url, bypass_cf, wait_for_selector, extra_wait_seconds)
        )
    except Exception as e:
        logger.error(f"[Playwright] Gagal menjalankan event loop: {e}", exc_info=True)
        return None
    finally:
        loop.close()


async def create_browser_context(bypass_cf: bool = False, headless: bool = True):
    """
    Buat dan return resource browser yang sudah dikonfigurasi.

    Digunakan oleh scraper yang butuh interaksi custom di dalam page
    (contoh: WA scraper yang perlu klik Show All + tunggu AJAX).

    ┌─────────────────┬──────────────────────────────────────────────────┐
    │ bypass_cf=False │ returns (playwright_instance, browser, context)  │
    │ bypass_cf=True  │ returns (camoufox_instance, browser, None)       │
    └─────────────────┴──────────────────────────────────────────────────┘

    PENTING: Caller wajib menutup resource setelah selesai.

    Contoh bypass_cf=False (Playwright):
        pw, browser, context = await create_browser_context()
        try:
            page = await context.new_page()
            html = await page.content()
        finally:
            await browser.close()
            await pw.stop()

    Contoh bypass_cf=True (Camoufox):
        cf, browser, _ = await create_browser_context(bypass_cf=True)
        try:
            page = await browser.new_page()
            html = await page.content()
        finally:
            await browser.close()
            await cf.__aexit__(None, None, None)

    Parameters
    ----------
    bypass_cf : False → headless Playwright.
                True  → headless Camoufox (CF-safe).

    Returns
    -------
    Tuple (engine_instance, browser, context_or_None)
    """
    if bypass_cf:
        if not _CAMOUFOX_AVAILABLE:
            raise RuntimeError(
                "camoufox tidak tersedia. "
                "Jalankan: pip install camoufox[geoip] && python -m camoufox fetch"
            )
        import os

        profile_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), ".camoufox_profile"
        )
        os.makedirs(profile_dir, exist_ok=True)

        # Deteksi apakah profil sudah punya sesi
        profile_has_session = any(os.scandir(profile_dir))

        if not profile_has_session:
            # Pertama kali — buka visible supaya user bisa login manual
            logger.info("[Camoufox] Profil baru — browser dibuka untuk login manual.")
            print("\n" + "!" * 60) # noqa: T201
            print("[CAMOUFOX] LOGIN DIPERLUKAN") # noqa: T201
            print("[CAMOUFOX] Silakan login ke Indeed pada jendela browser yang terbuka.") # noqa: T201
            print("[CAMOUFOX] Setelah login berhasil, kembalilah ke sini dan tekan ENTER.") # noqa: T201
            print("!" * 60 + "\n") # noqa: T201
            
            cf = AsyncCamoufox(
                headless=False,
                geoip=True,
                locale="en-AU",
                os="windows",
                persistent_context=True,
                user_data_dir=profile_dir,
                disable_coop=True,
            )
            browser = await cf.__aenter__()
            
            # Buka halaman login Indeed
            try:
                page = await browser.new_page()
                await page.goto("https://au.indeed.com/account/login", wait_until="domcontentloaded")
            except Exception as e:
                logger.warning(f"Gagal membuka halaman login: {e}") # noqa: G004

            # Tunggu input user di terminal secara asinkron
            print("\n>> TUNGGU: Selesaikan login di browser, lalu TEKAN [ENTER] di sini <<") # noqa: T201
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, input, "")
            
            print("[CAMOUFOX] Login dikonfirmasi. Melanjutkan scraping...") # noqa: T201
            return cf, browser, None
        else:
            # headless=True for production
            cf = AsyncCamoufox(
                headless=headless,
                geoip=True,
                locale="en-AU",
                os="windows",
                persistent_context=True,
                user_data_dir=profile_dir,
                disable_coop=True,
            )
            browser = await cf.__aenter__()
            return cf, browser, None

    else:
        if not _PLAYWRIGHT_AVAILABLE:
            raise RuntimeError(
                "playwright tidak tersedia. "
                "Jalankan: pip install playwright && playwright install chromium"
            )
        from playwright.async_api import async_playwright as _async_playwright

        pw = await _async_playwright().start()
        browser = await pw.chromium.launch(
            headless=headless,
            args=[
                "--no-sandbox",
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
            ],
        )
        context = await browser.new_context(
            user_agent=_UA, locale="en-AU", timezone_id="Australia/Sydney"
        )
        return pw, browser, context
