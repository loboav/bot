#!/usr/bin/env python3
"""
BACKUP: Binance Text-Based Parsing Methods
===========================================

This file contains the OLD text-based parsing methods from binance_p2p.py
Saved on 2024-10-24 as backup before switching to DOM parsing.

⚠️ This is a BACKUP only - not used in production!
⚠️ Kept for emergency fallback if DOM parsing fails completely.

Usage: Copy methods back to binance_p2p.py if needed.
"""

import re
from typing import List, Dict, Any, Tuple

# Constants from original file
PRICE_RANGE = (35.0, 55.0)
MIN_USDT_AMOUNT = 10.0
MIN_LIMIT_VALUE = 100.0
USERNAME_LENGTH_RANGE = (3, 25)
SEARCH_RADIUS = 20
USDT_SEARCH_RADIUS = 15
LIMIT_SEARCH_RADIUS = 15
MAX_OFFERS_TO_PARSE = 15


def _parse_offers_text(
    page_text: str, page_source: str, advertiser_ids: List[str]
) -> List[Dict[str, Any]]:
    """
    OLD TEXT-BASED PARSING METHOD
    Parse offers from page text with improved pattern matching

    This method splits page text into lines and tries to match
    price, username, USDT amount, and limits by searching in radius.

    ❌ PROBLEMS:
    - Fragile: breaks if page structure changes
    - Inaccurate: might match wrong username/price pairs
    - No real links: has to guess links
    """
    offers = []
    lines = page_text.split("\n")

    # Extract patterns
    price_patterns = _extract_price_patterns(lines)
    username_patterns = _extract_username_patterns(lines)
    usdt_patterns = _extract_usdt_patterns(lines)
    limit_patterns = _extract_limit_patterns(lines)

    # Match data by position
    for offer_idx, (price_idx, price_line, price_uah, priority) in enumerate(
        price_patterns[:MAX_OFFERS_TO_PARSE]
    ):
        try:
            username = _find_nearest_username(price_idx, username_patterns)
            if username == "Unknown":
                continue  # Skip offers without username

            usdt_amount = _find_nearest_usdt(price_idx, usdt_patterns)
            min_limit, max_limit = _find_nearest_limits(price_idx, limit_patterns)

            # Get advertiser ID
            advertiser_no = (
                advertiser_ids[offer_idx] if offer_idx < len(advertiser_ids) else None
            )
            direct_link = _build_offer_link(username, advertiser_no, usdt_amount)

            # Create offer
            raw_offer = {
                "username": username,
                "price": price_uah,
                "available": usdt_amount,
                "min_amount": min_limit,
                "max_amount": max_limit,
                "link": direct_link,
            }

            offers.append(raw_offer)

        except Exception as e:
            print(f"Error parsing offer at line {price_idx}: {e}")
            continue

    # Sort by price
    offers.sort(key=lambda x: x["price"])
    return offers


def _extract_price_patterns(lines: List[str]) -> List[Tuple[int, str, float, int]]:
    """Extract price patterns with priority"""
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


def _extract_username_patterns(lines: List[str]) -> List[Tuple[int, str]]:
    """Extract username patterns"""
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


def _extract_usdt_patterns(lines: List[str]) -> List[Tuple[int, str, float]]:
    """Extract USDT amount patterns"""
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


def _extract_limit_patterns(lines: List[str]) -> List[Tuple[int, str, float]]:
    """Extract limit patterns"""
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
    price_idx: int, username_patterns: List[Tuple[int, str]]
) -> str:
    """Find nearest username to price line (searches in radius)"""
    username = "Unknown"
    min_distance = float("inf")

    for user_idx, user_name in username_patterns:
        distance = abs(user_idx - price_idx)
        if distance < min_distance and distance <= SEARCH_RADIUS:
            username = user_name
            min_distance = distance

    return username


def _find_nearest_usdt(
    price_idx: int, usdt_patterns: List[Tuple[int, str, float]]
) -> float:
    """Find nearest USDT amount to price line"""
    usdt_amount = 100.0  # Default
    min_distance = float("inf")

    for usdt_idx, _, amount in usdt_patterns:
        distance = abs(usdt_idx - price_idx)
        if distance < min_distance and distance <= USDT_SEARCH_RADIUS:
            usdt_amount = amount
            min_distance = distance

    return usdt_amount


def _find_nearest_limits(
    price_idx: int, limit_patterns: List[Tuple[int, str, float]]
) -> Tuple[float, float]:
    """Find nearest limit values to price line"""
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


def _build_offer_link(username: str, advertiser_no: str, usdt_amount: float) -> str:
    """Build direct link to offer (guesses if no advertiser_no)"""
    if advertiser_no:
        return (
            f"https://c2c.binance.com/ru/advertiserDetail?advertiserNo={advertiser_no}"
        )
    else:
        # ❌ Fallback: guess the link
        return f"https://p2p.binance.com/ru/trade/all-payments/USDT?fiat=UAH&merchant={username}&amount={usdt_amount}"


# ============================================================================
# HOW TO RESTORE IF NEEDED:
# ============================================================================
#
# 1. Open bot/exchanges/binance_p2p.py
#
# 2. In _parse_offers() method, replace DOM parsing section with:
#    ```
#    # Use old text parsing
#    offers = _parse_offers_text(page_text, page_source, advertiser_ids)
#    return offers
#    ```
#
# 3. Copy all _extract_* and _find_nearest_* methods to binance_p2p.py class
#
# 4. Test with: python test_binance_dom.py
#
# ============================================================================


if __name__ == "__main__":
    print("=" * 60)
    print("⚠️ BACKUP FILE - DO NOT RUN DIRECTLY")
    print("=" * 60)
    print()
    print("This file contains backup of old text-based parsing methods.")
    print("It is NOT meant to be run directly.")
    print()
    print("To restore old parsing:")
    print("1. Copy methods to binance_p2p.py")
    print("2. Replace DOM parsing call with text parsing call")
    print("3. Test thoroughly")
    print()
    print("Created: 2024-10-24")
    print("Reason: Switching to DOM parsing")
    print("=" * 60)
