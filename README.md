# 🛍️ AI Product Review Intelligence Dashboard

A SaaS-style dashboard that takes a **Daraz product URL**, scrapes its customer reviews,
cleans the data, runs AI sentiment & verdict analysis, and produces a downloadable,
professionally formatted Excel report — plus an interactive analytics dashboard.

> Paste a link → get a buy/no-buy verdict backed by real customer review data.

---

## ✨ Features

- 🌐 **Daraz URL scraper** — extracts product info + all publicly visible reviews (multi-page)
- 🧹 **Data cleaning pipeline** — de-dupes, normalizes whitespace, standardizes dates/ratings
- 🤖 **Multi-provider AI analysis** — plug in OpenAI, Gemini, or Grok via one config switch
- 📊 **Live analytics** — sentiment donut, rating distribution, metric tiles
- 🧠 **AI verdict** — overall score /10, "Winning / Good / Average / Not Recommended" label,
  strengths, complaints, and a written buy recommendation
- 📥 **One-click Excel export** — `Product_Review_Analysis_Report.xlsx` with a Summary sheet
  and a full Reviews sheet (every review, sentiment-labeled, colour-coded)
- 🛟 **Graceful failure handling** — invalid links, zero reviews, network errors, and AI
  outages all show a friendly message instead of crashing; AI failures fall back to a
  transparent rating-based heuristic so the app never dies mid-demo

---

## 🧱 Tech Stack

| Layer            | Tech |
|-------------------|------|
| UI                | Streamlit + custom CSS (glassmorphism / gradient theme) + Plotly |
| Scraping          | Requests + BeautifulSoup (primary), Playwright (JS-render fallback) |
| Data processing   | Pandas |
| AI analysis       | OpenAI / Google Gemini / xAI Grok (switchable) |
| Excel export      | OpenPyXL |
| Config            | python-dotenv |

---

## 📂 Project Structure

```
project_folder/
├── app.py              # Streamlit entry point, pipeline orchestration
├── scraper.py           # Daraz scraping engine (API attempt + Playwright fallback)
├── cleaner.py            # Data cleaning / normalization pipeline
├── ai_analyzer.py        # Multi-provider AI review analysis + safe fallback
├── dashboard.py           # All UI components (CSS, cards, charts)
├── excel_exporter.py      # Builds the downloadable .xlsx report
├── config.py               # Central settings, loaded from .env
├── utils.py                 # Shared helpers (validation, text cleanup, fallback sentiment)
├── requirements.txt
├── .env.example
├── .gitignore
├── .streamlit/config.toml    # Dark theme config
└── README.md
```

---

## 🚀 Installation

### 1. Extract the project & open a terminal in the folder

### 2. Create a virtual environment

```bash
python -m venv venv

# Activate it:
# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
playwright install chromium   # only needed once, for the scraping fallback
```

### 4. Add your AI API key

```bash
cp .env.example .env       # macOS/Linux
copy .env.example .env     # Windows
```

Open `.env` and set:

```
AI_PROVIDER=openai          # or gemini / grok
OPENAI_API_KEY=sk-...       # only the key for your chosen provider is required
```

> No key? The app still runs — it falls back to a basic rating-based analysis and tells you
> in the UI that AI insights aren't active.

### 5. Run locally

```bash
streamlit run app.py
```

Open the URL Streamlit prints (usually `http://localhost:8501`).

---

## ☁️ Deploy on Streamlit Cloud

1. Push this project to a GitHub repository (`.env` is git-ignored — don't commit real keys).
2. Go to [share.streamlit.io](https://share.streamlit.io) → **New app**.
3. Select your repo, branch, and set the main file to `app.py`.
4. Under **Advanced settings → Secrets**, add your key(s) in TOML format, e.g.:
   ```toml
   AI_PROVIDER = "openai"
   OPENAI_API_KEY = "sk-..."
   ```
5. Deploy. Streamlit Cloud injects secrets as environment variables automatically.

> Note: Streamlit Cloud's containers don't always allow installing Playwright's browser
> binaries. If the Playwright fallback fails there, the HTTP/API scraping path will still
> run; for guaranteed Playwright support, deploy to a host that allows
> `playwright install chromium` in its build step (e.g. Render, Railway, a VPS).

---

## 🏗️ How the Pipeline Works

```
Daraz URL
   │
   ▼
scraper.py   → validates URL → tries HTML+review-API → falls back to Playwright
   │
   ▼
cleaner.py   → de-dupes, normalizes text/dates/ratings → clean DataFrame
   │
   ▼
ai_analyzer.py → sends review sample to OpenAI/Gemini/Grok → score, verdict,
                 sentiment split, strengths, complaints, recommendation
                 (falls back to a rating/keyword heuristic if no key / API error)
   │
   ▼
dashboard.py  → renders metric tiles, charts, insights, recommendation
   │
   ▼
excel_exporter.py → builds Product_Review_Analysis_Report.xlsx for download
```

---

## ⚠️ Honest Notes on Scraping Daraz

- Daraz's page markup, review-API paths, and anti-bot rules change over time and differ
  slightly by region (`.pk`, `.com.bd`, `.lk`, etc). `scraper.py` is written defensively
  with two strategies and clear failure messages, but if Daraz ships a structural change,
  the CSS selectors / API path constants at the top of `scraper.py` are the place to update.
- Only **publicly visible** product/review page content is read — no login, no private
  endpoints, no personal contact info. Respect Daraz's Terms of Service and `robots.txt`
  for your use case, and add request delays (already configurable via
  `SCRAPE_DELAY_SECONDS`) so you're not hammering their servers.
- If a product genuinely has zero reviews, or Daraz blocks the request, the dashboard shows
  a clear in-UI error instead of crashing.

---

## 🛟 Error Handling Coverage

| Scenario | Behavior |
|---|---|
| Invalid / non-Daraz URL | Friendly inline error, no crash |
| Zero reviews found | Friendly inline error explaining why |
| Network/timeout failure | Caught, falls back to Playwright, then friendly error |
| AI API failure / no key | Falls back to rating-based heuristic, UI banner explains it |
| Empty dataset after cleaning | Friendly inline error |

---

## 📜 License

Built as a portfolio project. Adapt freely for your own use — just make sure your scraping
usage complies with Daraz's Terms of Service.
