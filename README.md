# 🤖 Telegram Utility & Menu Bot

A modern, production-ready Telegram Bot built in Python using **`python-telegram-bot` (v20+ async architecture)**.

## ✨ Features

- 🎮 **Interactive Menus**: Inline keyboards with dynamic sub-menus and back-navigation.
- ⚡ **Auto-Registered Commands**: Commands are registered with Telegram's UI for native autocomplete.
- 🎲 **Utility Commands**:
  - `/roll [sides]` — Roll dice (e.g. `/roll 20`).
  - `/flip` — Heads or Tails coin flip.
  - `/calc <expression>` — Safe arithmetic calculator (built with AST parsing, avoiding `eval` security risks).
  - `/time` — Displays server and UTC time.
  - `/echo <text>` — Echo text with character and word count statistics.
  - `/status` — Real-time uptime, Python version, and system metrics.
- 📝 **Interactive Multi-Step Flow**: `/feedback` flow implemented with `ConversationHandler` (category selection, message input, cancellation support).
- 🛡 **Security & Error Handling**: Global exception handler, input validation, and AST expression execution.

---

## 📁 Project Structure

```text
├── config.py             # Configuration loader, environment validation & logger
├── main.py               # Application initialization, handler routing, polling loop
├── handlers/
│   ├── __init__.py
│   ├── start.py          # /start and /help command handlers & main menu
│   ├── menu.py           # Inline button callbacks & submenu router
│   ├── tools.py          # Utility commands (/roll, /flip, /calc, /time, /echo)
│   └── feedback.py       # Multi-step ConversationHandler flow
├── tests/
│   └── test_bot.py       # Unit tests
├── requirements.txt      # Python dependencies
├── .env.example          # Environment variable template
└── README.md             # Project documentation
```

---

## 🚀 Getting Started

### 1. Obtain a Bot Token from BotFather

1. Open Telegram and search for [@BotFather](https://t.me/BotFather).
2. Send `/newbot` and follow the prompts to choose a name and username for your bot.
3. BotFather will provide an **API token** (e.g., `123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ_Example`).

### 2. Configure Environment

Copy `.env.example` to `.env` and set your token:

```bash
cp .env.example .env
```

Edit `.env`:
```env
TELEGRAM_BOT_TOKEN=your_token_from_botfather
LOG_LEVEL=INFO
```

### 3. Run the Bot

Activate the virtual environment and launch `main.py`:

```bash
source .venv/bin/activate
python main.py
```

Open Telegram and send `/start` to your bot!

---

## 🧪 Running Unit Tests

Run the test suite with:

```bash
.venv/bin/python -m unittest tests/test_bot.py
```

---

## 🛠 Adding New Commands

To add a new command (e.g. `/weather`):

1. Define your async handler function in `handlers/tools.py` (or create a new file under `handlers/`):
   ```python
   from telegram import Update
   from telegram.ext import ContextTypes

   async def weather_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
       await update.message.reply_text("Current weather: Sunny, 24°C ☀️")
   ```
2. Register it in `main.py`:
   ```python
   application.add_handler(CommandHandler("weather", weather_command))
   ```
3. Optionally add it to `post_init` in `main.py` so it appears in Telegram's autocomplete menu.
