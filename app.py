"""
app.py
Entry point. Run with: streamlit run app.py
"""

import time

import streamlit as st

import dashboard
from ai_analyzer import AIAnalyzer
from cleaner import DataCleaner
from config import Config
from excel_exporter import ExcelExporter
from scraper import DarazScraper, ScraperError
from utils import get_logger

logger = get_logger(__name__) 

st.set_page_config(
    page_title=Config.APP_TITLE,
    page_icon=Config.APP_ICON,
    layout="wide",
    initial_sidebar_state="collapsed",
)

dashboard.inject_css()

if "result_data" not in st.session_state:
    st.session_state.result_data = None  # holds (scrape_result, clean_df, analysis)
if "last_error" not in st.session_state:
    st.session_state.last_error = None


def run_pipeline(url: str, status_placeholder):
    """Runs scrape -> clean -> analyze, updating the loading UI at each stage."""
    dashboard.render_stage(status_placeholder, "🌐", "Validating product link...", 0.1)
    time.sleep(0.3)

    dashboard.render_stage(status_placeholder, "🕷️", "Scraping reviews from Daraz...", 0.35)
    scraper = DarazScraper()
    scrape_result = scraper.scrape(url)  # raises ScraperError on failure

    dashboard.render_stage(status_placeholder, "🧹", "Cleaning and de-duplicating review data...", 0.6)
    clean_df = DataCleaner.clean(scrape_result.reviews)
    if clean_df.empty:
        raise ScraperError("Reviews were found but none contained usable text after cleaning.")

    dashboard.render_stage(status_placeholder, "🤖", "Running AI sentiment & verdict analysis...", 0.85)
    analyzer = AIAnalyzer()
    analysis = analyzer.analyze(clean_df, scrape_result.product_name)

    dashboard.render_stage(status_placeholder, "📊", "Building your dashboard...", 1.0)
    time.sleep(0.3)

    return scrape_result, clean_df, analysis


def render_results(scrape_result, clean_df, analysis):
    dashboard.product_header(scrape_result)
    st.write("")

    avg_rating = clean_df["rating"].mean() if not clean_df.empty else 0.0
    dashboard.metric_tiles(
        total_reviews=len(clean_df),
        avg_rating=avg_rating,
        positive_pct=analysis.positive_pct,
        neutral_pct=analysis.neutral_pct,
        negative_pct=analysis.negative_pct,
    )
    st.write("")

    col_score, col_donut, col_dist = st.columns([1, 1, 1])
    with col_score:
        dashboard.score_and_verdict(analysis)
    with col_donut:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown('<div class="metric-label">Sentiment Split</div>', unsafe_allow_html=True)
        dashboard.sentiment_donut(analysis.positive_pct, analysis.neutral_pct, analysis.negative_pct)
        st.markdown("</div>", unsafe_allow_html=True)
    with col_dist:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown('<div class="metric-label">Rating Distribution</div>', unsafe_allow_html=True)
        dashboard.rating_distribution_chart(clean_df)
        st.markdown("</div>", unsafe_allow_html=True)

    st.write("")
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    dashboard.insights_section(analysis)
    st.markdown("</div>", unsafe_allow_html=True)

    dashboard.recommendation_card(analysis)

    excel_bytes = ExcelExporter.build_report(clean_df, scrape_result.product_name, analysis)
    st.download_button(
        label="⬇️ Download Excel Report",
        data=excel_bytes,
        file_name=Config.EXCEL_FILENAME,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=False,
    )

    st.write("")
    with st.expander("📝 View sample reviews"):
        dashboard.review_sample_table(clean_df)


def main():
    dashboard.hero_section()
    url, analyze_clicked = dashboard.url_input_section()

    if not Config.active_ai_key_present():
        st.warning(
            f"⚠️ No AI API key found for provider **{Config.AI_PROVIDER}**. "
            "The dashboard will still run using a basic rating-based fallback analysis. "
            "Add a key to `.env` for full AI-powered insights.",
            icon="⚠️",
        )

    status_placeholder = st.empty()

    if analyze_clicked:
        if not url.strip():
            dashboard.error_banner("Please paste a Daraz product URL first.")
        else:
            try:
                scrape_result, clean_df, analysis = run_pipeline(url.strip(), status_placeholder)
                status_placeholder.empty()
                st.session_state.result_data = (scrape_result, clean_df, analysis)
                st.session_state.last_error = None
            except ScraperError as exc:
                status_placeholder.empty()
                st.session_state.result_data = None
                st.session_state.last_error = str(exc)
            except Exception as exc:  # noqa: BLE001 - catch-all so the UI never hard-crashes
                logger.exception("Unexpected pipeline failure")
                status_placeholder.empty()
                st.session_state.result_data = None
                st.session_state.last_error = (
                    f"Something went wrong while processing this product: {exc}"
                )

    if st.session_state.last_error:
        dashboard.error_banner(st.session_state.last_error)

    if st.session_state.result_data:
        render_results(*st.session_state.result_data)
    elif not st.session_state.last_error:
        dashboard.empty_state()


if __name__ == "__main__":
    main()
