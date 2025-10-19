#!/usr/bin/env python3
"""
Binance P2P Exchange Integration
================================

Real Binance P2P data extraction using browser automation
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
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from config.settings import BROWSER_HEADLESS, BROWSER_TIMEOUT

logger = logging.getLogger(__name__)

class BinanceP2P(BaseExchange):
    """Binance P2P integration with real browser data extraction"""
    
    def __init__(self):
        super().__init__("Binance")
        self.driver = None
        # Прямо заходим на страницу покупки USDT за UAH
        self.base_url = "https://p2p.binance.com/ru/trade/all-payments/USDT?fiat=UAH"
        
    def setup_browser(self):
        """Setup Chrome browser with optimized settings"""
        if self.driver:
            return True
            
        try:
            chrome_options = Options()
            
            # Use headless mode from config
            if BROWSER_HEADLESS:
                chrome_options.add_argument('--headless=new')
            
            # MAXIMUM SPEED optimizations
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            chrome_options.add_argument('--window-size=1280,720')  # Smaller window = faster
            chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
            
            # SPEED BOOST: Disable unnecessary features (SAFE options)
            chrome_options.add_argument('--disable-extensions')
            chrome_options.add_argument('--disable-plugins')
            chrome_options.add_argument('--disable-images')  # Don't load images - major speed boost
            chrome_options.add_argument('--disable-web-security')
            chrome_options.add_argument('--disable-features=VizDisplayCompositor')
            chrome_options.add_argument('--disable-background-timer-throttling')
            chrome_options.add_argument('--disable-backgrounding-occluded-windows')
            chrome_options.add_argument('--disable-renderer-backgrounding')
            chrome_options.add_argument('--disable-default-apps')
            chrome_options.add_argument('--disable-sync')
            chrome_options.add_argument('--disable-gpu')  # No GPU acceleration needed
            chrome_options.add_argument('--disable-css3-animations')
            chrome_options.add_argument('--disable-smooth-scrolling')
            chrome_options.add_argument('--memory-pressure-off')
            chrome_options.add_argument('--disable-logging')
            chrome_options.add_argument('--enable-unsafe-swiftshader')  # Fix WebGL warnings
            
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            logger.info("Binance browser setup successful")
            return True
            
        except Exception as e:
            logger.error(f"Binance browser setup failed: {e}")
            return False
    
    async def get_offers(self, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """Extract real P2P offers from Binance website - OPTIMIZED VERSION"""
        # Check cache first (5 minutes TTL) unless force refresh is requested
        if not force_refresh and self.offers_cache and self.last_update:
            from datetime import timedelta
            if datetime.now() - self.last_update < timedelta(minutes=5):
                logger.info(f"Using cached Binance data ({len(self.offers_cache)} offers)")
                return self.offers_cache
        
        if not self.setup_browser():
            logger.warning("Browser setup failed, returning cached offers")
            return self.offers_cache
            
        try:
            mode_text = "FRESH DATA" if force_refresh else "FAST MODE"
            logger.info(f"Fetching Binance P2P offers... ({mode_text})")
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
            await asyncio.sleep(5)  # Give time for P2P data to load
            
            # OPTIMIZATION: Multiple small scrolls to trigger lazy loading
            for i in range(3):
                self.driver.execute_script(f"window.scrollTo(0, {300 * (i + 1)});")
                await asyncio.sleep(1)  # Short waits
            
            # Extract offers from page text AND HTML - OPTIMIZED
            page_text = self.driver.find_element(By.TAG_NAME, "body").text
            page_source = self.driver.page_source  # Get HTML for potential user IDs
            offers = self.parse_offers_from_page_text(page_text, page_source)
            
            # Calculate timing
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            if offers:
                self.offers_cache = offers
                self.last_update = datetime.now()
                logger.info(f"Binance: Successfully extracted {len(offers)} offers in {duration:.1f}s (FAST!)")
            else:
                logger.warning(f"No offers extracted from Binance page (took {duration:.1f}s)")
            
            return offers if offers else self.offers_cache
            
        except Exception as e:
            logger.error(f"Binance offers fetch failed: {e}")
            return self.offers_cache
    
    def parse_offers_from_page_text(self, page_text: str, page_source: str = "") -> List[Dict[str, Any]]:
        """Parse P2P offers from Binance page text using real structure"""
        offers = []
        
        try:
            lines = page_text.split('\n')
            
            # Найдем все цены в UAH формате Binance
            price_patterns = []
            username_patterns = []
            usdt_patterns = []
            limit_patterns = []
            
            for i, line in enumerate(lines):
                line = line.strip()
                if not line:
                    continue
                    
                # Поиск цен в формате UAH: приоритет с символом валюты
                # 1. С символом гривны: "₴ 44.00", "₴ 42.50" и т.д.
                price_match_uah = re.match(r'^₴\s*([3-5][0-9](?:\.\d{1,2})?)$', line)
                # 2. С текстом UAH: "44.00 UAH", "42.50 UAH"
                price_match_text = re.match(r'^([3-5][0-9](?:\.\d{1,2})?)\s*UAH$', line, re.IGNORECASE)
                # 3. Последняя попытка: голые числа в диапазоне, но с осторожностью
                price_match_naked = re.match(r'^([4-5][0-9](?:\.\d{1,2})?)$', line) if not (price_match_uah or price_match_text) else None
                
                price_match = price_match_uah or price_match_text or price_match_naked
                if price_match:
                    try:
                        price_uah = float(price_match.group(1))
                        # Приоритет ценам с валютными маркерами
                        priority = 0  # высокий приоритет
                        if price_match_uah:
                            priority = 0  # наивысший приоритет
                        elif price_match_text:
                            priority = 1  # средний приоритет
                        elif price_match_naked:
                            priority = 2  # низкий приоритет
                        
                        if 35.0 <= price_uah <= 55.0:  # Разумные пределы для USDT-UAH
                            price_patterns.append((i, line, price_uah, priority))
                    except ValueError:
                        pass
                
                # Поиск USDT в формате: "16,406.53 USDT", "4,987.94 USDT"
                usdt_match = re.search(r'([0-9,]+\.?\d*)\s*USDT', line)
                if usdt_match:
                    try:
                        amount = float(usdt_match.group(1).replace(',', ''))
                        if amount > 10:  # Минимальное разумное количество
                            usdt_patterns.append((i, line, amount))
                    except ValueError:
                        pass
                
                # Поиск лимитов в UAH: Binance сторона часто показывает отдельные строки для мин/макс
                single_limit_match = re.match(r'^([0-9,]+\.?\d*)\s*UAH$', line)
                if single_limit_match:
                    try:
                        limit_value = float(single_limit_match.group(1).replace(',', ''))
                        if limit_value >= 100:  # Минимальная разумность
                            limit_patterns.append((i, line, limit_value))
                    except ValueError:
                        pass
                
                # Поиск имен пользователей (предполагаем что это строки 3-20 символов с буквами/цифрами)
                if (3 <= len(line) <= 25 and 
                    re.match(r'^[A-Za-z0-9_\-@.]+$', line) and 
                    line not in ['USDT', 'UAH', 'USD', 'BTC', 'ETH', 'BNB'] and
                    'UAH' not in line and 'USDT' not in line and
                    not re.match(r'^[0-9,.\s]+$', line)):  # Не только числа
                    username_patterns.append((i, line))
            
            logger.info(f"Found {len(price_patterns)} price patterns, {len(usdt_patterns)} USDT patterns, {len(limit_patterns)} limit patterns, {len(username_patterns)} usernames")
            
            # Сортируем по приоритету (0 = наивысший)
            price_patterns.sort(key=lambda x: x[3] if len(x) > 3 else 0)
            
            # Сопоставляем данные по позиции в тексте
            for offer_idx, price_info in enumerate(price_patterns[:15]):
                price_idx, price_line, price_uah = price_info[0], price_info[1], price_info[2]
                try:
                    # Цена уже в UAH
                    
                    # Ищем ближайшее имя пользователя
                    username = "Unknown"
                    min_distance = float('inf')
                    
                    # Проверяем около 20 строк вокруг цены
                    for user_idx, user_name in username_patterns:
                        distance = abs(user_idx - price_idx)
                        if distance < min_distance and distance <= 20:
                            username = user_name
                            min_distance = distance
                    
                    # Ищем ближайшее количество USDT
                    usdt_amount = 0.0
                    min_distance = float('inf')
                    
                    for usdt_idx, usdt_line, amount in usdt_patterns:
                        distance = abs(usdt_idx - price_idx)
                        if distance < min_distance and distance <= 15:
                            usdt_amount = amount
                            min_distance = distance
                    
                    # Ищем ближайшие лимиты в UAH (отдельные значения)
                    limits_nearby = []
                    
                    for limit_idx, limit_line, limit_value in limit_patterns:
                        distance = abs(limit_idx - price_idx)
                        if distance <= 15:  # В пределах 15 строк
                            limits_nearby.append((distance, limit_value))
                    
                    # Сортируем по расстоянию и берем первые два
                    limits_nearby.sort(key=lambda x: x[0])
                    
                    min_limit_uah = limits_nearby[0][1] if limits_nearby else 1000.0
                    max_limit_uah = limits_nearby[1][1] if len(limits_nearby) > 1 else min_limit_uah * 10
                    
                    # Если мин больше макс, поменяем местами
                    if min_limit_uah > max_limit_uah:
                        min_limit_uah, max_limit_uah = max_limit_uah, min_limit_uah
                    
                    # Используем значения по умолчанию если не нашли
                    if min_limit_uah == 0.0:
                        min_limit_uah = 1000.0
                    if max_limit_uah == 0.0:
                        max_limit_uah = 100000.0
                    
                    # Пропускаем предложения без распознанного имени (часто это промо-блоки)
                    if username == "Unknown":
                        continue
                    
                    # Создаем сырое предложение
                    raw_offer = {
                        'username': username,
                        'price': price_uah,
                        'available': usdt_amount if usdt_amount > 0 else 100.0,
                        'min_amount': min_limit_uah,
                        'max_amount': max_limit_uah,
                        'link': f"{self.base_url}&merchant={username}&amount={usdt_amount if usdt_amount > 0 else 100}",
                        'timestamp': datetime.now().isoformat()
                    }
                    
                    # Нормализуем через базовый класс
                    offer = self.normalize_offer(raw_offer)
                    
                    offers.append(offer)
                    
                except Exception as e:
                    logger.error(f"Error parsing offer at price line {price_idx}: {e}")
                    continue
            
            # Сортируем по цене (лучшие предложения первыми)
            offers.sort(key=lambda x: x['price'])
            
            logger.info(f"Successfully parsed {len(offers)} offers")
            return offers
            
        except Exception as e:
            logger.error(f"Error in parse_offers_from_page_text: {e}")
            return []
    
    def format_offer_message(self, offer: Dict[str, Any]) -> str:
        """Format Binance offer with direct link for user convenience"""
        username = offer.get('username', 'Unknown')
        price = offer.get('price', 0)
        available = offer.get('available', 0)
        min_amount = offer.get('min_amount', 0)
        max_amount = offer.get('max_amount', 0)
        link = offer.get('link', self.base_url)
        
        return f"""💰 <b>Binance P2P Offer</b>
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
                self.driver.current_url
            except Exception:
                # Браузер не отвечает, очищаем
                logger.warning("Binance browser not responding, cleaning up")
                try:
                    self.driver.quit()
                except:
                    pass
                self.driver = None
    
    def cleanup(self):
        """Clean up browser resources"""
        if self.driver:
            try:
                self.driver.quit()
                self.driver = None
                logger.info("Binance browser cleaned up")
            except Exception as e:
                logger.error(f"Error cleaning up browser: {e}")
