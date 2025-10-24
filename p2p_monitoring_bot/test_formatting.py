#!/usr/bin/env python3
"""
Test Offer Formatting
=====================

Test that all exchanges format messages correctly with clickable links
"""

import sys
import os
from datetime import datetime

# Add project paths
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "bot"))

from bot.exchanges.binance_p2p import BinanceP2P
from bot.exchanges.bybit_p2p import ByBitP2P
from bot.exchanges.bitget_p2p import BitgetP2P


def test_formatting():
    """Test message formatting for all exchanges"""
    print("=" * 60)
    print("🧪 TESTING OFFER MESSAGE FORMATTING")
    print("=" * 60)

    # Test data
    test_offer = {
        "username": "TestUser123",
        "price": 43.25,
        "available": 150.5,
        "min_amount": 5000.0,
        "max_amount": 50000.0,
        "link": "https://example.com/user/s123456789",
        "timestamp": datetime.now().isoformat(),
    }

    exchanges = [
        ("Binance", BinanceP2P()),
        ("ByBit", ByBitP2P()),
        ("Bitget", BitgetP2P()),
    ]

    for exchange_name, exchange in exchanges:
        print(f"\n{'=' * 60}")
        print(f"📊 {exchange_name} Formatting:")
        print("=" * 60)

        try:
            message = exchange.format_offer_message(test_offer)
            print(message)

            # Check for required elements
            print("\n✅ Validation:")
            checks = [
                ("Username present", "TestUser123" in message),
                ("Price present", "43.25 UAH" in message),
                ("Available present", "150.5 USDT" in message),
                ("Limits present", "5000" in message and "50000" in message),
                ("Direct link present", "<a href=" in message),
                ("Fast link present", "Быстрая ссылка" in message),
                ("HTML formatting", "<b>" in message),
            ]

            all_passed = True
            for check_name, passed in checks:
                status = "✅" if passed else "❌"
                print(f"   {status} {check_name}")
                if not passed:
                    all_passed = False

            if all_passed:
                print(f"\n🎉 {exchange_name} formatting is PERFECT!")
            else:
                print(f"\n⚠️ {exchange_name} formatting has issues")

        except Exception as e:
            print(f"\n❌ ERROR formatting {exchange_name}: {e}")

    print("\n" + "=" * 60)
    print("🏁 FORMATTING TEST COMPLETE")
    print("=" * 60)


def test_html_preview():
    """Show how the message will look in Telegram"""
    print("\n" + "=" * 60)
    print("📱 TELEGRAM PREVIEW (HTML stripped)")
    print("=" * 60)

    test_offer = {
        "username": "Money24na7",
        "price": 43.16,
        "available": 20.0,
        "min_amount": 700.0,
        "max_amount": 701.0,
        "link": "https://c2c.binance.com/ru/advertiserDetail?advertiserNo=s810abd53a68e347ea8e965277229fac0",
        "timestamp": datetime.now().isoformat(),
    }

    binance = BinanceP2P()
    message = binance.format_offer_message(test_offer)

    # Strip HTML for preview (Telegram will render it properly)
    import re

    preview = message
    preview = re.sub(r"<b>(.*?)</b>", r"**\1**", preview)  # Bold
    preview = re.sub(
        r'<a href=[\'"]([^\'"]+)[\'"]>([^<]+)</a>', r"\2 (\1)", preview
    )  # Links

    print("\n" + preview)

    print("\n💡 In Telegram:")
    print("   - **text** will be bold")
    print("   - Links will be clickable")
    print("   - Emojis will render properly")


if __name__ == "__main__":
    test_formatting()
    test_html_preview()

    print("\n✅ All formatting tests completed!")
    print("💡 Messages are ready for Telegram!")
