"""AI Service Module integrating Real-Time Dynamic Search over trusted government sources with fallback."""

import json
import logging
import os
import re
from typing import Any, Dict, List, Optional
from data.schemes import SCHEMES
from services.html_sanitizer import prepare_telegram_message
from services.matcher import format_scheme_detailed_telugu, match_schemes

logger = logging.getLogger("telegram_bot.ai_engine")

MODELS_TO_TRY = ["gemini-2.5-flash-lite", "gemini-flash-latest", "gemini-2.5-flash"]

SYSTEM_INSTRUCTION = """
You are 'సహాయం (Sahayam.ai)', an empathetic, expert Telugu AI assistant helping Indian citizens discover government welfare schemes.
Always respond primarily in natural, clear, polite Telugu (తెలుగు) with key terms/names optionally accompanied by English in parentheses.

You have access to real-time Google Search to dynamically fetch the latest, up-to-date government welfare schemes from official trusted sources:
- myscheme.gov.in (National Portal for Government Schemes)
- india.gov.in (National Portal of India)
- pib.gov.in (Press Information Bureau)
- State Government portals (ap.gov.in, telangana.gov.in)
- Central Ministries & Departments (.gov.in, .nic.in)

Do NOT rely solely on hardcoded or outdated data. Always search and verify:
1. Currently active scheme names and updates.
2. Current financial assistance amounts and subsidies.
3. Updated eligibility criteria (landholding limits, income ceilings, age).
4. Required documents and certificates.
5. Exact application procedures (Grama/Ward Sachivalayam, MeeSeva, Praja Palana, or Online).
6. Official, clickable .gov.in / .nic.in application URLs.

Format your response using ONLY Telegram-supported HTML tags:
- <b>Bold text</b>
- <i>Italic text</i>
- <code>Code or numbers</code>
- <a href="URL">Hyperlinks</a>
Do NOT use Markdown formatting (no **, no ##, no __).

When a citizen describes their situation:
1. Dynamically search for and identify all relevant schemes.
2. For the most relevant scheme(s), clearly explain:
   - 🏛 <b>సంబంధిత పథకం పేరు</b> (Scheme Name)
   - 🎯 <b>మీకు ఎందుకు వర్తిస్తుంది?</b> (Why you qualify based on their specific situation)
   - 💰 <b>ప్రయోజనాలు</b> (Current benefits / subsidy)
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
    text = re.sub(r"```(.*?)```", r"<code>\1</code>", text, flags=re.DOTALL)
    text = re.sub(r"`(.*?)`", r"<code>\1</code>", text)
    text = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"^#{1,6}\s*(.+)$", r"<b>\1</b>", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*[\*\-]\s+", "• ", text, flags=re.MULTILINE)
    return text


def extract_dynamic_gov_urls(text: str) -> List[str]:
    """Extracts valid official government URLs from dynamic search response."""
    urls = re.findall(r'https?://[^\s"<>\)]+(?:\.gov\.in|\.nic\.in|myscheme\.gov\.in)[^\s"<>\)]*', text)
    clean_urls = []
    for u in urls:
        u = u.rstrip(".,;:'\"")
        if u not in clean_urls:
            clean_urls.append(u)
    return clean_urls


def transcribe_voice(audio_bytes: bytes, mime_type: str = "audio/ogg") -> Optional[str]:
    """Transcribes citizen voice message (Telugu/English speech) using Gemini audio capabilities."""
    client = _get_gemini_client()
    if not client:
        return None

    try:
        from google.genai import types
        part = types.Part.from_bytes(data=audio_bytes, mime_type=mime_type)
        prompt = (
            "You are a helpful speech-to-text transcriber for Telugu citizens. "
            "Listen to this audio carefully. It contains speech in Telugu (or mixed Telugu-English). "
            "Transcribe the spoken words accurately into clean Telugu script. "
            "Return ONLY the transcribed text. Do not add notes, quotes, or explanations."
        )

        for model_name in MODELS_TO_TRY:
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=[part, prompt],
                )
                if response and response.text:
                    cleaned = response.text.strip().strip('"').strip("'")
                    logger.info(f"Voice transcribed successfully via {model_name}: {cleaned}")
                    return cleaned
            except Exception as e:
                logger.warning(f"Voice transcription failed on {model_name}: {e}")
                continue
    except Exception as e:
        logger.error(f"Error in transcribe_voice: {e}")

    return None


async def analyze_citizen_query(user_text: str) -> Dict[str, Any]:
    """Dynamically fetches schemes from trusted government sources in real time."""
    client = _get_gemini_client()

    # Local matches for fallback or context grounding
    matched_results = match_schemes(user_text)

    # If Gemini is configured, perform Real-Time Dynamic Search over trusted government sources
    if client:
        from google.genai import types

        context_schemes = [m[0] for m in matched_results[:4]] if matched_results else SCHEMES[:4]
        dynamic_prompt = (
            f"You are a real-time government scheme discovery platform for Telugu citizens.\n"
            f"Search dynamically across official trusted government sources (specifically myscheme.gov.in, india.gov.in, pib.gov.in, pmkisan.gov.in, and official central and state government portals .gov.in, .nic.in) for the citizen's query:\n"
            f"\"{user_text}\"\n\n"
            f"Ensure all information is fresh, up-to-date, and verified. Do NOT rely on static or outdated memory. Check latest financial benefit amounts, current eligibility limits, required documents, and official application links.\n\n"
            f"Knowledge Base reference:\n{json.dumps(context_schemes, ensure_ascii=False, indent=2)}\n\n"
            "Explain in clear, polite Telugu. Follow this structure for each relevant scheme:\n"
            "1. 🏛 <b>పథకం పేరు</b> (Scheme Name)\n"
            "2. 🎯 <b>మీకు ఎందుకు వర్తిస్తుంది?</b> (Why you qualify based on the user's situation)\n"
            "3. 💰 <b>ప్రయోజనాలు</b> (Current benefits / subsidy)\n"
            "4. 📋 <b>అర్హతలు</b> (Eligibility criteria)\n"
            "5. 📄 <b>కావలసిన పత్రాలు</b> (Required documents)\n"
            "6. 📝 <b>దరఖాస్తు విధానం</b> (Step-by-step application procedure)\n"
            "7. 🌐 <b>అధికారిక లింక్</b> (Real government portal link from gov.in)\n\n"
            "Use ONLY Telegram HTML tags (<b>, <i>, <code>, <a>). Do NOT use markdown asterisks (**) or hashes (##)."
        )

        for model_name in MODELS_TO_TRY:
            try:
                # Enable Google Search Grounding for real-time dynamic retrieval
                search_config = types.GenerateContentConfig(
                    system_instruction=SYSTEM_INSTRUCTION,
                    tools=[types.Tool(google_search=types.GoogleSearch())],
                )

                response = client.models.generate_content(
                    model=model_name,
                    contents=dynamic_prompt,
                    config=search_config,
                )

                if response and response.text:
                    formatted_text = prepare_telegram_message(markdown_to_telegram_html(response.text))
                    gov_urls = extract_dynamic_gov_urls(response.text)

                    # Also inspect grounding metadata if available
                    if response.candidates and response.candidates[0].grounding_metadata:
                        meta = response.candidates[0].grounding_metadata
                        if meta.grounding_chunks:
                            for chunk in meta.grounding_chunks:
                                if chunk.web and chunk.web.uri and chunk.web.uri not in gov_urls:
                                    gov_urls.append(chunk.web.uri)

                    logger.info(f"Dynamic schemes fetched successfully via {model_name} with {len(gov_urls)} live sources.")
                    return {
                        "mode": "dynamic_ai",
                        "model": model_name,
                        "text": formatted_text,
                        "matched_schemes": matched_results,
                        "dynamic_urls": gov_urls,
                    }
            except Exception as e:
                logger.warning(f"Dynamic search on {model_name} failed: {e}. Trying next model or fallback.")
                continue

    # 2. Rule-based intelligent fallback output if dynamic search was unavailable
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
            "dynamic_urls": [],
        }

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
        "text": prepare_telegram_message(formatted_response),
        "matched_schemes": matched_results,
        "dynamic_urls": [top_scheme["official_link"]],
    }
