#!/usr/bin/env python3
"""
Browser Opener Utility
======================

Utility for opening URLs in user's default browser
Cross-platform support for Windows, Linux, and macOS
"""

import webbrowser
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class BrowserOpener:
    """Opens URLs in user's default browser"""
    
    @staticmethod
    def open_url(url: str) -> bool:
        """
        Open URL in user's default browser
        
        Args:
            url: URL to open
            
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"🌐 Opening URL in browser: {url}")
            
            # webbrowser.open() is cross-platform and opens in default browser
            # It returns True if successful
            success = webbrowser.open(url, new=2)  # new=2 opens in new tab if possible
            
            if success:
                logger.info(f"✅ Successfully opened URL in browser")
            else:
                logger.warning(f"⚠️ webbrowser.open() returned False for URL: {url}")
                
            return success
            
        except Exception as e:
            logger.error(f"❌ Error opening URL in browser: {e}")
            return False
    
    @staticmethod
    def open_multiple_urls(urls: list, delay_seconds: float = 0.5) -> int:
        """
        Open multiple URLs in browser with delay between each
        
        Args:
            urls: List of URLs to open
            delay_seconds: Delay between opening each URL (to avoid overwhelming browser)
            
        Returns:
            Number of successfully opened URLs
        """
        import time
        
        success_count = 0
        
        for i, url in enumerate(urls, 1):
            logger.info(f"Opening URL {i}/{len(urls)}: {url}")
            
            if BrowserOpener.open_url(url):
                success_count += 1
            
            # Add delay between URLs (except for last one)
            if i < len(urls) and delay_seconds > 0:
                time.sleep(delay_seconds)
        
        logger.info(f"✅ Opened {success_count}/{len(urls)} URLs successfully")
        return success_count
