#!/usr/bin/env python3
"""
Auto Monitor Test
==================

Test automatic monitoring functionality
"""

import sys
import os

# Add both project root and bot directory to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
bot_dir = os.path.join(project_root, 'bot')
sys.path.append(project_root)
sys.path.append(bot_dir)

import asyncio
import logging
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

# Import from correct paths
from utils.auto_monitor import AutoMonitor
from utils.user_manager import UserManager
from main import P2PMonitoringBot

async def test_auto_monitor_initialization():
    """Test auto monitor initialization"""
    print("🧪 Test 1: Auto Monitor Initialization")
    
    try:
        # Mock telegram application
        mock_app = MagicMock()
        mock_app.bot = MagicMock()
        mock_app.bot.send_message = AsyncMock()
        
        # Create bot instance
        bot_instance = P2PMonitoringBot()
        
        # Create auto monitor
        auto_monitor = AutoMonitor(bot_instance, mock_app)
        
        # Test initial state
        assert auto_monitor.monitoring_active == False
        assert auto_monitor.monitoring_task is None
        assert auto_monitor.last_check_time is None
        
        print("   ✅ Auto monitor initialized correctly")
        return True
        
    except Exception as e:
        print(f"   ❌ Initialization failed: {e}")
        return False

async def test_user_settings():
    """Test user auto monitoring settings"""
    print("\n🧪 Test 2: User Settings Management")
    
    try:
        user_manager = UserManager()
        test_user_id = 99998
        
        # Get default user data
        user_data = user_manager.get_user_data(test_user_id)
        
        # Check default auto monitoring setting
        auto_enabled = user_data.get('auto_monitoring_enabled', None)
        print(f"   Default auto_monitoring_enabled: {auto_enabled}")
        
        # Enable auto monitoring
        user_manager.update_user_data(test_user_id, {
            'auto_monitoring_enabled': True,
            'min_rate': 41.0,
            'max_rate': 43.0,
            'min_limit': 10000.0,
            'max_limit': 50000.0
        })
        
        # Verify update
        updated_data = user_manager.get_user_data(test_user_id)
        assert updated_data['auto_monitoring_enabled'] == True
        assert updated_data['min_rate'] == 41.0
        
        print("   ✅ User settings updated correctly")
        return True
        
    except Exception as e:
        print(f"   ❌ User settings test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_monitoring_logic():
    """Test monitoring logic without actual web scraping"""
    print("\n🧪 Test 3: Monitoring Logic")
    
    try:
        # Mock telegram application
        mock_app = MagicMock()
        mock_app.bot = MagicMock()
        mock_app.bot.send_message = AsyncMock()
        
        # Create bot instance
        bot_instance = P2PMonitoringBot()
        
        # Mock get_offers_for_user to return test data
        async def mock_get_offers(user_id):
            return [
                {
                    'exchange': 'ByBit',
                    'username': 'TestUser1',
                    'price': 42.0,
                    'available': 100.0,
                    'min_amount': 5000.0,
                    'max_amount': 50000.0,
                    'link': 'https://test.com/1'
                },
                {
                    'exchange': 'ByBit',
                    'username': 'TestUser2',
                    'price': 42.5,
                    'available': 200.0,
                    'min_amount': 10000.0,
                    'max_amount': 100000.0,
                    'link': 'https://test.com/2'
                }
            ]
        
        bot_instance.get_offers_for_user = mock_get_offers
        
        # Create auto monitor
        auto_monitor = AutoMonitor(bot_instance, mock_app)
        
        # Set up test user
        user_manager = bot_instance.user_manager
        test_user_id = 99997
        user_manager.update_user_data(test_user_id, {
            'auto_monitoring_enabled': True,
            'min_rate': 41.0,
            'max_rate': 43.0,
            'notifications_enabled': True
        })
        
        # Test getting enabled users
        enabled_users = auto_monitor._get_auto_monitoring_users()
        print(f"   Enabled users found: {len(enabled_users)}")
        
        # Test can_send_notification
        can_send = auto_monitor._can_send_notification(test_user_id)
        print(f"   Can send notification: {can_send}")
        assert can_send == True
        
        # Test checking user offers
        await auto_monitor._check_user_offers(test_user_id)
        
        # Verify notification was sent
        mock_app.bot.send_message.assert_called()
        print("   ✅ Mock notification sent successfully")
        
        print("   ✅ Monitoring logic working correctly")
        return True
        
    except Exception as e:
        print(f"   ❌ Monitoring logic test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_rate_limiting():
    """Test notification rate limiting"""
    print("\n🧪 Test 4: Rate Limiting")
    
    try:
        # Mock telegram application
        mock_app = MagicMock()
        mock_app.bot = MagicMock()
        mock_app.bot.send_message = AsyncMock()
        
        # Create bot instance and auto monitor
        bot_instance = P2PMonitoringBot()
        auto_monitor = AutoMonitor(bot_instance, mock_app)
        
        test_user_id = 99996
        user_manager = bot_instance.user_manager
        
        # Set user data with recent notification
        user_manager.update_user_data(test_user_id, {
            'auto_monitoring_enabled': True,
            'last_notification_time': datetime.now().isoformat(),
            'notification_count_hour': 5
        })
        
        # Test rate limiting - should not allow notification too soon
        can_send_1 = auto_monitor._can_send_notification(test_user_id)
        print(f"   Can send immediately after notification: {can_send_1}")
        assert can_send_1 == False
        
        # Set old notification time
        old_time = (datetime.now() - timedelta(minutes=10)).isoformat()
        user_manager.update_user_data(test_user_id, {
            'last_notification_time': old_time,
            'notification_count_hour': 5
        })
        
        can_send_2 = auto_monitor._can_send_notification(test_user_id)
        print(f"   Can send after 10 minutes: {can_send_2}")
        assert can_send_2 == True
        
        # Test hourly limit
        user_manager.update_user_data(test_user_id, {
            'last_notification_time': old_time,
            'notification_count_hour': 15  # Over limit
        })
        
        can_send_3 = auto_monitor._can_send_notification(test_user_id)
        print(f"   Can send when over hourly limit: {can_send_3}")
        assert can_send_3 == False
        
        print("   ✅ Rate limiting working correctly")
        return True
        
    except Exception as e:
        print(f"   ❌ Rate limiting test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_message_formatting():
    """Test auto notification message formatting"""
    print("\n🧪 Test 5: Message Formatting")
    
    try:
        # Mock telegram application
        mock_app = MagicMock()
        bot_instance = P2PMonitoringBot()
        auto_monitor = AutoMonitor(bot_instance, mock_app)
        
        # Test offers
        test_offers = [
            {
                'exchange': 'ByBit',
                'username': 'TestUser1',
                'price': 42.0,
                'available': 100.0,
                'min_amount': 5000.0,
                'max_amount': 50000.0,
                'link': 'https://test.com/1'
            }
        ]
        
        # Format message
        message = auto_monitor._format_auto_notification(test_offers)
        
        # Check message content
        assert 'Автомониторинг' in message
        assert 'TestUser1' in message
        assert '42.00 UAH' in message
        assert 'найдено 1 предложений' in message
        
        print(f"   Message preview:")
        for line in message.split('\n')[:3]:
            print(f"      {line}")
        print("      ...")
        
        print("   ✅ Message formatting working correctly")
        return True
        
    except Exception as e:
        print(f"   ❌ Message formatting test failed: {e}")
        return False

async def test_toggle_functionality():
    """Test enable/disable auto monitoring"""
    print("\n🧪 Test 6: Toggle Functionality")
    
    try:
        # Mock telegram application
        mock_app = MagicMock()
        bot_instance = P2PMonitoringBot()
        auto_monitor = AutoMonitor(bot_instance, mock_app)
        
        test_user_id = 99995
        
        # Test enabling
        result1 = await auto_monitor.toggle_user_monitoring(test_user_id, True)
        print(f"   Enable result: {result1[:50]}...")
        
        user_data = bot_instance.user_manager.get_user_data(test_user_id)
        assert user_data['auto_monitoring_enabled'] == True
        
        # Test disabling
        result2 = await auto_monitor.toggle_user_monitoring(test_user_id, False)
        print(f"   Disable result: {result2[:50]}...")
        
        user_data = bot_instance.user_manager.get_user_data(test_user_id)
        assert user_data['auto_monitoring_enabled'] == False
        
        print("   ✅ Toggle functionality working correctly")
        return True
        
    except Exception as e:
        print(f"   ❌ Toggle functionality test failed: {e}")
        return False

async def test_system_status():
    """Test system status reporting"""
    print("\n🧪 Test 7: System Status")
    
    try:
        # Mock telegram application
        mock_app = MagicMock()
        bot_instance = P2PMonitoringBot()
        auto_monitor = AutoMonitor(bot_instance, mock_app)
        
        # Get status
        status = auto_monitor.get_monitoring_status()
        
        # Check status fields
        assert 'active' in status
        assert 'enabled_users_count' in status
        assert 'check_interval_minutes' in status
        assert 'safe_interval_minutes' in status
        assert 'max_notifications_per_hour' in status
        
        print(f"   Status: {status}")
        
        # Check values are reasonable
        assert status['check_interval_minutes'] > 0
        assert status['safe_interval_minutes'] > 0
        assert status['max_notifications_per_hour'] > 0
        
        print("   ✅ System status working correctly")
        return True
        
    except Exception as e:
        print(f"   ❌ System status test failed: {e}")
        return False

async def main():
    """Run all auto monitor tests"""
    print("🚀 AUTO MONITOR TEST SUITE")
    print("=" * 50)
    
    tests = [
        test_auto_monitor_initialization,
        test_user_settings,
        test_monitoring_logic,
        test_rate_limiting,
        test_message_formatting,
        test_toggle_functionality,
        test_system_status
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            result = await test()
            if result:
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"   💥 Test crashed: {e}")
            failed += 1
    
    print("\n" + "=" * 50)
    print("🏁 TEST RESULTS:")
    print(f"   ✅ Passed: {passed}")
    print(f"   ❌ Failed: {failed}")
    
    if failed == 0:
        print("\n🎉 ALL AUTO MONITOR TESTS PASSED!")
        print("🤖 Auto monitoring system is ready for production!")
        print("\nNext steps:")
        print("• Run the bot: python bot/main.py")
        print("• Use /automonitor to enable auto monitoring")
        print("• Configure price ranges and limits in /settings")
    else:
        print(f"\n⚠️ {failed} TESTS FAILED")
        print("🔧 Please check the errors above")
    
    success_rate = (passed / (passed + failed)) * 100
    print(f"\n📊 SUCCESS RATE: {success_rate:.1f}%")
    
    return failed == 0

if __name__ == "__main__":
    asyncio.run(main())