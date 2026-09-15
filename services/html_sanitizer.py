"""HTML Sanitizer and tag balancer for Telegram message rendering."""

import html
import re

ALLOWED_TELEGRAM_TAGS = {
    "b", "strong", "i", "em", "u", "s", "strike", "del", "a", "code", "pre", "blockquote"
}


def clean_telegram_html(text: str) -> str:
    """Sanitizes text by converting unsupported HTML tags and escaping reserved characters."""
    if not text:
        return ""

    # 1. Convert headers (h1-h6) into bold text with line breaks
    text = re.sub(r"<h[1-6][^>]*>(.*?)</h[1-6]>", r"<b>\1</b>\n\n", text, flags=re.IGNORECASE | re.DOTALL)

    # 2. Convert standard block tags to newlines
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</p\s*>", "\n\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<p\s*>", "", text, flags=re.IGNORECASE)
    text = re.sub(r"<li\s*>", "• ", text, flags=re.IGNORECASE)
    text = re.sub(r"</li\s*>", "\n", text, flags=re.IGNORECASE)

    # 3. Strip any tags not supported by Telegram
    def tag_replacer(match: re.Match) -> str:
        tag_content = match.group(0)
        tag_name_match = re.match(r"</?([a-zA-Z0-9]+)", tag_content)
        if tag_name_match:
            tag_name = tag_name_match.group(1).lower()
            if tag_name in ALLOWED_TELEGRAM_TAGS:
                return tag_content
        return ""

    text = re.sub(r"<[^>]+>", tag_replacer, text)

    # 4. Escape naked ampersands that are not part of an existing valid entity
    text = re.sub(r"&(?!(?:amp|lt|gt|quot|apos);)", "&amp;", text)

    # 5. Collapse excessive whitespace / newlines
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def balance_telegram_tags(text: str) -> str:
    """Ensures all opened Telegram tags have matching closing tags in correct order."""
    if not text:
        return ""

    stack = []
    for match in re.finditer(r"<(/)?([a-zA-Z0-9]+)(?:\s+[^>]*)?>", text):
        is_closing = bool(match.group(1))
        tag_name = match.group(2).lower()
        if tag_name in ALLOWED_TELEGRAM_TAGS:
            if not is_closing:
                stack.append(tag_name)
            else:
                if stack and stack[-1] == tag_name:
                    stack.pop()
                elif tag_name in stack:
                    stack.remove(tag_name)

    # Append any remaining unclosed tags
    for tag in reversed(stack):
        text += f"</{tag}>"
    return text


def strip_html_tags(text: str) -> str:
    """Removes all HTML tags and unescapes entities for clean plain-text fallback."""
    if not text:
        return ""
    clean = re.sub(r"<[^>]+>", "", text)
    return html.unescape(clean).strip()


def prepare_telegram_message(text: str) -> str:
    """Full pipeline: cleans, formats, balances, and truncates text for Telegram."""
    cleaned = clean_telegram_html(text)
    balanced = balance_telegram_tags(cleaned)

    # Truncate to Telegram's 4096 limit safely
    if len(balanced) > 4000:
        balanced = balanced[:3990] + "..."
        balanced = balance_telegram_tags(balanced)

    return balanced
