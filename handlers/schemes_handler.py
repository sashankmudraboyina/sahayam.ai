"""Handlers for natural language Telugu scheme queries and interactive scheme navigation."""

import html
import io
import re
import time
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ChatAction, ParseMode
from telegram.ext import ContextTypes

import config
from data.schemes import SCHEMES, get_all_categories, get_scheme_by_id
from services.ai_engine import analyze_citizen_query, transcribe_voice
from services.eligibility_flow import (
    DOMAIN_AGRICULTURE,
    DOMAIN_BUSINESS,
    DOMAIN_GENERAL,
    DOMAIN_HEALTH,
    DOMAIN_HOUSING,
    DOMAIN_PENSION,
    DOMAIN_SCHOLARSHIP,
    DOMAIN_WOMEN,
    detect_domain,
    extract_slots_from_text,
    format_final_eligibility_report,
    get_missing_slots,
    get_slot_question_and_buttons,
    match_eligible_schemes_for_profile,
)
from services.html_sanitizer import prepare_telegram_message, strip_html_tags, split_telegram_message
from services.matcher import find_scheme_by_name_or_query, format_scheme_detailed_telugu
from services.tts_service import generate_telugu_speech


def format_voice_recognized_header(user_text: str, lang: str = "te") -> str:
    """Formats a prominent header showing the citizen their recognized voice input."""
    cleaned = user_text.strip()
    if lang == "en":
        return f"🎙 <b>Understood voice query:</b>\n<i>\"{html.escape(cleaned)}\"</i>\n\n"
    return f"🎙 <b>మీరు మాట్లాడినది (గుర్తించబడింది):</b>\n<i>\"{html.escape(cleaned)}\"</i>\n\n"


def build_eligibility_keyboard(buttons_spec: list, lang: str = "te") -> InlineKeyboardMarkup:
    """Builds inline keyboard for eligibility clarification questions."""
    rows = []
    for row in buttons_spec:
        rows.append([InlineKeyboardButton(text=label, callback_data=cb) for label, cb in row])
    reset_label = "🔄 Reset Chat" if lang == "en" else "🔄 కొత్త సంభాషణ (Reset)"
    rows.append([InlineKeyboardButton(reset_label, callback_data="nav:reset_chat")])
    return InlineKeyboardMarkup(rows)


def build_scheme_actions_keyboard(
    scheme: dict = None,
    matched_schemes: list = None,
    dynamic_urls: list = None,
    is_detail_view: bool = False,
    include_voice_btn: bool = True,
    lang: str = "te",
) -> InlineKeyboardMarkup:
    """Builds interactive action buttons with dynamic official links and 'Know More' buttons."""
    buttons = []
    is_en = (lang == "en")

    # Case 1: Detailed single-scheme view (User clicked 'Know More' or requested a specific scheme)
    if is_detail_view and scheme:
        # Priority 1: Official website & documents
        if scheme.get("official_link"):
            web_label = "🌐 Official Website" if is_en else "🌐 అధికారిక వెబ్‌సైట్"
            doc_label = "📄 Required Documents" if is_en else "📄 కావలసిన పత్రాలు"
            buttons.append([
                InlineKeyboardButton(web_label, url=scheme["official_link"]),
                InlineKeyboardButton(doc_label, callback_data=f"doc:{scheme['id']}"),
            ])

        # Priority 2: Voice audio listening button
        if include_voice_btn:
            v_label = "🔊 Listen in Voice" if is_en else "🔊 వాయిస్‌లో వినండి (Listen Audio)"
            buttons.append([
                InlineKeyboardButton(v_label, callback_data="voice:speak"),
            ])

        # Quick navigation to other matched schemes
        if matched_schemes and len(matched_schemes) > 1:
            other_buttons = []
            for other_s, _, _ in matched_schemes[:4]:
                if other_s["id"] != scheme.get("id"):
                    raw_title = other_s.get("name_en" if is_en else "name_te", other_s["name_te"])
                    btn_label = raw_title.split("(")[0].strip()[:18]
                    other_buttons.append(
                        InlineKeyboardButton(f"👉 {btn_label}", callback_data=f"sch:{other_s['id']}")
                    )
            for i in range(0, len(other_buttons), 2):
                buttons.append(other_buttons[i:i+2])

    # Case 2: Multi-scheme summary view (when 2 or more schemes matched)
    elif matched_schemes and len(matched_schemes) > 1:
        # Provide a clear, prominent "Know More" button for EACH matched scheme
        for s, _, _ in matched_schemes[:4]:
            raw_title = s.get("name_en" if is_en else "name_te", s["name_te"])
            btn_label = raw_title.split("(")[0].strip()[:20]
            more_text = f"ℹ️ {btn_label} - Details" if is_en else f"ℹ️ {btn_label} - పూర్తి వివరాలు"
            buttons.append([
                InlineKeyboardButton(
                    more_text,
                    callback_data=f"sch:{s['id']}",
                )
            ])

        # If official dynamic URLs discovered
        if dynamic_urls:
            url_row = []
            for u in dynamic_urls[:2]:
                domain = u.split("//")[-1].split("/")[0].replace("www.", "")
                url_row.append(InlineKeyboardButton(f"🌐 {domain}", url=u))
            if url_row:
                buttons.append(url_row)

        if include_voice_btn:
            v_label = "🔊 Listen in Voice" if is_en else "🔊 వాయిస్‌లో వినండి (Listen Audio)"
            buttons.append([
                InlineKeyboardButton(v_label, callback_data="voice:speak"),
            ])

    # Case 3: Single scheme view
    else:
        if dynamic_urls:
            url_row = []
            for u in dynamic_urls[:2]:
                domain = u.split("//")[-1].split("/")[0].replace("www.", "")
                url_row.append(InlineKeyboardButton(f"🌐 {domain}", url=u))
            if url_row:
                buttons.append(url_row)
        elif scheme and scheme.get("official_link"):
            web_label = "🌐 Application Portal" if is_en else "🌐 దరఖాస్తు వెబ్‌సైట్"
            doc_label = "📄 Required Documents" if is_en else "📄 కావలసిన పత్రాలు"
            buttons.append([
                InlineKeyboardButton(web_label, url=scheme["official_link"]),
                InlineKeyboardButton(doc_label, callback_data=f"doc:{scheme['id']}"),
            ])

        if include_voice_btn:
            v_label = "🔊 Listen in Voice" if is_en else "🔊 వాయిస్‌లో వినండి (Listen Audio)"
            buttons.append([
                InlineKeyboardButton(v_label, callback_data="voice:speak"),
            ])

    # Universal navigation footer
    cat_nav = "📋 All Categories" if is_en else "📋 అన్ని విభాగాలు"
    wiz_nav = "🎯 Eligibility Wizard" if is_en else "🎯 అర్హత చెకర్"
    rst_nav = "🔄 New Chat (Reset)" if is_en else "🔄 కొత్త చాట్ (Reset)"
    buttons.append([
        InlineKeyboardButton(cat_nav, callback_data="nav:categories"),
        InlineKeyboardButton(wiz_nav, callback_data="nav:wizard"),
        InlineKeyboardButton(rst_nav, callback_data="nav:reset_chat"),
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


def is_voice_requested(text: str) -> bool:
    """Detects whether citizen explicitly requests audio/voice response."""
    lower = text.lower()
    voice_cues = [
        "వాయిస్", "వాయిస్‌", "ఆడియో", "వినాలి", "వినాలని", "నోటితో", "మాట్లాడి",
        "voice", "audio", "speak", "listen", "read out", "audio note"
    ]
    return any(c in lower for c in voice_cues)


async def send_voice_response(
    chat_id: int,
    text: str,
    context: ContextTypes.DEFAULT_TYPE,
    reply_to_message_id: int = None,
    lang: str = "te",
) -> bool:
    """Synthesizes speech (Telugu or English) and sends voice message to citizen with deduplication & concurrency locks."""
    # Prevent concurrent voice syntheses for the same user
    if context.user_data.get("is_synthesizing_voice"):
        config.logger.info("Voice synthesis already in progress for this user. Skipping duplicate request.")
        return False

    # Prevent sending the exact same audio note multiple times within 20 seconds
    now = time.time()
    text_hash = hash((text, lang))
    last_sent_hash = context.user_data.get("last_voice_sent_hash")
    last_sent_time = context.user_data.get("last_voice_sent_time", 0)

    if last_sent_hash == text_hash and (now - last_sent_time) < 20:
        config.logger.info("Voice response for this text was already sent recently (<20s). Suppressing duplicate.")
        return True

    context.user_data["is_synthesizing_voice"] = True
    try:
        await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.RECORD_VOICE)

        # Check in-memory cache for this text
        cached = context.user_data.get("cached_voice")
        if cached and cached.get("text_hash") == text_hash and cached.get("lang") == lang:
            audio_data = cached.get("audio_data")
        else:
            audio_data = await generate_telugu_speech(text, lang=lang)
            if audio_data:
                context.user_data["cached_voice"] = {
                    "text_hash": text_hash,
                    "lang": lang,
                    "audio_data": audio_data,
                }

        if audio_data:
            voice_file = io.BytesIO(audio_data)
            voice_file.name = f"sahayam_{lang}_voice.mp3"
            caption = "🔊 <b>Sahayam Voice Response</b>" if lang == "en" else "🔊 <b>సహాయం ఆడియో సమాధానం (Telugu Voice Response)</b>"
            await context.bot.send_voice(
                chat_id=chat_id,
                voice=voice_file,
                caption=caption,
                parse_mode=ParseMode.HTML,
                reply_to_message_id=reply_to_message_id,
            )
            context.user_data["last_voice_sent_hash"] = text_hash
            context.user_data["last_voice_sent_time"] = time.time()
            return True
        else:
            config.logger.warning("generate_telugu_speech returned empty audio.")
            return False
    except Exception as e:
        config.logger.error(f"Error sending voice response: {e}", exc_info=True)
        return False
    finally:
        context.user_data["is_synthesizing_voice"] = False


async def process_citizen_utterance(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    user_text: str,
    is_voice: bool = False,
    interim_msg=None,
) -> None:
    """Unified conversational processing engine for both text and voice inputs with English & Telugu support."""
    from handlers.start import get_home_keyboard

    message = update.message
    if not message:
        return

    user_text = user_text.strip()
    if user_text.startswith("/"):
        return

    lower_text = user_text.lower()

    # Detect language if not explicitly chosen
    if context.user_data.get("language") is None:
        words = lower_text.split()
        if len(words) >= 3 and re.match(r"^[a-zA-Z0-9\s\.,\?!'-]+$", user_text):
            context.user_data["language"] = "en"

    lang = context.user_data.get("language", "te")
    voice_header = format_voice_recognized_header(user_text, lang=lang) if is_voice else ""

    # 1. Language switch requests
    if any(w in lower_text for w in ["english please", "speak english", "speak in english", "talk in english", "in english", "switch to english", "change language to english", "use english"]) or lower_text.strip() in ["english", "/en"]:
        context.user_data["language"] = "en"
        voice_header = format_voice_recognized_header(user_text, lang="en") if is_voice else ""
        msg = (
            "🌐 <b>Language switched to English!</b>\n\n"
            "You can now converse with Sahayam.ai in English via text or voice. "
            "How can I help you discover government welfare schemes?"
        )
        if interim_msg:
            try:
                await interim_msg.delete()
            except Exception:
                pass
        await safe_reply_text(message, text=voice_header + msg, reply_markup=get_home_keyboard(lang="en"))
        if is_voice and update.effective_chat:
            await send_voice_response(chat_id=update.effective_chat.id, text=msg, context=context, lang="en")
        return

    if any(w in lower_text for w in ["తెలుగులో మాట్లాడు", "తెలుగు మాట్లాడండి", "తెలుగు", "in telugu", "switch to telugu", "change language to telugu"]) and len(lower_text.split()) <= 4:
        context.user_data["language"] = "te"
        voice_header = format_voice_recognized_header(user_text, lang="te") if is_voice else ""
        msg = (
            "🌐 <b>భాష తెలుగులోకి మార్చబడింది!</b>\n\n"
            "మీరు ఇప్పుడు సహాయం.ai తో తెలుగులో సంభాషించవచ్చు. "
            "మీకు ఏ ప్రభుత్వ పథకాల గురించి సమాచారం కావాలి?"
        )
        if interim_msg:
            try:
                await interim_msg.delete()
            except Exception:
                pass
        await safe_reply_text(message, text=voice_header + msg, reply_markup=get_home_keyboard(lang="te"))
        if is_voice and update.effective_chat:
            await send_voice_response(chat_id=update.effective_chat.id, text=msg, context=context, lang="te")
        return

    # Check for reset keywords
    if lower_text in ["reset", "new", "cancel", "రద్దు", "వద్దు", "కొత్తది", "మొదటి నుండి", "స్టార్ట్"]:
        context.user_data["eligibility_session"] = None
        context.user_data["conversation_history"] = []
        reply_text = (
            "🔄 <b>Conversation Reset!</b>\n\nHow can I help you with government welfare schemes? Describe your situation or question."
            if lang == "en"
            else "🔄 <b>సంభాషణ రీసెట్ చేయబడింది!</b>\n\nనమస్కారం! మీకు ఏ ప్రభుత్వ సంక్షేమ పథకాల గురించి సహాయం కావాలి? మీ పరిస్థితిని లేదా ప్రశ్నను ఇక్కడ వివరించండి."
        )
        if interim_msg:
            try:
                await interim_msg.delete()
            except Exception:
                pass
        await safe_reply_text(message, text=voice_header + reply_text, reply_markup=get_home_keyboard(lang=lang))
        if is_voice and update.effective_chat:
            await send_voice_response(chat_id=update.effective_chat.id, text=reply_text, context=context, lang=lang)
        return

    # Send typing status
    if update.effective_chat:
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)

    # Retrieve and maintain persistent citizen profile across all turns
    citizen_profile = context.user_data.setdefault("citizen_profile", {})

    # Extract any profile slots provided in the current user text and merge with persistent profile
    extracted_now = extract_slots_from_text(user_text, current_slots=citizen_profile)
    citizen_profile.update(extracted_now)

    # Check if citizen specifically references a known scheme by name
    direct_scheme = find_scheme_by_name_or_query(user_text)

    # Detect informational / factual queries
    is_informational_query = any(
        w in lower_text
        for w in [
            "what is", "how much", "how many", "who is", "who can", "when is", "where is",
            "how to", "apply process", "portal", "website", "link", "documents needed",
            "age limit", "income limit", "rules", "can i", "is it", "is there",
            "ఏమిటి", "ఏంటి", "ఎంత", "ఎంతవరకు", "ఎప్పుడు", "ఎక్కడ", "ఎలా", "ఎవరు", "ఎవరికి",
            "వర్తిస్తుందా", "వస్తుందా", "నిబంధనలు", "పరిమితి", "వయస్సు", "పత్రాలు", "డాక్యుమెంట్లు", "లింక్"
        ]
    )

    # Detect explicit requests for eligibility assessment
    is_eligibility_discovery = any(
        w in lower_text
        for w in [
            "పథకాలు వర్తిస్తాయి", "పథకాలు వస్తాయి", "ఏ పథకాలు", "పథకాలు కావాలి", "ఏమేం పథకాలు", "ఏం పథకాలు",
            "పథకాలు ఏమున్నాయి", "నాకు ఏ పథకాలు", "అర్హుడినా", "అర్హురాలినా", "అర్హత చెకర్", "నన్ను ప్రశ్నలు అడగండి",
            "నాకు వర్తిస్తాయా", "ఏ పథకం వస్తుంది", "ఏ పథకానికి అర్హత", "స్కీమ్స్ వర్తిస్తాయి", "స్కీమ్స్ వస్తాయి",
            "ఏం స్కీమ్స్", "ఏమేం స్కీమ్స్", "ఏ స్కీమ్స్", "schemes apply", "eligible schemes", "which schemes",
            "schemes for me", "schemes can i get", "check my eligibility", "am i eligible", "what can i apply"
        ]
    )

    # Case A: If user asked about a specific known scheme (and not an open eligibility check),
    # answer directly without asking redundant questions!
    if direct_scheme and not is_eligibility_discovery:
        context.user_data["eligibility_session"] = None
        qual_reason = direct_scheme.get("qualify_reason_en" if lang == "en" else "qualify_reason_te", "")
        if not qual_reason:
            qual_reason = "Eligible citizens can apply for this scheme." if lang == "en" else "అర్హత కలిగిన లబ్ధిదారులు దరఖాస్తు చేసుకోవచ్చు."
        detailed_text = format_scheme_detailed_telugu(direct_scheme, qual_reason, lang=lang)
        context.user_data["last_response_text"] = detailed_text
        context.user_data["last_matched_schemes"] = [(direct_scheme, 15.0, qual_reason)]
        markup = build_scheme_actions_keyboard(scheme=direct_scheme, matched_schemes=[(direct_scheme, 15.0, qual_reason)], is_detail_view=True, lang=lang)

        if interim_msg:
            try:
                await interim_msg.delete()
            except Exception:
                pass

        full_text = voice_header + detailed_text
        chunks = split_telegram_message(full_text)
        for i, chunk in enumerate(chunks):
            is_last = (i == len(chunks) - 1)
            m = markup if is_last else None
            await safe_reply_text(message, text=chunk, reply_markup=m, disable_web_page_preview=True)

        should_send_voice = is_voice or context.user_data.get("auto_voice", False) or is_voice_requested(user_text)
        if should_send_voice and update.effective_chat:
            await send_voice_response(
                chat_id=update.effective_chat.id,
                text=detailed_text,
                context=context,
                reply_to_message_id=message.message_id,
                lang=lang,
            )
        return

    # Case B: Check active conversational eligibility session
    session = context.user_data.get("eligibility_session")
    if session and not direct_scheme:
        domain = session.get("domain", DOMAIN_GENERAL)
        if domain == DOMAIN_GENERAL:
            extracted_cat = extract_slots_from_text(user_text, expected_slot="category").get("category")
            if extracted_cat:
                session["domain"] = extracted_cat
                domain = extracted_cat
            else:
                new_d = detect_domain(user_text)
                if new_d and new_d != DOMAIN_GENERAL:
                    session["domain"] = new_d
                    domain = new_d

        current_missing = get_missing_slots(domain, session.get("slots", {}))
        expected_slot = current_missing[0] if current_missing else None

        # Merge newly extracted slots with persistent profile and session
        session_slots = dict(citizen_profile)
        session_slots.update(session.get("slots", {}))
        new_slots = extract_slots_from_text(user_text, current_slots=session_slots, expected_slot=expected_slot)
        session_slots.update(new_slots)
        citizen_profile.update(session_slots)
        session["slots"] = session_slots

        missing = get_missing_slots(domain, session_slots)

        if missing:
            # Ask ONLY the single genuinely missing piece of information
            next_slot = missing[0]
            q_text, btn_spec = get_slot_question_and_buttons(domain, next_slot, session_slots, lang=lang)
            reply_markup = build_eligibility_keyboard(btn_spec, lang=lang) if btn_spec else None
            context.user_data["last_response_text"] = q_text

            if interim_msg:
                try:
                    await interim_msg.delete()
                except Exception:
                    pass

            msg_to_send = voice_header + q_text
            await safe_reply_text(message, text=msg_to_send, reply_markup=reply_markup)
            if is_voice or context.user_data.get("auto_voice", False):
                if update.effective_chat:
                    await send_voice_response(
                        chat_id=update.effective_chat.id,
                        text=q_text,
                        context=context,
                        reply_to_message_id=message.message_id,
                        lang=lang,
                    )
            return
        else:
            # All details collected! Formulate targeted scheme report
            eligible_schemes = match_eligible_schemes_for_profile(domain, session_slots)
            report_text = format_final_eligibility_report(domain, session_slots, eligible_schemes, lang=lang)
            context.user_data["eligibility_session"] = None

            matched_tuples = [(s, 10.0, s.get("qualify_reason_te", "")) for s in eligible_schemes]
            context.user_data["last_matched_schemes"] = matched_tuples
            context.user_data["last_response_text"] = report_text

            top_scheme = eligible_schemes[0] if eligible_schemes else None
            reply_markup = build_scheme_actions_keyboard(
                scheme=top_scheme,
                matched_schemes=matched_tuples,
                is_detail_view=(len(eligible_schemes) == 1),
                lang=lang,
            )

            if interim_msg:
                try:
                    await interim_msg.delete()
                except Exception:
                    pass

            full_report_text = voice_header + report_text
            chunks = split_telegram_message(full_report_text)
            for i, chunk in enumerate(chunks):
                is_last = (i == len(chunks) - 1)
                markup = reply_markup if is_last else None
                await safe_reply_text(
                    message,
                    text=chunk,
                    reply_markup=markup,
                    disable_web_page_preview=True,
                )

            should_send_voice = is_voice or context.user_data.get("auto_voice", False) or is_voice_requested(user_text)
            if should_send_voice and update.effective_chat:
                await send_voice_response(
                    chat_id=update.effective_chat.id,
                    text=report_text,
                    context=context,
                    reply_to_message_id=message.message_id,
                    lang=lang,
                )
            return

    # Case C: Check if message initiates eligibility questioning
    # Only initiate if citizen is explicitly looking for eligibility/schemes for their profile
    # and NOT asking a general informational question
    domain = detect_domain(user_text)
    should_evaluate_eligibility = (
        domain is not None
        and not is_informational_query
        and (is_eligibility_discovery or len(extracted_now) > 0 or domain != DOMAIN_GENERAL)
    )

    if should_evaluate_eligibility and not direct_scheme:
        slots = dict(citizen_profile)
        missing = get_missing_slots(domain, slots)

        if missing:
            # Essential details missing! Ask ONLY the missing piece
            context.user_data["eligibility_session"] = {"domain": domain, "slots": slots}
            next_slot = missing[0]
            q_text, btn_spec = get_slot_question_and_buttons(domain, next_slot, slots, lang=lang)
            reply_markup = build_eligibility_keyboard(btn_spec, lang=lang) if btn_spec else None
            context.user_data["last_response_text"] = q_text

            if interim_msg:
                try:
                    await interim_msg.delete()
                except Exception:
                    pass

            msg_to_send = voice_header + q_text
            await safe_reply_text(message, text=msg_to_send, reply_markup=reply_markup)
            if is_voice or context.user_data.get("auto_voice", False):
                if update.effective_chat:
                    await send_voice_response(
                        chat_id=update.effective_chat.id,
                        text=q_text,
                        context=context,
                        reply_to_message_id=message.message_id,
                        lang=lang,
                    )
            return
        else:
            # Citizen already provided all details or they were already known!
            # ZERO questions asked! Output recommendation immediately.
            eligible_schemes = match_eligible_schemes_for_profile(domain, slots)
            report_text = format_final_eligibility_report(domain, slots, eligible_schemes, lang=lang)
            matched_tuples = [(s, 10.0, s.get("qualify_reason_te", "")) for s in eligible_schemes]
            context.user_data["last_matched_schemes"] = matched_tuples
            context.user_data["last_response_text"] = report_text

            top_scheme = eligible_schemes[0] if eligible_schemes else None
            reply_markup = build_scheme_actions_keyboard(
                scheme=top_scheme,
                matched_schemes=matched_tuples,
                is_detail_view=(len(eligible_schemes) == 1),
                lang=lang,
            )

            if interim_msg:
                try:
                    await interim_msg.delete()
                except Exception:
                    pass

            full_report_text = voice_header + report_text
            chunks = split_telegram_message(full_report_text)
            for i, chunk in enumerate(chunks):
                is_last = (i == len(chunks) - 1)
                markup = reply_markup if is_last else None
                await safe_reply_text(
                    message,
                    text=chunk,
                    reply_markup=markup,
                    disable_web_page_preview=True,
                )

            should_send_voice = is_voice or context.user_data.get("auto_voice", False) or is_voice_requested(user_text)
            if should_send_voice and update.effective_chat:
                await send_voice_response(
                    chat_id=update.effective_chat.id,
                    text=report_text,
                    context=context,
                    reply_to_message_id=message.message_id,
                    lang=lang,
                )
            return

    # 5. Otherwise, use conversational query analyzer
    history = context.user_data.get("conversation_history", [])
    result = await analyze_citizen_query(user_text, conversation_history=history, lang=lang)
    matched = result.get("matched_schemes", [])
    dynamic_urls = result.get("dynamic_urls", [])

    context.user_data["last_matched_schemes"] = matched
    context.user_data["last_response_text"] = result["text"]

    history.append({"role": "user", "text": user_text})
    history.append({"role": "model", "text": strip_html_tags(result["text"])})
    context.user_data["conversation_history"] = history[-10:]

    top_scheme = matched[0][0] if matched else None
    reply_markup = build_scheme_actions_keyboard(
        scheme=top_scheme,
        matched_schemes=matched,
        dynamic_urls=dynamic_urls,
        is_detail_view=(len(matched) == 1),
        lang=lang,
    )

    if interim_msg:
        try:
            await interim_msg.delete()
        except Exception:
            pass

    final_text = voice_header + result["text"]

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

    should_send_voice = is_voice or context.user_data.get("auto_voice", False) or is_voice_requested(user_text)
    if should_send_voice and update.effective_chat:
        await send_voice_response(
            chat_id=update.effective_chat.id,
            text=result["text"],
            context=context,
            reply_to_message_id=message.message_id,
            lang=lang,
        )


async def handle_citizen_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles natural language messages in Telugu or English with step-by-step eligibility questioning."""
    if not update.message or not update.message.text:
        return
    await process_citizen_utterance(update, context, user_text=update.message.text, is_voice=False)


async def eligibility_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles button taps for step-by-step eligibility questions."""
    query = update.callback_query
    if not query or not query.data:
        return

    await query.answer()
    data = query.data
    parts = data.split(":")
    if len(parts) < 3:
        return

    slot_name = parts[1]
    slot_val = parts[2]
    lang = context.user_data.get("language", "te")

    session = context.user_data.get("eligibility_session")

    # Handle domain category selection from DOMAIN_GENERAL
    if slot_name == "cat":
        domain = slot_val
        session = {"domain": domain, "slots": {}}
        context.user_data["eligibility_session"] = session
        missing = get_missing_slots(domain, {})
        if missing:
            next_slot = missing[0]
            q_text, btn_spec = get_slot_question_and_buttons(domain, next_slot, {}, lang=lang)
            reply_markup = build_eligibility_keyboard(btn_spec, lang=lang) if btn_spec else None
            context.user_data["last_response_text"] = q_text
            if query.message:
                await query.message.reply_text(text=q_text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)
        return

    if not session:
        domain = DOMAIN_SCHOLARSHIP if slot_name in ["course", "caste", "income"] else DOMAIN_AGRICULTURE
        session = {"domain": domain, "slots": {}}
        context.user_data["eligibility_session"] = session

    slot_key_map = {
        "state": "state",
        "course": "course_level",
        "caste": "caste_category",
        "income": "income_or_ration",
        "land": "land_status",
        "pen": "pension_type",
        "site": "has_site",
        "wom": "welfare_type",
        "biz": "business_type",
    }
    actual_slot = slot_key_map.get(slot_name, slot_name)
    session["slots"][actual_slot] = slot_val
    citizen_profile = context.user_data.setdefault("citizen_profile", {})
    citizen_profile[actual_slot] = slot_val

    domain = session.get("domain", DOMAIN_SCHOLARSHIP)
    missing = get_missing_slots(domain, session["slots"])

    if missing:
        next_slot = missing[0]
        q_text, btn_spec = get_slot_question_and_buttons(domain, next_slot, session["slots"], lang=lang)
        reply_markup = build_eligibility_keyboard(btn_spec, lang=lang) if btn_spec else None
        context.user_data["last_response_text"] = q_text
        if query.message:
            await query.message.reply_text(text=q_text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)
    else:
        eligible_schemes = match_eligible_schemes_for_profile(domain, session["slots"])
        report_text = format_final_eligibility_report(domain, session["slots"], eligible_schemes, lang=lang)
        context.user_data["eligibility_session"] = None

        matched_tuples = [(s, 10.0, s.get("qualify_reason_te", "")) for s in eligible_schemes]
        context.user_data["last_matched_schemes"] = matched_tuples
        context.user_data["last_response_text"] = report_text

        top_scheme = eligible_schemes[0] if eligible_schemes else None
        reply_markup = build_scheme_actions_keyboard(
            scheme=top_scheme,
            matched_schemes=matched_tuples,
            is_detail_view=(len(eligible_schemes) == 1),
            lang=lang,
        )

        chunks = split_telegram_message(report_text)
        for i, chunk in enumerate(chunks):
            is_last = (i == len(chunks) - 1)
            markup = reply_markup if is_last else None
            if query.message:
                await query.message.reply_text(
                    text=chunk,
                    reply_markup=markup,
                    parse_mode=ParseMode.HTML,
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

    user_lang = context.user_data.get("language", "te")

    if not scheme:
        not_found = "Scheme details not found." if user_lang == "en" else "పథకం వివరాలు కనుగొనబడలేదు."
        await query.answer(not_found, show_alert=True)
        return

    qual_reason = scheme.get("qualify_reason_en" if user_lang == "en" else "qualify_reason_te", "")
    if not qual_reason:
        qual_reason = "Eligible citizens can apply for this welfare scheme." if user_lang == "en" else "అర్హత కలిగిన లబ్ధిదారులు దరఖాస్తు చేసుకోవచ్చు."

    text = format_scheme_detailed_telugu(scheme, qual_reason, lang=user_lang)
    context.user_data["last_response_text"] = text
    last_matched = context.user_data.get("last_matched_schemes")
    markup = build_scheme_actions_keyboard(scheme=scheme, matched_schemes=last_matched, is_detail_view=True, lang=user_lang)

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
    user_lang = context.user_data.get("language", "te")

    if not scheme:
        await query.answer("No information." if user_lang == "en" else "సమాచారం లేదు.", show_alert=True)
        return

    if user_lang == "en":
        docs = scheme.get("documents_en") or scheme.get("documents_te", [])
        docs_list = "\n".join([f"• {d}" for d in docs])
        msg = (
            f"📄 <b>{scheme.get('name_en', scheme['name_te'])} - Required Documents:</b>\n\n"
            f"{docs_list}\n\n"
            "💡 <i>Keep original documents ready along with photocopies for verification.</i>"
        )
    else:
        docs_list = "\n".join([f"• {d}" for d in scheme.get("documents_te", [])])
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
    user_lang = context.user_data.get("language", "te")
    categories = get_all_categories()
    keyboard = []
    for cat in categories:
        lbl = cat.get("name_en" if user_lang == "en" else "name_te", cat["name_te"])
        keyboard.append([
            InlineKeyboardButton(lbl, callback_data=f"cat_browse:{cat['key']}")
        ])
    home_lbl = "⬅️ Main Menu" if user_lang == "en" else "⬅️ ముఖ్య మెనూ"
    keyboard.append([InlineKeyboardButton(home_lbl, callback_data="nav:home")])

    if user_lang == "en":
        text = (
            "📂 <b>Government Welfare Scheme Categories:</b>\n\n"
            "Choose a category below to explore available welfare schemes:"
        )
    else:
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
    user_lang = context.user_data.get("language", "te")
    cat_key = query.data.replace("cat_browse:", "")

    matching = [s for s in SCHEMES if s["category"] == cat_key]
    if not matching:
        text = "No schemes currently available in this category." if user_lang == "en" else "ఈ విభాగంలో ప్రస్తుతం పథకాలు అందుబాటులో లేవు."
        back_lbl = "⬅️ Back" if user_lang == "en" else "⬅️ వెనుకకు"
        markup = InlineKeyboardMarkup([[InlineKeyboardButton(back_lbl, callback_data="nav:categories")]])
    else:
        cat_title = matching[0].get("category" if user_lang == "en" else "category_te", matching[0]["category_te"])
        if user_lang == "en":
            text = f"📋 <b>{cat_title} - Available Schemes:</b>\n\nClick any scheme below to view complete details:"
        else:
            text = f"📋 <b>{cat_title} - అందుబాటులో ఉన్న పథకాలు:</b>\n\nఏదైనా పథకంపై క్లిక్ చేసి పూర్తి వివరాలు చూడండి:"

        keyboard = []
        for s in matching:
            s_name = s.get("name_en" if user_lang == "en" else "name_te", s["name_te"])
            keyboard.append([
                InlineKeyboardButton(s_name, callback_data=f"sch:{s['id']}")
            ])
        all_cats_lbl = "⬅️ All Categories" if user_lang == "en" else "⬅️ అన్ని విభాగాలు"
        keyboard.append([InlineKeyboardButton(all_cats_lbl, callback_data="nav:categories")])
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

    user_lang = context.user_data.get("language", "te")
    wait_msg = (
        "🎙 <i>Listening to your voice message... Please wait a moment.</i>"
        if user_lang == "en"
        else "🎙 <i>మీ వాయిస్ సందేశాన్ని వింటున్నాను... దయచేసి కాసేపు వేచి ఉండండి.</i>"
    )
    status_msg = await message.reply_text(
        wait_msg,
        parse_mode=ParseMode.HTML,
    )

    try:
        # Download voice file
        voice_obj = message.voice or message.audio
        voice_file = await context.bot.get_file(voice_obj.file_id)
        voice_bytes = await voice_file.download_as_bytearray()
        mime_type = getattr(voice_obj, "mime_type", "audio/ogg") or "audio/ogg"

        # Transcribe audio with Gemini or Google Speech Recognition fallback
        transcribed_text = transcribe_voice(bytes(voice_bytes), mime_type=mime_type, preferred_lang=user_lang)

        if not transcribed_text:
            err_st = (
                "⚠️ <i>Sorry, could not clearly understand your audio. Please record again or type your message.</i>"
                if user_lang == "en"
                else "⚠️ <i>క్షమించండి, మీ వాయిస్ సందేశం స్పష్టంగా వినిపించలేదు. దయచేసి మళ్లీ రికార్డ్ చేసి పంపండి లేదా టైప్ చేయండి.</i>"
            )
            await status_msg.edit_text(
                err_st,
                parse_mode=ParseMode.HTML,
            )
            return

        # Update status
        recog_status = (
            f"🎙 <b>Recognized question:</b>\n<i>\"{html.escape(transcribed_text)}\"</i>\n\n🔍 <i>Analyzing...</i>"
            if user_lang == "en"
            else f"🎙 <b>మీరు అడిగిన ప్రశ్న (గుర్తించబడింది):</b>\n<i>\"{html.escape(transcribed_text)}\"</i>\n\n🔍 <i>పరిశీలిస్తున్నాను...</i>"
        )
        await status_msg.edit_text(
            recog_status,
            parse_mode=ParseMode.HTML,
        )

        await process_citizen_utterance(
            update,
            context,
            user_text=transcribed_text,
            is_voice=True,
            interim_msg=status_msg,
        )

    except Exception as e:
        config.logger.error(f"Error handling voice message: {e}", exc_info=True)
        try:
            fail_st = (
                "⚠️ <i>Technical issue processing voice message. Please send as text.</i>"
                if user_lang == "en"
                else "⚠️ <i>వాయిస్ సందేశాన్ని ప్రాసెస్ చేయడంలో సాంకేతిక సమస్య ఏర్పడింది. దయచేసి టైప్ చేసి పంపండి.</i>"
            )
            await status_msg.edit_text(
                fail_st,
                parse_mode=ParseMode.HTML,
            )
        except Exception:
            pass


async def speak_voice_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Triggered when user clicks '🔊 వాయిస్‌లో వినండి (Listen Audio)' button."""
    query = update.callback_query
    if not query:
        return

    user_lang = context.user_data.get("language", "te")

    # If voice synthesis is already in progress, notify user politely without re-triggering
    if context.user_data.get("is_synthesizing_voice"):
        prep_msg = "🔊 Preparing voice audio, please wait a moment..." if user_lang == "en" else "🔊 వాయిస్ సిద్ధమవుతోంది, ఒక్క క్షణం వేచి ఉండండి..."
        await query.answer(prep_msg, show_alert=False)
        return

    # Retrieve last response text from user session or query message
    last_text = context.user_data.get("last_response_text")
    if not last_text and query.message and query.message.text:
        last_text = query.message.text

    if not last_text:
        no_info = "No information." if user_lang == "en" else "సమాచారం లేదు."
        await query.answer(no_info, show_alert=True)
        return

    # Check if this exact audio was already sent in the last 20 seconds
    now = time.time()
    text_hash = hash((last_text, user_lang))
    if context.user_data.get("last_voice_sent_hash") == text_hash and (now - context.user_data.get("last_voice_sent_time", 0)) < 20:
        alr_msg = "🔊 Voice answer was already sent above 👆" if user_lang == "en" else "🔊 వాయిస్ సమాధానం ఇప్పటికే పైన పంపబడింది 👆"
        await query.answer(alr_msg, show_alert=False)
        return

    wait_audio = "🔊 Generating audio... please wait a moment." if user_lang == "en" else "🔊 ఆడియో రూపొందిస్తున్నాము... కాసేపు వేచి ఉండండి."
    await query.answer(wait_audio)
    chat_id = update.effective_chat.id if update.effective_chat else query.message.chat_id

    success = await send_voice_response(chat_id, last_text, context, lang=user_lang)
    if not success and query.message:
        err_tts = (
            "⚠️ Technical issue generating voice audio. Please try again."
            if user_lang == "en"
            else "⚠️ ఆడియో రూపొందించడంలో సాంకేతిక సమస్య ఏర్పడింది. దయచేసి మళ్లీ ప్రయత్నించండి."
        )
        await query.message.reply_text(err_tts)


async def voice_toggle_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Toggles automatic voice responses on/off for the citizen."""
    current = context.user_data.get("auto_voice", False)
    new_state = not current
    context.user_data["auto_voice"] = new_state
    user_lang = context.user_data.get("language", "te")

    if new_state:
        if user_lang == "en":
            msg = (
                "🔊 <b>Voice Mode ON!</b>\n\n"
                "From now on, every query response will automatically include an <b>English voice note</b>.\n\n"
                "💡 <i>To turn voice mode off, type <code>/voice</code> again.</i>"
            )
        else:
            msg = (
                "🔊 <b>వాయిస్ మోడ్ ఆన్ చేయబడింది (Voice Mode ON)!</b>\n\n"
                "ఇకపై మీరు అడిగే ప్రతి ప్రశ్నకు లిఖితపూర్వక సమాధానంతో పాటు <b>తెలుగు వాయిస్ ఆడియో</b> కూడా స్వయంచాలకంగా పంపబడుతుంది.\n\n"
                "💡 <i>వాయిస్ మోడ్ ఆఫ్ చేయాలనుకుంటే మళ్లీ <code>/voice</code> అని టైప్ చేయండి.</i>"
            )
    else:
        if user_lang == "en":
            msg = (
                "🔇 <b>Voice Mode OFF.</b>\n\n"
                "Responses will now be sent in text only.\n"
                "(You can still click '🔊 Listen Audio' whenever you want audio)."
            )
        else:
            msg = (
                "🔇 <b>వాయిస్ మోడ్ ఆఫ్ చేయబడింది (Voice Mode OFF).</b>\n\n"
                "ఇకపై కేవలం టెక్స్ట్ రూపంలో మాత్రమే సమాధానాలు వస్తాయి.\n"
                "(మీకు అవసరమైనప్పుడు '🔊 వాయిస్‌లో వినండి' బటన్ నొక్కి కూడా ఆడియో వినవచ్చు)."
            )

    if update.message:
        await safe_reply_text(update.message, text=msg)
    elif update.callback_query and update.callback_query.message:
        await safe_reply_text(update.callback_query.message, text=msg)


async def reset_chat_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Clears conversation history and resets chat context."""
    context.user_data["conversation_history"] = []
    context.user_data["eligibility_session"] = None
    context.user_data["citizen_profile"] = {}
    user_lang = context.user_data.get("language", "te")

    if user_lang == "en":
        msg = (
            "🔄 <b>Conversation Cleared!</b>\n\n"
            "You can start fresh with a new question or scheme inquiry.\n"
            "Type your query in English or send a voice message."
        )
    else:
        msg = (
            "🔄 <b>సంభాషణ క్లియర్ చేయబడింది!</b>\n\n"
            "మీరు కొత్త ప్రశ్న లేదా కొత్త పథకం గురించి అడగవచ్చు.\n"
            "మీ పరిస్థితిని సాధారణ తెలుగులో టైప్ చేయండి లేదా వాయిస్ మెసేజ్ పంపండి."
        )

    if update.message:
        await safe_reply_text(update.message, text=msg)
    elif update.callback_query and update.callback_query.message:
        reset_ack = "Conversation reset." if user_lang == "en" else "సంభాషణ రీసెట్ చేయబడింది."
        await update.callback_query.answer(reset_ack)
        await safe_reply_text(update.callback_query.message, text=msg)
