#!/usr/bin/env python3
"""
ByBit P2P Exchange Integration
==============================

Real ByBit P2P data extraction using browser automation
Simplified version with nickname-based links
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
from config.settings import BROWSER_HEADLESS, EXCHANGE_URLS

logger = logging.getLogger(__name__)

# Constants for parsing
PRICE_RANGE = (35.0, 55.0)  # Valid USDT-UAH price range
MIN_USDT_AMOUNT = 10.0  # Minimum reasonable USDT amount
MIN_LIMIT_VALUE = 100.0  # Minimum reasonable limit in UAH
USERNAME_LENGTH_RANGE = (3, 25)  # Valid username length
SEARCH_RADIUS = 5  # Lines to search around price for username
USDT_SEARCH_RADIUS = 5  # Lines to search around price for USDT amount
LIMIT_SEARCH_RADIUS = 5  # Lines to search around price for limits
MAX_OFFERS_TO_PARSE = 10  # Maximum offers to extract

# Timing constants - OPTIMIZED для скорости
PAGE_LOAD_TIMEOUT = 8  # Seconds to wait for page load (было 10)
CONTENT_LOAD_DELAY = 4  # Seconds to wait for dynamic content (было 5→2→3, теперь 4 для максимальной стабильности)
SCROLL_DELAY = 0.2  # Seconds between scrolls (было 0.5)
SCROLL_COUNT = 2  # Number of scroll iterations (было 4)
SCROLL_DISTANCE = 300  # Pixels per scroll

# Cache settings
CACHE_TTL_MINUTES = 5  # Cache time-to-live in minutes

# Browser reuse settings - НОВОЕ для скорости!
BROWSER_REUSE_TIME = 600  # 10 минут держим браузер открытым


class ByBitP2P(BaseExchange):
    """ByBit P2P integration with optimized browser data extraction"""

    def __init__(self):
        super().__init__("ByBit")
        self.driver = None
        self.base_url = EXCHANGE_URLS["bybit"]
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
                logger.debug("ByBit: Reusing existing browser instance (FAST!)")
                return True
            except Exception:
                logger.warning("ByBit: Browser died, reopening...")
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

            logger.info("ByBit browser setup successful")
            return True

        except Exception as e:
            logger.error(f"ByBit browser setup failed: {e}")
            return False

    async def get_offers(self, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """Extract P2P offers from ByBit with smart caching - ASYNC версия с run_in_executor"""
        # Check cache
        if not force_refresh and self._is_cache_valid():
            logger.info(f"Using cached ByBit data ({len(self.offers_cache)} offers)")
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
            logger.info(f"Fetching ByBit P2P offers... ({mode})")
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

            # Scroll to trigger lazy loading (уменьшено с 4 до 2 прокруток)
            self._scroll_page_sync()

            # Extract data
            page_text = self.driver.find_element(By.TAG_NAME, "body").text

            # Parse offers
            offers = self._parse_offers(page_text)

            # Calculate duration
            duration = (datetime.now() - start_time).total_seconds()

            if offers:
                self.offers_cache = offers
                self.last_update = datetime.now()
                self.browser_last_used = (
                    datetime.now()
                )  # НОВОЕ: обновляем время использования
                logger.info(
                    f"ByBit: Successfully extracted {len(offers)} offers in {duration:.1f}s (OPTIMIZED!)"
                )
            else:
                logger.warning(
                    f"No offers extracted from ByBit page (took {duration:.1f}s)"
                )

            # ВАЖНО: НЕ закрываем браузер сразу - переиспользуем!
            # Закроем позже через cleanup_if_needed()

            return offers if offers else self.offers_cache

        except ConnectionError as e:
            logger.error(f"ByBit connection error: {e} - using cache")
            return self.offers_cache
        except Exception as e:
            logger.error(f"ByBit offers fetch failed: {e} - using cache")
            import traceback

            logger.debug(traceback.format_exc())
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

    def _parse_offers(self, page_text: str) -> List[Dict[str, Any]]:
        """Parse offers from page text with improved pattern matching"""
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
        for offer_idx, (price_idx, price_line, price) in enumerate(
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

                # Build simple nickname-based link
                direct_link = self._build_offer_link(username, usdt_amount)

                logger.info(f"✅ {username} -> {price:.2f} UAH")

                # Create and normalize offer
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
                logger.error(f"Error parsing offer at line {price_idx}: {e}")
                continue

        # Sort by price
        offers.sort(key=lambda x: x["price"])
        logger.info(f"Successfully parsed {len(offers)} offers")

        return offers

    def _extract_price_patterns(self, lines: List[str]) -> List[Tuple[int, str, float]]:
        """Extract price patterns from lines"""
        patterns = []

        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue

            # Pattern: "42.50 UAH", "42,50 UAH"
            match = re.search(r"(\d+[,\.]\d+)\s*UAH", line)
            if match:
                try:
                    price_str = match.group(1).replace(",", ".")
                    price = float(price_str)
                    if PRICE_RANGE[0] <= price <= PRICE_RANGE[1]:
                        patterns.append((i, line, price))
                except ValueError:
                    pass

        return patterns

    def _extract_username_patterns(self, lines: List[str]) -> List[Tuple[int, str]]:
        """Extract username patterns"""
        patterns = []
        excluded = {"USDT", "UAH", "USD", "BTC", "ETH", "BNB"}

        for i, line in enumerate(lines):
            line = line.strip()
            min_len, max_len = USERNAME_LENGTH_RANGE

            # Pattern: usernames with alphanumeric + special chars (⓻, 👻, etc)
            if (
                min_len <= len(line) <= max_len
                and re.match(r"^[A-Za-z0-9⓻👻_\-@.]+$", line)
                and line not in excluded
                and "UAH" not in line
                and "USDT" not in line
                and not re.match(r"^[0-9,.\s]+$", line)
            ):
                patterns.append((i, line))

        return patterns

    def _extract_usdt_patterns(self, lines: List[str]) -> List[Tuple[int, str, float]]:
        """Extract USDT amount patterns"""
        patterns = []

        for i, line in enumerate(lines):
            match = re.search(r"(\d+[,\.]\d+)\s*USDT", line)
            if match:
                try:
                    amount_str = match.group(1).replace(",", ".")
                    amount = float(amount_str)
                    if amount > MIN_USDT_AMOUNT:
                        patterns.append((i, line, amount))
                except ValueError:
                    pass

        return patterns

    def _extract_limit_patterns(
        self, lines: List[str]
    ) -> List[Tuple[int, str, float, float]]:
        """Extract limit patterns"""
        patterns = []

        for i, line in enumerate(lines):
            # Pattern: "5,000 ~ 50,000 UAH", "5 000 ~ 50 000 UAH"
            match = re.search(
                r"(\d+(?:[,\s]\d+)*[,\.]\d+)\s*~\s*(\d+(?:[,\s]\d+)*[,\.]\d+)\s*UAH",
                line,
            )
            if match:
                try:
                    min_str = match.group(1).replace(" ", "").replace(",", ".")
                    max_str = match.group(2).replace(" ", "").replace(",", ".")
                    min_value = float(min_str)
                    max_value = float(max_str)
                    if min_value >= MIN_LIMIT_VALUE:
                        patterns.append((i, line, min_value, max_value))
                except ValueError:
                    pass

        return patterns

    def _find_nearest_username(
        self, price_idx: int, username_patterns: List[Tuple[int, str]]
    ) -> str:
        """Find nearest username to price line"""
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
        """Find nearest USDT amount to price line"""
        usdt_amount = 50.0  # Default
        min_distance = float("inf")

        for usdt_idx, _, amount in usdt_patterns:
            distance = abs(usdt_idx - price_idx)
            if distance < min_distance and distance <= USDT_SEARCH_RADIUS:
                usdt_amount = amount
                min_distance = distance

        return usdt_amount

    def _find_nearest_limits(
        self, price_idx: int, limit_patterns: List[Tuple[int, str, float, float]]
    ) -> Tuple[float, float]:
        """Find nearest limit values to price line"""
        min_limit = 1000.0  # Default
        max_limit = 50000.0  # Default
        min_distance = float("inf")

        for limit_idx, _, min_val, max_val in limit_patterns:
            distance = abs(limit_idx - price_idx)
            if distance < min_distance and distance <= LIMIT_SEARCH_RADIUS:
                min_limit = min_val
                max_limit = max_val
                min_distance = distance

        # Ensure min < max
        if min_limit > max_limit:
            min_limit, max_limit = max_limit, min_limit

        return min_limit, max_limit

    def _build_offer_link(self, username: str, usdt_amount: float) -> str:
        """Build direct link to offer (nickname-based)"""
        # Simple nickname-based link (fallback)
        return f"{self.base_url}&amount={usdt_amount}&nickName={username}"

    def format_offer_message(self, offer: Dict[str, Any]) -> str:
        """Format ByBit offer with direct link for user convenience"""
        username = offer.get("username", "Unknown")
        price = offer.get("price", 0)
        available = offer.get("available", 0)
        min_amount = offer.get("min_amount", 0)
        max_amount = offer.get("max_amount", 0)
        link = offer.get("link", self.base_url)

        return f"""💰 <b>ByBit P2P Offer</b>
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
                            f"ByBit: Closing idle browser (idle for {idle_time:.0f}s)"
                        )
                        self.cleanup()

            except Exception:
                logger.warning("ByBit browser not responding, cleaning up")
                try:
                    self.driver.quit()
                except Exception as cleanup_error:
                    logger.debug(f"Error during ByBit cleanup: {cleanup_error}")
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
                logger.info("ByBit browser cleaned up")
            except KeyboardInterrupt:
                # Тихо закрываем при Ctrl+C
                self.driver = None
                self.browser_last_used = None
            except Exception as e:
                # Игнорируем ошибки при закрытии (ConnectionRefusedError и т.д.)
                logger.debug(f"ByBit cleanup error (ignored): {e}")
                self.driver = None
                self.browser_last_used = None

        # Закрываем executor при полной очистке
        if hasattr(self, "executor"):
            try:
                self.executor.shutdown(wait=False)
            except Exception:
                pass  # Игнорируем ошибки при закрытии executor
