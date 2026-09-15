"""Interactive Step-by-Step Eligibility Wizard for Telugu Citizens."""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from data.schemes import SCHEMES
from handlers.schemes_handler import build_scheme_actions_keyboard, safe_edit_text
from services.matcher import format_multiple_schemes_summary, format_scheme_detailed_telugu


async def start_wizard_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Step 1 of Eligibility Wizard: Select citizen category."""
    query = update.callback_query
    if query:
        await query.answer()

    text = (
        "🎯 <b>సంక్షేమ పథకాల అర్హత చెకర్ (Eligibility Wizard)</b>\n\n"
        "మీకు తగిన పథకాలను వేగంగా తెలుసుకోవడానికి, దయచేసి మీ వర్గాన్ని ఎంచుకోండి:\n"
    )

    keyboard = [
        [
            InlineKeyboardButton("🌾 రైతు / వ్యవసాయం", callback_data="wiz:cat:agriculture"),
            InlineKeyboardButton("👩 మహిళ / డ్వాక్రా", callback_data="wiz:cat:women"),
        ],
        [
            InlineKeyboardButton("🎓 విద్యార్థి / చదువు", callback_data="wiz:cat:education"),
            InlineKeyboardButton("🏥 ఆరోగ్యం / వైద్య సాయం", callback_data="wiz:cat:health"),
        ],
        [
            InlineKeyboardButton("👴 వృద్ధులు / పెన్షన్", callback_data="wiz:cat:pension"),
            InlineKeyboardButton("💼 వ్యాపారి / స్వయం ఉపాధి", callback_data="wiz:cat:business"),
        ],
        [
            InlineKeyboardButton("🏠 ఇల్లు / గృహ నిర్మాణం", callback_data="wiz:cat:housing"),
        ],
        [
            InlineKeyboardButton("⬅️ ముఖ్య మెనూ", callback_data="nav:home"),
        ],
    ]

    markup = InlineKeyboardMarkup(keyboard)
    if query and query.message:
        await safe_edit_text(query.message, text=text, reply_markup=markup)
    elif update.message:
        await update.message.reply_text(text=text, reply_markup=markup, parse_mode=ParseMode.HTML)


async def wizard_category_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Step 2: Sub-questions based on category."""
    query = update.callback_query
    if not query or not query.data:
        return

    await query.answer()
    category = query.data.replace("wiz:cat:", "")

    if category == "agriculture":
        text = (
            "🌾 <b>వ్యవసాయం & రైతు వివరాలు:</b>\n\n"
            "మీ వద్ద ఎంత సాగుభూమి ఉంది?"
        )
        keyboard = [
            [
                InlineKeyboardButton("🌱 2 ఎకరాల లోపు (సన్నకారు రైతు)", callback_data="wiz:land:2"),
            ],
            [
                InlineKeyboardButton("🚜 2 నుండి 5 ఎకరాలు (చిన్న రైతు)", callback_data="wiz:land:5"),
            ],
            [
                InlineKeyboardButton("🌾 5 ఎకరాల కంటే ఎక్కువ", callback_data="wiz:land:10"),
            ],
            [
                InlineKeyboardButton("🤝 కౌలు రైతు (సొంత భూమి లేదు)", callback_data="wiz:land:tenant"),
            ],
            [
                InlineKeyboardButton("⬅️ వెనుకకు", callback_data="nav:wizard"),
            ],
        ]
        await safe_edit_text(query.message, text=text, reply_markup=InlineKeyboardMarkup(keyboard))
        return

    # For other categories, show matched schemes directly
    matching = [s for s in SCHEMES if s["category"] == category]
    if matching:
        matched_tuples = [(s, 10.0, s.get("qualify_reason_te", "")) for s in matching]
        context.user_data["last_matched_schemes"] = matched_tuples
        if len(matching) > 1:
            text = format_multiple_schemes_summary(matched_tuples)
            markup = build_scheme_actions_keyboard(matched_schemes=matched_tuples)
        else:
            top_s = matching[0]
            text = (
                f"✅ <b>మీ వర్గానికి అనువైన పథకం:</b>\n\n"
                f"{format_scheme_detailed_telugu(top_s, top_s.get('qualify_reason_te', ''))}"
            )
            markup = build_scheme_actions_keyboard(scheme=top_s, matched_schemes=matched_tuples, is_detail_view=True)
        context.user_data["last_response_text"] = text
        await safe_edit_text(query.message, text=text, reply_markup=markup, disable_web_page_preview=True)
    else:
        await safe_edit_text(query.message, text="సమాచారం లభించలేదు.")


async def wizard_land_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Step 3 for Agriculture: evaluate land size and display schemes."""
    query = update.callback_query
    if not query or not query.data:
        return

    await query.answer()
    land_type = query.data.replace("wiz:land:", "")

    if land_type in ("2", "5"):
        acres = 2.0 if land_type == "2" else 4.0
        # Matches PM-KISAN, Rythu Bharosa, Free Power, Insurance
        pm_kisan = [s for s in SCHEMES if s["id"] == "pm_kisan"][0]
        reason = f"మీ వద్ద {acres} ఎకరాల భూమి ఉన్నందున మీరు చిన్న/సన్నకారు రైతుగా పరిగణించబడతారు. 5 ఎకరాల లోపు భూమి ఉన్నందున కేంద్ర-రాష్ట్ర ప్రభుత్వాల పెట్టుబడి పథకాలకు మీరు పూర్తి అర్హులు."

        other_schemes = [
            (s, 10.0, reason) for s in SCHEMES if s["category"] == "agriculture" and s["id"] != "pm_kisan"
        ]
        all_matches = [(pm_kisan, 15.0, reason)] + other_schemes
        context.user_data["last_matched_schemes"] = all_matches
        text = format_multiple_schemes_summary(all_matches)
        context.user_data["last_response_text"] = text
        markup = build_scheme_actions_keyboard(matched_schemes=all_matches)
        await safe_edit_text(query.message, text=text, reply_markup=markup, disable_web_page_preview=True)

    elif land_type == "tenant":
        rythu_bharosa = [s for s in SCHEMES if s["id"] == "rythu_bharosa"][0]
        reason = "కౌలు రైతులు CCRC (Crop Cultivator Rights Card) కార్డు ద్వారా రైతు భరోసా పెట్టుబడి సాయం మరియు పంటల బీమా పొందవచ్చు."
        other_schemes = [(s, 8.0, reason) for s in SCHEMES if s["id"] in ("pmfby_crop_insurance", "free_agri_power")]
        all_matches = [(rythu_bharosa, 12.0, reason)] + other_schemes
        context.user_data["last_matched_schemes"] = all_matches
        text = format_multiple_schemes_summary(all_matches)
        context.user_data["last_response_text"] = text
        markup = build_scheme_actions_keyboard(matched_schemes=all_matches)
        await safe_edit_text(query.message, text=text, reply_markup=markup, disable_web_page_preview=True)

    else:
        # > 5 acres
        free_power = [s for s in SCHEMES if s["id"] == "free_agri_power"][0]
        reason = "మీ వద్ద 5 ఎకరాల కంటే ఎక్కువ భూమి ఉన్నందున PM-KISAN పరిమితి మించవచ్చు, కానీ ఉచిత వ్యవసాయ విద్యుత్ మరియు పంటల బీమా పథకాలు వర్తిస్తాయి."
        all_matches = [
            (free_power, 10.0, reason),
            ([s for s in SCHEMES if s["id"] == "pmfby_crop_insurance"][0], 9.0, reason),
        ]
        context.user_data["last_matched_schemes"] = all_matches
        text = format_multiple_schemes_summary(all_matches)
        context.user_data["last_response_text"] = text
        markup = build_scheme_actions_keyboard(matched_schemes=all_matches)
        await safe_edit_text(query.message, text=text, reply_markup=markup, disable_web_page_preview=True)
