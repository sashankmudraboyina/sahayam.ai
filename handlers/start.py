"""Start and Help Handlers for Sahayam.ai Telugu Welfare Scheme Platform."""

import html
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes


def get_home_keyboard() -> InlineKeyboardMarkup:
    """Main menu navigation buttons."""
    keyboard = [
        [
            InlineKeyboardButton("🎯 అర్హత చెకర్ (Wizard)", callback_data="nav:wizard"),
            InlineKeyboardButton("📂 పథకాల విభాగాలు", callback_data="nav:categories"),
        ],
        [
            InlineKeyboardButton("💡 నమూనా ప్రశ్నలు (Examples)", callback_data="nav:samples"),
            InlineKeyboardButton("📖 పూర్తి గైడ్ (Help)", callback_data="nav:help"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_welcome_text(user_first_name: str) -> str:
    """Generates the main welcoming message in polite, encouraging Telugu."""
    safe_name = html.escape(user_first_name)
    return (
        f"🙏 <b>నమస్కారం {safe_name} గారూ!</b>\n\n"
        "నేను <b>సహాయం (Sahayam.ai)</b> — ప్రభుత్వ సంక్షేమ పథకాలను సులభంగా తెలుసుకోవడానికి మీ డిజిటల్ సహాయకుడిని.\n\n"
        "📢 <b>మీరు ఎలా అడగవచ్చు?</b>\n"
        "మీ పరిస్థితిని సాధారణ తెలుగులో మెసేజ్ చేయండి. ఉదాహరణకు:\n\n"
        "👉 <i>\"నాకు రెండు ఎకరాల పొలం ఉంది. నేను చిన్న రైతును. నాకు ఏ ప్రభుత్వ పథకాలు వర్తిస్తాయి?\"</i>\n"
        "👉 <i>\"నేను డిగ్రీ చదువుతున్నాను. నాకు ఫీజు రీయింబర్స్‌మెంట్ పథకం కావాలి.\"</i>\n"
        "👉 <i>\"మా అమ్మగారికి 62 ఏళ్లు. వృద్ధాప్య పెన్షన్ ఎలా వస్తుంది?\"</i>\n"
        "👉 <i>\"చిన్న కిరాణా షాపు కోసం లోన్ కావాలి.\"</i>\n\n"
        "⚡ <b>వ్యవస్థ తక్షణమే మీకు:</b>\n"
        "• సంబంధిత పథకాలు\n"
        "• మీకు ఎందుకు వర్తిస్తుంది?\n"
        "• ప్రయోజనాలు & అర్హతలు\n"
        "• కావలసిన పత్రాల జాబితా\n"
        "• దరఖాస్తు విధానం & అధికారిక లింక్\n\n"
        "క్రింది బటన్లను ఉపయోగించి కూడా ప్రారంభించవచ్చు:"
    )


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles /start command."""
    user = update.effective_user
    name = user.first_name if user else "మిత్రమా"
    reply_markup = get_home_keyboard()

    if update.message:
        await update.message.reply_text(
            text=get_welcome_text(name),
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML,
        )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles /help command."""
    help_text = (
        "📖 <b>సహాయం (Sahayam.ai) - వినియోగ గైడ్:</b>\n\n"
        "<b>1. నేరుగా సందేశం పంపడం:</b>\n"
        "మీ పరిస్థితి, భూమి విస్తీర్ణం, కుటుంబ ఆదాయం, లేదా వృత్తి గురించి ఎలాంటి సందేహం ఉన్నా తెలుగులో టైప్ చేసి పంపండి.\n\n"
        "<b>2. ఆదేశాలు (Commands):</b>\n"
        "• <code>/start</code> - ముఖ్య మెనూకి తిరిగి వెళ్లండి\n"
        "• <code>/schemes</code> - సంక్షేమ పథకాల విభాగాలను చూడండి\n"
        "• <code>/wizard</code> - దశలవారీ అర్హత పరిశీలన ప్రారంభించండి\n"
        "• <code>/help</code> - ఈ సమాచార మార్గదర్శిని\n\n"
        "<b>3. నమూనా ప్రశ్నలు:</b>\n"
        "• <i>\"నాకు 2 ఎకరాల పొలం ఉంది, నాకు ఏ పథకాలు వస్తాయి?\"</i>\n"
        "• <i>\"ఆరోగ్యశ్రీ ఆపరేషన్లకు ఏయే పత్రాలు కావాలి?\"</i>\n"
        "• <i>\"డ్వాక్రా మహిళల సున్నా వడ్డీ రుణాలు ఎలా పొందాలి?\"</i>\n"
        "• <i>\"రోడ్డు పక్కన పండ్ల వ్యాపారం చేస్తున్నాను, ముద్ర రుణం వర్తిస్తుందా?\"</i>"
    )

    markup = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🎯 అర్హత చెకర్ ప్రారంభించండి", callback_data="nav:wizard"),
            InlineKeyboardButton("⬅️ ముఖ్య మెనూ", callback_data="nav:home"),
        ]
    ])

    if update.message:
        await update.message.reply_text(text=help_text, reply_markup=markup, parse_mode=ParseMode.HTML)
    elif update.callback_query and update.callback_query.message:
        await update.callback_query.message.edit_text(text=help_text, reply_markup=markup, parse_mode=ParseMode.HTML)
