"""
scraper.py
Scrapes publicly visible review data from a Daraz product page.

Strategy (in order):
  1. Parse product page HTML for embedded JSON state (Daraz SSR pages often
     ship a window.pdpData / __INITIAL_STATE__ blob with itemId/sellerId).
  2. Call Daraz's public review-list API with the extracted itemId, paginating
     through all pages.
  3. If steps 1-2 fail (markup changed, JS-only render, region variant, bot
     wall), fall back to Playwright: load the page, click "Ratings & Reviews",
     scroll/click "Next" through pages, and scrape the rendered DOM directly.

NOTE: Daraz frequently changes DOM structure, API paths, and bot-detection
rules across regions (.pk / .com.bd / .lk / etc). The CSS selectors and the
review-API path below are current best-effort patterns — if Daraz ships a
markup change, update SELECTORS / REVIEW_API_PATH below. This is a normal
maintenance reality of any scraper, not a bug in the pipeline.

Only publicly visible page/API content is read. No login, no private
endpoints, no personal contact info is collected — review text, star
rating, display name, and date only.
"""

import json
import re
import time
from dataclasses import dataclass, field
from typing import List, Optional

import requests
from bs4 import BeautifulSoup

from config import Config
from utils import get_logger, is_valid_daraz_url, clean_whitespace

logger = get_logger(__name__)


class ScraperError(Exception):
    """Raised for any user-facing scraping failure (invalid URL, no reviews, network error)."""


@dataclass
class RawReview:
    reviewer_name: str = "Anonymous"
    rating: Optional[float] = None
    review_text: str = ""
    review_date: str = ""


@dataclass
class ScrapeResult:
    product_name: str = "Unknown Product"
    product_image_url: str = ""
    product_url: str = ""
    reviews: List[RawReview] = field(default_factory=list)
    pages_scraped: int = 0
    method_used: str = ""


class DarazScraper:

    REVIEW_API_PATH_TEMPLATES = [
        # Common Daraz review-list endpoint shape (varies slightly by region/tenant).
        "https://{host}/pdp/review/list?itemId={item_id}&pageSize=20&filter=0&sort=0&pageNum={page}",
        "https://{host}/pdp/review/getReviewList?itemId={item_id}&pageSize=20&pageNum={page}",
    ]

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": Config.USER_AGENT,
            "Accept-Language": "en-US,en;q=0.9",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        })

    # ---------- public entry point ----------

    def scrape(self, product_url: str) -> ScrapeResult:
        product_url = (product_url or "").strip()
        if not is_valid_daraz_url(product_url):
            raise ScraperError(
                "That doesn't look like a valid Daraz product URL. "
                "Paste a full link like https://www.daraz.pk/products/....html"
            )

        try:
            html = self._fetch_html(product_url)
        except requests.exceptions.RequestException as exc:
            logger.warning("Initial HTML fetch failed: %s", exc)
            html = None

        if html:
            try:
                result = self._scrape_via_api(product_url, html)
                if result and result.reviews:
                    return result
            except Exception as exc:  # noqa: BLE001 - any parsing failure -> try fallback
                logger.warning("API-based scrape failed, falling back: %s", exc)

        if Config.USE_PLAYWRIGHT_FALLBACK:
            try:
                result = self._scrape_via_playwright(product_url)
                if result and result.reviews:
                    return result
            except Exception as exc:  # noqa: BLE001
                logger.error("Playwright fallback failed: %s", exc)
                raise ScraperError(
                    "Could not load reviews for this product. Daraz may be blocking "
                    "automated access right now, or this product genuinely has no "
                    "reviews yet. Try again in a moment or test with another product."
                ) from exc

        raise ScraperError(
            "No reviews could be found for this product. It may have zero reviews, "
            "or Daraz's page structure has changed (scraper selectors need an update)."
        )

    # ---------- strategy 1: HTML + review API ----------

    def _fetch_html(self, url: str) -> str:
        resp = self.session.get(url, timeout=Config.REQUEST_TIMEOUT)
        resp.raise_for_status()
        return resp.text

    def _extract_product_meta(self, html: str) -> dict:
        """Pull product name, image, and itemId out of the SSR HTML payload."""
        soup = BeautifulSoup(html, "html.parser")
        meta = {"name": "Unknown Product", "image": "", "item_id": None}

        og_title = soup.find("meta", property="og:title")
        if og_title and og_title.get("content"):
            meta["name"] = clean_whitespace(og_title["content"])

        og_image = soup.find("meta", property="og:image")
        if og_image and og_image.get("content"):
            meta["image"] = og_image["content"]

        # Daraz SSR pages typically embed a JSON blob containing "itemId":NNNN
        item_id_match = re.search(r'"itemId"\s*:\s*"?(\d+)"?', html)
        if item_id_match:
            meta["item_id"] = item_id_match.group(1)

        return meta

    def _scrape_via_api(self, product_url: str, html: str) -> Optional[ScrapeResult]:
        meta = self._extract_product_meta(html)
        if not meta["item_id"]:
            logger.info("No itemId found in page HTML; cannot use review API strategy.")
            return None

        host = re.sub(r"^https?://", "", product_url).split("/")[0]
        host = host.replace("www.", "")
        api_host_candidates = [f"{host}", f"www.{host}"]

        all_reviews: List[RawReview] = []
        pages_scraped = 0

        for page in range(1, Config.MAX_REVIEW_PAGES + 1):
            page_reviews = self._fetch_review_page(api_host_candidates, meta["item_id"], page)
            if page_reviews is None:
                break
            if not page_reviews:
                break
            all_reviews.extend(page_reviews)
            pages_scraped += 1
            time.sleep(Config.SCRAPE_DELAY_SECONDS)

        if not all_reviews:
            return None

        return ScrapeResult(
            product_name=meta["name"],
            product_image_url=meta["image"],
            product_url=product_url,
            reviews=all_reviews,
            pages_scraped=pages_scraped,
            method_used="http_api",
        )

    def _fetch_review_page(self, hosts: list, item_id: str, page: int) -> Optional[List[RawReview]]:
        for host in hosts:
            for template in self.REVIEW_API_PATH_TEMPLATES:
                url = template.format(host=host, item_id=item_id, page=page)
                try:
                    resp = self.session.get(url, timeout=Config.REQUEST_TIMEOUT)
                    if resp.status_code != 200:
                        continue
                    data = resp.json()
                except (requests.exceptions.RequestException, ValueError):
                    continue

                items = self._extract_review_items(data)
                if items is not None:
                    return [self._parse_api_review(item) for item in items]
        return None

    @staticmethod
    def _extract_review_items(data: dict) -> Optional[list]:
        """Daraz API response shapes vary by tenant; check the common keys."""
        if not isinstance(data, dict):
            return None
        for path in (
            ("model", "items"),
            ("data", "items"),
            ("items",),
            ("model", "ratings"),
        ):
            node = data
            ok = True
            for key in path:
                if isinstance(node, dict) and key in node:
                    node = node[key]
                else:
                    ok = False
                    break
            if ok and isinstance(node, list):
                return node
        return None

    @staticmethod
    def _parse_api_review(item: dict) -> RawReview:
        return RawReview(
            reviewer_name=item.get("buyerName") or item.get("userName") or "Anonymous",
            rating=item.get("rating") or item.get("ratingScore"),
            review_text=clean_whitespace(item.get("reviewContent") or item.get("comment") or ""),
            review_date=item.get("reviewTime") or item.get("createTime") or "",
        )

    # ---------- strategy 2: Playwright rendered DOM ----------

    def _scrape_via_playwright(self, product_url: str) -> ScrapeResult:
        from playwright.sync_api import sync_playwright  # local import: optional dependency

        reviews: List[RawReview] = []
        product_name = "Unknown Product"
        product_image = ""

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(user_agent=Config.USER_AGENT)
            try:
                page.goto(product_url, timeout=Config.REQUEST_TIMEOUT * 1000, wait_until="domcontentloaded")
                page.wait_for_timeout(2000)

                title_el = page.query_selector("meta[property='og:title']")
                if title_el:
                    product_name = clean_whitespace(title_el.get_attribute("content") or product_name)

                image_el = page.query_selector("meta[property='og:image']")
                if image_el:
                    product_image = image_el.get_attribute("content") or ""

                review_tab = page.query_selector("text=Ratings & Reviews") or page.query_selector("a[href*='review']")
                if review_tab:
                    review_tab.click()
                    page.wait_for_timeout(1500)

                for current_page in range(1, Config.MAX_REVIEW_PAGES + 1):
                    page.wait_for_timeout(1000)
                    cards = page.query_selector_all("[class*='item-content'], [class*='mod-reviews'] [class*='item']")
                    if not cards:
                        break

                    for card in cards:
                        text_el = card.query_selector("[class*='content']")
                        rating_el = card.query_selector("[class*='star']")
                        name_el = card.query_selector("[class*='name']")
                        date_el = card.query_selector("[class*='date']")

                        review_text = clean_whitespace(text_el.inner_text()) if text_el else ""
                        if not review_text:
                            continue

                        reviews.append(RawReview(
                            reviewer_name=clean_whitespace(name_el.inner_text()) if name_el else "Anonymous",
                            rating=self._stars_from_class(rating_el) if rating_el else None,
                            review_text=review_text,
                            review_date=clean_whitespace(date_el.inner_text()) if date_el else "",
                        ))

                    next_btn = page.query_selector("button[class*='next']:not([disabled])")
                    if not next_btn:
                        break
                    next_btn.click()
                    page.wait_for_timeout(Config.SCRAPE_DELAY_SECONDS * 1000)

            finally:
                browser.close()

        if not reviews:
            raise ScraperError("No reviews found in the rendered page.")

        return ScrapeResult(
            product_name=product_name,
            product_image_url=product_image,
            product_url=product_url,
            reviews=reviews,
            pages_scraped=1,
            method_used="playwright",
        )

    @staticmethod
    def _stars_from_class(rating_el) -> Optional[float]:
        """Some Daraz themes encode the star count in a class name like 'star-4'."""
        try:
            class_attr = rating_el.get_attribute("class") or ""
            match = re.search(r"star-?(\d)", class_attr)
            if match:
                return float(match.group(1))
        except Exception:  # noqa: BLE001
            pass
        return None
