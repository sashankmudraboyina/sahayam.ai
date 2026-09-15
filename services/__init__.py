"""Services package for NLP matching, AI generation, HTML sanitization, and TTS."""
from services.matcher import extract_entities, format_scheme_detailed_telugu, match_schemes
from services.ai_engine import analyze_citizen_query, transcribe_voice
from services.html_sanitizer import (
    clean_telegram_html,
    balance_telegram_tags,
    strip_html_tags,
    prepare_telegram_message,
    split_telegram_message,
)
from services.tts_service import generate_telugu_speech, prepare_text_for_speech

__all__ = [
    "extract_entities",
    "match_schemes",
    "format_scheme_detailed_telugu",
    "analyze_citizen_query",
    "transcribe_voice",
    "clean_telegram_html",
    "balance_telegram_tags",
    "strip_html_tags",
    "prepare_telegram_message",
    "split_telegram_message",
    "generate_telugu_speech",
    "prepare_text_for_speech",
]
