# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Project Overview

This is a **P2P USDT-UAH Monitoring Bot** - a Telegram bot that monitors cryptocurrency exchange rates on peer-to-peer platforms and notifies users of favorable trading opportunities. The bot scrapes real-time data from ByBit P2P marketplace using browser automation (Selenium) and provides users with direct links to trading opportunities.

### Key Capabilities
- Real-time P2P rate monitoring using browser automation
- Customizable price range notifications  
- Direct links to trading opportunities
- Multi-exchange support architecture (currently ByBit, others planned)
- Telegram bot interface with inline keyboards

## Development Commands

### Setup and Installation
```bash
# Install dependencies (Python 3.7+)
pip install -r p2p_monitoring_bot/requirements.txt

# Install Chrome/ChromeDriver (required for web scraping)
# Ensure Chrome browser is installed for Selenium automation
```

### Running the Bot
```bash
# Main bot - organized modular version
python p2p_monitoring_bot/bot/main.py

# Alternative: batch file for Windows
p2p_monitoring_bot/start_bot.bat

# Legacy single-file version (archived)
python old_project_archive/complete_p2p_monitoring_bot.py
```

### Testing
```bash
# Live ByBit data extraction test
python p2p_monitoring_bot/tests/test_live_bybit.py

# Test final functionality
python p2p_monitoring_bot/tests/test_final_functionality.py

# Test organized structure
python p2p_monitoring_bot/tests/test_organized_structure.py
```

### Configuration
- Bot token: Set `BOT_TOKEN` in `p2p_monitoring_bot/config/settings.py`
- Browser settings: Configure `BROWSER_HEADLESS`, `BROWSER_TIMEOUT` in settings
- Monitoring intervals: Adjust `MONITORING_INTERVAL` (default 60 seconds)
- User defaults: Modify `DEFAULT_USER_SETTINGS` for new user configurations

## Architecture Overview

### Project Structure
```
p2p_monitoring_bot/                 # Main organized codebase
├── bot/
│   ├── main.py                    # Application entry point
│   ├── exchanges/                 # Exchange integrations
│   │   ├── base_exchange.py       # Abstract base class for exchanges
│   │   ├── bybit_p2p.py          # ByBit P2P scraping implementation
│   │   └── placeholder_exchange.py # Template for future exchanges
│   ├── handlers/                  # Telegram bot handlers
│   │   └── bot_handlers.py        # Command and callback handlers
│   └── utils/
│       └── user_manager.py        # User settings persistence
├── config/
│   ├── settings.py               # All configuration constants
│   └── users_settings.json       # User data persistence (auto-created)
├── tests/                        # Test files
└── temp/                         # Runtime temporary files

old_project_archive/               # Legacy single-file implementation
└── complete_p2p_monitoring_bot.py # Monolithic version (working reference)
```

### Key Components

**Exchange Integration System** (`bot/exchanges/`)
- `BaseExchange`: Abstract class defining exchange interface
- `ByBitP2P`: Selenium-based web scraping for real-time P2P data
- Browser automation with anti-detection measures
- Offer parsing from dynamic web content using regex patterns
- Extensible architecture for adding new exchanges

**User Management** (`bot/utils/user_manager.py`)
- JSON-based user settings persistence
- Default configuration management
- User-specific price range settings and notification preferences

**Telegram Bot Interface** (`bot/handlers/bot_handlers.py`)
- Command handlers: `/start`, `/menu`, `/check`, `/settings`, `/status`, `/help`
- Reply keyboard menu for quick command access
- Inline keyboard interactions for user settings
- Real-time offer checking with user-customized price filters
- Formatted message generation with direct trading links

**Configuration System** (`config/settings.py`)
- Centralized settings: bot tokens, browser config, monitoring intervals
- Exchange URLs and API endpoints
- User defaults and system parameters

### Data Flow
1. User sets price range via Telegram interface
2. Bot periodically scrapes exchange data using browser automation
3. Offers filtered by user's price preferences
4. Formatted notifications sent with direct trading links
5. User settings persisted in JSON files

## Exchange Integration Guidelines

### Adding New Exchanges
1. Create new class inheriting from `BaseExchange`
2. Implement `get_offers()` method returning standardized offer format
3. Add exchange to `P2PMonitoringBot.exchanges` dictionary
4. Update configuration with new exchange URLs
5. Test with real data extraction

### Offer Data Format
```python
{
    'exchange': 'ExchangeName',
    'username': 'trader_username',
    'price': 42.50,  # Float price per USDT
    'available': 1000.0,  # Available USDT amount
    'min_amount': 500.0,   # Min UAH transaction
    'max_amount': 50000.0, # Max UAH transaction
    'link': 'https://...',  # Trading page URL
    'direct_link': 'https://...',  # Direct offer URL
    'timestamp': '2024-01-01T12:00:00'
}
```

## Browser Automation Considerations

### Selenium Configuration
- Chrome browser required for ByBit scraping
- Headless mode configurable via `BROWSER_HEADLESS`
- Anti-detection measures implemented (user agent, automation flags)
- Page load timeouts and lazy loading handling

### Web Scraping Resilience
- Regex-based text parsing from full page content
- Fallback to cached offers on scraping failures
- Error handling and logging for debugging
- Scroll-triggered lazy loading for dynamic content

## Telegram Bot Configuration

### Required Setup
1. Create bot via @BotFather in Telegram
2. Copy token to `BOT_TOKEN` in `config/settings.py`
3. Bot supports inline keyboards and HTML message formatting
4. User settings automatically persist across sessions

### User Interaction Flow
- `/start`: Bot introduction, feature overview, and reply keyboard menu
- `/menu`: Show reply keyboard menu with quick command access buttons
- `/settings`: Interactive price range configuration
- `/check`: On-demand offer checking with real-time data
- `/status`: Current user settings and bot status

## Development Notes

### Key Dependencies
- `python-telegram-bot==20.7`: Modern Telegram Bot API
- `selenium==4.15.0`: Browser automation for web scraping
- `requests==2.31.0`: HTTP requests (backup/future APIs)

### File Organization
- **Active codebase**: `p2p_monitoring_bot/` (modular, production-ready)
- **Legacy reference**: `old_project_archive/` (working single-file version)
- User data stored in `config/users_settings.json` (auto-created)
- Temporary files in `temp/` directory

### Error Handling
- Browser failures gracefully fall back to cached data
- User input validation for price ranges
- Exchange API errors logged but don't crash bot
- Selenium timeouts handled with appropriate user feedback

### Performance Considerations
- Browser instances reused across scraping sessions
- Offer caching to reduce unnecessary web requests
- Configurable monitoring intervals to balance freshness vs. load
- Cleanup methods for proper resource management

This bot architecture prioritizes reliability and extensibility, with browser automation providing real-time market data and a modular design supporting multiple exchange integrations.