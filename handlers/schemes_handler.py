"""Handlers for natural language Telugu scheme queries and interactive scheme navigation."""

import html
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ChatAction, ParseMode
from telegram.ext import ContextTypes

from data.schemes import SCHEMES, get_all_categories, get_scheme_by_id
from services.ai_engine import analyze_citizen_query
from services.matcher import format_scheme_detailed_telugu


def build_scheme_actions_keyboard(scheme: dict, matched_schemes: list = None) -> InlineKeyboardMarkup:
    """Builds interactive action buttons for a scheme."""
    buttons = [
        [
            InlineKeyboardButton("🌐 దరఖాస్తు వెబ్‌సైట్", url=scheme["official_link"]),
            InlineKeyboardButton("📄 పత్రాల జాబితా", callback_data=f"doc:{scheme['id']}"),
        ]
    ]

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
        InlineKeyboardButton("🔍 కొత్త ప్రశ్న", callback_data="nav:help_query"),
    ])

    return InlineKeyboardMarkup(buttons)


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

    # Analyze citizen query using AI Engine & Matcher
    result = await analyze_citizen_query(user_text)
    matched = result.get("matched_schemes", [])

    if matched:
        top_scheme = matched[0][0]
        reply_markup = build_scheme_actions_keyboard(top_scheme, matched)
    else:
        reply_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("📋 వర్గాల వారీగా చూడండి", callback_data="nav:categories")],
            [InlineKeyboardButton("🎯 అర్హత చెకర్ (Wizard)", callback_data="nav:wizard")],
        ])

    # Telegram limit safety
    msg_text = result["text"]
    if len(msg_text) > 4000:
        msg_text = msg_text[:3990] + "..."

    await update.message.reply_text(
        text=msg_text,
        reply_markup=reply_markup,
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

    if not scheme:
        await query.answer("పథకం వివరాలు కనుగొనబడలేదు.", show_alert=True)
        return

    text = format_scheme_detailed_telugu(scheme, scheme.get("qualify_reason_te", "అర్హత కలిగిన లబ్ధిదారులు దరఖాస్తు చేసుకోవచ్చు."))
    markup = build_scheme_actions_keyboard(scheme)

    if query.message:
        await query.message.reply_text(
            text=text,
            reply_markup=markup,
            parse_mode=ParseMode.HTML,
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
        await query.message.reply_text(msg, parse_mode=ParseMode.HTML)


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
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)


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
        await query.message.edit_text(text, reply_markup=markup, parse_mode=ParseMode.HTML)
