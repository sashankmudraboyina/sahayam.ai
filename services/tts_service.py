"""Text-to-Speech (TTS) service for generating Telugu voice responses."""

import io
import logging
import re
from typing import Optional

from services.html_sanitizer import strip_html_tags

logger = logging.getLogger("telegram_bot.tts")


def prepare_text_for_speech(text: str, max_chars: int = 700) -> str:
    """Prepares text for natural, pleasant speech by removing HTML, URLs, and formatting markers."""
    clean = strip_html_tags(text)
    # Remove web URLs so the TTS engine doesn't read out raw letters
    clean = re.sub(r"https?://\S+", "", clean)
    # Remove decorative/bullet characters
    clean = re.sub(r"[•\*\#\=\-\_]", " ", clean)
    # Collapse multiple whitespace
    clean = re.sub(r"\s+", " ", clean).strip()

    if len(clean) > max_chars:
        cut = clean[:max_chars]
        last_punct = max(cut.rfind("."), cut.rfind("।"), cut.rfind("!"), cut.rfind("?"))
        if last_punct > max_chars // 2:
            clean = cut[:last_punct + 1]
        else:
            clean = cut + "..."

    return clean


async def generate_telugu_speech(text: str) -> Optional[bytes]:
    """Synthesizes Telugu speech audio (MP3 format) using edge-tts with gTTS fallback."""
    speech_text = prepare_text_for_speech(text)
    if not speech_text:
        return None

    # 1. Primary: edge-tts (High quality neural Telugu voice)
    try:
        import edge_tts
        communicate = edge_tts.Communicate(speech_text, voice="te-IN-MohanNeural")
        audio_data = b""
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_data += chunk["data"]
        if audio_data:
            logger.info(f"Generated {len(audio_data)} bytes of neural Telugu speech via edge-tts.")
            return audio_data
    except Exception as e:
        logger.warning(f"edge-tts synthesis failed: {e}. Falling back to gTTS.")

    # 2. Fallback: gTTS (Google Translate Telugu TTS)
    try:
        from gtts import gTTS
        fp = io.BytesIO()
        tts = gTTS(text=speech_text, lang="te")
        tts.write_to_fp(fp)
        data = fp.getvalue()
        logger.info(f"Generated {len(data)} bytes of Telugu speech via gTTS fallback.")
        return data
    except Exception as e:
        logger.error(f"gTTS fallback synthesis failed: {e}")
        return None
