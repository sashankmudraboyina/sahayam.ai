import html
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ConversationHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# Conversation states
SELECTING_CATEGORY, TYPING_FEEDBACK = range(2)


def get_category_keyboard() -> InlineKeyboardMarkup:
    """Keyboard for selecting feedback category."""
    keyboard = [
        [
            InlineKeyboardButton("💡 Feature Request", callback_data="cat:feature"),
            InlineKeyboardButton("🐛 Bug Report", callback_data="cat:bug"),
        ],
        [
            InlineKeyboardButton("💬 General Feedback", callback_data="cat:general"),
            InlineKeyboardButton("❌ Cancel", callback_data="cat:cancel"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


async def feedback_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Entry point for /feedback command or menu:feedback button."""
    text = (
        "📝 <b>Feedback & Suggestions</b>\n\n"
        "We'd love to hear from you! Please choose a category for your submission:"
    )
    markup = get_category_keyboard()

    if update.callback_query:
        await update.callback_query.answer()
        if update.callback_query.message:
            await update.callback_query.message.edit_text(
                text=text, reply_markup=markup, parse_mode=ParseMode.HTML
            )
    elif update.message:
        await update.message.reply_text(
            text=text, reply_markup=markup, parse_mode=ParseMode.HTML
        )

    return SELECTING_CATEGORY


async def category_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores chosen category and prompts for feedback text."""
    query = update.callback_query
    if not query or not query.data:
        return ConversationHandler.END

    await query.answer()
    category_map = {
        "cat:feature": "💡 Feature Request",
        "cat:bug": "🐛 Bug Report",
        "cat:general": "💬 General Feedback",
    }

    if query.data == "cat:cancel":
        if query.message:
            await query.message.edit_text(
                "❌ <i>Feedback submission cancelled.</i>", parse_mode=ParseMode.HTML
            )
        return ConversationHandler.END

    selected_category = category_map.get(query.data, "Feedback")
    context.user_data["feedback_category"] = selected_category

    text = (
        f"Selected: <b>{selected_category}</b>\n\n"
        "Please type and send your feedback message below.\n"
        "<i>(Type /cancel at any point to abort)</i>"
    )
    if query.message:
        await query.message.edit_text(text=text, parse_mode=ParseMode.HTML)

    return TYPING_FEEDBACK


async def feedback_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receives message text and completes submission."""
    if not update.message or not update.message.text:
        return TYPING_FEEDBACK

    category = context.user_data.get("feedback_category", "General Feedback")
    user_msg = update.message.text
    user = update.effective_user
    user_display = f"@{user.username}" if (user and user.username) else (user.first_name if user else "Anonymous")

    # In production, you would log to database, send to admin chat, etc.
    safe_msg = html.escape(user_msg)
    response_text = (
        "✅ <b>Thank You for Your Feedback!</b>\n\n"
        f"<b>Category:</b> {category}\n"
        f"<b>From:</b> {html.escape(user_display)}\n"
        f"<b>Message:</b>\n<i>\"{safe_msg}\"</i>\n\n"
        "Your thoughts have been recorded."
    )

    await update.message.reply_text(response_text, parse_mode=ParseMode.HTML)
    context.user_data.clear()
    return ConversationHandler.END


async def feedback_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels active feedback conversation."""
    context.user_data.clear()
    if update.message:
        await update.message.reply_text(
            "❌ <i>Feedback cancelled.</i>", parse_mode=ParseMode.HTML
        )
    elif update.callback_query and update.callback_query.message:
        await update.callback_query.answer()
        await update.callback_query.message.edit_text(
            "❌ <i>Feedback cancelled.</i>", parse_mode=ParseMode.HTML
        )
    return ConversationHandler.END


def get_feedback_conversation_handler() -> ConversationHandler:
    """Builds and returns the ConversationHandler for feedback."""
    return ConversationHandler(
        entry_points=[
            CommandHandler("feedback", feedback_entry),
            CallbackQueryHandler(feedback_entry, pattern=r"^menu:feedback$"),
        ],
        states={
            SELECTING_CATEGORY: [
                CallbackQueryHandler(category_selected, pattern=r"^cat:"),
            ],
            TYPING_FEEDBACK: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, feedback_received),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", feedback_cancel),
            CallbackQueryHandler(feedback_cancel, pattern=r"^cat:cancel$"),
        ],
        allow_reentry=True,
        per_message=False,
    )
