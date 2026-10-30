"""Start and Help Handlers for Sahayam.ai Telugu Welfare Scheme Platform."""

import html
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes


def get_home_keyboard(lang: str = "te") -> InlineKeyboardMarkup:
    """Main menu navigation buttons with bilingual support."""
    is_en = (lang == "en")
    if is_en:
        keyboard = [
            [
                InlineKeyboardButton("🎯 Eligibility Wizard", callback_data="nav:wizard"),
                InlineKeyboardButton("📂 Scheme Categories", callback_data="nav:categories"),
            ],
            [
                InlineKeyboardButton("💡 Sample Questions", callback_data="nav:samples"),
                InlineKeyboardButton("📖 User Guide (Help)", callback_data="nav:help"),
            ],
            [
                InlineKeyboardButton("🌐 భాష / Language (English / తెలుగు)", callback_data="nav:language"),
            ],
        ]
    else:
        keyboard = [
            [
                InlineKeyboardButton("🎯 అర్హత చెకర్ (Wizard)", callback_data="nav:wizard"),
                InlineKeyboardButton("📂 పథకాల విభాగాలు", callback_data="nav:categories"),
            ],
            [
                InlineKeyboardButton("💡 నమూనా ప్రశ్నలు (Examples)", callback_data="nav:samples"),
                InlineKeyboardButton("📖 పూర్తి గైడ్ (Help)", callback_data="nav:help"),
            ],
            [
                InlineKeyboardButton("🌐 భాష / Language (తెలుగు / English)", callback_data="nav:language"),
            ],
        ]
    return InlineKeyboardMarkup(keyboard)


def get_welcome_text(user_first_name: str, lang: str = "te") -> str:
    """Generates the main welcoming message in polite, encouraging Telugu or English."""
    safe_name = html.escape(user_first_name)
    if lang == "en":
        return (
            f"🙏 <b>Hello {safe_name}! Welcome to Sahayam.ai</b>\n\n"
            "I am <b>Sahayam.ai</b> — your intelligent digital assistant to discover and apply for Central & State government welfare schemes.\n\n"
            "📢 <b>How can you ask?</b>\n"
            "Simply describe your situation in English (or Telugu) via text or <b>voice note (🎙 hold mic button)</b>. For example:\n\n"
            "👉 <i>\"I have 2 acres of farmland. I am a small farmer, which government schemes apply to me?\"</i>\n"
            "👉 <i>\"I am studying degree. How can I get fee reimbursement scholarship?\"</i>\n"
            "👉 <i>\"My mother is 62 years old. How to apply for old age pension?\"</i>\n"
            "👉 <i>\"Need a government loan for small grocery business.\"</i>\n\n"
            "⚡ <b>The assistant will instantly deliver:</b>\n"
            "• Relevant matching schemes\n"
            "• Why you qualify\n"
            "• Benefits & financial amounts\n"
            "• Required documents checklist\n"
            "• Step-by-step application procedure & official portal links\n\n"
            "🔊 <b>Voice Response:</b>\n"
            "Tap '🔊 Listen in Voice' on any response, or enable auto-voice anytime with <code>/voice</code>!\n\n"
            "🌐 <b>Language:</b> Use <code>/language</code> anytime to switch between English and Telugu."
        )
    return (
        f"🙏 <b>నమస్కారం {safe_name} గారూ!</b>\n\n"
        "నేను <b>సహాయం (Sahayam.ai)</b> — ప్రభుత్వ సంక్షేమ పథకాలను సులభంగా తెలుసుకోవడానికి మీ డిజిటల్ సహాయకుడిని.\n\n"
        "📢 <b>మీరు ఎలా అడగవచ్చు?</b>\n"
        "మీ పరిస్థితిని సాధారణ తెలుగులో టైప్ చేయండి లేదా <b>వాయిస్ మెసేజ్ (🎙 మైక్రోఫోన్ నొక్కి)</b> పంపండి. ఉదాహరణకు:\n\n"
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
        "🔊 <b>వాయిస్ సౌలభ్యం (Voice Feature):</b>\n"
        "సమాధానాన్ని వినడానికి '🔊 వాయిస్‌లో వినండి' బటన్ నొక్కండి, లేదా <code>/voice</code> ద్వారా ఆటో-వాయిస్ ఆన్ చేయండి!\n\n"
        "🌐 <b>భాష మార్పు:</b> ఆంగ్లంలో సంభాషించడానికి <code>/language</code> ఉపయోగించండి లేదా క్రింది బటన్ నొక్కండి!"
    )


async def language_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Allows citizens to choose between Telugu and English."""
    markup = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🌾 తెలుగు (Telugu)", callback_data="lang:te"),
            InlineKeyboardButton("🇬🇧 English", callback_data="lang:en"),
        ],
        [
            InlineKeyboardButton("⬅️ ముఖ్య మెనూ / Main Menu", callback_data="nav:home"),
        ],
    ])
    text = (
        "🌐 <b>భాషను ఎంచుకోండి / Select Language:</b>\n\n"
        "దయచేసి మీరు సంభాషించడానికి ఇష్టపడే భాషను ఎంచుకోండి:\n"
        "Please select your preferred language for discovery and voice responses:"
    )
    if update.message:
        await update.message.reply_text(text=text, reply_markup=markup, parse_mode=ParseMode.HTML)
    elif update.callback_query and update.callback_query.message:
        await update.callback_query.message.edit_text(text=text, reply_markup=markup, parse_mode=ParseMode.HTML)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles /start command."""
    user = update.effective_user
    name = user.first_name if user else "మిత్రమా"
    lang = context.user_data.get("language", "te")
    reply_markup = get_home_keyboard(lang=lang)

    if update.message:
        await update.message.reply_text(
            text=get_welcome_text(name, lang=lang),
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML,
        )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles /help command."""
    lang = context.user_data.get("language", "te")
    is_en = (lang == "en")

    if is_en:
        help_text = (
            "📖 <b>Sahayam.ai - User Guide:</b>\n\n"
            "<b>1. Natural Conversational Queries:</b>\n"
            "Send any question about your land, education, family income, pension, housing, healthcare or trade via text or voice.\n\n"
            "<b>2. Commands:</b>\n"
            "• <code>/start</code> - Return to Main Menu\n"
            "• <code>/language</code> - Switch between English & Telugu\n"
            "• <code>/schemes</code> - Browse Welfare Scheme Categories\n"
            "• <code>/wizard</code> - Step-by-step Interactive Eligibility Checker\n"
            "• <code>/voice</code> - Toggle Automatic Voice Responses (Auto Voice)\n"
            "• <code>/reset</code> - Start a Fresh Conversation (Reset Chat)\n"
            "• <code>/help</code> - This Information Guide\n\n"
            "<b>3. Sample English Queries:</b>\n"
            "• <i>\"I have 2 acres of land, which schemes can I apply for?\"</i>\n"
            "• <i>\"What documents are required for Aarogyasri free hospital treatment?\"</i>\n"
            "• <i>\"How to get zero interest loans for DWACRA women?\"</i>\n"
            "• <i>\"I am a street vendor selling vegetables, can I get PM SVANidhi loan?\"</i>"
        )
        markup = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🎯 Start Eligibility Wizard", callback_data="nav:wizard"),
                InlineKeyboardButton("⬅️ Main Menu", callback_data="nav:home"),
            ]
        ])
    else:
        help_text = (
            "📖 <b>సహాయం (Sahayam.ai) - వినియోగ గైడ్:</b>\n\n"
            "<b>1. నేరుగా సందేశం పంపడం:</b>\n"
            "మీ పరిస్థితి, భూమి విస్తీర్ణం, కుటుంబ ఆదాయం, లేదా వృత్తి గురించి ఎలాంటి సందేహం ఉన్నా తెలుగులో టైప్ చేసి లేదా వాయిస్ మెసేజ్ ద్వారా పంపండి.\n\n"
            "<b>2. ఆదేశాలు (Commands):</b>\n"
            "• <code>/start</code> - ముఖ్య మెనూకి తిరిగి వెళ్లండి\n"
            "• <code>/language</code> - భాష మార్చుకోండి (తెలుగు / English)\n"
            "• <code>/schemes</code> - సంక్షేమ పథకాల విభాగాలను చూడండి\n"
            "• <code>/wizard</code> - దశలవారీ అర్హత పరిశీలన ప్రారంభించండి\n"
            "• <code>/voice</code> - వాయిస్ సమాధానాల మోడ్ ఆన్/ఆఫ్ (Auto Voice)\n"
            "• <code>/reset</code> - కొత్త సంభాషణ ప్రారంభించండి (Reset Chat)\n"
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
