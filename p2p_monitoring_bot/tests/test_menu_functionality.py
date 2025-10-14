#!/usr/bin/env python3
"""
Test Menu Functionality
========================

Test script to verify the new menu functionality works correctly
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import logging
from bot.handlers.bot_handlers import BotHandlers
from bot.exchanges.bybit_p2p import ByBitP2P
from bot.exchanges.placeholder_exchange import PlaceholderExchange
from bot.utils.user_manager import UserManager

# Mock P2P Bot class for testing
class MockP2PBot:
    def __init__(self):
        self.exchanges = {
            'bybit': ByBitP2P(),
            'okx': PlaceholderExchange('OKX'),
        }
        self.user_manager = UserManager()

async def test_menu_functionality():
    """Test the new menu functionality"""
    print("🧪 Testing New Menu Functionality")
    print("=" * 50)
    
    success = True
    
    # Test 1: Bot handlers can be instantiated with menu methods
    print("1. 📋 Testing menu methods...")
    try:
        bot_instance = MockP2PBot()
        handlers = BotHandlers(bot_instance)
        
        # Check if menu methods exist
        assert hasattr(handlers, 'build_main_reply_keyboard'), "build_main_reply_keyboard method missing"
        assert hasattr(handlers, 'menu_command'), "menu_command method missing"
        
        print("   ✅ Menu methods exist")
    except Exception as e:
        print(f"   ❌ Menu methods error: {e}")
        success = False
    
    # Test 2: Reply keyboard can be built
    print("\n2. ⌨️ Testing reply keyboard construction...")
    try:
        keyboard = handlers.build_main_reply_keyboard()
        assert keyboard is not None, "Keyboard should not be None"
        assert hasattr(keyboard, 'keyboard'), "Keyboard should have keyboard attribute"
        
        # Check keyboard structure
        keyboard_buttons = keyboard.keyboard
        assert len(keyboard_buttons) == 2, "Should have 2 rows"
        assert len(keyboard_buttons[0]) == 2, "First row should have 2 buttons"
        assert len(keyboard_buttons[1]) == 2, "Second row should have 2 buttons"
        
        # Check button text
        button_texts = []
        for row in keyboard_buttons:
            for button in row:
                button_texts.append(button.text)
        
        expected_commands = ['/check', '/settings', '/status', '/help']
        for cmd in expected_commands:
            assert cmd in button_texts, f"Command {cmd} should be in keyboard"
        
        print("   ✅ Reply keyboard constructed correctly")
        print(f"   📱 Keyboard layout: {[row[0].text + ' | ' + row[1].text for row in keyboard_buttons]}")
    except Exception as e:
        print(f"   ❌ Keyboard construction error: {e}")
        success = False
    
    # Test 3: Import check for new Telegram components
    print("\n3. 📦 Testing Telegram imports...")
    try:
        from telegram import ReplyKeyboardMarkup, KeyboardButton
        print("   ✅ New Telegram components imported successfully")
    except ImportError as e:
        print(f"   ❌ Import error: {e}")
        success = False
    
    # Test 4: Check handlers registration includes menu
    print("\n4. 🔧 Testing handler registration...")
    try:
        # This would normally require an actual Application instance
        # For testing, we just check the method exists
        assert hasattr(handlers, 'register_handlers'), "register_handlers method should exist"
        print("   ✅ Handler registration method exists")
        print("   💡 Menu command (/menu) should be registered in register_handlers")
    except Exception as e:
        print(f"   ❌ Handler registration error: {e}")
        success = False
    
    # Cleanup
    bot_instance.exchanges['bybit'].cleanup()
    
    # Final Result
    print("\n" + "="*50)
    if success:
        print("🎉 MENU FUNCTIONALITY TEST PASSED!")
        print("✅ New menu is ready to use!")
        print("🚀 Users can now use:")
        print("   • /start - Shows welcome + menu")
        print("   • /menu - Shows menu anytime")
        print("   • Reply keyboard buttons for easy access")
    else:
        print("❌ SOME MENU TESTS FAILED")
        print("🔧 Please check the errors above")
    
    print(f"\n📋 Menu Test Result: {'SUCCESS' if success else 'FAILED'}")
    return success

if __name__ == "__main__":
    asyncio.run(test_menu_functionality())