"""Navigation and callback routing for Sahayam.ai."""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from handlers.schemes_handler import (
    category_browse_callback,
    categories_callback,
    reset_chat_command,
    scheme_detail_callback,
    scheme_documents_callback,
)
from handlers.start import get_home_keyboard, get_welcome_text, help_command
from handlers.wizard import (
    start_wizard_callback,
    wizard_category_selected,
    wizard_land_selected,
)


async def samples_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Shows sample queries users can ask in natural Telugu."""
    query = update.callback_query
    if not query:
        return

    await query.answer()
    text = (
        "💡 <b>నమూనా ప్రశ్నలు (Sample Questions):</b>\n\n"
        "మీరు క్రింది విధంగా సహజమైన తెలుగులో సందేశం పంపవచ్చు:\n\n"
        "1. 🌾 <i>\"నాకు రెండు ఎకరాల పొలం ఉంది. నేను చిన్న రైతును. నాకు ఏ ప్రభుత్వ పథకాలు వర్తిస్తాయి?\"</i>\n\n"
        "2. 🏥 <i>\"ఆరోగ్యశ్రీ ద్వారా ఉచిత వైద్యం పొందడానికి తెల్ల రేషన్ కార్డు సరిపోతుందా?\"</i>\n\n"
        "3. 🎓 <i>\"మా అబ్బాయి కాలేజీ చదువుతున్నాడు, ఫీజు రీయింబర్స్‌మెంట్ పథకం కావాలి.\"</i>\n\n"
        "4. 👴 <i>\"60 ఏళ్లు దాటిన వారికి వృద్ధాప్య పెన్షన్ కు ఏమేం కాగితాలు కావాలి?\"</i>\n\n"
        "5. 💼 <i>\"తోపుడు బండిపై పండ్ల వ్యాపారం చేస్తున్నాను, లోన్ ఎలా పొందాలి?\"</i>\n\n"
        "6. 🏠 <i>\"సొంత స్థలంలో ఇల్లు కట్టుకోవడానికి ప్రభుత్వ రాయితీ పథకం ఉందా?\"</i>\n\n"
        "👉 <i>పై ప్రశ్నల్లో ఒకదాన్ని కాపీ చేసి మెసేజ్ బాక్స్‌లో పేస్ట్ చేయండి లేదా మీ సొంత పరిస్థితిని వివరించండి!</i>"
    )

    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎯 అర్హత చెకర్ ప్రారంభించండి", callback_data="nav:wizard")],
        [InlineKeyboardButton("⬅️ ముఖ్య మెనూ", callback_data="nav:home")],
    ])

    if query.message:
        await query.message.edit_text(text, reply_markup=markup, parse_mode=ParseMode.HTML)


async def main_callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Central router for all callback queries."""
    query = update.callback_query
    if not query or not query.data:
        return

    data = query.data

    if data == "nav:home":
        await query.answer()
        user = update.effective_user
        name = user.first_name if user else "మిత్రమా"
        if query.message:
            await query.message.edit_text(
                text=get_welcome_text(name),
                reply_markup=get_home_keyboard(),
                parse_mode=ParseMode.HTML,
            )

    elif data == "nav:wizard":
        await start_wizard_callback(update, context)

    elif data == "nav:categories":
        await categories_callback(update, context)

    elif data == "nav:samples":
        await samples_callback(update, context)

    elif data == "nav:help":
        await help_command(update, context)

    elif data == "nav:help_query":
        await query.answer()
        if query.message:
            await query.message.reply_text(
                "✍️ <i>దయచేసి మీ పరిస్థితి లేదా ప్రశ్నను ఇక్కడ తెలుగులో టైప్ చేసి పంపండి. నేను తక్షణమే సమాధానం ఇస్తాను!</i>",
                parse_mode=ParseMode.HTML,
            )

    elif data == "nav:reset_chat":
        await reset_chat_command(update, context)

    elif data.startswith("wiz:cat:"):
        await wizard_category_selected(update, context)

    elif data.startswith("wiz:land:"):
        await wizard_land_selected(update, context)

    elif data.startswith("cat_browse:"):
        await category_browse_callback(update, context)

    elif data.startswith("sch:"):
        await scheme_detail_callback(update, context)

    elif data.startswith("doc:"):
        await scheme_documents_callback(update, context)
