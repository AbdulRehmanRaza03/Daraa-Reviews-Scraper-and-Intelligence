"""
cleaner.py
Turns raw scraped reviews into a clean pandas DataFrame ready for AI
analysis and Excel export. Never shortens/summarizes review text here —
only whitespace/format normalization.
"""

from datetime import datetime
from typing import List

import pandas as pd

from scraper import RawReview
from utils import get_logger, clean_whitespace, safe_float

logger = get_logger(__name__) 

DATE_FORMATS_TO_TRY = [
    "%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d", "%d %b %Y", "%d %B %Y",
    "%b %d, %Y", "%B %d, %Y", "%Y-%m-%dT%H:%M:%S", "%m/%d/%Y",
]


class DataCleaner:

    @staticmethod
    def clean(raw_reviews: List[RawReview]) -> pd.DataFrame:
        if not raw_reviews:
            return pd.DataFrame(columns=["reviewer_name", "rating", "review_text", "review_date"])

        rows = []
        for r in raw_reviews:
            text = clean_whitespace(r.review_text)
            if not text:
                continue  # drop empty reviews

            rows.append({
                "reviewer_name": clean_whitespace(r.reviewer_name) or "Anonymous",
                "rating": DataCleaner._normalize_rating(r.rating),
                "review_text": text,
                "review_date": DataCleaner._standardize_date(r.review_date),
            })

        if not rows:
            return pd.DataFrame(columns=["reviewer_name", "rating", "review_text", "review_date"])

        df = pd.DataFrame(rows)

        before = len(df)
        df = df.drop_duplicates(subset=["reviewer_name", "review_text"], keep="first")
        removed = before - len(df)
        if removed:
            logger.info("Removed %d duplicate review(s).", removed)

        df = df.reset_index(drop=True)
        return df

    @staticmethod
    def _normalize_rating(rating) -> float:
        value = safe_float(rating, default=0.0)
        if value > 5:  # some APIs return 0-100 scale
            value = round(value / 20, 1)
        return max(0.0, min(5.0, round(value, 1)))

    @staticmethod
    def _standardize_date(raw_date: str) -> str:
        """Returns YYYY-MM-DD where parseable, otherwise the original cleaned string."""
        if not raw_date:
            return ""
        raw_date = clean_whitespace(str(raw_date))

        # epoch millis (some Daraz APIs return createTime as a timestamp)
        if raw_date.isdigit() and len(raw_date) >= 10:
            try:
                ts = int(raw_date)
                if ts > 10**12:  # milliseconds
                    ts //= 1000
                return datetime.utcfromtimestamp(ts).strftime("%Y-%m-%d")
            except (ValueError, OSError):
                pass

        for fmt in DATE_FORMATS_TO_TRY:
            try:
                return datetime.strptime(raw_date, fmt).strftime("%Y-%m-%d")
            except ValueError:
                continue

        return raw_date  # keep original rather than discard information
