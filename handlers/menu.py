import datetime
import html
import platform
import random
import sys
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

import config
from handlers.start import get_main_menu_keyboard, get_welcome_text
from handlers.tools import get_tools_keyboard

FUN_FACTS = [
    "The first computer bug was an actual real moth trapped in a Mark II computer relay in 1947.",
    "Python was named after the British comedy troupe 'Monty Python', not the snake!",
    "Telegram was launched in 2013 by brothers Nikolai and Pavel Durov.",
    "The @BotFather is the official Telegram bot used to create and manage all Telegram bots.",
    "Over 700 million people use Telegram monthly worldwide.",
    "The first 1GB hard drive, released by IBM in 1980, weighed about 550 pounds (250 kg) and cost $40,000.",
]


async def menu_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Dispatches inline keyboard button callbacks."""
    query = update.callback_query
    if not query or not query.data:
        return

    # Always acknowledge the callback query so user sees instant response
    await query.answer()

    data = query.data

    if data == "menu:main":
        user = update.effective_user
        first_name = user.first_name if user else "Friend"
        await query.edit_message_text(
            text=get_welcome_text(first_name),
            reply_markup=get_main_menu_keyboard(),
            parse_mode=ParseMode.HTML,
        )

    elif data == "menu:tools":
        text = (
            "🛠 <b>Utilities Menu</b>\n\n"
            "Choose a quick tool below to run directly, or type <code>/help</code> to see command syntax."
        )
        await query.edit_message_text(
            text=text,
            reply_markup=get_tools_keyboard(),
            parse_mode=ParseMode.HTML,
        )

    elif data == "menu:status":
        uptime = config.get_uptime_str()
        py_ver = platform.python_version()
        sys_os = f"{platform.system()} {platform.release()}"
        user_id = update.effective_user.id if update.effective_user else "N/A"

        status_text = (
            "📊 <b>Bot & System Status</b>\n\n"
            f"⏱ <b>Uptime:</b> <code>{uptime}</code>\n"
            f"🐍 <b>Python:</b> <code>v{py_ver}</code>\n"
            f"🖥 <b>Host OS:</b> <code>{sys_os}</code>\n"
            f"👤 <b>Your Telegram ID:</b> <code>{user_id}</code>\n"
            f"⚡️ <b>Status:</b> 🟢 Operational"
        )
        back_markup = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🔄 Refresh", callback_data="menu:status"),
                InlineKeyboardButton("⬅️ Back", callback_data="menu:main"),
            ]
        ])
        await query.edit_message_text(
            text=status_text,
            reply_markup=back_markup,
            parse_mode=ParseMode.HTML,
        )

    elif data == "menu:help":
        from handlers.start import help_command
        await help_command(update, context)

    elif data == "menu:close":
        if query.message:
            await query.message.delete()

    # Tool callbacks
    elif data == "tool:roll":
        result = random.randint(1, 6)
        text = (
            f"🎲 <b>Dice Roll Result:</b>\n"
            f"You rolled a <b>{result}</b> (1–6)"
        )
        markup = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🎲 Roll Again", callback_data="tool:roll"),
                InlineKeyboardButton("⬅️ Back to Tools", callback_data="menu:tools"),
            ]
        ])
        await query.edit_message_text(text=text, reply_markup=markup, parse_mode=ParseMode.HTML)

    elif data == "tool:flip":
        outcome = random.choice(["Heads 🦅", "Tails 🪙"])
        text = f"🪙 <b>Coin Flip Result:</b>\n<b>{outcome}</b>"
        markup = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🪙 Flip Again", callback_data="tool:flip"),
                InlineKeyboardButton("⬅️ Back to Tools", callback_data="menu:tools"),
            ]
        ])
        await query.edit_message_text(text=text, reply_markup=markup, parse_mode=ParseMode.HTML)

    elif data == "tool:time":
        now_utc = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        now_local = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        text = (
            "🕒 <b>Current Time:</b>\n\n"
            f"🌐 <b>UTC:</b> <code>{now_utc}</code>\n"
            f"🖥 <b>Server:</b> <code>{now_local}</code>"
        )
        markup = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🔄 Refresh", callback_data="tool:time"),
                InlineKeyboardButton("⬅️ Back to Tools", callback_data="menu:tools"),
            ]
        ])
        await query.edit_message_text(text=text, reply_markup=markup, parse_mode=ParseMode.HTML)

    elif data == "tool:fact":
        fact = random.choice(FUN_FACTS)
        text = f"💡 <b>Did You Know?</b>\n\n<i>{fact}</i>"
        markup = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🎲 Another Fact", callback_data="tool:fact"),
                InlineKeyboardButton("⬅️ Back to Tools", callback_data="menu:tools"),
            ]
        ])
        await query.edit_message_text(text=text, reply_markup=markup, parse_mode=ParseMode.HTML)
