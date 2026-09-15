"""Handlers for natural language Telugu scheme queries and interactive scheme navigation."""

import html
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ChatAction, ParseMode
from telegram.ext import ContextTypes

import config
from data.schemes import SCHEMES, get_all_categories, get_scheme_by_id
from services.ai_engine import analyze_citizen_query, transcribe_voice
from services.html_sanitizer import prepare_telegram_message, strip_html_tags, split_telegram_message
from services.matcher import format_scheme_detailed_telugu


def build_scheme_actions_keyboard(scheme: dict = None, matched_schemes: list = None, dynamic_urls: list = None) -> InlineKeyboardMarkup:
    """Builds interactive action buttons with dynamic official links."""
    buttons = []

    # Priority 1: Real-time official government links discovered dynamically
    if dynamic_urls:
        url_row = []
        for u in dynamic_urls[:2]:
            domain = u.split("//")[-1].split("/")[0].replace("www.", "")
            url_row.append(InlineKeyboardButton(f"🌐 {domain}", url=u))
        if url_row:
            buttons.append(url_row)
    elif scheme and scheme.get("official_link"):
        buttons.append([
            InlineKeyboardButton("🌐 దరఖాస్తు వెబ్‌సైట్", url=scheme["official_link"]),
            InlineKeyboardButton("📄 పత్రాల జాబితా", callback_data=f"doc:{scheme['id']}"),
        ])

    # If other schemes matched, add navigation buttons
    if matched_schemes and len(matched_schemes) > 1:
        other_row = []
        for other_s, _, _ in matched_schemes[1:3]:
            btn_label = other_s["name_te"].split("(")[0].strip()[:18]
            other_row.append(
                InlineKeyboardButton(f"👉 {btn_label}", callback_data=f"sch:{other_s['id']}")
            )
        if other_row:
            buttons.append(other_row)

    buttons.append([
        InlineKeyboardButton("📋 అన్ని విభాగాలు", callback_data="nav:categories"),
        InlineKeyboardButton("🎯 అర్హత చెకర్", callback_data="nav:wizard"),
        InlineKeyboardButton("🔄 కొత్త చాట్ (Reset)", callback_data="nav:reset_chat"),
    ])

    return InlineKeyboardMarkup(buttons)


async def safe_reply_text(target_msg, text: str, reply_markup=None, disable_web_page_preview: bool = True):
    """Sends message with sanitized HTML; falls back to stripped plain text if Telegram parser errors."""
    safe_html = prepare_telegram_message(text)
    try:
        return await target_msg.reply_text(
            text=safe_html,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=disable_web_page_preview,
        )
    except Exception as e:
        config.logger.warning(f"HTML render failed ({e}). Falling back to clean stripped plain text.")
        clean_text = strip_html_tags(text)
        return await target_msg.reply_text(
            text=clean_text,
            reply_markup=reply_markup,
            disable_web_page_preview=disable_web_page_preview,
        )


async def safe_edit_text(query_msg, text: str, reply_markup=None, disable_web_page_preview: bool = True):
    """Edits message with sanitized HTML; falls back to stripped plain text if Telegram parser errors."""
    safe_html = prepare_telegram_message(text)
    try:
        return await query_msg.edit_text(
            text=safe_html,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=disable_web_page_preview,
        )
    except Exception as e:
        config.logger.warning(f"HTML edit failed ({e}). Falling back to clean stripped plain text.")
        clean_text = strip_html_tags(text)
        return await query_msg.edit_text(
            text=clean_text,
            reply_markup=reply_markup,
            disable_web_page_preview=disable_web_page_preview,
        )


async def handle_citizen_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles natural language messages in Telugu or English."""
    if not update.message or not update.message.text:
        return

    user_text = update.message.text.strip()
    if user_text.startswith("/"):
        return  # Let CommandHandlers deal with commands

    # Send typing status
    if update.effective_chat:
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)

    # Retrieve conversation history
    history = context.user_data.get("conversation_history", [])

    # Analyze citizen query using AI Engine & Matcher with conversation history
    result = await analyze_citizen_query(user_text, conversation_history=history)
    matched = result.get("matched_schemes", [])
    dynamic_urls = result.get("dynamic_urls", [])

    # Update conversation history
    history.append({"role": "user", "text": user_text})
    history.append({"role": "model", "text": strip_html_tags(result["text"])})
    context.user_data["conversation_history"] = history[-10:]

    top_scheme = matched[0][0] if matched else None
    reply_markup = build_scheme_actions_keyboard(
        scheme=top_scheme,
        matched_schemes=matched,
        dynamic_urls=dynamic_urls,
    )

    chunks = split_telegram_message(result["text"])
    for i, chunk in enumerate(chunks):
        is_last = (i == len(chunks) - 1)
        markup = reply_markup if is_last else None
        await safe_reply_text(
            update.message,
            text=chunk,
            reply_markup=markup,
            disable_web_page_preview=True,
        )


async def scheme_detail_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Shows full details of a specific scheme when clicked from buttons."""
    query = update.callback_query
    if not query or not query.data:
        return

    await query.answer()
    scheme_id = query.data.replace("sch:", "")
    scheme = get_scheme_by_id(scheme_id)

    if not scheme:
        await query.answer("పథకం వివరాలు కనుగొనబడలేదు.", show_alert=True)
        return

    text = format_scheme_detailed_telugu(scheme, scheme.get("qualify_reason_te", "అర్హత కలిగిన లబ్ధిదారులు దరఖాస్తు చేసుకోవచ్చు."))
    markup = build_scheme_actions_keyboard(scheme)

    if query.message:
        await safe_reply_text(
            query.message,
            text=text,
            reply_markup=markup,
            disable_web_page_preview=True,
        )


async def scheme_documents_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Displays pop-up / alert or message with required documents list."""
    query = update.callback_query
    if not query or not query.data:
        return

    scheme_id = query.data.replace("doc:", "")
    scheme = get_scheme_by_id(scheme_id)

    if not scheme:
        await query.answer("సమాచారం లేదు.", show_alert=True)
        return

    docs_list = "\n".join([f"• {d}" for d in scheme["documents_te"]])
    msg = (
        f"📄 <b>{scheme['name_te']} - కావలసిన పత్రాలు (Required Documents):</b>\n\n"
        f"{docs_list}\n\n"
        "💡 <i>ఈ పత్రాల జిరాక్స్ కాపీలతో పాటు ఒరిజినల్ కాపీలను ధ్రువీకరణ కొరకు వెంట ఉంచుకోండి.</i>"
    )

    await query.answer()
    if query.message:
        await safe_reply_text(query.message, text=msg)


async def categories_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Displays all welfare scheme categories."""
    query = update.callback_query
    if not query:
        return

    await query.answer()
    categories = get_all_categories()
    keyboard = []
    for cat in categories:
        keyboard.append([
            InlineKeyboardButton(cat["name_te"], callback_data=f"cat_browse:{cat['key']}")
        ])
    keyboard.append([InlineKeyboardButton("⬅️ ముఖ్య మెనూ", callback_data="nav:home")])

    text = (
        "📂 <b>ప్రభుత్వ సంక్షేమ పథకాల విభాగాలు:</b>\n\n"
        "మీకు అవసరమైన విభాగాన్ని ఎంచుకుని, అందుబాటులో ఉన్న పథకాల వివరాలను తెలుసుకోండి:"
    )

    if query.message:
        await safe_edit_text(query.message, text=text, reply_markup=InlineKeyboardMarkup(keyboard))


async def category_browse_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Lists all schemes under a selected category."""
    query = update.callback_query
    if not query or not query.data:
        return

    await query.answer()
    cat_key = query.data.replace("cat_browse:", "")

    matching = [s for s in SCHEMES if s["category"] == cat_key]
    if not matching:
        text = "ఈ విభాగంలో ప్రస్తుతం పథకాలు అందుబాటులో లేవు."
        markup = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ వెనుకకు", callback_data="nav:categories")]])
    else:
        text = f"📋 <b>{matching[0]['category_te']} - అందుబాటులో ఉన్న పథకాలు:</b>\n\nఏదైనా పథకంపై క్లిక్ చేసి పూర్తి వివరాలు చూడండి:"
        keyboard = []
        for s in matching:
            keyboard.append([
                InlineKeyboardButton(s["name_te"], callback_data=f"sch:{s['id']}")
            ])
        keyboard.append([InlineKeyboardButton("⬅️ అన్ని విభాగాలు", callback_data="nav:categories")])
        markup = InlineKeyboardMarkup(keyboard)

    if query.message:
        await safe_edit_text(query.message, text=text, reply_markup=markup)


async def handle_citizen_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles Telugu/English citizen voice messages and audio files."""
    message = update.message
    if not message or (not message.voice and not message.audio):
        return

    # Indicate recording/typing action
    if update.effective_chat:
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)

    status_msg = await message.reply_text(
        "🎙 <i>మీ వాయిస్ సందేశాన్ని వింటున్నాను... దయచేసి కాసేపు వేచి ఉండండి.</i>",
        parse_mode=ParseMode.HTML,
    )

    try:
        # Download voice file
        voice_obj = message.voice or message.audio
        voice_file = await context.bot.get_file(voice_obj.file_id)
        voice_bytes = await voice_file.download_as_bytearray()
        mime_type = getattr(voice_obj, "mime_type", "audio/ogg") or "audio/ogg"

        # Transcribe Telugu audio with Gemini
        transcribed_text = transcribe_voice(bytes(voice_bytes), mime_type=mime_type)

        if not transcribed_text:
            await status_msg.edit_text(
                "⚠️ <i>క్షమించండి, మీ వాయిస్ సందేశం స్పష్టంగా వినిపించలేదు. దయచేసి మళ్లీ రికార్డ్ చేసి పంపండి లేదా టైప్ చేయండి.</i>",
                parse_mode=ParseMode.HTML,
            )
            return

        # Update status
        await status_msg.edit_text(
            f"🎙 <b>మీరు అడిగిన ప్రశ్న (గుర్తించబడింది):</b>\n<i>\"{html.escape(transcribed_text)}\"</i>\n\n"
            "🔍 <i>పథకాల సమాచారాన్ని విశ్లేషిస్తున్నాను...</i>",
            parse_mode=ParseMode.HTML,
        )

        # Retrieve conversation history
        history = context.user_data.get("conversation_history", [])

        # Process the transcribed text with history
        result = await analyze_citizen_query(transcribed_text, conversation_history=history)
        matched = result.get("matched_schemes", [])
        dynamic_urls = result.get("dynamic_urls", [])

        # Update conversation history
        history.append({"role": "user", "text": transcribed_text})
        history.append({"role": "model", "text": strip_html_tags(result["text"])})
        context.user_data["conversation_history"] = history[-10:]

        top_scheme = matched[0][0] if matched else None
        reply_markup = build_scheme_actions_keyboard(
            scheme=top_scheme,
            matched_schemes=matched,
            dynamic_urls=dynamic_urls,
        )

        response_header = (
            f"🎙 <b>మీ వాయిస్ ప్రశ్న (Voice Query):</b>\n"
            f"<i>\"{html.escape(transcribed_text)}\"</i>\n\n"
        )
        final_text = response_header + result["text"]

        chunks = split_telegram_message(final_text)
        for i, chunk in enumerate(chunks):
            is_last = (i == len(chunks) - 1)
            markup = reply_markup if is_last else None
            await safe_reply_text(
                message,
                text=chunk,
                reply_markup=markup,
                disable_web_page_preview=True,
            )

        # Clean up interim status message
        try:
            await status_msg.delete()
        except Exception:
            pass

    except Exception as e:
        config.logger.error(f"Error handling voice message: {e}", exc_info=True)
        await status_msg.edit_text(
            "⚠️ <i>వాయిస్ సందేశాన్ని ప్రాసెస్ చేయడంలో సాంకేతిక సమస్య ఏర్పడింది. దయచేసి టైప్ చేసి పంపండి.</i>",
            parse_mode=ParseMode.HTML,
        )


async def reset_chat_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Clears conversation history and resets chat context."""
    context.user_data["conversation_history"] = []
    msg = (
        "🔄 <b>సంభాషణ క్లియర్ చేయబడింది!</b>\n\n"
        "మీరు కొత్త ప్రశ్న లేదా కొత్త పథకం గురించి అడగవచ్చు.\n"
        "మీ పరిస్థితిని సాధారణ తెలుగులో టైప్ చేయండి లేదా వాయిస్ మెసేజ్ పంపండి."
    )
    if update.message:
        await safe_reply_text(update.message, text=msg)
    elif update.callback_query and update.callback_query.message:
        await update.callback_query.answer("సంభాషణ రీసెట్ చేయబడింది.")
        await safe_reply_text(update.callback_query.message, text=msg)
