"""
config.py
Central config. Loads .env, exposes settings used across modules.
"""

import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # ---- AI Provider ----
    # one of: "openai", "gemini", "grok"
    AI_PROVIDER = os.getenv("AI_PROVIDER", "openai").lower()

    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

    GROK_API_KEY = os.getenv("GROK_API_KEY", "")
    GROK_MODEL = os.getenv("GROK_MODEL", "grok-2-latest")
    GROK_BASE_URL = os.getenv("GROK_BASE_URL", "https://api.x.ai/v1")

    # ---- Scraper ----
    REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "20"))
    MAX_REVIEW_PAGES = int(os.getenv("MAX_REVIEW_PAGES", "10"))
    SCRAPE_DELAY_SECONDS = float(os.getenv("SCRAPE_DELAY_SECONDS", "1.5"))
    USE_PLAYWRIGHT_FALLBACK = os.getenv("USE_PLAYWRIGHT_FALLBACK", "true").lower() == "true"

    USER_AGENT = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )

    # ---- App ----
    APP_TITLE = "AI Product Review Intelligence Dashboard"
    APP_ICON = "🛍️"
    EXCEL_FILENAME = "Product_Review_Analysis_Report.xlsx"
    MAX_REVIEWS_FOR_AI = int(os.getenv("MAX_REVIEWS_FOR_AI", "150"))  # cap sent to AI per call to control cost

    @classmethod
    def active_ai_key_present(cls) -> bool:
        if cls.AI_PROVIDER == "openai":
            return bool(cls.OPENAI_API_KEY)
        if cls.AI_PROVIDER == "gemini":
            return bool(cls.GEMINI_API_KEY)
        if cls.AI_PROVIDER == "grok":
            return bool(cls.GROK_API_KEY)
        return False
