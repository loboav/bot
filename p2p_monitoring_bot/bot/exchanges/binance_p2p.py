#!/usr/bin/env python3
"""
Binance P2P Exchange Integration
================================

Real Binance P2P data extraction using browser automation
Optimized version with better code organization and performance
"""

import asyncio
import re
from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple
from concurrent.futures import ThreadPoolExecutor
import logging

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from .base_exchange import BaseExchange

# Import settings
import sys
import os

sys.path.append(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
from config.settings import BROWSER_HEADLESS, BROWSER_TIMEOUT

logger = logging.getLogger(__name__)

# Constants for parsing
PRICE_RANGE = (35.0, 55.0)  # Valid USDT-UAH price range
MIN_USDT_AMOUNT = 10.0  # Minimum reasonable USDT amount
MIN_LIMIT_VALUE = 100.0  # Minimum reasonable limit in UAH
USERNAME_LENGTH_RANGE = (3, 25)  # Valid username length
SEARCH_RADIUS = 20  # Lines to search around price for username
USDT_SEARCH_RADIUS = 15  # Lines to search around price for USDT amount
LIMIT_SEARCH_RADIUS = 15  # Lines to search around price for limits
MAX_OFFERS_TO_PARSE = 15  # Maximum offers to extract

# Timing constants - OPTIMIZED для скорости
PAGE_LOAD_TIMEOUT = 8  # Seconds to wait for page load (было 10)
CONTENT_LOAD_DELAY = 2  # Seconds to wait for dynamic content (было 5)
SCROLL_DELAY = 0.3  # Seconds between scrolls (было 1)
SCROLL_COUNT = 2  # Number of scroll iterations (было 3)
SCROLL_DISTANCE = 300  # Pixels per scroll

# Cache settings
CACHE_TTL_MINUTES = 5  # Cache time-to-live in minutes

# Browser reuse settings - НОВОЕ для скорости!
BROWSER_REUSE_TIME = 600  # 10 минут держим браузер открытым


class BinanceP2P(BaseExchange):
    """Binance P2P integration with optimized browser data extraction"""

    def __init__(self):
        super().__init__("Binance")
        self.driver = None
        self.base_url = "https://p2p.binance.com/ru/trade/all-payments/USDT?fiat=UAH"
        self.browser_last_used = (
            None  # НОВОЕ: отслеживаем когда браузер последний раз использовался
        )
        self.executor = ThreadPoolExecutor(max_workers=1)  # НОВОЕ: для run_in_executor

    def setup_browser(self) -> bool:
        """Setup Chrome browser with maximum speed optimizations"""
        # НОВОЕ: Проверяем живой ли уже открытый браузер
        if self.driver:
            try:
                self.driver.current_url  # Проверка что браузер жив
                logger.debug("Binance: Reusing existing browser instance (FAST!)")
                return True
            except Exception:
                logger.warning("Binance: Browser died, reopening...")
                self.cleanup()  # Закрываем мертвый браузер

        try:
            chrome_options = Options()

            # Headless mode
            if BROWSER_HEADLESS:
                chrome_options.add_argument("--headless=new")

            # Core performance options
            performance_args = [
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled",
                "--window-size=1280,720",
                "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            ]

            # Speed boost options
            speed_args = [
                "--disable-extensions",
                "--disable-plugins",
                "--disable-images",  # Major speed boost
                "--disable-web-security",
                "--disable-features=VizDisplayCompositor",
                "--disable-background-timer-throttling",
                "--disable-backgrounding-occluded-windows",
                "--disable-renderer-backgrounding",
                "--disable-default-apps",
                "--disable-sync",
                "--disable-gpu",
                "--disable-css3-animations",
                "--disable-smooth-scrolling",
                "--memory-pressure-off",
                "--disable-logging",
                "--enable-unsafe-swiftshader",
            ]

            for arg in performance_args + speed_args:
                chrome_options.add_argument(arg)

            chrome_options.add_experimental_option(
                "excludeSwitches", ["enable-automation"]
            )
            chrome_options.add_experimental_option("useAutomationExtension", False)

            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.execute_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            )

            logger.info("Binance browser setup successful")
            return True

        except Exception as e:
            logger.error(f"Binance browser setup failed: {e}")
            return False

    async def get_offers(self, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """Extract P2P offers from Binance with smart caching - ASYNC версия с run_in_executor"""
        # Check cache
        if not force_refresh and self._is_cache_valid():
            logger.info(f"Using cached Binance data ({len(self.offers_cache)} offers)")
            return self.offers_cache

        # Запускаем синхронный парсинг в отдельном потоке чтобы не блокировать бот
        loop = asyncio.get_event_loop()
        offers = await loop.run_in_executor(
            self.executor, self._get_offers_sync, force_refresh
        )

        return offers

    def _get_offers_sync(self, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """Синхронная версия парсинга для run_in_executor"""

        if not self.setup_browser():
            logger.warning("Browser setup failed, returning cached offers")
            return self.offers_cache

        try:
            mode = "FRESH DATA" if force_refresh else "FAST MODE"
            logger.info(f"Fetching Binance P2P offers... ({mode})")
            start_time = datetime.now()

            # Load page
            self.driver.get(self.base_url)

            # Wait for page load
            try:
                WebDriverWait(self.driver, PAGE_LOAD_TIMEOUT).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
            except Exception as e:
                logger.error(f"Page load timeout: {e}")
                return self.offers_cache

            # Wait for dynamic content (уменьшено с 5 до 2 секунд)
            import time

            time.sleep(CONTENT_LOAD_DELAY)

            # Scroll to trigger lazy loading (уменьшено с 3 до 2 прокруток)
            self._scroll_page_sync()

            # Extract data
            page_text = self.driver.find_element(By.TAG_NAME, "body").text
            page_source = self.driver.page_source
            advertiser_ids = self._extract_advertiser_ids(page_source)

            # Parse offers
            offers = self._parse_offers(page_text, page_source, advertiser_ids)

            # Calculate duration
            duration = (datetime.now() - start_time).total_seconds()

            if offers:
                self.offers_cache = offers
                self.last_update = datetime.now()
                self.browser_last_used = (
                    datetime.now()
                )  # НОВОЕ: обновляем время использования
                logger.info(
                    f"Binance: Successfully extracted {len(offers)} offers in {duration:.1f}s (OPTIMIZED!)"
                )
            else:
                logger.warning(
                    f"No offers extracted from Binance page (took {duration:.1f}s)"
                )

            # ВАЖНО: НЕ закрываем браузер сразу - переиспользуем!
            # Закроем позже через cleanup_if_needed()

            return offers if offers else self.offers_cache

        except ConnectionError as e:
            logger.error(f"Binance connection error: {e} - using cache")
            return self.offers_cache
        except Exception as e:
            logger.error(f"Binance offers fetch failed: {e}")
            import traceback

            logger.error(traceback.format_exc())
            return self.offers_cache

    def _is_cache_valid(self) -> bool:
        """Check if cache is still valid"""
        if not self.offers_cache or not self.last_update:
            return False
        return datetime.now() - self.last_update < timedelta(minutes=CACHE_TTL_MINUTES)

    def _scroll_page_sync(self):
        """Scroll page to trigger lazy loading - SYNC версия для executor"""
        import time

        for i in range(SCROLL_COUNT):
            self.driver.execute_script(
                f"window.scrollTo(0, {SCROLL_DISTANCE * (i + 1)});"
            )
            time.sleep(SCROLL_DELAY)

    def _extract_advertiser_ids(self, page_source: str) -> List[str]:
        """Extract advertiser IDs from page source using multiple methods"""
        advertiser_ids = []

        # Method 1: Extract from storage
        try:
            storage_data = self.driver.execute_script("""
                let data = [];
                for (let i = 0; i < localStorage.length; i++) {
                    let value = localStorage.getItem(localStorage.key(i));
                    if (value && value.includes('advertiserNo')) data.push(value);
                }
                for (let i = 0; i < sessionStorage.length; i++) {
                    let value = sessionStorage.getItem(sessionStorage.key(i));
                    if (value && value.includes('advertiserNo')) data.push(value);
                }
                return data.join('|||');
            """)

            if storage_data:
                matches = re.findall(
                    r'"?advertiserNo"?\s*:\s*"?(s[a-f0-9]{32,})"?', storage_data
                )
                advertiser_ids.extend(matches)
                logger.info(f"📦 Found {len(matches)} IDs in storage")
        except Exception as e:
            logger.debug(f"Storage extraction failed: {e}")

        # Method 2: Extract from DOM links
        try:
            links = self.driver.execute_script("""
                return Array.from(document.querySelectorAll('a[href*="advertiserNo"]'))
                    .map(link => {
                        let match = link.href.match(/advertiserNo=([a-f0-9s]+)/);
                        return match ? match[1] : null;
                    })
                    .filter(id => id);
            """)
            if links:
                advertiser_ids.extend(links)
                logger.info(f"🔗 Found {len(links)} IDs in links")
        except Exception as e:
            logger.debug(f"Link extraction failed: {e}")

        # Method 3: Extract from HTML source
        html_matches = re.findall(r'advertiserNo["\s:=]+(s[a-f0-9]{32,})', page_source)
        if html_matches:
            advertiser_ids.extend(html_matches)
            logger.info(f"📄 Found {len(html_matches)} IDs in HTML source")

        # Remove duplicates while preserving order
        unique_ids = list(dict.fromkeys(advertiser_ids))

        if unique_ids:
            logger.info(f"✅ Total unique advertiser IDs: {len(unique_ids)}")
            logger.info(f"First 3: {unique_ids[:3]}")

        return unique_ids

    def _parse_offers_dom(self, advertiser_ids: List[str]) -> List[Dict[str, Any]]:
        """
        ✅ NEW: DOM-based parsing (cleaner and more reliable)
        Falls back to text parsing if this fails
        """
        offers = []

        try:
            # Find all offer containers using common CSS patterns
            # Binance uses div elements with specific classes for P2P offers

            # Try multiple possible selectors (Binance changes classes sometimes)
            selectors_to_try = [
                "div[class*='advertiser']",  # Advertiser container
                "div[class*='ad-container']",  # Ad container
                "div[class*='advertise-container']",  # Advertise container
                "[class*='UserInfo']",  # User info component
                "[class*='AdvertItem']",  # Advert item
                "div[class*='trade']",  # Trade container
                "[data-bn-type='text']",  # Binance text elements
                ".css-1m1f8hn",  # Specific CSS class (if stable)
                ".css-vurnku",  # Another potential class
                "div > div > div > a[href*='advertiserNo']",  # Link-based approach
            ]

            offer_elements = []

            # 🎯 APPROACH 1: Try to find by link to advertiser
            try:
                links = self.driver.find_elements(
                    By.CSS_SELECTOR, "a[href*='advertiserNo']"
                )
                if links and len(links) >= 5:
                    # Get parent containers of these links
                    parents = []
                    for link in links[:15]:  # Limit to 15
                        try:
                            # Go up 4-5 levels to get the FULL card container (not just seller info)
                            parent = link.find_element(By.XPATH, "./ancestor::*[5]")
                            if parent not in parents:
                                parents.append(parent)
                        except:
                            try:
                                parent = link.find_element(By.XPATH, "./ancestor::*[4]")
                                if parent not in parents:
                                    parents.append(parent)
                            except:
                                try:
                                    parent = link.find_element(
                                        By.XPATH, "./ancestor::*[3]"
                                    )
                                    if parent not in parents:
                                        parents.append(parent)
                                except:
                                    pass

                    if parents:
                        offer_elements = parents
                        logger.info(
                            f"✅ Found {len(parents)} elements via advertiser links"
                        )
            except Exception as e:
                logger.debug(f"Link-based approach failed: {e}")

            # 🎯 APPROACH 2: Try CSS selectors if approach 1 failed
            if not offer_elements:
                for selector in selectors_to_try:
                    try:
                        elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        if elements and len(elements) > 3:  # Need at least a few offers
                            offer_elements = elements
                            logger.info(
                                f"✅ Found {len(elements)} elements with selector: {selector}"
                            )
                            break
                    except Exception as e:
                        logger.debug(f"Selector '{selector}' failed: {e}")
                        continue

            if not offer_elements:
                logger.warning("⚠️ No offer containers found with any approach")
                return []

            # Parse each offer container
            for idx, element in enumerate(offer_elements[:MAX_OFFERS_TO_PARSE]):
                try:
                    # Extract text from this container
                    element_text = element.text

                    if not element_text or len(element_text) < 10:
                        continue

                    # Parse data from element text
                    lines = element_text.split("\n")

                    # Find price (check current line and adjacent lines for currency)
                    price = None
                    for i, line in enumerate(lines):
                        # Pattern 1: Price and currency on same line
                        # "43.20 UAH" or "₴43.20"
                        price_match = re.search(
                            r"([3-5][0-9](?:\.\d{1,2})?)\s*(?:UAH|₴)",
                            line,
                            re.IGNORECASE,
                        )
                        if not price_match:
                            price_match = re.search(
                                r"(?:UAH|₴)\s*([3-5][0-9](?:\.\d{1,2})?)",
                                line,
                                re.IGNORECASE,
                            )

                        # Pattern 2: Check if previous line has currency symbol
                        if not price_match and i > 0:
                            prev_line = lines[i - 1]
                            if prev_line.strip() in ["₴", "UAH"]:
                                # Current line might be the price
                                num_match = re.match(
                                    r"^([3-5][0-9](?:\.\d{1,2})?)$", line.strip()
                                )
                                if num_match:
                                    price_match = num_match

                        # Pattern 3: Check if next line has currency symbol
                        if not price_match and i < len(lines) - 1:
                            next_line = lines[i + 1]
                            if next_line.strip() in ["₴", "UAH"]:
                                # Current line might be the price
                                num_match = re.match(
                                    r"^([3-5][0-9](?:\.\d{1,2})?)$", line.strip()
                                )
                                if num_match:
                                    price_match = num_match

                        if price_match:
                            try:
                                price = float(price_match.group(1))
                                if PRICE_RANGE[0] <= price <= PRICE_RANGE[1]:
                                    break
                            except ValueError:
                                continue

                    if not price:
                        continue

                    # Find username (usually alphanumeric, 3-25 chars)
                    username = "Unknown"
                    for line in lines:
                        line = line.strip()
                        if (
                            3 <= len(line) <= 25
                            and re.match(r"^[A-Za-z0-9_\-]+$", line)
                            and line not in ["USDT", "UAH", "USD", "Купить", "Buy"]
                        ):
                            username = line
                            break

                    # Find USDT amount
                    usdt_amount = 100.0  # Default
                    for line in lines:
                        usdt_match = re.search(r"([\d,\.]+)\s*USDT", line)
                        if usdt_match:
                            try:
                                usdt_amount = float(
                                    usdt_match.group(1).replace(",", "")
                                )
                                if usdt_amount >= MIN_USDT_AMOUNT:
                                    break
                            except ValueError:
                                continue

                    # Find limits - look for two consecutive lines with "UAH" and "-" separator
                    min_limit, max_limit = 1000.0, 100000.0  # Defaults
                    for i, line in enumerate(lines):
                        # Pattern 1: Both on same line "1000 - 50000 UAH"
                        limit_match = re.search(
                            r"([\d,\.\s]+)\s*[-–—]\s*([\d,\.\s]+)\s*(?:UAH|₴)",
                            line,
                            re.IGNORECASE,
                        )

                        # Pattern 2: Check consecutive lines (Binance splits min and max)
                        # Line i: "1,185.00 UAH"
                        # Line i+1: "-"
                        # Line i+2: "1,186.00 UAH"
                        if not limit_match and i < len(lines) - 2:
                            line1 = lines[i]
                            line2 = lines[i + 1]
                            line3 = lines[i + 2]

                            # Check if middle line is separator
                            if line2.strip() in ["-", "–", "—"]:
                                # Extract numbers from line1 and line3
                                min_match = re.search(
                                    r"([\d,\.]+)\s*(?:UAH|₴)", line1, re.IGNORECASE
                                )
                                max_match = re.search(
                                    r"([\d,\.]+)\s*(?:UAH|₴)", line3, re.IGNORECASE
                                )

                                if min_match and max_match:
                                    try:
                                        min_limit = float(
                                            min_match.group(1).replace(",", "")
                                        )
                                        max_limit = float(
                                            max_match.group(1).replace(",", "")
                                        )
                                        if (
                                            min_limit >= MIN_LIMIT_VALUE
                                            and min_limit <= max_limit
                                        ):
                                            break
                                    except ValueError:
                                        pass

                        if limit_match:
                            try:
                                # Remove spaces and commas, convert to float
                                min_str = (
                                    limit_match.group(1)
                                    .replace(",", "")
                                    .replace(" ", "")
                                )
                                max_str = (
                                    limit_match.group(2)
                                    .replace(",", "")
                                    .replace(" ", "")
                                )
                                min_limit = float(min_str)
                                max_limit = float(max_str)
                                if (
                                    min_limit >= MIN_LIMIT_VALUE
                                    and min_limit < max_limit
                                ):
                                    break
                            except ValueError:
                                continue

                    # Get advertiser ID for link
                    advertiser_no = (
                        advertiser_ids[idx] if idx < len(advertiser_ids) else None
                    )

                    # Try to find direct link in element
                    direct_link = self._build_offer_link(
                        username, advertiser_no, usdt_amount
                    )
                    try:
                        link_element = element.find_element(By.TAG_NAME, "a")
                        href = link_element.get_attribute("href")
                        if href and "advertiserNo" in href:
                            direct_link = href
                    except:
                        pass  # Use fallback link

                    # Create offer
                    raw_offer = {
                        "username": username,
                        "price": price,
                        "available": usdt_amount,
                        "min_amount": min_limit,
                        "max_amount": max_limit,
                        "link": direct_link,
                        "timestamp": datetime.now().isoformat(),
                    }

                    offer = self.normalize_offer(raw_offer)
                    offers.append(offer)

                except Exception as e:
                    logger.debug(f"Error parsing DOM element {idx}: {e}")
                    continue

            # Sort by price
            offers.sort(key=lambda x: x["price"])

            if offers:
                logger.info(
                    f"✅ DOM parsing extracted {len(offers)} offers successfully"
                )

            return offers

        except Exception as e:
            logger.warning(f"⚠️ DOM parsing failed completely: {e}")
            return []

    def _parse_offers(
        self, page_text: str, page_source: str, advertiser_ids: List[str]
    ) -> List[Dict[str, Any]]:
        """Parse offers from page text with improved pattern matching"""

        # ✅ TRY DOM PARSING FIRST (better approach)
        try:
            dom_offers = self._parse_offers_dom(advertiser_ids)
            if dom_offers and len(dom_offers) > 0:
                logger.info(f"✅ DOM parsing succeeded: {len(dom_offers)} offers")
                return dom_offers
            else:
                logger.warning(
                    "⚠️ DOM parsing returned no offers, falling back to text parsing"
                )
        except Exception as e:
            logger.warning(f"⚠️ DOM parsing failed: {e}, falling back to text parsing")

        # ❌ FALLBACK: Old text parsing method
        offers = []
        lines = page_text.split("\n")

        # Extract patterns
        price_patterns = self._extract_price_patterns(lines)
        username_patterns = self._extract_username_patterns(lines)
        usdt_patterns = self._extract_usdt_patterns(lines)
        limit_patterns = self._extract_limit_patterns(lines)

        logger.info(
            f"Found {len(price_patterns)} price patterns, {len(usdt_patterns)} USDT patterns, "
            f"{len(limit_patterns)} limit patterns, {len(username_patterns)} usernames"
        )

        # Match data by position
        for offer_idx, (price_idx, price_line, price_uah, priority) in enumerate(
            price_patterns[:MAX_OFFERS_TO_PARSE]
        ):
            try:
                username = self._find_nearest_username(price_idx, username_patterns)
                if username == "Unknown":
                    continue  # Skip offers without username

                usdt_amount = self._find_nearest_usdt(price_idx, usdt_patterns)
                min_limit, max_limit = self._find_nearest_limits(
                    price_idx, limit_patterns
                )

                # Get advertiser ID
                advertiser_no = (
                    advertiser_ids[offer_idx]
                    if offer_idx < len(advertiser_ids)
                    else None
                )
                direct_link = self._build_offer_link(
                    username, advertiser_no, usdt_amount
                )

                # Log mapping
                if advertiser_no:
                    logger.info(f"✅ {username} -> {advertiser_no[:10]}...")
                else:
                    logger.warning(f"❌ {username} -> NO ID (fallback to merchant)")

                # Create and normalize offer
                raw_offer = {
                    "username": username,
                    "price": price_uah,
                    "available": usdt_amount,
                    "min_amount": min_limit,
                    "max_amount": max_limit,
                    "link": direct_link,
                    "timestamp": datetime.now().isoformat(),
                }

                offer = self.normalize_offer(raw_offer)
                offers.append(offer)

            except Exception as e:
                logger.error(f"Error parsing offer at line {price_idx}: {e}")
                continue

        # Sort by price
        offers.sort(key=lambda x: x["price"])
        logger.info(f"Successfully parsed {len(offers)} offers")

        return offers

    def _extract_price_patterns(
        self, lines: List[str]
    ) -> List[Tuple[int, str, float, int]]:
        """Extract price patterns with priority (for text parsing fallback)"""
        patterns = []

        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue

            # Priority 0: With currency symbol ₴
            match = re.match(r"^₴\s*([3-5][0-9](?:\.\d{1,2})?)$", line)
            if match:
                price = float(match.group(1))
                if PRICE_RANGE[0] <= price <= PRICE_RANGE[1]:
                    patterns.append((i, line, price, 0))
                continue

            # Priority 1: With UAH text
            match = re.match(r"^([3-5][0-9](?:\.\d{1,2})?)\s*UAH$", line, re.IGNORECASE)
            if match:
                price = float(match.group(1))
                if PRICE_RANGE[0] <= price <= PRICE_RANGE[1]:
                    patterns.append((i, line, price, 1))
                continue

            # Priority 2: Naked numbers (careful)
            match = re.match(r"^([4-5][0-9](?:\.\d{1,2})?)$", line)
            if match:
                price = float(match.group(1))
                if PRICE_RANGE[0] <= price <= PRICE_RANGE[1]:
                    patterns.append((i, line, price, 2))

        # Sort by priority
        patterns.sort(key=lambda x: x[3])
        return patterns

    def _extract_username_patterns(self, lines: List[str]) -> List[Tuple[int, str]]:
        """Extract username patterns (for text parsing fallback)"""
        patterns = []
        excluded = {"USDT", "UAH", "USD", "BTC", "ETH", "BNB"}

        for i, line in enumerate(lines):
            line = line.strip()
            min_len, max_len = USERNAME_LENGTH_RANGE

            if (
                min_len <= len(line) <= max_len
                and re.match(r"^[A-Za-z0-9_\-@.]+$", line)
                and line not in excluded
                and "UAH" not in line
                and "USDT" not in line
                and not re.match(r"^[0-9,.\s]+$", line)
            ):
                patterns.append((i, line))

        return patterns

    def _extract_usdt_patterns(self, lines: List[str]) -> List[Tuple[int, str, float]]:
        """Extract USDT amount patterns (for text parsing fallback)"""
        patterns = []

        for i, line in enumerate(lines):
            match = re.search(r"([0-9,]+\.?\d*)\s*USDT", line)
            if match:
                try:
                    amount = float(match.group(1).replace(",", ""))
                    if amount > MIN_USDT_AMOUNT:
                        patterns.append((i, line, amount))
                except ValueError:
                    pass

        return patterns

    def _extract_limit_patterns(self, lines: List[str]) -> List[Tuple[int, str, float]]:
        """Extract limit patterns (for text parsing fallback)"""
        patterns = []

        for i, line in enumerate(lines):
            match = re.match(r"^([0-9,]+\.?\d*)\s*UAH$", line)
            if match:
                try:
                    value = float(match.group(1).replace(",", ""))
                    if value >= MIN_LIMIT_VALUE:
                        patterns.append((i, line, value))
                except ValueError:
                    pass

        return patterns

    def _find_nearest_username(
        self, price_idx: int, username_patterns: List[Tuple[int, str]]
    ) -> str:
        """Find nearest username to price line (for text parsing fallback)"""
        username = "Unknown"
        min_distance = float("inf")

        for user_idx, user_name in username_patterns:
            distance = abs(user_idx - price_idx)
            if distance < min_distance and distance <= SEARCH_RADIUS:
                username = user_name
                min_distance = distance

        return username

    def _find_nearest_usdt(
        self, price_idx: int, usdt_patterns: List[Tuple[int, str, float]]
    ) -> float:
        """Find nearest USDT amount to price line (for text parsing fallback)"""
        usdt_amount = 100.0  # Default
        min_distance = float("inf")

        for usdt_idx, _, amount in usdt_patterns:
            distance = abs(usdt_idx - price_idx)
            if distance < min_distance and distance <= USDT_SEARCH_RADIUS:
                usdt_amount = amount
                min_distance = distance

        return usdt_amount

    def _find_nearest_limits(
        self, price_idx: int, limit_patterns: List[Tuple[int, str, float]]
    ) -> Tuple[float, float]:
        """Find nearest limit values to price line (for text parsing fallback)"""
        limits_nearby = []

        for limit_idx, _, limit_value in limit_patterns:
            distance = abs(limit_idx - price_idx)
            if distance <= LIMIT_SEARCH_RADIUS:
                limits_nearby.append((distance, limit_value))

        limits_nearby.sort(key=lambda x: x[0])

        min_limit = limits_nearby[0][1] if limits_nearby else 1000.0
        max_limit = limits_nearby[1][1] if len(limits_nearby) > 1 else min_limit * 10

        # Ensure min < max
        if min_limit > max_limit:
            min_limit, max_limit = max_limit, min_limit

        return min_limit, max_limit

    def _build_offer_link(
        self, username: str, advertiser_no: str, usdt_amount: float
    ) -> str:
        """Build direct link to offer"""
        if advertiser_no:
            return f"https://c2c.binance.com/ru/advertiserDetail?advertiserNo={advertiser_no}"
        else:
            return f"{self.base_url}&merchant={username}&amount={usdt_amount}"

    def format_offer_message(self, offer: Dict[str, Any]) -> str:
        """Format Binance offer for user notification with clickable links"""
        username = offer.get("username", "Unknown")
        price = offer.get("price", 0)
        available = offer.get("available", 0)
        min_amount = offer.get("min_amount", 0)
        max_amount = offer.get("max_amount", 0)
        link = offer.get("link", self.base_url)

        return f"""💰 <b>Binance P2P Offer</b>
👤 Пользователь: <b>{username}</b>
💲 Цена: <b>{price:.2f} UAH</b> за USDT
📊 Доступно: <b>{available:.1f} USDT</b>
💳 Лимиты: {min_amount:.0f} - {max_amount:.0f} UAH
🔗 Прямая ссылка: <a href='{link}'>Купить у {username}</a>
⚡ Быстрая ссылка: {self.base_url}""".strip()

    def _force_cleanup_browser(self):
        """Force cleanup browser immediately after request - DEPRECATED, используем cleanup_if_needed"""
        # ВАЖНО: Больше НЕ вызываем это автоматически!
        # Браузер переиспользуется между запросами для скорости
        pass

    def cleanup_if_needed(self):
        """Smart cleanup - закрываем браузер только если он давно не использовался или не отвечает"""
        if self.driver:
            try:
                # Проверяем жив ли браузер
                self.driver.current_url

                # НОВОЕ: Закрываем если браузер долго не использовался (экономим память)
                if self.browser_last_used:
                    idle_time = (
                        datetime.now() - self.browser_last_used
                    ).total_seconds()
                    if idle_time > BROWSER_REUSE_TIME:
                        logger.info(
                            f"Binance: Closing idle browser (idle for {idle_time:.0f}s)"
                        )
                        self.cleanup()

            except Exception:
                logger.warning("Binance browser not responding, cleaning up")
                try:
                    self.driver.quit()
                except:
                    pass
                self.driver = None
                self.browser_last_used = None

    def cleanup(self):
        """Clean up browser resources"""
        if self.driver:
            try:
                self.driver.quit()
                self.driver = None
                self.browser_last_used = None
                logger.info("Binance browser cleaned up")
            except KeyboardInterrupt:
                # Тихо закрываем при Ctrl+C
                self.driver = None
                self.browser_last_used = None
            except Exception as e:
                # Игнорируем ошибки при закрытии (ConnectionRefusedError и т.д.)
                logger.debug(f"Binance cleanup error (ignored): {e}")
                self.driver = None
                self.browser_last_used = None

        # Закрываем executor при полной очистке
        if hasattr(self, "executor"):
            try:
                self.executor.shutdown(wait=False)
            except Exception:
                pass  # Игнорируем ошибки при закрытии executor
