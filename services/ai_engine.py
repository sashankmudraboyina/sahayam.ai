"""AI Service Module grounded strictly on the Government Schemes Dataset with Multi-Turn Conversation & Boundary Guardrails."""

import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from data.schemes import SCHEMES
from services.html_sanitizer import prepare_telegram_message
from services.matcher import (
    find_scheme_by_name_or_query,
    format_multiple_schemes_summary,
    format_scheme_detailed_telugu,
    match_schemes,
)

logger = logging.getLogger("telegram_bot.ai_engine")

MODELS_TO_TRY = ["gemini-2.5-flash", "gemini-3.5-flash", "gemini-flash-latest", "gemini-3.1-flash-lite"]

# Load local Government Schemes Dataset
DATASET_PATH = Path(__file__).resolve().parent.parent / "govt_schemes_dataset.md"
try:
    with open(DATASET_PATH, "r", encoding="utf-8") as f:
        DATASET_CONTENT = f.read()
except Exception as e:
    logger.warning(f"Could not load govt_schemes_dataset.md: {e}")
    DATASET_CONTENT = ""

SYSTEM_INSTRUCTION = f"""You are 'సహాయం (Sahayam.ai)', an empathetic, expert, conversational Telugu AI assistant dedicated to helping Indian citizens discover and apply for Central and State government welfare schemes.
Always respond primarily in natural, polite, respectful Telugu (తెలుగు) with key terms/names optionally accompanied by English in parentheses.

STRICT LOCAL DATASET GROUNDING (NO EXTERNAL WEB BROWSING):
- You MUST base all scheme information, eligibility rules, financial amounts, required documents, and portal links STRICTLY on the authoritative Government Welfare Schemes Dataset provided below.
- Do NOT browse the live web or call external search engines.
- When schemes were renamed (e.g. YSR Amma Vodi -> Talliki Vandanam, YSR Rythu Bharosa -> Annadata Sukhibhava, Rythu Bandhu -> Rythu Bharosa, YSR Pension Kanuka -> NTR Bharosa), reflect the current active scheme name and details from the dataset while noting the previous name.

CONVERSATIONAL CONTINUITY & BOUNDARIES:
1. Multi-Turn Context:
   - When a citizen asks follow-up questions (e.g., "దీనికి ఎలా దరఖాస్తు చేయాలి?", "ఏ పత్రాలు కావాలి?", "నాకు రేషన్ కార్డు లేదు, వర్తిస్తుందా?", "మా భార్య పేరు మీద పెట్టొచ్చా?"), resolve references to the schemes discussed previously in the conversation using the dataset.
2. Strict Domain Boundary:
   - Stay strictly within the boundary of Government Welfare Schemes, social security, subsidies, pensions, agricultural support, scholarships, housing, healthcare, loans (MUDRA/SVANidhi), eligibility criteria, required documents, and application procedures.
   - If a citizen asks about unrelated topics (movies, sports, coding, general trivia, politics):
     Politely decline in Telugu and gently guide them back to welfare schemes:
     "క్షమించండి, నేను ప్రభుత్వ సంక్షేమ పథకాలు మరియు వాటి అర్హతలకు సంబంధించిన సమాచారాన్ని మాత్రమే అందించే సహాయకుడిని. దయచేసి సంక్షేమ పథకాల గురించి అడగండి."
3. WHEN TO ASK QUESTIONS (CRITICAL - ASK ONLY WHEN NEEDED, NEVER ASK REDUNDANT INFO):
   - Ask clarifying questions ONLY when the citizen explicitly requests to evaluate their personal eligibility or find matching schemes for themselves, AND essential criteria are missing.
   - NEVER ask questions if:
     • The citizen is asking about a specific scheme (e.g. "Tell me about PM Kisan", "Kalyana Lakshmi application", "PM Mudra loan", "Rythu Bharosa"). Directly provide the complete details, benefits, documents, and portal link for that scheme!
     • The citizen is asking an informational, factual, or rule question (e.g. "What is the age limit for pension?", "How much financial aid is given?", "Is white ration card needed?"). Answer their question directly without interrogating them!
     • The information was already provided earlier in the conversation or in their query. NEVER ask for redundant information you already know!
     • The scheme is a Central scheme that applies across all states (e.g. PM-KISAN, MUDRA, SVANidhi, PM Vishwakarma). Do NOT ask for state!
   - When asking is genuinely needed:
     Ask ONLY for the single missing piece of information (only 1 single polite question per message). Never ask multiple questions.
   - When all details are known or provided upfront:
     Immediately present the exact eligible schemes with reasons, benefits, documents, and official portal links.

4. When Multiple Schemes Are Identified (CRITICAL - AVOID LONG OVERWHELMING MESSAGES):
   - When 2 or more schemes apply to the citizen's query (e.g., small farmer qualifies for PM-KISAN, Rythu Bharosa, and PMFBY):
     DO NOT dump full documents, eligibility, and step-by-step application steps for every single scheme at once. That overwhelms the citizen!
     Instead, provide a CRISP, CLEAN SUMMARY OVERVIEW:
     For EACH matching scheme, provide:
     • 🏛 <b>[క్రమసంఖ్య. పథకం పేరు (Scheme Name)]</b>
       💰 <b>ప్రయోజనం:</b> (Key financial or material benefit in 1 short sentence)
       🎯 <b>అర్హత:</b> (Briefly why this citizen qualifies in 1 short sentence)
     Then add a clear prompt at the end:
     "👉 <i>ఏదైనా పథకం యొక్క పూర్తి వివరాలు (Full Description), కావలసిన పత్రాలు (Documents), మరియు దరఖాస్తు విధానం (Application Process) కోసం క్రింది బటన్ నొక్కండి లేదా ఆ పథకం పేరును ఇక్కడ అడగండి!</i>"

5. When a Single Scheme is Discussed or When Citizen Requests "పూర్తి వివరాలు / More Details / How to Apply":
   - Provide the complete, structured detailed breakdown for that specific scheme:
     • 🏛 <b>పథకం పేరు</b> (Scheme Name & Category)
     • 🎯 <b>మీకు ఎందుకు వర్తిస్తుంది? / అర్హత విశ్లేషణ</b> (Why you qualify)
     • 💰 <b>ప్రయోజనాలు</b> (Current benefits / amount)
     • 📋 <b>అర్హతలు</b> (Eligibility criteria)
     • 📄 <b>కావలసిన పత్రాలు</b> (Required documents)
     • 📝 <b>దరఖాస్తు విధానం</b> (Step-by-step application procedure)
     • 🌐 <b>అధికారిక లింక్</b> (Official government application portal)
     • End with a welcoming follow-up offer in Telugu: "మీకు దరఖాస్తు చేయడంలో లేదా డాక్యుమెంట్లలో ఏమైనా సందేహాలు ఉంటే అడగండి!"

6. Formatting:
   Use ONLY Telegram HTML tags:
   <b>bold</b>, <i>italic</i>, <code>code</code>, <a href="URL">links</a>.
   Do NOT use markdown asterisks (**) or hashes (##).

<GOVERNMENT_WELFARE_SCHEMES_DATASET>
{DATASET_CONTENT}
</GOVERNMENT_WELFARE_SCHEMES_DATASET>
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


def extract_gov_urls(text: str, matched_schemes: Optional[List[Tuple[Dict[str, Any], float, str]]] = None) -> List[str]:
    """Extracts valid official government URLs from dataset response or matched schemes."""
    urls = re.findall(
        r'https?://[^\s"<>\)]+(?:\.gov\.in|\.nic\.in|myscheme\.gov\.in|cgg\.gov\.in|telangana\.gov\.in|ap\.gov\.in)[^\s"<>\)]*',
        text,
    )
    clean_urls = []
    for u in urls:
        u = u.rstrip(".,;:'\"")
        if u not in clean_urls:
            clean_urls.append(u)

    if matched_schemes:
        for m in matched_schemes[:3]:
            sch_link = m[0].get("official_link")
            if sch_link and sch_link not in clean_urls and sch_link != "https://myscheme.gov.in":
                clean_urls.append(sch_link)

    return clean_urls


def _transcribe_with_speech_recognition(audio_bytes: bytes, preferred_lang: str = "te") -> Optional[str]:
    """Transcribes audio using Google Speech Recognition (free, no API key required) supporting Telugu (te-IN) and English (en-IN)."""
    try:
        import io
        import subprocess
        import speech_recognition as sr

        ffmpeg_exe = "ffmpeg"
        try:
            import imageio_ffmpeg
            ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        except Exception:
            pass

        proc = subprocess.Popen(
            [ffmpeg_exe, "-y", "-i", "pipe:0", "-f", "wav", "-ar", "16000", "-ac", "1", "pipe:1"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        wav_bytes, err = proc.communicate(input=audio_bytes)
        if proc.returncode != 0 or not wav_bytes:
            logger.warning(f"Audio conversion failed: {err.decode(errors='ignore')}")
            return None

        recognizer = sr.Recognizer()
        with sr.AudioFile(io.BytesIO(wav_bytes)) as source:
            audio = recognizer.record(source)

        lang_order = ["en-IN", "te-IN"] if preferred_lang == "en" else ["te-IN", "en-IN"]
        for target_lang in lang_order:
            try:
                rec_text = recognizer.recognize_google(audio, language=target_lang)
                if rec_text and rec_text.strip():
                    logger.info(f"Voice transcribed via speech_recognition ({target_lang}): {rec_text.strip()}")
                    return rec_text.strip()
            except sr.UnknownValueError:
                continue
            except Exception as e:
                logger.warning(f"{target_lang} speech recognition error: {e}")

        # If standard audio failed to recognize, try with volume normalization (helps low-volume/distant microphone audio)
        try:
            proc_norm = subprocess.Popen(
                [ffmpeg_exe, "-y", "-i", "pipe:0", "-af", "loudnorm=I=-16:TP=-1.5:LRA=11", "-f", "wav", "-ar", "16000", "-ac", "1", "pipe:1"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            wav_norm, _ = proc_norm.communicate(input=audio_bytes)
            if proc_norm.returncode == 0 and wav_norm:
                with sr.AudioFile(io.BytesIO(wav_norm)) as source:
                    audio_norm = recognizer.record(source)
                for target_lang in lang_order:
                    try:
                        rec_text = recognizer.recognize_google(audio_norm, language=target_lang)
                        if rec_text and rec_text.strip():
                            logger.info(f"Voice transcribed via speech_recognition normalized ({target_lang}): {rec_text.strip()}")
                            return rec_text.strip()
                    except sr.UnknownValueError:
                        continue
                    except Exception as e:
                        logger.warning(f"{target_lang} normalized speech recognition error: {e}")
        except Exception as e:
            logger.debug(f"Audio normalization fallback skipped: {e}")

    except Exception as e:
        logger.error(f"Error in _transcribe_with_speech_recognition: {e}")

    return None


def transcribe_voice(audio_bytes: bytes, mime_type: str = "audio/ogg", preferred_lang: str = "te") -> Optional[str]:
    """Transcribes citizen voice message (Telugu/English speech) using Gemini or Google Speech Recognition fallback."""
    client = _get_gemini_client()
    if client:
        try:
            from google.genai import types
            part = types.Part.from_bytes(data=audio_bytes, mime_type=mime_type)
            if preferred_lang == "en":
                prompt = (
                    "You are a helpful speech-to-text transcriber for Indian citizens. "
                    "Listen to this audio carefully. It contains speech in English (or mixed Indian English/Telugu). "
                    "Transcribe the spoken words accurately into clean English text. "
                    "Return ONLY the transcribed text. Do not add notes, quotes, or explanations."
                )
            else:
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
            logger.error(f"Error in Gemini transcribe_voice: {e}")

    # Fallback: Google Speech Recognition with ffmpeg audio decoding
    fallback_text = _transcribe_with_speech_recognition(audio_bytes, preferred_lang=preferred_lang)
    if fallback_text:
        return fallback_text

    return None


async def analyze_citizen_query(user_text: str, conversation_history: list = None, lang: str = "te") -> Dict[str, Any]:
    """Answers conversational queries grounded strictly on the local government schemes dataset."""
    client = _get_gemini_client()

    # Match relevant schemes from local database for context & fallback
    matched_results = match_schemes(user_text)
    if not matched_results:
        found_direct = find_scheme_by_name_or_query(user_text)
        if found_direct:
            matched_results = [(found_direct, 10.0, "నేరుగా పేర్కొన్న పథకం" if lang == "te" else "Directly queried scheme")]

    # If still no match, inspect conversation history for recently discussed scheme
    if not matched_results and conversation_history:
        for turn in reversed(conversation_history):
            t_text = turn.get("text", "")
            s = find_scheme_by_name_or_query(t_text)
            if s:
                matched_results = [(s, 8.0, "మునుపటి సంభాషణలో చర్చించబడిన పథకం" if lang == "te" else "Scheme discussed in previous turns")]
                break

    # If Gemini is configured, use it grounded strictly on the dataset (without external search tools)
    if client:
        from google.genai import types

        matched_context = [
            {
                "id": m[0].get("id"),
                "name": m[0].get("name_en" if lang == "en" else "name_te"),
                "jurisdiction": m[0].get("jurisdiction"),
                "category": m[0].get("category" if lang == "en" else "category_te"),
                "benefits": m[0].get("benefits_en" if lang == "en" else "benefits_te"),
                "eligibility": m[0].get("eligibility_en" if lang == "en" else "eligibility_te"),
                "official_link": m[0].get("official_link"),
            }
            for m in matched_results[:5]
        ] if matched_results else []

        lang_instruction = (
            "LANGUAGE DIRECTIVE: The citizen prefers English. You MUST respond completely in clear, polite English (optionally mention Telugu scheme names in parentheses)."
            if lang == "en"
            else "LANGUAGE DIRECTIVE: The citizen prefers Telugu. You MUST respond primarily in natural, polite Telugu."
        )

        knowledge_context = (
            f"{lang_instruction}\n"
            f"Top matched schemes from dataset for this query:\n{json.dumps(matched_context, ensure_ascii=False, indent=2)}\n\n"
            "Ground your answer strictly on the authoritative dataset provided in the system instruction. "
            "Do NOT browse or search online. Follow the concise multi-scheme format if 2 or more schemes apply. "
            f"If user query is vague, ask 1 or 2 targeted {'English' if lang == 'en' else 'Telugu'} clarifying questions."
        )

        # Build multi-turn contents list
        contents: List[types.Content] = []
        if conversation_history:
            for turn in conversation_history[-8:]:  # keep last 8 turns (4 interactions)
                contents.append(types.Content(
                    role=turn.get("role", "user"),
                    parts=[types.Part.from_text(text=turn.get("text", ""))]
                ))

        # Current turn with context directive
        current_turn_text = f"{user_text}\n\n[Context: {knowledge_context}]"
        contents.append(types.Content(
            role="user",
            parts=[types.Part.from_text(text=current_turn_text)]
        ))

        sys_inst = SYSTEM_INSTRUCTION
        if lang == "en":
            sys_inst += (
                "\n\nCRITICAL LANGUAGE OVERRIDE: The citizen has chosen to communicate in English. "
                "You MUST provide all your responses, explanations, step-by-step guides, benefits, "
                "and clarifying questions strictly in English. You may mention the Telugu scheme names in parentheses."
            )

        for model_name in MODELS_TO_TRY:
            try:
                # Strictly local dataset grounding: NO tools=[google_search]
                gen_config = types.GenerateContentConfig(
                    system_instruction=sys_inst,
                )

                response = client.models.generate_content(
                    model=model_name,
                    contents=contents,
                    config=gen_config,
                )

                if response and response.text:
                    formatted_text = prepare_telegram_message(markdown_to_telegram_html(response.text))
                    gov_urls = extract_gov_urls(response.text, matched_results)

                    logger.info(f"Dataset-grounded conversational answer generated via {model_name}.")
                    return {
                        "mode": "dataset_ai",
                        "model": model_name,
                        "text": formatted_text,
                        "matched_schemes": matched_results,
                        "dynamic_urls": gov_urls,
                    }
            except Exception as e:
                logger.warning(f"Dataset query on {model_name} failed: {e}. Trying next model or fallback.")
                continue

    # 2. Rule-based intelligent fallback output if Gemini was unavailable or errored
    if not matched_results:
        if lang == "en":
            no_match_text = (
                "🙏 <b>Sahayam (సహాయం.ai)</b>\n\n"
                "Sorry, we could not find matching schemes in our dataset with the details provided.\n\n"
                "💡 <b>Tip:</b> Please tell us your occupation (farmer, student, woman, business), "
                "landholding (e.g. 2 acres), or the specific assistance you are looking for.\n\n"
                "<i>Example: 'I have 2 acres of land. I am a small farmer. What government schemes are available for me?'</i>"
            )
        else:
            no_match_text = (
                "🙏 <b>సహాయం (Sahayam.ai)</b>\n\n"
                "క్షమించండి, మీరు తెలిపిన వివరాలతో సరిపోయే పథకాలను మా డేటాసెట్‌లో గుర్తించలేకపోయాము.\n\n"
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

    if len(matched_results) > 1:
        formatted_response = format_multiple_schemes_summary(matched_results, lang=lang)
        return {
            "mode": "deterministic_summary",
            "text": prepare_telegram_message(formatted_response),
            "matched_schemes": matched_results,
            "dynamic_urls": [m[0]["official_link"] for m in matched_results[:2] if m[0].get("official_link")],
        }

    top_scheme, top_score, top_reason = matched_results[0]
    header = "🌾 <b>Sahayam (సహాయం.ai) - Scheme Details</b>\n\n" if lang == "en" else "🌾 <b>సహాయం (Sahayam.ai) - పథకం వివరాలు</b>\n\n"
    formatted_response = (
        header + format_scheme_detailed_telugu(top_scheme, top_reason, lang=lang)
    )
    return {
        "mode": "deterministic_detail",
        "text": prepare_telegram_message(formatted_response),
        "matched_schemes": matched_results,
        "dynamic_urls": [top_scheme["official_link"]] if top_scheme.get("official_link") else [],
    }
