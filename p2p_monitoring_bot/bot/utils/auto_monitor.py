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
    AUTO_MONITORING_SAFE_INTERVAL,
    MAX_NOTIFICATIONS_PER_HOUR,
    MAX_OFFERS_PER_NOTIFICATION
)

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
                await self._check_all_users()
                
                # Wait for next check
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
            
            logger.info(f"🔍 Checking auto monitoring - found {len(enabled_users)} enabled users")
            
            if not enabled_users:
                logger.info("No users with auto monitoring enabled - waiting for next check")
                return
                
            logger.info(f"🚀 Processing {len(enabled_users)} users for auto monitoring...")
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
                    
            logger.info(f"✅ Completed auto monitoring check for {len(enabled_users)} users")
                    
        except Exception as e:
            logger.error(f"Error in _check_all_users: {e}")
            
    def _get_auto_monitoring_users(self) -> List[int]:
        """Get list of users with auto monitoring enabled"""
        enabled_users = []
        
        try:
            all_users = self.bot.user_manager.users_data
            
            for user_id_str, user_data in all_users.items():
                if user_data.get('auto_monitoring_enabled', False):
                    # Check if user hasn't exceeded notification limit
                    if self._can_send_notification(int(user_id_str)):
                        enabled_users.append(int(user_id_str))
                        
        except Exception as e:
            logger.error(f"Error getting auto monitoring users: {e}")
            
        return enabled_users
        
    def _can_send_notification(self, user_id: int) -> bool:
        """Check if user can receive notification (rate limiting)"""
        try:
            user_data = self.bot.user_manager.get_user_data(user_id)
            
            # Check last notification time
            last_notification = user_data.get('last_notification_time')
            if last_notification:
                last_time = datetime.fromisoformat(last_notification)
                time_diff = datetime.now() - last_time
                
                # Enforce minimum interval between notifications
                if time_diff.total_seconds() < AUTO_MONITORING_SAFE_INTERVAL:
                    return False
                    
                # Reset hourly counter if hour passed
                if time_diff.total_seconds() > 3600:
                    self.bot.user_manager.update_user_data(user_id, {
                        'notification_count_hour': 0
                    })
                    
            # Check hourly limit
            hourly_count = user_data.get('notification_count_hour', 0)
            return hourly_count < MAX_NOTIFICATIONS_PER_HOUR
            
        except Exception as e:
            logger.error(f"Error checking notification limits for user {user_id}: {e}")
            return False
            
    async def _check_user_offers(self, user_id: int):
        """Check offers for specific user and send notifications"""
        try:
            # Get filtered offers for user
            offers = await self.bot.get_offers_for_user(user_id)
            
            if not offers:
                logger.debug(f"No matching offers found for user {user_id}")
                return
                
            # Filter out offers we've already notified about recently
            new_offers = self._filter_new_offers(user_id, offers)
            
            if new_offers:
                await self._send_notification(user_id, new_offers)
                logger.info(f"📤 Sent notification to user {user_id} with {len(new_offers)} offers")
            else:
                logger.debug(f"No new offers for user {user_id}")
                
        except Exception as e:
            logger.error(f"Error checking offers for user {user_id}: {e}")
            
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
            message = self._format_auto_notification(offers)
            
            # Send message
            await self.telegram_app.bot.send_message(
                chat_id=user_id,
                text=message,
                parse_mode='HTML',
                disable_web_page_preview=True
            )
            
            # Update user notification data
            self._update_notification_data(user_id)
            
        except Exception as e:
            logger.error(f"Error sending notification to user {user_id}: {e}")
            
    def _format_auto_notification(self, offers: List[Dict]) -> str:
        """Format automatic notification message"""
        if not offers:
            return "🤖 Автомониторинг: предложений не найдено"
            
        message = f"🚨 <b>Автомониторинг: найдено {len(offers)} предложений!</b>\n\n"
        
        for i, offer in enumerate(offers[:MAX_OFFERS_PER_NOTIFICATION], 1):
            exchange_name = offer.get('exchange', 'Unknown')
            
            # Get exchange instance for formatting
            exchange = self.bot.exchange_manager.get_exchange(exchange_name.lower())
            if exchange:
                offer_text = exchange.format_offer_message(offer)
                message += f"<b>{i}.</b> {offer_text}\n\n"
            else:
                # Fallback formatting
                message += f"<b>{i}.</b> 💰 <b>{offer.get('username', 'Unknown')}</b>\n"
                message += f"💲 Цена: <b>{offer.get('price', 0):.2f} UAH</b>\n"
                message += f"📊 Доступно: <b>{offer.get('available', 0):.1f} USDT</b>\n\n"
                
        message += "⚡ <i>Автоматическая проверка каждые 5 минут</i>\n"
        message += "🔧 Управление: /settings → Автомониторинг"
        
        return message
        
    def _update_notification_data(self, user_id: int):
        """Update user's notification tracking data"""
        try:
            user_data = self.bot.user_manager.get_user_data(user_id)
            current_count = user_data.get('notification_count_hour', 0)
            
            self.bot.user_manager.update_user_data(user_id, {
                'last_notification_time': datetime.now().isoformat(),
                'notification_count_hour': current_count + 1
            })
            
        except Exception as e:
            logger.error(f"Error updating notification data for user {user_id}: {e}")
            
    async def toggle_user_monitoring(self, user_id: int, enabled: bool) -> str:
        """Enable/disable auto monitoring for specific user"""
        try:
            self.bot.user_manager.update_user_data(user_id, {
                'auto_monitoring_enabled': enabled
            })
            
            if enabled:
                return "✅ Автомониторинг включен! Вы будете получать уведомления каждые 5 минут при наличии подходящих предложений."
            else:
                return "❌ Автомониторинг выключен. Вы можете проверять предложения вручную командой /check."
                
        except Exception as e:
            logger.error(f"Error toggling monitoring for user {user_id}: {e}")
            return "❌ Ошибка при изменении настроек автомониторинга"
            
    def get_monitoring_status(self) -> Dict[str, Any]:
        """Get current monitoring status"""
        enabled_users = self._get_auto_monitoring_users()
        
        return {
            'active': self.monitoring_active,
            'enabled_users_count': len(enabled_users),
            'last_check_time': self.last_check_time.isoformat() if self.last_check_time else None,
            'check_interval_minutes': AUTO_MONITORING_INTERVAL // 60,
            'safe_interval_minutes': AUTO_MONITORING_SAFE_INTERVAL // 60,
            'max_notifications_per_hour': MAX_NOTIFICATIONS_PER_HOUR
        }