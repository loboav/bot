#!/usr/bin/env python3
"""
ByBit P2P Exchange Integration
==============================

Real ByBit P2P data extraction using browser automation
"""

import asyncio
import re
from datetime import datetime
from typing import List, Dict, Any, Optional
import logging

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from .base_exchange import BaseExchange

# Import settings with proper path handling
import sys
import os

sys.path.append(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
from config.settings import BROWSER_HEADLESS, BROWSER_TIMEOUT, EXCHANGE_URLS

logger = logging.getLogger(__name__)


class ByBitP2P(BaseExchange):
    """ByBit P2P integration with real browser data extraction"""

    def __init__(self):
        super().__init__("ByBit")
        self.driver = None
        self.base_url = EXCHANGE_URLS["bybit"]

    def setup_browser(self):
        """Setup Chrome browser with optimized settings"""
        if self.driver:
            return True

        try:
            chrome_options = Options()

            # Use headless mode from config
            if BROWSER_HEADLESS:
                chrome_options.add_argument("--headless=new")

            # MAXIMUM SPEED optimizations
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_experimental_option(
                "excludeSwitches", ["enable-automation"]
            )
            chrome_options.add_experimental_option("useAutomationExtension", False)
            chrome_options.add_argument(
                "--window-size=1280,720"
            )  # Smaller window = faster
            chrome_options.add_argument(
                "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )

            # SPEED BOOST: Disable unnecessary features (SAFE options)
            chrome_options.add_argument("--disable-extensions")
            chrome_options.add_argument("--disable-plugins")
            chrome_options.add_argument(
                "--disable-images"
            )  # Don't load images - major speed boost
            chrome_options.add_argument("--disable-web-security")
            chrome_options.add_argument("--disable-features=VizDisplayCompositor")
            chrome_options.add_argument("--disable-background-timer-throttling")
            chrome_options.add_argument("--disable-backgrounding-occluded-windows")
            chrome_options.add_argument("--disable-renderer-backgrounding")
            chrome_options.add_argument("--disable-default-apps")
            chrome_options.add_argument("--disable-sync")
            chrome_options.add_argument("--disable-gpu")  # No GPU acceleration needed
            chrome_options.add_argument("--disable-css3-animations")
            chrome_options.add_argument("--disable-smooth-scrolling")
            chrome_options.add_argument("--memory-pressure-off")
            chrome_options.add_argument("--disable-logging")
            chrome_options.add_argument(
                "--enable-unsafe-swiftshader"
            )  # Fix WebGL warnings

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
        """Extract real P2P offers from ByBit website - OPTIMIZED VERSION"""
        # Check cache first (5 minutes TTL) unless force refresh is requested
        if not force_refresh and self.offers_cache and self.last_update:
            from datetime import timedelta

            if datetime.now() - self.last_update < timedelta(minutes=5):
                logger.info(
                    f"Using cached ByBit data ({len(self.offers_cache)} offers)"
                )
                return self.offers_cache

        if not self.setup_browser():
            logger.warning("Browser setup failed, returning cached offers")
            return self.offers_cache

        try:
            mode_text = "FRESH DATA" if force_refresh else "FAST MODE"
            logger.info(f"Fetching ByBit P2P offers... ({mode_text})")
            start_time = datetime.now()

            # Navigate to P2P page
            self.driver.get(self.base_url)

            # OPTIMIZATION: Reduced wait times and smarter loading
            try:
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
            except:
                logger.error("Page load timeout")
                return self.offers_cache

            # OPTIMIZATION: Much shorter wait for dynamic content
            await asyncio.sleep(3)  # Reduced from 8 to 3 seconds

            # OPTIMIZATION: Multiple small scrolls instead of one big
            for i in range(3):
                self.driver.execute_script(f"window.scrollTo(0, {200 * (i + 1)});")
                await asyncio.sleep(0.5)  # Very short waits

            # Extract offers from page text - OPTIMIZED
            page_text = self.driver.find_element(By.TAG_NAME, "body").text
            offers = self.parse_offers_from_page_text(page_text)

            # Calculate timing
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            if offers:
                self.offers_cache = offers
                self.last_update = datetime.now()
                logger.info(
                    f"ByBit: Successfully extracted {len(offers)} offers in {duration:.1f}s (FAST!)"
                )
            else:
                logger.warning(
                    f"No offers extracted from ByBit page (took {duration:.1f}s)"
                )

            return offers if offers else self.offers_cache

        except ConnectionError as e:
            logger.error(f"ByBit connection error: {e} - using cache")
            return self.offers_cache
        except Exception as e:
            logger.error(f"ByBit offers fetch failed: {e} - using cache")
            import traceback

            logger.debug(traceback.format_exc())
            return self.offers_cache

    def parse_offers_from_page_text(self, page_text: str) -> List[Dict[str, Any]]:
        """Parse P2P offers from full page text using improved patterns"""
        offers = []

        try:
            lines = page_text.split("\n")

            # Find lines with price patterns
            price_lines = []
            for i, line in enumerate(lines):
                if re.search(r"\d+[,\.]\d+\s*UAH", line.strip()):
                    price_lines.append((i, line.strip()))

            logger.info(f"Found {len(price_lines)} price patterns")

            # Extract usernames and other data from context
            for line_idx, price_line in price_lines[:10]:  # Top 10 offers
                try:
                    # Extract price
                    price_match = re.search(r"(\d+[,\.]\d+)\s*UAH", price_line)
                    if not price_match:
                        continue

                    price_str = price_match.group(1).replace(",", ".")
                    price = float(price_str)

                    # Look for username in nearby lines
                    username = "Unknown"
                    for check_idx in range(
                        max(0, line_idx - 5), min(len(lines), line_idx + 3)
                    ):
                        line = lines[check_idx].strip()
                        # Fixed regex to capture the full username including first character
                        username_match = re.match(
                            r"^([A-Za-z0-9⓻👻][A-Za-z0-9_]+)", line
                        )
                        if username_match and len(username_match.group(1)) > 2:
                            username = username_match.group(1)
                            break

                    # Look for USDT amounts
                    available = 50.0  # Default
                    for check_idx in range(
                        max(0, line_idx - 2), min(len(lines), line_idx + 5)
                    ):
                        line = lines[check_idx].strip()
                        usdt_match = re.search(r"(\d+[,\.]\d+)\s*USDT", line)
                        if usdt_match:
                            usdt_str = usdt_match.group(1).replace(",", ".")
                            available = float(usdt_str)
                            break

                    # Look for limit ranges
                    min_amount, max_amount = 1000.0, 50000.0
                    for check_idx in range(
                        max(0, line_idx - 2), min(len(lines), line_idx + 5)
                    ):
                        line = lines[check_idx].strip()
                        limit_match = re.search(
                            r"(\d+(?:[,\s]\d+)*[,\.]\d+)\s*~\s*(\d+(?:[,\s]\d+)*[,\.]\d+)\s*UAH",
                            line,
                        )
                        if limit_match:
                            min_str = (
                                limit_match.group(1).replace(" ", "").replace(",", ".")
                            )
                            max_str = (
                                limit_match.group(2).replace(" ", "").replace(",", ".")
                            )
                            try:
                                min_amount = float(min_str)
                                max_amount = float(max_str)
                            except:
                                pass
                            break

                    # Создаем сырое предложение
                    raw_offer = {
                        "username": username,
                        "price": price,
                        "available": available,
                        "min_amount": min_amount,
                        "max_amount": max_amount,
                        "link": f"{self.base_url}&amount={available}&nickName={username}",
                        "timestamp": datetime.now().isoformat(),
                    }

                    # Нормализуем через базовый класс
                    offer = self.normalize_offer(raw_offer)

                    offers.append(offer)

                except Exception as e:
                    logger.error(f"Error parsing offer at line {line_idx}: {e}")
                    continue

            # Sort by price (best offers first)
            offers.sort(key=lambda x: x["price"])

            logger.info(f"Successfully parsed {len(offers)} offers")
            return offers

        except Exception as e:
            logger.error(f"Error in parse_offers_from_page_text: {e}")
            return []

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

    def cleanup_if_needed(self):
        """Smart cleanup - only if browser has been idle"""
        if self.driver:
            try:
                # Проверяем, что браузер еще отвечает
                self.driver.current_url  # Простая проверка
            except Exception:
                # Браузер не отвечает, очищаем
                logger.warning("ByBit browser not responding, cleaning up")
                try:
                    self.driver.quit()
                except Exception as cleanup_error:
                    logger.debug(f"Error during ByBit cleanup: {cleanup_error}")
                    pass
                self.driver = None

    def cleanup(self):
        """Clean up browser resources"""
        if self.driver:
            try:
                self.driver.quit()
                self.driver = None
                logger.info("ByBit browser cleaned up")
            except Exception as e:
                logger.warning(f"Error cleaning up ByBit browser: {e}")
                # Игнорируем ошибку, ставим driver в None в любом случае
                self.driver = None
