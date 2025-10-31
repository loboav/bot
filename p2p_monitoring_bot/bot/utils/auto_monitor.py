#!/usr/bin/env python3
"""
Auto Monitor
============

Automatic P2P monitoring system with smart notification delivery
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import traceback

from config.settings import (
    AUTO_MONITORING_INTERVAL,
    MAX_OFFERS_PER_NOTIFICATION,
    AUTO_MONITOR_TOP_OFFERS_LIMIT,
)

try:
    from .browser_opener import BrowserOpener
except ImportError:
    from browser_opener import BrowserOpener

logger = logging.getLogger(__name__)


class AutoMonitor:
    """Automatic P2P monitoring with smart rate limiting"""

    def __init__(self, bot_instance, telegram_application):
        self.bot = bot_instance
        self.telegram_app = telegram_application
        self.monitoring_active = False
        self.monitoring_task = None
        self.last_check_time = None

    async def start_monitoring(self):
        """Start automatic monitoring for all enabled users"""
        if self.monitoring_active:
            logger.warning("Auto monitoring already active")
            return

        self.monitoring_active = True
        self.monitoring_task = asyncio.create_task(self._monitoring_loop())
        logger.info("🚀 Auto monitoring started!")

    async def stop_monitoring(self):
        """Stop automatic monitoring"""
        self.monitoring_active = False
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
        logger.info("⏹️ Auto monitoring stopped")

    async def _monitoring_loop(self):
        """Main monitoring loop with error handling"""
        logger.info("🔄 Auto monitoring loop started")

        while self.monitoring_active:
            try:
                cycle_start = datetime.now()
                logger.info(
                    f"⏰ Starting new cycle at {cycle_start.strftime('%H:%M:%S')}"
                )

                await self._check_all_users()

                cycle_end = datetime.now()
                cycle_duration = (cycle_end - cycle_start).total_seconds()
                logger.info(f"✅ Cycle completed in {cycle_duration:.1f}s")

                # Wait for next check
                logger.info(f"💤 Sleeping for {AUTO_MONITORING_INTERVAL} seconds...")
                await asyncio.sleep(AUTO_MONITORING_INTERVAL)

            except asyncio.CancelledError:
                logger.info("Auto monitoring cancelled")
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                logger.error(traceback.format_exc())
                # Wait a bit before retrying on error
                await asyncio.sleep(60)

    async def _check_all_users(self):
        """Check offers for all users with auto monitoring enabled"""
        try:
            # Get users with auto monitoring enabled
            enabled_users = self._get_auto_monitoring_users()

            logger.info(
                f"🔍 Checking auto monitoring - found {len(enabled_users)} enabled users"
            )

            if not enabled_users:
                logger.info(
                    "No users with auto monitoring enabled - waiting for next check"
                )
                return

            logger.info(
                f"🚀 Processing {len(enabled_users)} users for auto monitoring..."
            )
            self.last_check_time = datetime.now()

            # Process users in batches to avoid overwhelming the system
            for user_id in enabled_users:
                try:
                    logger.info(f"Checking offers for user {user_id}...")
                    await self._check_user_offers(user_id)
                    # Small delay between users to be gentle
                    await asyncio.sleep(2)
                except Exception as e:
                    logger.error(f"Error checking offers for user {user_id}: {e}")

            logger.info(
                f"✅ Completed auto monitoring check for {len(enabled_users)} users"
            )

        except Exception as e:
            logger.error(f"Error in _check_all_users: {e}")

    def _get_auto_monitoring_users(self) -> List[int]:
        """Get list of users with auto monitoring enabled"""
        enabled_users = []

        try:
            all_users = self.bot.user_manager.users_data

            for user_id_str, user_data in all_users.items():
                if user_data.get("auto_monitoring_enabled", False):
                    enabled_users.append(int(user_id_str))

        except Exception as e:
            logger.error(f"Error getting auto monitoring users: {e}")

        return enabled_users

    async def _check_user_offers(self, user_id: int):
        """Check offers for specific user and send notifications"""
        try:
            # Используем отдельные настройки автомониторинга (узкий диапазон)
            offers = await self._get_automonitor_offers(user_id)

            if not offers:
                logger.debug(
                    f"No matching offers found for user {user_id} in automonitor range"
                )
                return

            # Filter out offers we've already notified about recently
            new_offers = self._filter_new_offers(user_id, offers)

            if new_offers:
                await self._send_notification(user_id, new_offers)
                logger.info(
                    f"📤 Sent notification to user {user_id} with {len(new_offers)} offers"
                )
            else:
                logger.debug(f"No new offers for user {user_id}")

        except Exception as e:
            logger.error(f"Error checking offers for user {user_id}: {e}")
            logger.error(traceback.format_exc())
            # Не падаем, продолжаем работу

    async def _get_automonitor_offers(self, user_id: int) -> List[Dict[str, Any]]:
        """Get offers for automonitor with narrow range and top offers limit"""
        user_data = self.bot.user_manager.get_user_data(user_id)

        # Используем отдельные настройки для автомониторинга
        auto_min_rate = user_data.get("auto_monitor_min_rate", user_data["min_rate"])
        auto_max_rate = user_data.get("auto_monitor_max_rate", user_data["max_rate"])
        auto_min_limit = user_data.get(
            "auto_monitor_min_limit", user_data.get("min_limit", 5000)
        )
        auto_max_limit = user_data.get(
            "auto_monitor_max_limit", user_data.get("max_limit", 100000)
        )

        logger.info(
            f"Automonitor settings for user {user_id}: rate {auto_min_rate}-{auto_max_rate}, limits {auto_min_limit}-{auto_max_limit}"
        )

        # Get offers from user's active exchanges
        try:
            all_offers = await self.bot.exchange_manager.get_combined_offers(
                exchange_names=user_data["active_exchanges"],
                force_refresh=True,  # Всегда свежие данные для автомониторинга
            )
        except Exception as e:
            logger.error(f"Error getting combined offers for automonitor: {e}")
            logger.error(traceback.format_exc())
            # Возвращаем пустой список вместо падения
            return []

        # Сортируем по цене и берем только топ N предложений
        all_offers.sort(key=lambda x: x.get("price", float("inf")))
        top_offers = all_offers[:AUTO_MONITOR_TOP_OFFERS_LIMIT]

        # Фильтруем только топ предложения по узкому диапазону
        filtered_offers = []
        top_prices = [f"{o['price']:.2f}" for o in top_offers]
        logger.info(f"Top {len(top_offers)} offers prices: {top_prices}")

        for offer in top_offers:
            username = offer.get("username", "Unknown")
            price = offer.get("price", 0)
            offer_min = offer.get("min_amount", 0)
            offer_max = offer.get("max_amount", 999999)

            # Price filter - узкий диапазон
            if not (auto_min_rate <= price <= auto_max_rate):
                logger.info(
                    f"❌ {username}: price {price:.2f} NOT in range {auto_min_rate}-{auto_max_rate}"
                )
                continue

            logger.info(
                f"✅ {username}: price {price:.2f} IN range {auto_min_rate}-{auto_max_rate}"
            )

            # Limits filter - проверяем пересечение диапазонов
            if offer_max >= auto_min_limit and offer_min <= auto_max_limit:
                filtered_offers.append(offer)
                logger.info(
                    f"✅✅ MATCH! {username} - {price:.2f} UAH, limits {offer_min:.0f}-{offer_max:.0f} overlap with {auto_min_limit:.0f}-{auto_max_limit:.0f}"
                )
            else:
                logger.info(
                    f"❌ {username}: limits {offer_min:.0f}-{offer_max:.0f} DON'T overlap with {auto_min_limit:.0f}-{auto_max_limit:.0f}"
                )

        logger.info(
            f"Automonitor: checked top {AUTO_MONITOR_TOP_OFFERS_LIMIT} offers, found {len(filtered_offers)} matching narrow range"
        )
        return filtered_offers

    def _filter_new_offers(self, user_id: int, offers: List[Dict]) -> List[Dict]:
        """Filter out offers that user has already been notified about"""
        # For simplicity, we'll consider offers "new" if they're different from last check
        # In a more sophisticated system, we could track individual offer IDs

        # Limit to top offers only
        return offers[:MAX_OFFERS_PER_NOTIFICATION]

    async def _send_notification(self, user_id: int, offers: List[Dict]):
        """Send notification to user about new offers"""
        try:
            # Format notification message
            message = (
                f"🚨 <b>Автомониторинг: найдено {len(offers)} предложений!</b>\n\n"
            )

            # Collect unique exchanges from offers
            exchanges_in_offers = set()

            for i, offer in enumerate(offers, 1):
                exchange_name = offer.get("exchange", "unknown")
                exchanges_in_offers.add(exchange_name)

                exchange = self.bot.exchange_manager.get_exchange(exchange_name)

                if exchange:
                    offer_text = exchange.format_offer_message(offer)
                else:
                    # Fallback formatting
                    username = offer.get("username", "Unknown")
                    price = offer.get("price", 0)
                    available = offer.get("available", 0)
                    min_amount = offer.get("min_amount", 0)
                    max_amount = offer.get("max_amount", 0)
                    link = offer.get("link", "#")

                    offer_text = f"""💰 <b>{exchange_name.title()} P2P Offer</b>
👤 Пользователь: <b>{username}</b>
💲 Цена: <b>{price:.2f} UAH</b> за USDT
📊 Доступно: <b>{available:.1f} USDT</b>
💳 Лимиты: {min_amount:.0f} - {max_amount:.0f} UAH
🔗 Прямая ссылка: <a href='{link}'>Купить у {username}</a>""".strip()

                message += f"<b>{i}.</b> {offer_text}\n\n"

            # Add quick links for exchanges that appeared in offers
            exchange_links = {
                "binance": "https://p2p.binance.com/ru/trade/all-payments/USDT?fiat=UAH",
                "bybit": "https://www.bybit.com/fiat/trade/otc/?actionType=1&token=USDT&fiat=UAH&paymentMethod=",
                "bitget": "https://www.bitget.com/ru/p2p-trade?paymethodIds=-1&fiatName=UAH",
            }

            for exchange_name in sorted(exchanges_in_offers):
                if exchange_name in exchange_links:
                    exchange_title = exchange_name.title()
                    link = exchange_links[exchange_name]
                    message += f"⚡ Быстрая ссылка: <a href='{link}'>Все объявления {exchange_title} P2P</a>\n"

            message += "\n⚡ Данные обновлены только что!\n"
            message += f"🕐 Время проверки: {datetime.now().strftime('%H:%M:%S')}"

            # Send notification via Telegram
            await self.telegram_app.bot.send_message(
                chat_id=user_id,
                text=message,
                parse_mode="HTML",
                disable_web_page_preview=True,
            )

            logger.info(f"✅ Notification sent to user {user_id}")
            
            # Auto-open browser if enabled for this user
            await self._auto_open_browser_if_enabled(user_id, offers)

        except Exception as e:
            logger.error(f"Error sending notification to user {user_id}: {e}")
            logger.error(traceback.format_exc())
    
    async def _auto_open_browser_if_enabled(self, user_id: int, offers: List[Dict]):
        """Automatically open offer links in browser if user has this feature enabled"""
        try:
            user_data = self.bot.user_manager.get_user_data(user_id)
            auto_open_enabled = user_data.get('auto_open_browser', True)
            
            if not auto_open_enabled:
                logger.info(f"Auto-open browser disabled for user {user_id}")
                return
            
            if not offers:
                logger.info(f"No offers to open for user {user_id}")
                return
            
            # Extract links from offers
            links_to_open = []
            for offer in offers:
                link = offer.get('link')
                if link and link != '#':
                    links_to_open.append(link)
            
            if not links_to_open:
                logger.warning(f"No valid links found in offers for user {user_id}")
                return
            
            logger.info(f"🌐 Auto-opening {len(links_to_open)} links in browser for user {user_id}")
            
            # Open links in browser (run in executor to not block async loop)
            import asyncio
            loop = asyncio.get_event_loop()
            
            def open_links():
                return BrowserOpener.open_multiple_urls(links_to_open, delay_seconds=0.3)
            
            success_count = await loop.run_in_executor(None, open_links)
            
            logger.info(f"✅ Auto-opened {success_count}/{len(links_to_open)} links for user {user_id}")
            
        except Exception as e:
            logger.error(f"Error auto-opening browser for user {user_id}: {e}")
            logger.error(traceback.format_exc())
            # Don't fail the notification if browser opening fails

    async def toggle_user_monitoring(self, user_id: int, enabled: bool) -> str:
        """Toggle auto monitoring for specific user"""
        try:
            self.bot.user_manager.update_user_data(
                user_id, {"auto_monitoring_enabled": enabled}
            )

            if enabled:
                return "✅ Автомониторинг включен! Вы будете получать уведомления о выгодных предложениях."
            else:
                return "❌ Автомониторинг выключен. Уведомления остановлены."

        except Exception as e:
            logger.error(f"Error toggling monitoring for user {user_id}: {e}")
            return f"❌ Ошибка при изменении настроек: {str(e)}"

    def get_monitoring_status(self) -> Dict[str, Any]:
        """Get current monitoring status"""
        enabled_users = self._get_auto_monitoring_users()

        return {
            "active": self.monitoring_active,
            "enabled_users_count": len(enabled_users),
            "last_check_time": self.last_check_time.isoformat()
            if self.last_check_time
            else None,
            "check_interval_seconds": AUTO_MONITORING_INTERVAL,
        }
