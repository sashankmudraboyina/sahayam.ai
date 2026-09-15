import html
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes


def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    """Builds the main interactive menu inline keyboard."""
    keyboard = [
        [
            InlineKeyboardButton("🛠 Tools & Utilities", callback_data="menu:tools"),
            InlineKeyboardButton("📊 System Status", callback_data="menu:status"),
        ],
        [
            InlineKeyboardButton("📝 Give Feedback", callback_data="menu:feedback"),
            InlineKeyboardButton("❓ Help Guide", callback_data="menu:help"),
        ],
        [
            InlineKeyboardButton("❌ Close Menu", callback_data="menu:close"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_welcome_text(user_first_name: str) -> str:
    """Generates the welcome text for the main menu."""
    safe_name = html.escape(user_first_name)
    return (
        f"👋 <b>Welcome, {safe_name}!</b>\n\n"
        "I am your multipurpose <b>Telegram Utility Bot</b>.\n"
        "Use the buttons below to explore tools, check bot status, or access help.\n\n"
        "💡 <i>Tip: You can also type <code>/help</code> at any time to see the list of commands.</i>"
    )


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles /start command: sends welcome message and main menu."""
    user = update.effective_user
    first_name = user.first_name if user else "Friend"
    reply_markup = get_main_menu_keyboard()

    if update.message:
        await update.message.reply_text(
            text=get_welcome_text(first_name),
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML,
        )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles /help command: sends list of available commands and usage instructions."""
    help_text = (
        "📖 <b>Bot Command Guide</b>\n\n"
        "<b>Core Commands:</b>\n"
        "• <code>/start</code> - Open main menu\n"
        "• <code>/help</code> - Show this command guide\n"
        "• <code>/status</code> - View bot uptime and system info\n\n"
        "<b>Utility Commands:</b>\n"
        "• <code>/tools</code> - Open tools menu\n"
        "• <code>/roll [sides]</code> - Roll a die (default 6 sides, e.g. <code>/roll 20</code>)\n"
        "• <code>/flip</code> - Flip a coin (Heads or Tails)\n"
        "• <code>/calc &lt;math&gt;</code> - Calculate an expression (e.g. <code>/calc (15 * 4) + 10</code>)\n"
        "• <code>/time</code> - View current UTC and server time\n"
        "• <code>/echo &lt;text&gt;</code> - Echo text with word/character count\n\n"
        "<b>Interactive Flows:</b>\n"
        "• <code>/feedback</code> - Start interactive feedback questionnaire\n"
        "• <code>/cancel</code> - Cancel any active conversation flow"
    )

    if update.message:
        await update.message.reply_text(text=help_text, parse_mode=ParseMode.HTML)
    elif update.callback_query and update.callback_query.message:
        back_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("⬅️ Back to Main Menu", callback_data="menu:main")]
        ])
        await update.callback_query.message.edit_text(
            text=help_text,
            reply_markup=back_markup,
            parse_mode=ParseMode.HTML,
        )
