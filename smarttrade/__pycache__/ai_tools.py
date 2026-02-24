from google import genai
import yfinance as yf
import requests
from datetime import datetime
from config import ALPHAVANTAGE_KEY
import json
import os

# MODEL + GOOGLE CLIENT INIT

MODEL = "gemini-2.5-flash"

client = genai.Client(
    api_key="AIzaSyAct23Kt1kn91pFlgoHROaaF1XKeu2eaWU")

NEWSAPI_KEY = "51f3a0b3612546f285cad0b7cbf644ec"
CRAMER_STORE_FILE = "cramer_store.json"

# SAFE AI WRAPPER

def _safe_ai(prompt: str) -> str:
    try:
        out = client.models.generate_content(
            model=MODEL,
            contents=prompt
        )
        return out.text.strip()
    except Exception as e:
        return f"[AI Error] CramerBot is taking a breather: {e}"

# CRAMER STORE — WEEKLY MEMORY

def _load_cramer_store():
    if not os.path.exists(CRAMER_STORE_FILE):
        return {}
    try:
        with open(CRAMER_STORE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}


def _save_cramer_store(store: dict):
    try:
        with open(CRAMER_STORE_FILE, "w", encoding="utf-8") as f:
            json.dump(store, f, indent=2)
    except:
        pass

# NEWS PIPELINE

def get_company_news_multi(ticker: str):
    headlines = []

    try:
        tk = yf.Ticker(ticker)
        news = tk.news
        if news:
            for n in news[:8]:
                title = n.get("title")
                if title:
                    headlines.append(title)
    except:
        pass

    try:
        url = (
            "https://newsapi.org/v2/everything"
            f"?q={ticker}&language=en&sortBy=publishedAt&apiKey={NEWSAPI_KEY}"
        )
        dat = requests.get(url).json()
        for a in dat.get("articles", []):
            t = a.get("title")
            if t:
                headlines.append(t)
    except:
        pass

    try:
        url = (
            "https://www.alphavantage.co/query?"
            f"function=NEWS_SENTIMENT&tickers={ticker}&apikey={ALPHAVANTAGE_KEY}"
        )
        dat = requests.get(url).json()
        for item in dat.get("feed", [])[:6]:
            title = item.get("title")
            src = item.get("source", "")
            sentiment = item.get("overall_sentiment_label", "Neutral")
            if title:
                headlines.append(f"{title} — {src} [{sentiment}]")
    except:
        pass

    cleaned = list(dict.fromkeys([h.strip() for h in headlines if h.strip()]))

    return "\n".join(f"- {h}" for h in cleaned) if cleaned else "No recent news available."

# ALPHAVANTAGE FUNDAMENTAL HELPERS

def alpha_income(ticker):
    try:
        url = (
            "https://www.alphavantage.co/query?"
            f"function=INCOME_STATEMENT&symbol={ticker}&apikey={ALPHAVANTAGE_KEY}"
        )
        return requests.get(url).json().get("quarterlyReports", [])
    except:
        return []



def alpha_earnings(ticker):
    try:
        url = (
            "https://www.alphavantage.co/query?"
            f"function=EARNINGS&symbol={ticker}&apikey={ALPHAVANTAGE_KEY}"
        )
        return requests.get(url).json().get("quarterlyEarnings", [])
    except:
        return []



def alpha_balance(ticker):
    try:
        url = (
            "https://www.alphavantage.co.query?"
            f"function=BALANCE_SHEET&symbol={ticker}&apikey={ALPHAVANTAGE_KEY}"
        )
        return requests.get(url).json().get("quarterlyReports", [])
    except:
        return []

# VOLATILITY + MACRO RISK MODELS

def compute_company_volatility(ticker):
    try:
        hist = yf.download(ticker, period="1y", progress=False)
        if len(hist) < 50:
            return None
        hist["return"] = hist["Close"].pct_change()
        daily = hist["return"].std()
        return float(daily * (252 ** 0.5)) if daily else None
    except:
        return None

def compute_macro_risk_score():
    score = 0
    n = 0

    try:
        vix = yf.Ticker("^VIX").history(period="5d")["Close"].iloc[-1]
        score += 0.2 if vix < 15 else 0.45 if vix < 22 else 0.75
        n += 1
    except:
        pass

    try:
        tnx = yf.Ticker("^TNX").history(period="5d")["Close"].iloc[-1]
        y = tnx / 10
        score += 0.2 if y < 2 else 0.45 if y < 4 else 0.75
        n += 1
    except:
        pass

    try:
        data = requests.get(
            f"https://www.alphavantage.co/query?function=UNEMPLOYMENT&apikey={ALPHAVANTAGE_KEY}"
        ).json().get("data", [])
        if data:
            r = float(data[0]["value"])
            score += 0.2 if r < 4 else 0.45 if r < 5 else 0.75
            n += 1
    except:
        pass

    return (score / n) if n else 0.50

def compute_forward_risk_scores(ticker):
    vol = compute_company_volatility(ticker)

    if vol is None:
        c = 0.5
    elif vol < 0.25:
        c = 0.25
    elif vol < 0.40:
        c = 0.5
    else:
        c = 0.75

    m = compute_macro_risk_score()
    return (c, m)

# CRAMER REPORT — WEEKLY MEMORY + LIVE FUNDAMENTALS

def ai_company_summary(ticker: str, fundamentals=None):
    ticker = ticker.upper()
    tk = yf.Ticker(ticker)
    info = tk.info or {}

    name = info.get("longName") or info.get("shortName") or ticker
    sector = info.get("sector", "Unknown")
    industry = info.get("industry", "Unknown")
    description = info.get("longBusinessSummary", "")

    inc = alpha_income(ticker)
    latest_fiscal = inc[0].get("fiscalDateEnding") if inc else None

    store = _load_cramer_store()

    # --- Weekly refresh logic ---
    last_gen = store.get(ticker, {}).get("generated_at")
    refresh_due = True

    if last_gen:
        try:
            dt = datetime.fromisoformat(last_gen)
            days_old = (datetime.now() - dt).days
            refresh_due = days_old >= 7
        except:
            refresh_due = True

    cached_fiscal = store.get(ticker, {}).get("last_fiscal")
    fiscal_changed = (latest_fiscal != cached_fiscal)

    smarttrade_trigger = fundamentals is not None

    # --- FINAL CACHE CHECK ---
    if (
        ticker in store
        and not refresh_due
        and not fiscal_changed
        and not smarttrade_trigger
    ):
        return store[ticker]["note"]

    # --- Fresh generation ---
    try:
        hist = tk.history(period="5d")
        price = float(hist["Close"].iloc[-1])
    except:
        price = None

    tgt_mean = info.get("targetMeanPrice")
    tgt_high = info.get("targetHighPrice")
    tgt_low = info.get("targetLowPrice")
    analysts = info.get("numberOfAnalystOpinions")

    upside = (tgt_mean / price - 1) * 100 if price and tgt_mean else None

    try:
        cal = tk.calendar
        raw = cal.loc["Earnings Date"][0]
        next_earn = raw.to_pydatetime() if hasattr(raw, "to_pydatetime") else raw
        days_to_earn = (next_earn.date() - datetime.now().date()).days
    except:
        days_to_earn = None

    try:
        ana = tk.analysis
        forward_table = (
            ana.to_string().replace("00:00:00", "")
            if (ana is not None and not ana.empty)
            else "No forward revenue or EPS estimates available."
        )
    except:
        forward_table = "No forward revenue or EPS estimates available."

    forward_block = ""

    if fundamentals:
        qtrs = fundamentals.get("quarters", [])
        projs = fundamentals.get("projections", [])

        if qtrs:
            forward_block += "Historical EPS (Actual vs Estimates):\n"
            for q in qtrs:
                forward_block += (
                    f"{q['label']}: Actual={q['eps']}, Est={q['eps_est']}, "
                    f"Surprise={q['eps_surprise']}\n"
                )

        if projs:
            forward_block += "\nForward Projections (Revenue + EPS):\n"
            for p in projs:
                forward_block += (
                    f"{p['label']}: Projected EPS={p['eps']:.2f}, "
                    f"Projected Revenue={p['revenue']:.2f}\n"
                )

    if not forward_block:
        forward_block = "No SmartTrade forward data available."

    news_block = get_company_news_multi(ticker)
    company_risk, macro_risk = compute_forward_risk_scores(ticker)

    prompt = f"""
You are CramerBot, a high-energy but professional equity analyst.

Formatting rules:
- No markdown.
- No asterisks.
- No bold text.
- No lists or bullet points.
- Write ONLY clean paragraphs.
- Each section must have a plain text title on its own line, for example:
  Section 1: Company History

Write a full equity research report with EXACT sections:

Section 1: Company History
Section 2: Company Overview
Section 3: Business Model
Section 4: Recent Company News
Section 5: Company Outlook and Forward Estimates
Section 6: CramerBot Prediction and Rating

In Section 6 you MUST include:
- A single conviction score from 0 to 100.
- A clear BUY, HOLD, or SELL rating.
- High-energy phrases are allowed, but formatting must stay clean paragraphs.

Ticker: {ticker}
Company: {name}
Sector: {sector}
Industry: {industry}

Business Description:
{description}

Forward Estimates Table (Yahoo Native):
{forward_table}

SmartTrade Forward Data (More Accurate EPS + Revenue Projections):
{forward_block}

Price: {price}
Target Mean: {tgt_mean}
Target High: {tgt_high}
Target Low: {tgt_low}
Analyst Count: {analysts}
Upside Potential: {upside}

Earnings in: {days_to_earn} days

Recent Headlines:
{news_block}

INTERNAL RISK INPUTS (not shown to the user):
Company Risk Score = {company_risk}
Macro Risk Score = {macro_risk}
"""

    note = _safe_ai(prompt)

    store[ticker] = {
        "note": note,
        "last_fiscal": latest_fiscal,
        "generated_at": datetime.now().isoformat(),
        "price_at_generation": price
    }
    _save_cramer_store(store)

    return note

# Q&A

def ai_ask_cramer(ticker: str, question: str):
    prompt = f"""
You are CramerBot — energetic, bold, funny, dramatic when needed,
but ALWAYS fundamentally correct.

Your answer MUST:
- align 100% with SmartTrade fundamentals
- reflect volatility, sector dynamics, macro trends
- teach the user something real
- avoid invented numbers
- be 5 sentences at least long
- high-energy Cramer style
- no markdown or bullets

User question about {ticker}:
{question}

Respond with conviction.
"""
    return _safe_ai(prompt)

# PORTFOLIO SUMMARY

def ai_portfolio_summary(text: str):
    prompt = f"""
You are CramerBot reviewing a portfolio.

Tone:
- energetic
- educational
- slightly dramatic
- fundamentally rigorous

Explain diversification quality, sector balance, concentration risk,
volatility exposure, and overall strength.

Portfolio Data:
{text}

Return 4–6 sentences.
"""
    return _safe_ai(prompt)