import logging
import os
import sys
import time
from dotenv import load_dotenv

# Record startup timestamp
START_TIME = time.time()

# Load environment variables from .env if present
load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=getattr(logging, LOG_LEVEL, logging.INFO),
)
logger = logging.getLogger("telegram_bot")


def get_uptime_str() -> str:
    """Returns a human-readable uptime string."""
    seconds = int(time.time() - START_TIME)
    days, seconds = divmod(seconds, 86400)
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)

    parts = []
    if days > 0:
        parts.append(f"{days}d")
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    parts.append(f"{seconds}s")
    return " ".join(parts)


def validate_config() -> None:
    """Validates that necessary configuration is present."""
    if not BOT_TOKEN or BOT_TOKEN == "your_bot_token_here":
        logger.error(
            "TELEGRAM_BOT_TOKEN is not configured! Please set it in your .env file or environment."
        )
        print("\n" + "=" * 60)
        print("ERROR: Missing TELEGRAM_BOT_TOKEN!")
        print("1. Create a bot using @BotFather on Telegram (https://t.me/BotFather)")
        print("2. Copy your bot API token")
        print("3. Copy .env.example to .env:")
        print("      cp .env.example .env")
        print("4. Paste your token in .env:")
        print("      TELEGRAM_BOT_TOKEN=your_token_here")
        print("=" * 60 + "\n")
        sys.exit(1)
