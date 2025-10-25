#!/usr/bin/env python3
"""
ByBit P2P API Integration
==========================

Fast API-based integration for ByBit P2P (no Selenium needed!)
This is a new implementation that works alongside the old bybit_p2p.py
"""

import asyncio
import aiohttp
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

# Import base class
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from .base_exchange import BaseExchange

logger = logging.getLogger(__name__)

# API Configuration
BYBIT_API_URL = "https://api2.bybit.com/fiat/otc/item/online"
CACHE_TTL_MINUTES = 5
REQUEST_TIMEOUT = 15  # seconds


class ByBitP2PAPI(BaseExchange):
    """
    ByBit P2P integration using official API

    Much faster and more reliable than Selenium parsing!
    """

    def __init__(self):
        super().__init__("bybit")
        self.api_url = BYBIT_API_URL
        self.session = None
        logger.info("🚀 Initialized ByBit P2P API (NEW FAST VERSION!)")

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "Accept": "application/json",
                    "Origin": "https://www.bybit.com",
                    "Referer": "https://www.bybit.com/",
                }
            )
        return self.session

    async def get_offers(self, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """
        Get P2P offers from ByBit API

        Args:
            force_refresh: If True, ignore cache and fetch fresh data

        Returns:
            List of normalized offers
        """
        # Check cache first
        if not force_refresh and self._is_cache_valid():
            logger.info(
                f"✅ Using cached ByBit API data ({len(self.offers_cache)} offers)"
            )
            return self.offers_cache

        try:
            logger.info("🔄 Fetching ByBit P2P offers via API...")
            start_time = datetime.now()

            # Prepare request payload
            payload = {
                "userId": "",
                "tokenId": "USDT",
                "currencyId": "UAH",
                "payment": [],
                "side": "1",  # 1 = Sell (they sell USDT, we buy)
                "size": "20",  # Get top 20 offers
                "page": "1",
                "amount": "",
            }

            session = await self._get_session()

            # Make API request
            async with session.post(
                self.api_url,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT),
            ) as response:
                if response.status != 200:
                    logger.error(f"❌ ByBit API returned status {response.status}")
                    return self.offers_cache

                data = await response.json()

                # Parse response
                offers = self._parse_api_response(data)

                # Calculate duration
                duration = (datetime.now() - start_time).total_seconds()

                if offers:
                    self.offers_cache = offers
                    self.last_update = datetime.now()
                    logger.info(
                        f"✅ ByBit API: Got {len(offers)} offers in {duration:.2f}s "
                        f"(🚀 {10 / duration:.0f}x faster than Selenium!)"
                    )
                else:
                    logger.warning(f"⚠️ No offers from ByBit API")

                return offers if offers else self.offers_cache

        except asyncio.TimeoutError:
            logger.error(f"⏱️ ByBit API timeout after {REQUEST_TIMEOUT}s - using cache")
            return self.offers_cache

        except aiohttp.ClientError as e:
            logger.error(f"🔌 ByBit API connection error: {e} - using cache")
            return self.offers_cache

        except Exception as e:
            logger.error(f"❌ ByBit API error: {e} - using cache")
            import traceback

            logger.debug(traceback.format_exc())
            return self.offers_cache

    def _parse_api_response(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Parse ByBit API response into normalized offers

        Args:
            data: Raw API response

        Returns:
            List of normalized offers
        """
        offers = []

        try:
            # Check if response is successful
            ret_code = data.get("ret_code")
            if ret_code != 0:
                logger.error(
                    f"API returned ret_code={ret_code}: {data.get('ret_msg', 'Unknown error')}"
                )
                return offers

            # Extract items list
            result = data.get("result", {})
            items = result.get("items", [])

            if not items:
                logger.warning("No items in API response")
                return offers

            logger.debug(f"Processing {len(items)} items from ByBit API...")

            for item in items:
                try:
                    # Check if seller is online (важно!)
                    is_online = item.get("isOnline", False)
                    if not is_online:
                        logger.debug(
                            f"Skipping offline seller: {item.get('nickName', 'Unknown')}"
                        )
                        continue

                    # Extract user info
                    username = item.get("nickName", "Unknown")
                    user_mask_id = item.get("userMaskId", "")

                    # Extract price and amounts
                    price = float(item.get("price", 0))

                    # Available amount in USDT
                    available_usdt = float(item.get("lastQuantity", 0))

                    # Trade limits in fiat (UAH)
                    min_amount = float(item.get("minAmount", 0))
                    max_amount = float(item.get("maxAmount", 0))

                    # Build direct link to offer
                    link = self._build_offer_link(username, user_mask_id)

                    # Validate offer data
                    if price <= 0 or available_usdt <= 0:
                        logger.debug(
                            f"Skipping invalid offer: price={price}, available={available_usdt}"
                        )
                        continue

                    # Create normalized offer
                    offer = {
                        "exchange": "bybit",
                        "username": username,
                        "price": price,
                        "available": available_usdt,
                        "min_amount": min_amount,
                        "max_amount": max_amount,
                        "link": link,
                        "timestamp": datetime.now().isoformat(),
                        "raw_data": item,  # Keep raw data for debugging
                    }

                    offers.append(offer)
                    logger.debug(
                        f"✅ Parsed offer: {username} - {price:.2f} UAH "
                        f"(available: {available_usdt:.1f} USDT, limits: {min_amount:.0f}-{max_amount:.0f} UAH)"
                    )

                except (ValueError, KeyError, TypeError) as e:
                    logger.warning(f"⚠️ Error parsing item: {e}")
                    continue

            # Sort by price (best offers first)
            offers.sort(key=lambda x: x["price"])

            logger.info(f"Successfully parsed {len(offers)} valid offers from API")

        except Exception as e:
            logger.error(f"Error parsing API response: {e}")
            import traceback

            logger.debug(traceback.format_exc())

        return offers

    def _build_offer_link(self, username: str, user_mask_id: str) -> str:
        """
        Build direct link to ByBit P2P offer

        Args:
            username: Advertiser username
            user_mask_id: User mask ID from API

        Returns:
            Direct link to advertiser page
        """
        if user_mask_id:
            # Direct link to user's P2P profile with currency pair
            return f"https://www.bybit.com/fiat/trade/otc/profile/{user_mask_id}/USDT/UAH/item"
        else:
            # Fallback to general P2P page
            return "https://www.bybit.com/fiat/trade/otc/?actionType=1&token=USDT&fiat=UAH&paymentMethod="

    def _is_cache_valid(self) -> bool:
        """Check if cache is still valid"""
        if not self.offers_cache or not self.last_update:
            return False
        return datetime.now() - self.last_update < timedelta(minutes=CACHE_TTL_MINUTES)

    def format_offer_message(self, offer: Dict[str, Any]) -> str:
        """
        Format offer for user notification (Telegram HTML)

        Args:
            offer: Normalized offer dict

        Returns:
            Formatted message string
        """
        username = offer.get("username", "Unknown")
        price = offer.get("price", 0)
        available = offer.get("available", 0)
        min_amount = offer.get("min_amount", 0)
        max_amount = offer.get("max_amount", 0)
        link = offer.get("link", "#")

        return f"""💰 <b>ByBit P2P Offer</b>
👤 Пользователь: <b>{username}</b>
💲 Цена: <b>{price:.2f} UAH</b> за USDT
📊 Доступно: <b>{available:.1f} USDT</b>
💳 Лимиты: {min_amount:.0f} - {max_amount:.0f} UAH
🔗 Прямая ссылка: <a href='{link}'>Купить у {username}</a>""".strip()

    async def cleanup(self):
        """Clean up resources (close aiohttp session)"""
        if self.session and not self.session.closed:
            await self.session.close()
            logger.debug("✅ Closed ByBit API session")

    def __del__(self):
        """Cleanup on deletion"""
        if self.session and not self.session.closed:
            try:
                # Try to close session if event loop is still running
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(self.cleanup())
                else:
                    loop.run_until_complete(self.cleanup())
            except:
                pass  # Best effort cleanup
