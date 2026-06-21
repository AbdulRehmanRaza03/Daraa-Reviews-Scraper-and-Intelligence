"""
ai_analyzer.py
Sends cleaned review data to an AI provider (OpenAI / Gemini / Grok — pick
one via AI_PROVIDER in .env) and gets back a structured verdict: overall
score, sentiment split, strengths, complaints, and a buy recommendation.

Per-review "Sentiment Label" (used in the Excel export) is derived
deterministically from each review's star rating rather than one AI call
per row — sending hundreds of individual review-classification calls would
be slow and expensive. The AI call instead reads a representative sample of
full review text to produce the qualitative verdict (score, strengths,
complaints, recommendation) and the aggregate sentiment split. This keeps
cost predictable on large review sets while still being grounded in real
customer language.

If no API key is configured, or the AI call fails for any reason (timeout,
quota, malformed response), the analyzer falls back to a transparent
rating/keyword-based heuristic so the dashboard never breaks.
"""

import json
from dataclasses import dataclass, field
from typing import List

import pandas as pd

from config import Config
from utils import get_logger, basic_keyword_sentiment, percentage

logger = get_logger(__name__)


@dataclass
class AnalysisResult:
    overall_score: float = 0.0
    verdict: str = "Average Product"
    positive_pct: float = 0.0
    neutral_pct: float = 0.0
    negative_pct: float = 0.0
    strengths: List[str] = field(default_factory=list)
    complaints: List[str] = field(default_factory=list)
    recommendation: str = ""
    ai_provider_used: str = "none"
    used_fallback: bool = False
    fallback_reason: str = ""


VERDICT_OPTIONS = ["Winning Product", "Good Product", "Average Product", "Not Recommended"]

SYSTEM_PROMPT = (
    "You are an e-commerce customer-review analyst. You will be given a product "
    "name and a sample of real customer reviews with their star ratings. "
    "Respond ONLY with a single valid JSON object — no markdown, no commentary, "
    "no code fences. The JSON object must have exactly these keys: "
    '"overall_score" (number 0-10), '
    '"verdict" (one of: "Winning Product", "Good Product", "Average Product", "Not Recommended"), '
    '"positive_pct" (number 0-100), "neutral_pct" (number 0-100), "negative_pct" (number 0-100) '
    "(these three must sum to 100), "
    '"strengths" (array of up to 5 short strings, what customers like), '
    '"complaints" (array of up to 5 short strings, common problems — empty array if none found), '
    '"recommendation" (2-4 sentence buy/no-buy explanation grounded in the review evidence).'
)


class AIAnalyzer:

    def __init__(self):
        self.provider = Config.AI_PROVIDER

    # ---------- public entry point ----------

    def analyze(self, df: pd.DataFrame, product_name: str) -> AnalysisResult:
        if df.empty:
            return AnalysisResult(
                used_fallback=True,
                fallback_reason="No cleaned reviews available to analyze.",
            )

        if not Config.active_ai_key_present():
            return self._fallback_analysis(df, reason=f"No API key configured for provider '{self.provider}'.")

        prompt = self._build_prompt(df, product_name)

        try:
            if self.provider == "openai":
                raw_response = self._call_openai(prompt)
            elif self.provider == "gemini":
                raw_response = self._call_gemini(prompt)
            elif self.provider == "grok":
                raw_response = self._call_grok(prompt)
            else:
                return self._fallback_analysis(df, reason=f"Unknown AI_PROVIDER '{self.provider}'.")

            parsed = self._parse_json_response(raw_response)
            return self._build_result_from_ai(parsed)

        except Exception as exc:  # noqa: BLE001 - any provider/parse failure -> safe fallback
            logger.error("AI analysis failed (%s): %s", self.provider, exc)
            return self._fallback_analysis(df, reason=f"AI request failed: {exc}")

    # ---------- prompt building ----------

    @staticmethod
    def _build_prompt(df: pd.DataFrame, product_name: str) -> str:
        sample = df
        if len(df) > Config.MAX_REVIEWS_FOR_AI:
            sample = df.sample(n=Config.MAX_REVIEWS_FOR_AI, random_state=42)

        lines = [f"Product: {product_name}", f"Total reviews collected: {len(df)}", "", "Sample reviews:"]
        for _, row in sample.iterrows():
            lines.append(f"- Rating: {row['rating']}/5 | Review: {row['review_text']}")

        return "\n".join(lines)

    # ---------- provider calls ----------

    @staticmethod
    def _call_openai(prompt: str) -> str:
        from openai import OpenAI

        client = OpenAI(api_key=Config.OPENAI_API_KEY)
        response = client.chat.completions.create(
            model=Config.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            response_format={"type": "json_object"},
        )
        return response.choices[0].message.content

    @staticmethod
    def _call_gemini(prompt: str) -> str:
        import google.generativeai as genai

        genai.configure(api_key=Config.GEMINI_API_KEY)
        model = genai.GenerativeModel(
            Config.GEMINI_MODEL,
            system_instruction=SYSTEM_PROMPT,
            generation_config={"response_mime_type": "application/json"},
        )
        response = model.generate_content(prompt)
        return response.text

    @staticmethod
    def _call_grok(prompt: str) -> str:
        # Grok's API is OpenAI-compatible, so the openai SDK works with a custom base_url.
        from openai import OpenAI

        client = OpenAI(api_key=Config.GROK_API_KEY, base_url=Config.GROK_BASE_URL)
        response = client.chat.completions.create(
            model=Config.GROK_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
        )
        return response.choices[0].message.content

    # ---------- response handling ----------

    @staticmethod
    def _parse_json_response(raw_response: str) -> dict:
        text = (raw_response or "").strip()
        # Strip accidental code fences if a model ignores the "no markdown" instruction.
        if text.startswith("```"):
            text = text.strip("`")
            text = text.replace("json\n", "", 1).replace("json\r\n", "", 1)
        return json.loads(text)

    def _build_result_from_ai(self, parsed: dict) -> AnalysisResult:
        verdict = parsed.get("verdict", "Average Product")
        if verdict not in VERDICT_OPTIONS:
            verdict = "Average Product"

        pos = float(parsed.get("positive_pct", 0) or 0)
        neu = float(parsed.get("neutral_pct", 0) or 0)
        neg = float(parsed.get("negative_pct", 0) or 0)
        total = pos + neu + neg
        if total > 0 and abs(total - 100) > 1.5:
            pos, neu, neg = (pos / total * 100, neu / total * 100, neg / total * 100)

        return AnalysisResult(
            overall_score=round(float(parsed.get("overall_score", 0) or 0), 1),
            verdict=verdict,
            positive_pct=round(pos, 1),
            neutral_pct=round(neu, 1),
            negative_pct=round(neg, 1),
            strengths=list(parsed.get("strengths", []))[:5],
            complaints=list(parsed.get("complaints", []))[:5],
            recommendation=parsed.get("recommendation", ""),
            ai_provider_used=self.provider,
            used_fallback=False,
        )

    # ---------- fallback (no key / AI failure) ----------

    @staticmethod
    def _fallback_analysis(df: pd.DataFrame, reason: str) -> AnalysisResult:
        logger.warning("Using fallback heuristic analysis: %s", reason)

        labels = [
            basic_keyword_sentiment(row["review_text"], row["rating"])
            for _, row in df.iterrows()
        ]
        total = len(labels)
        pos = labels.count("Positive")
        neu = labels.count("Neutral")
        neg = labels.count("Negative")

        avg_rating = df["rating"].mean() if "rating" in df.columns and not df.empty else 0
        score = round(avg_rating * 2, 1)  # map 0-5 stars to 0-10 score

        if score >= 8:
            verdict = "Winning Product"
        elif score >= 6.5:
            verdict = "Good Product"
        elif score >= 4.5:
            verdict = "Average Product"
        else:
            verdict = "Not Recommended"

        recommendation = (
            f"Based on {total} review(s) with an average rating of {avg_rating:.1f}/5, "
            f"this is a basic rating-based estimate (AI analysis was unavailable: {reason}). "
            "Configure a valid AI API key in .env for deeper, language-based insights."
        )

        return AnalysisResult(
            overall_score=score,
            verdict=verdict,
            positive_pct=percentage(pos, total),
            neutral_pct=percentage(neu, total),
            negative_pct=percentage(neg, total),
            strengths=[],
            complaints=[],
            recommendation=recommendation,
            ai_provider_used="fallback_heuristic",
            used_fallback=True,
            fallback_reason=reason,
        )
