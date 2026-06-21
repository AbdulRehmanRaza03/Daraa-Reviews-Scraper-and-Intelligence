"""
dashboard.py
All visual/UI building blocks for app.py. Keeps app.py focused on pipeline
orchestration instead of markup.

Design direction: a "mission control" intelligence console — deep navy
base, violet→cyan signal gradient (the AI "scanning" the product), glass
panels with a soft inner border. Headline type is Space Grotesk (technical,
slightly unusual display face); body is Inter.
"""

import streamlit as st
import plotly.graph_objects as go

from ai_analyzer import AnalysisResult
from scraper import ScrapeResult
from utils import truncate_for_display


def inject_css():
    st.markdown(
        """
        <link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
        <style>
        :root {
            --bg-navy: #0F1629;
            --bg-navy-light: #161F38;
            --accent-violet: #7C5CFC;
            --accent-cyan: #34D9D4;
            --text-light: #E7E9F3;
            --text-dim: #9099B8;
            --positive: #2ECC71;
            --neutral: #F4C744;
            --negative: #FF5C7A;
            --glass-border: rgba(255,255,255,0.08);
        }

        html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

        .stApp {
            background: radial-gradient(circle at 15% 0%, #1A2245 0%, var(--bg-navy) 45%, #0A0F1F 100%);
            color: var(--text-light);
        }

        h1, h2, h3, .hero-title { font-family: 'Space Grotesk', sans-serif !important; }

        /* ---- Hero ---- */
        .hero-wrap { padding: 2.2rem 0 1.2rem 0; text-align: center; }
        .hero-eyebrow {
            display: inline-block; font-size: 0.78rem; letter-spacing: 0.14em;
            color: var(--accent-cyan); text-transform: uppercase; font-weight: 600;
            border: 1px solid var(--glass-border); border-radius: 999px;
            padding: 0.32rem 0.9rem; margin-bottom: 1rem; background: rgba(124,92,252,0.08);
        }
        .hero-title {
            font-size: 2.6rem; font-weight: 700; line-height: 1.15; margin: 0 auto 0.7rem auto;
            max-width: 800px;
            background: linear-gradient(100deg, #F2F3FA 30%, var(--accent-cyan) 70%, var(--accent-violet) 100%);
            -webkit-background-clip: text; background-clip: text; -webkit-text-fill-color: transparent;
        }
        .hero-sub { color: var(--text-dim); font-size: 1.02rem; max-width: 560px; margin: 0 auto; }

        /* ---- Glass panel ---- */
        .glass-card {
            background: linear-gradient(160deg, rgba(255,255,255,0.05), rgba(255,255,255,0.02));
            border: 1px solid var(--glass-border);
            border-radius: 18px;
            padding: 1.4rem 1.6rem;
            backdrop-filter: blur(14px);
            box-shadow: 0 8px 30px rgba(0,0,0,0.25);
            margin-bottom: 1rem;
        }

        /* ---- Metric tiles ---- */
        .metric-tile {
            background: linear-gradient(160deg, rgba(255,255,255,0.06), rgba(255,255,255,0.015));
            border: 1px solid var(--glass-border); border-radius: 16px;
            padding: 1.1rem 1rem; text-align: center; height: 100%;
        }
        .metric-value { font-family: 'Space Grotesk', sans-serif; font-size: 1.9rem; font-weight: 700; color: var(--text-light); }
        .metric-label { color: var(--text-dim); font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.06em; margin-top: 0.2rem; }
        .metric-accent { color: var(--accent-cyan); }

        /* ---- Score badge ---- */
        .score-ring-wrap { text-align: center; }
        .verdict-pill {
            display: inline-block; padding: 0.4rem 1rem; border-radius: 999px;
            font-weight: 600; font-size: 0.85rem; margin-top: 0.6rem;
        }

        /* ---- Insight list ---- */
        .insight-item {
            padding: 0.55rem 0.7rem; border-radius: 10px; margin-bottom: 0.5rem;
            background: rgba(255,255,255,0.04); border-left: 3px solid var(--accent-cyan);
            font-size: 0.92rem; color: var(--text-light);
        }
        .insight-item.complaint { border-left-color: var(--negative); }

        .review-snippet {
            font-size: 0.85rem; color: var(--text-dim); border-top: 1px solid var(--glass-border);
            padding-top: 0.5rem; margin-top: 0.5rem;
        }

        div[data-testid="stButton"] button {
            background: linear-gradient(100deg, var(--accent-violet), var(--accent-cyan));
            color: #0F1629; font-weight: 700; border: none; border-radius: 12px;
            padding: 0.65rem 1.4rem; font-size: 1rem; transition: transform 0.15s ease, box-shadow 0.15s ease;
        }
        div[data-testid="stButton"] button:hover {
            transform: translateY(-1px); box-shadow: 0 6px 18px rgba(124,92,252,0.35);
        }

        div[data-testid="stTextInput"] input {
            background: rgba(255,255,255,0.05); border: 1px solid var(--glass-border);
            border-radius: 12px; color: var(--text-light); padding: 0.7rem 0.9rem;
        }

        footer, #MainMenu { visibility: hidden; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def hero_section():
    st.markdown(
        """
        <div class="hero-wrap">
            <span class="hero-eyebrow">⚡ AI Review Intelligence</span>
            <div class="hero-title">AI Product Review Intelligence Dashboard</div>
            <p class="hero-sub">Paste any Daraz product link. Get scraped reviews, cleaned data,
            an AI-generated verdict, and a downloadable Excel report — in one pass.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def url_input_section():
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    col1, col2 = st.columns([4, 1], vertical_alignment="bottom")
    with col1:
        url = st.text_input(
            "Daraz Product URL",
            placeholder="https://www.daraz.pk/products/example-product-i123456789.html",
            label_visibility="collapsed",
        )
    with col2:
        analyze_clicked = st.button("🔍 Analyze Product", use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)
    return url, analyze_clicked


def loading_sequence(placeholder):
    """Runs the animated multi-stage loading UI inside a given st.empty() placeholder."""
    stages = [
        ("🌐", "Validating product link..."),
        ("🕷️", "Scraping reviews from Daraz..."),
        ("🧹", "Cleaning and de-duplicating review data..."),
        ("🤖", "Running AI sentiment & verdict analysis..."),
        ("📊", "Building your dashboard..."),
    ]
    return stages, placeholder


def render_stage(placeholder, icon, text, progress_value):
    with placeholder.container():
        st.markdown(
            f"""
            <div class="glass-card" style="text-align:center;">
                <div style="font-size:1.8rem;">{icon}</div>
                <div style="color:var(--text-light); font-weight:600; margin-top:0.3rem;">{text}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.progress(progress_value)


def product_header(result: ScrapeResult):
    col1, col2 = st.columns([1, 4])
    with col1:
        if result.product_image_url:
            st.image(result.product_image_url, use_container_width=True)
        else:
            st.markdown(
                '<div class="metric-tile" style="height:120px; display:flex; align-items:center; '
                'justify-content:center;">🛍️</div>',
                unsafe_allow_html=True,
            )
    with col2:
        st.markdown(f"### {result.product_name}")
        st.caption(result.product_url)


def metric_tiles(total_reviews, avg_rating, positive_pct, neutral_pct, negative_pct):
    cols = st.columns(5)
    tiles = [
        (f"{total_reviews}", "Total Reviews"),
        (f"{avg_rating:.1f} ★", "Average Rating"),
        (f"{positive_pct}%", "Positive"),
        (f"{neutral_pct}%", "Neutral"),
        (f"{negative_pct}%", "Negative"),
    ]
    for col, (value, label) in zip(cols, tiles):
        with col:
            st.markdown(
                f"""
                <div class="metric-tile">
                    <div class="metric-value">{value}</div>
                    <div class="metric-label">{label}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def score_and_verdict(analysis: AnalysisResult):
    verdict_colors = {
        "Winning Product": ("#2ECC71", "rgba(46,204,113,0.15)"),
        "Good Product": ("#34D9D4", "rgba(52,217,212,0.15)"),
        "Average Product": ("#F4C744", "rgba(244,199,68,0.15)"),
        "Not Recommended": ("#FF5C7A", "rgba(255,92,122,0.15)"),
    }
    color, bg = verdict_colors.get(analysis.verdict, ("#9099B8", "rgba(144,153,184,0.15)"))

    st.markdown(
        f"""
        <div class="glass-card score-ring-wrap">
            <div class="metric-label">Overall Product Score</div>
            <div class="metric-value" style="font-size:3rem;">{analysis.overall_score}<span style="font-size:1.2rem; color:var(--text-dim);"> / 10</span></div>
            <span class="verdict-pill" style="color:{color}; background:{bg};">{analysis.verdict}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def sentiment_donut(positive_pct, neutral_pct, negative_pct):
    fig = go.Figure(
        data=[
            go.Pie(
                labels=["Positive", "Neutral", "Negative"],
                values=[positive_pct, neutral_pct, negative_pct],
                hole=0.62,
                marker=dict(colors=["#2ECC71", "#F4C744", "#FF5C7A"]),
                textinfo="percent",
                textfont=dict(color="#0F1629", size=13),
            )
        ]
    )
    fig.update_layout(
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=-0.15, font=dict(color="#E7E9F3")),
        margin=dict(t=10, b=10, l=10, r=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=300,
    )
    st.plotly_chart(fig, use_container_width=True)


def rating_distribution_chart(df):
    counts = df["rating"].round().value_counts().reindex([1, 2, 3, 4, 5], fill_value=0)
    fig = go.Figure(
        data=[
            go.Bar(
                x=[f"{int(r)} ★" for r in counts.index],
                y=counts.values,
                marker_color=["#FF5C7A", "#FF5C7A", "#F4C744", "#34D9D4", "#2ECC71"],
            )
        ]
    )
    fig.update_layout(
        margin=dict(t=10, b=10, l=10, r=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#E7E9F3"),
        height=300,
        yaxis=dict(gridcolor="rgba(255,255,255,0.06)"),
    )
    st.plotly_chart(fig, use_container_width=True)


def insights_section(analysis: AnalysisResult):
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### 👍 What Customers Like")
        items = analysis.strengths or ["No standout strengths identified."]
        for item in items:
            st.markdown(f'<div class="insight-item">{item}</div>', unsafe_allow_html=True)
    with col2:
        st.markdown("#### ⚠️ Common Complaints")
        items = analysis.complaints or ["No major complaints identified."]
        for item in items:
            st.markdown(f'<div class="insight-item complaint">{item}</div>', unsafe_allow_html=True)


def recommendation_card(analysis: AnalysisResult):
    st.markdown(
        f"""
        <div class="glass-card">
            <div class="metric-label" style="margin-bottom:0.5rem;">🧠 Buy Recommendation</div>
            <div style="font-size:1.0rem; line-height:1.5;">{analysis.recommendation}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if analysis.used_fallback:
        st.info(
            f"ℹ️ This is a basic rating-based estimate — AI analysis was unavailable "
            f"({analysis.fallback_reason}). Add a valid AI API key in `.env` for full "
            f"language-based insights.",
        )


def review_sample_table(df, limit=8):
    st.markdown("#### 📝 Recent Reviews")
    for _, row in df.head(limit).iterrows():
        st.markdown(
            f"""
            <div class="insight-item">
                <strong>{row['reviewer_name']}</strong> — {'⭐' * int(round(row['rating']))} ({row['rating']})
                <div class="review-snippet">{truncate_for_display(row['review_text'], 220)}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def error_banner(message: str):
    st.error(f"🚫 {message}")


def empty_state():
    st.markdown(
        """
        <div class="glass-card" style="text-align:center; padding:2.4rem;">
            <div style="font-size:2.2rem;">📦</div>
            <div style="font-weight:600; margin-top:0.5rem;">No analysis yet</div>
            <div class="metric-label" style="margin-top:0.3rem;">Paste a Daraz product URL above and hit Analyze.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
