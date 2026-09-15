import platform
from telegram import BotCommand, Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

import config
from handlers.feedback import get_feedback_conversation_handler
from handlers.menu import menu_callback_handler
from handlers.start import help_command, start_command
from handlers.tools import (
    calc_command,
    echo_command,
    flip_command,
    roll_command,
    time_command,
    tools_menu_command,
)


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles /status command."""
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
    if update.message:
        await update.message.reply_text(status_text, parse_mode=ParseMode.HTML)


async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles unrecognized commands."""
    if update.message:
        await update.message.reply_text(
            "❓ Unrecognized command. Type <code>/help</code> to see all available commands or <code>/start</code> for the main menu.",
            parse_mode=ParseMode.HTML,
        )


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Global error handler for unexpected exceptions."""
    config.logger.error("Exception while handling an update:", exc_info=context.error)
    if isinstance(update, Update) and update.effective_message:
        try:
            await update.effective_message.reply_text(
                "⚠️ <i>An unexpected error occurred while processing your request. Please try again.</i>",
                parse_mode=ParseMode.HTML,
            )
        except Exception:
            pass


async def post_init(application: Application) -> None:
    """Configures bot commands in the Telegram UI after startup."""
    commands = [
        BotCommand("start", "Launch the main interactive menu"),
        BotCommand("help", "Display command guide and instructions"),
        BotCommand("tools", "Open interactive utilities menu"),
        BotCommand("status", "Check bot uptime and system diagnostics"),
        BotCommand("roll", "Roll a die (e.g. /roll 20)"),
        BotCommand("flip", "Flip a coin"),
        BotCommand("calc", "Evaluate math expression safely"),
        BotCommand("time", "Current UTC and server time"),
        BotCommand("feedback", "Submit suggestions or bug reports"),
    ]
    try:
        await application.bot.set_my_commands(commands)
        config.logger.info("Bot commands successfully registered with Telegram.")
    except Exception as e:
        config.logger.warning(f"Could not register commands with Telegram: {e}")


def main() -> None:
    """Initializes and runs the Telegram bot."""
    # Check that TELEGRAM_BOT_TOKEN is set
    config.validate_config()

    config.logger.info("Starting Telegram Bot Application...")

    application = (
        ApplicationBuilder()
        .token(config.BOT_TOKEN)
        .post_init(post_init)
        .build()
    )

    # 1. Conversation handlers (highest priority)
    application.add_handler(get_feedback_conversation_handler())

    # 2. Command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("tools", tools_menu_command))
    application.add_handler(CommandHandler("roll", roll_command))
    application.add_handler(CommandHandler("flip", flip_command))
    application.add_handler(CommandHandler("calc", calc_command))
    application.add_handler(CommandHandler("time", time_command))
    application.add_handler(CommandHandler("echo", echo_command))

    # 3. Callback query handlers for inline menu buttons
    application.add_handler(CallbackQueryHandler(menu_callback_handler))

    # 4. Unknown commands handler
    application.add_handler(MessageHandler(filters.COMMAND, unknown_command))

    # 5. Global error handler
    application.add_error_handler(error_handler)

    print("\n" + "=" * 50)
    print("🤖 Telegram Bot is running! Press Ctrl+C to stop.")
    print("=" * 50 + "\n")

    # Run polling loop
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
