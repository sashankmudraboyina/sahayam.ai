"""Sahayam.ai (సహాయం) - Telugu AI-Powered Government Welfare Scheme Discovery Platform.

Telegram Bot main entry point.
"""

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
from handlers.menu import main_callback_router
from handlers.schemes_handler import (
    categories_callback,
    handle_citizen_message,
    handle_citizen_voice,
    reset_chat_command,
    voice_toggle_command,
)
from handlers.start import help_command, language_command, start_command
from handlers.wizard import start_wizard_callback


async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles unrecognized commands with Telugu and English assistance."""
    if update.message:
        await update.message.reply_text(
            "❓ <i>క్షమించండి, ఈ కమాండ్ గుర్తించబడలేదు / Sorry, command not recognized.</i>\n\n"
            "దయచేసి <code>/start</code>, <code>/language</code> లేదా <code>/help</code> టైప్ చేయండి.",
            parse_mode=ParseMode.HTML,
        )


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Global error handler for exceptions during update processing."""
    config.logger.error("Exception while handling an update:", exc_info=context.error)
    if isinstance(update, Update) and update.effective_message:
        try:
            await update.effective_message.reply_text(
                "⚠️ <i>సందేశాన్ని ప్రాసెస్ చేయడంలో సాంకేతిక సమస్య ఏర్పడింది. దయచేసి కాసేపటి తర్వాత మళ్లీ ప్రయత్నించండి.</i>",
                parse_mode=ParseMode.HTML,
            )
        except Exception:
            pass


async def post_init(application: Application) -> None:
    """Registers bot commands in the Telegram client UI."""
    commands = [
        BotCommand("start", "ముఖ్య మెనూ ప్రారంభించండి (Main Menu)"),
        BotCommand("language", "భాషను మార్చండి / Select Language (English / తెలుగు)"),
        BotCommand("wizard", "అర్హత చెకర్ - దశలవారీగా (Eligibility Wizard)"),
        BotCommand("schemes", "పథకాల విభాగాలు చూడండి (Browse Categories)"),
        BotCommand("voice", "వాయిస్ సమాధానాలు ఆన్/ఆఫ్ (Toggle Voice)"),
        BotCommand("reset", "కొత్త సంభాషణ ప్రారంభించండి (Reset Chat)"),
        BotCommand("help", "సహాయం మరియు వినియోగ గైడ్ (Help Guide)"),
    ]
    try:
        await application.bot.set_my_commands(commands)
        config.logger.info("Bot commands successfully registered with Telegram.")
    except Exception as e:
        config.logger.warning(f"Could not register commands with Telegram: {e}")


def main() -> None:
    """Initializes and runs the Sahayam.ai Telegram Bot."""
    config.validate_config()

    config.logger.info("Starting Sahayam.ai (సహాయం) Telegram Bot Application...")

    application = (
        ApplicationBuilder()
        .token(config.BOT_TOKEN)
        .post_init(post_init)
        .build()
    )

    # 1. Core Commands
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("language", language_command))
    application.add_handler(CommandHandler("lang", language_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("voice", voice_toggle_command))
    application.add_handler(CommandHandler("reset", reset_chat_command))
    application.add_handler(CommandHandler("new", reset_chat_command))
    application.add_handler(CommandHandler("wizard", start_wizard_callback))
    application.add_handler(CommandHandler("schemes", categories_callback))

    # 2. Interactive Menu & Wizard Callbacks
    application.add_handler(CallbackQueryHandler(main_callback_router))

    # 3. Natural Language Telugu/English Citizen Message Handler (Text & Voice)
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_citizen_message)
    )
    application.add_handler(
        MessageHandler(filters.VOICE | filters.AUDIO, handle_citizen_voice)
    )

    # 4. Unknown Commands Fallback
    application.add_handler(MessageHandler(filters.COMMAND, unknown_command))

    # 5. Global Error Handler
    application.add_error_handler(error_handler)

    print("\n" + "=" * 60)
    print("🌾 Sahayam.ai (సహాయం) Telugu Bot is running!")
    print("👉 Send /start on Telegram or type in Telugu.")
    print("=" * 60 + "\n")

    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
