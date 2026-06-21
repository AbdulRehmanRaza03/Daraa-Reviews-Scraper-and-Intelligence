"""
utils.py
Shared helpers used by scraper, cleaner, ai_analyzer, dashboard.
"""

import logging
import re
from urllib.parse import urlparse

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def is_valid_daraz_url(url: str) -> bool:
    """Basic structural validation for a Daraz product URL."""
    if not url or not isinstance(url, str):
        return False
    url = url.strip()
    try:
        parsed = urlparse(url)
    except ValueError:
        return False
    if parsed.scheme not in ("http", "https"):
        return False
    if not parsed.netloc:
        return False
    return "daraz." in parsed.netloc.lower()


def clean_whitespace(text: str) -> str:
    """Collapse repeated whitespace/newlines, strip ends. Keeps full sentence content."""
    if not text:
        return ""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def truncate_for_display(text: str, length: int = 160) -> str:
    """UI-only truncation. Never use this on data going to Excel or AI analysis."""
    if not text:
        return ""
    return text if len(text) <= length else text[: length - 1].rstrip() + "…"


def safe_float(value, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def basic_keyword_sentiment(text: str, rating: float = None) -> str:
    """
    Lightweight fallback sentiment classifier (no AI key configured / AI call failed).
    Rating-led when available, keyword-led otherwise. Not a replacement for AI analysis.
    """
    if rating is not None:
        if rating >= 4:
            return "Positive"
        if rating <= 2:
            return "Negative"
        return "Neutral"

    if not text:
        return "Neutral"

    text_lower = text.lower()
    positive_words = [
        "good", "great", "excellent", "love", "amazing", "perfect", "best",
        "recommend", "nice", "awesome", "worth", "satisfied", "fast delivery",
        "original", "genuine", "quality",
    ]
    negative_words = [
        "bad", "worst", "poor", "terrible", "fake", "broken", "damaged",
        "late", "slow", "waste", "disappointed", "defective", "cheap quality",
        "not working", "refund", "scam",
    ]
    pos_score = sum(1 for w in positive_words if w in text_lower)
    neg_score = sum(1 for w in negative_words if w in text_lower)

    if pos_score > neg_score:
        return "Positive"
    if neg_score > pos_score:
        return "Negative"
    return "Neutral"


def percentage(part: int, whole: int) -> float:
    if whole == 0:
        return 0.0
    return round((part / whole) * 100, 1)
