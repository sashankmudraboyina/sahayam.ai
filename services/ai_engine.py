"""AI Service Module integrating Google Gemini with fallback to deterministic matching."""

import json
import logging
import os
import re
from typing import Any, Dict, List, Optional
from data.schemes import SCHEMES
from services.matcher import format_scheme_detailed_telugu, match_schemes

logger = logging.getLogger("telegram_bot.ai_engine")

MODELS_TO_TRY = ["gemini-2.5-flash-lite", "gemini-flash-latest", "gemini-2.5-flash"]

SYSTEM_INSTRUCTION = """
You are 'సహాయం (Sahayam.ai)', an empathetic, expert Telugu AI assistant helping Indian citizens discover government welfare schemes.
Always respond primarily in natural, clear, polite Telugu (తెలుగు) with key terms/names optionally accompanied by English in parentheses.

Format your response using ONLY Telegram-supported HTML tags:
- <b>Bold text</b>
- <i>Italic text</i>
- <code>Code or numbers</code>
- <a href="URL">Hyperlinks</a>
Do NOT use Markdown formatting (no **, no ##, no __).

When a citizen describes their situation (e.g. farmer with 2 acres, student needing fees, woman seeking loan):
1. Identify all relevant Central & State government schemes from the provided knowledge base.
2. For the most relevant scheme(s), clearly explain:
   - 🏛 <b>సంబంధిత పథకం పేరు</b> (Scheme Name)
   - 🎯 <b>మీకు ఎందుకు వర్తిస్తుంది?</b> (Why you qualify based on their specific situation)
   - 💰 <b>ప్రయోజనాలు</b> (Benefits)
   - 📋 <b>అర్హతలు</b> (Eligibility criteria)
   - 📄 <b>కావలసిన పత్రాలు / డాక్యుమెంట్లు</b> (Required documents)
   - 📝 <b>దరఖాస్తు విధానం</b> (Step-by-step application procedure)
   - 🌐 <b>అధికారిక వెబ్‌సైట్ లింక్</b> (Official application website link)
3. Keep the tone respectful, encouraging, and easy to understand for rural or non-technical citizens.
4. If the user does not qualify or needs extra conditions (like e-KYC, income certificate, land records), gently inform them.
"""


def _get_gemini_client():
    """Initializes Google GenAI client if GEMINI_API_KEY is configured."""
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        return None
    try:
        from google import genai
        return genai.Client(api_key=api_key)
    except Exception as e:
        logger.warning(f"Failed to initialize google-genai client: {e}")
        return None


def markdown_to_telegram_html(text: str) -> str:
    """Converts basic markdown bold/italic/code syntax into Telegram-safe HTML."""
    # Convert code blocks
    text = re.sub(r"```(.*?)```", r"<code>\1</code>", text, flags=re.DOTALL)
    text = re.sub(r"`(.*?)`", r"<code>\1</code>", text)
    # Convert bold
    text = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", text)
    # Convert headers (### Header -> <b>Header</b>)
    text = re.sub(r"^#{1,6}\s*(.+)$", r"<b>\1</b>", text, flags=re.MULTILINE)
    # Convert bullets * or - to bullet symbol
    text = re.sub(r"^\s*[\*\-]\s+", "• ", text, flags=re.MULTILINE)
    return text


async def analyze_citizen_query(user_text: str) -> Dict[str, Any]:
    """Analyzes user query and returns structured scheme discovery results."""
    client = _get_gemini_client()

    # 1. Deterministic match results
    matched_results = match_schemes(user_text)

    # If Gemini is configured, use it for conversational synthesis
    if client:
        # Build context with top 5 relevant schemes or all if few
        context_schemes = [m[0] for m in matched_results[:5]] if matched_results else SCHEMES[:5]
        prompt = (
            f"పౌరుడి ప్రశ్న / పరిస్థితి:\n\"{user_text}\"\n\n"
            f"అందుబాటులో ఉన్న పథకాల సమాచారం (Knowledge Base):\n"
            f"{json.dumps(context_schemes, ensure_ascii=False, indent=2)}\n\n"
            "దయచేసి పైన పేర్కొన్న ప్రశ్నను పరిశీలించి, సంబంధిత పథకాలను, వాటి ప్రయోజనాలు, అర్హతలు, "
            "కావలసిన పత్రాలు, దరఖాస్తు విధానం, అధికారిక వెబ్‌సైట్ లింక్ మరియు పౌరుడికి ఎందుకు వర్తిస్తుందో స్పష్టమైన తెలుగులో వివరించండి. "
            "HTML ట్యాగ్‌లు (<b>, <i>, <code>, <a>) మాత్రమే ఉపయోగించండి."
        )

        for model_name in MODELS_TO_TRY:
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config={"system_instruction": SYSTEM_INSTRUCTION},
                )
                if response and response.text:
                    formatted_text = markdown_to_telegram_html(response.text)
                    return {
                        "mode": "ai",
                        "model": model_name,
                        "text": formatted_text,
                        "matched_schemes": matched_results,
                    }
            except Exception as e:
                logger.warning(f"Model {model_name} failed: {e}. Trying fallback.")
                continue

    # 2. Rule-based intelligent output
    if not matched_results:
        no_match_text = (
            "🙏 <b>సహాయం (Sahayam.ai)</b>\n\n"
            "క్షమించండి, మీరు తెలిపిన వివరాలతో సరిపోయే పథకాలను గుర్తించలేకపోయాము.\n\n"
            "💡 <b>సూచన:</b> దయచేసి మీ వృత్తి (రైతు, విద్యార్థి, మహిళ, వ్యాపారి), మీ వద్ద ఉన్న భూమి (ఉదా: 2 ఎకరాలు), "
            "లేదా మీకు కావలసిన సాయం గురించి మరింత వివరంగా తెలియజేయండి.\n\n"
            "<i>ఉదాహరణ: 'నాకు రెండు ఎకరాల పొలం ఉంది. నేను చిన్న రైతును. నాకు ఏ ప్రభుత్వ పథకాలు వర్తిస్తాయి?'</i>"
        )
        return {
            "mode": "fallback_empty",
            "text": no_match_text,
            "matched_schemes": [],
        }

    # Format the top matched scheme and list others
    top_scheme, top_score, top_reason = matched_results[0]
    formatted_response = (
        f"🌾 <b>సహాయం (Sahayam.ai) - సంక్షేమ పథకాల శోధన ఫలితాలు</b>\n\n"
        f"మీ వివరాల ఆధారంగా <b>{len(matched_results)}</b> అనువైన ప్రభుత్వ పథకాలు గుర్తించబడ్డాయి:\n\n"
        f"═════════════════════════════\n"
        f"{format_scheme_detailed_telugu(top_scheme, top_reason)}\n"
        f"═════════════════════════════\n"
    )

    if len(matched_results) > 1:
        formatted_response += "\n📌 <b>మీకు వర్తించే ఇతర సంబంధిత పథకాలు:</b>\n"
        for i, (other_scheme, score, reason) in enumerate(matched_results[1:4], 1):
            formatted_response += f"{i}. <b>{other_scheme['name_te']}</b>\n   <i>👉 {reason}</i>\n"
        formatted_response += "\n💡 <i>క్రింది బటన్ల ద్వారా ఇతర పథకాల పూర్తి వివరాలు, కావలసిన పత్రాలు మరియు దరఖాస్తు లింక్ చూడవచ్చు.</i>"

    return {
        "mode": "deterministic",
        "text": formatted_response,
        "matched_schemes": matched_results,
    }
