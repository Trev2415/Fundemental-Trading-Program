import yfinance as yf
import requests
import math
import random
from datetime import datetime
from config import ALPHAVANTAGE_KEY

# SAFE FLOAT

def safe_float(v):
    try:
        if v is None:
            return None

        s = str(v).strip().replace(",", "").replace("$", "")

        if s in ("", "-", "null", "NULL", "None", "nan", "NaN"):
            return None

        # suffix multipliers
        if s.endswith(("B", "b")):
            return float(s[:-1]) * 1e9
        if s.endswith(("M", "m")):
            return float(s[:-1]) * 1e6
        if s.endswith(("K", "k")):
            return float(s[:-1]) * 1e3
        if s.endswith(("T", "t")):
            return float(s[:-1]) * 1e12

        return float(s)

    except:
        return None

# ALPHA HELPERS (Revenue + Income ONLY)

def alpha_request(function, ticker):
    try:
        url = (
            f"https://www.alphavantage.co/query?function={function}"
            f"&symbol={ticker}&apikey={ALPHAVANTAGE_KEY}"
        )
        return requests.get(url).json()
    except:
        return {}

def alpha_income(ticker):
    return alpha_request("INCOME_STATEMENT", ticker).get("quarterlyReports", [])

def alpha_balance(ticker):
    return alpha_request("BALANCE_SHEET", ticker).get("quarterlyReports", [])

# QUARTER LABEL

def date_to_quarter(dt):
    try:
        d = datetime.strptime(dt, "%Y-%m-%d")
        q = (d.month - 1) // 3 + 1
        return f"Q{q} {d.year}"
    except:
        return dt

# UNIVERSAL EPS FETCHER 

def get_eps_data(tk):
    """
    Clean EPS fetcher using ONLY Yahoo's modern get_earnings_dates() output.
    This is the ONLY stable EPS source left in yfinance.
    """

    eps_actual = {}
    eps_est = {}
    eps_surprise = {}

    try:
        df = tk.get_earnings_dates(limit=20)
        if df is None or df.empty:
            return eps_actual, eps_est, eps_surprise

        for idx, row in df.iterrows():
            dt = idx.strftime("%Y-%m-%d")

            eps_est[dt] = safe_float(row.get("EPS Estimate"))
            eps_actual[dt] = safe_float(row.get("Reported EPS"))
            eps_surprise[dt] = safe_float(row.get("Surprise(%)"))

    except:
        pass

    return eps_actual, eps_est, eps_surprise

# BUILD QUARTERS (Revenue, Income, EPS)

def build_quarters(tk, ticker):

    # Revenue + Income
    q_fin = tk.quarterly_financials
    revs = {}
    incs = {}

    if q_fin is not None and not q_fin.empty:
        df = q_fin.T.sort_index(ascending=False)
        for idx, row in df.iterrows():
            dt = idx.strftime("%Y-%m-%d")
            revs[dt] = safe_float(row.get("Total Revenue"))
            incs[dt] = safe_float(row.get("Net Income"))

    # Alpha fallback
    for q in alpha_income(ticker):
        dt = q.get("fiscalDateEnding")
        if dt not in revs or revs[dt] is None:
            revs[dt] = safe_float(q.get("totalRevenue"))
        if dt not in incs or incs[dt] is None:
            incs[dt] = safe_float(q.get("netIncome"))

    # EPS (modern API)
    eps_actual, eps_est, eps_surprise = get_eps_data(tk)

    eps_list = []
    for dt, val in eps_actual.items():
        try:
            eps_list.append({
                "date": datetime.strptime(dt, "%Y-%m-%d"),
                "eps": val,
                "est": eps_est.get(dt),
                "surp": eps_surprise.get(dt),
            })
        except:
            pass

    quarters = []

    for dt in sorted(revs.keys(), reverse=True)[:4]:

        q_date = datetime.strptime(dt, "%Y-%m-%d")
        q_end_month = q_date.month
        q_end_year = q_date.year

        best_match = None
        best_diff = 999

        for ep in eps_list:
            if ep["date"].year != q_end_year:
                continue

            month_diff = abs(ep["date"].month - q_end_month)

            if month_diff <= 2 and month_diff < best_diff:
                best_diff = month_diff
                best_match = ep

        if best_match:
            eps_val = best_match["eps"]
            eps_est_val = best_match["est"]
            eps_surp_val = best_match["surp"]
        else:
            eps_val = None
            eps_est_val = None
            eps_surp_val = None

        quarters.append({
            "date": dt,
            "label": date_to_quarter(dt),
            "revenue": revs.get(dt),
            "income": incs.get(dt),
            "eps": eps_val,
            "eps_est": eps_est_val,
            "eps_surprise": eps_surp_val,
        })

    return quarters

# PROJECTION ENGINE

def project_forward_quarters(quarters, ticker):

    if not quarters or len(quarters) < 2:
        return []

    q_sorted = sorted(quarters, key=lambda x: x["date"], reverse=True)
    last = q_sorted[0]

    last_rev = float(last["revenue"] or 0)
    last_inc = float(last["income"] or 0)
    last_eps = float(last["eps"] or 0)

    dt = datetime.strptime(last["date"], "%Y-%m-%d")
    last_q = (dt.month - 1) // 3 + 1
    year = dt.year

    # Revenue Trend
    rev_list = [float(q["revenue"] or 0) for q in q_sorted[:4]]
    growth = []

    for i in range(1, len(rev_list)):
        if rev_list[i] > 0:
            growth.append((rev_list[i - 1] - rev_list[i]) / rev_list[i])

    base_growth = sum(growth) / len(growth) if growth else 0.04

    # Volatility
    avg_rev = sum(rev_list) / len(rev_list)
    if avg_rev > 0:
        std = math.sqrt(sum((r - avg_rev) ** 2 for r in rev_list) / len(rev_list))
        vol_factor = min(max(std / avg_rev, 0.02), 0.20)
    else:
        vol_factor = 0.05

    random.seed(hash(ticker) % 999999)

    projections = []
    curr_rev = last_rev
    curr_inc = last_inc
    curr_eps = last_eps if last_eps > 0 else 0.20

    for _ in range(4):

        next_q = last_q + 1
        if next_q > 4:
            next_q = 1
            year += 1
        last_q = next_q

        shock = random.uniform(-vol_factor, vol_factor)
        g = base_growth + shock

        curr_rev *= (1 + g)
        curr_inc *= (1 + g * 1.1)
        curr_eps *= (1 + g * 1.3)

        projections.append({
            "label": f"Q{next_q} {year}",
            "revenue": curr_rev,
            "income": curr_inc,
            "eps": curr_eps,
        })

    return projections

# MAIN FUNDAMENTALS FUNCTION

def get_fundamentals(ticker: str):

    ticker = ticker.upper()
    tk = yf.Ticker(ticker)

    try:
        info = tk.get_info()
    except:
        info = {}

    long_name = info.get("longName", ticker)
    sector = info.get("sector", "Unknown")

    # Price
    price = safe_float(info.get("currentPrice"))
    if price is None:
        try:
            price = float(tk.history(period="1d")["Close"].iloc[-1])
        except:
            price = None

    # Valuation
    trailing_pe = safe_float(info.get("trailingPE"))
    forward_pe = safe_float(info.get("forwardPE"))
    peg = safe_float(info.get("pegRatio"))  
    market_cap = safe_float(info.get("marketCap"))
    beta = safe_float(info.get("beta"))

    try:
        if peg is not None:
            peg = float(peg)
            if peg <= 0 or peg > 200:
                peg = None
    except:
        peg = None

    earnings_growth = safe_float(info.get("earningsGrowth"))

    if peg is None and forward_pe and earnings_growth and earnings_growth > 0.01:
        try:
            peg_val = forward_pe / earnings_growth
            if 0 < peg_val <= 200:
                peg = peg_val
        except:
            peg = None

    # Dividend Yield
    dividend_rate = safe_float(info.get("dividendRate"))
    if dividend_rate and price:
        dividend_yield = dividend_rate / price
    else:
        dividend_yield = 0.0

    # Financial Health
    debt_to_equity = safe_float(info.get("debtToEquity"))
    current_ratio = safe_float(info.get("currentRatio"))

    # TTM income & revenue
    revenue_ttm = None
    income_ttm = None

    q_fin = tk.quarterly_financials
    if q_fin is not None and not q_fin.empty:
        try:
            revenue_ttm = float(q_fin.loc["Total Revenue"].iloc[:4].sum())
        except:
            pass
        try:
            income_ttm = float(q_fin.loc["Net Income"].iloc[:4].sum())
        except:
            pass

    # Fallback to Alpha
    if revenue_ttm is None or income_ttm is None:
        inc = alpha_income(ticker)
        if len(inc) >= 4:
            rsum = sum(safe_float(q.get("totalRevenue") or 0) for q in inc[:4])
            isum = sum(safe_float(q.get("netIncome") or 0) for q in inc[:4])
            if revenue_ttm is None:
                revenue_ttm = rsum
            if income_ttm is None:
                income_ttm = isum

    net_margin = (income_ttm / revenue_ttm) if revenue_ttm else None

    # ROE / ROA
    q_bs = tk.quarterly_balance_sheet
    equity = None
    assets = None

    equity_aliases = [
        "Total Stockholder Equity", "Total Shareholder Equity",
        "Stockholders Equity", "Common Stock Equity",
        "Total Equity", "Total Equity Gross Minority Interest",
    ]

    assets_aliases = ["Total Assets", "Assets"]

    if q_bs is not None and not q_bs.empty:
        for lbl in equity_aliases:
            try:
                val = q_bs.loc[lbl].iloc[0]
                if val not in (None, 0):
                    equity = float(val)
                    break
            except:
                pass

        for lbl in assets_aliases:
            try:
                val = q_bs.loc[lbl].iloc[0]
                if val not in (None, 0):
                    assets = float(val)
                    break
            except:
                pass

    # Alpha fallback
    if equity is None or assets is None:
        bal = alpha_balance(ticker)
        if bal:
            b = bal[0]
            if equity is None:
                equity = safe_float(b.get("totalShareholderEquity"))
            if assets is None:
                assets = safe_float(b.get("totalAssets"))

    roe = (income_ttm / equity) if equity else None
    roa = (income_ttm / assets) if assets else None

    # Quarters
    quarters = build_quarters(tk, ticker)

    # Projections
    projections = project_forward_quarters(quarters, ticker)

    return {
        "ticker": ticker,
        "longName": long_name,
        "sector": sector,
        "price": price,
        "marketCap": market_cap,
        "beta": beta,
        "trailingPE": trailing_pe,
        "forwardPE": forward_pe,
        "pegRatio": peg,      
        "revenueTTM": revenue_ttm,
        "incomeTTM": income_ttm,
        "netMargin": net_margin,
        "roeTTM": roe,
        "roaTTM": roa,
        "debtToEquity": debt_to_equity,
        "currentRatio": current_ratio,
        "dividendYield": dividend_yield,
        "dividendPerShare": dividend_rate,
        "quarters": quarters,
        "projections": projections,
    }

# SECTOR & MARKET COMPARISON

def _calc_return(symbol: str, years: int):
    try:
        df = yf.download(symbol, period=f"{years}y",
                         interval="1d", progress=False)
        if df.empty or "Close" not in df.columns:
            return None
        start = float(df["Close"].iloc[0])
        end = float(df["Close"].iloc[-1])
        return (end / start) - 1 if start != 0 else None
    except:
        return None


MARKET_INDEX = "SPY"

SECTOR_ETF_MAP = {
    "Technology": ("XLK", "Technology ETF"),
    "Financial Services": ("XLF", "Financials ETF"),
    "Energy": ("XLE", "Energy ETF"),
    "Industrials": ("XLI", "Industrials ETF"),
    "Utilities": ("XLU", "Utilities ETF"),
    "Communication Services": ("XLC", "Communications ETF"),
    "Consumer Cyclical": ("XLY", "Consumer Cyclical ETF"),
    "Consumer Defensive": ("XLP", "Consumer Defensive ETF"),
    "Healthcare": ("XLV", "Healthcare ETF"),
    "Real Estate": ("XLRE", "Real Estate ETF"),
    "Materials": ("XLB", "Materials ETF"),
}


def compare_sector_and_market(ticker: str):
    ticker = ticker.upper()
    info = yf.Ticker(ticker).info or {}
    sector = info.get("sector")

    print("\nSector & Market Comparison (1yr / 3yr / 5yr)")
    print("--------------------------------------------------------------")
    print(f"{' ':20} {'1yr':>8} {'3yr':>8} {'5yr':>8}")
    print("--------------------------------------------------------------")

    def f(x):
        return "--".rjust(8) if x is None else f"{x*100:8.2f}%"

    c1 = _calc_return(ticker, 1)
    c3 = _calc_return(ticker, 3)
    c5 = _calc_return(ticker, 5)

    m1 = _calc_return(MARKET_INDEX, 1)
    m3 = _calc_return(MARKET_INDEX, 3)
    m5 = _calc_return(MARKET_INDEX, 5)

    if sector in SECTOR_ETF_MAP:
        etf, name = SECTOR_ETF_MAP[sector]
        s1 = _calc_return(etf, 1)
        s3 = _calc_return(etf, 3)
        s5 = _calc_return(etf, 5)
        etf_label = f"{etf} ({name})"
    else:
        s1 = s3 = s5 = None
        etf_label = "Sector ETF"

    print(f"{ticker:<20}{f(c1)}{f(c3)}{f(c5)}")
    print(f"{(MARKET_INDEX + ' (Market)'):<20}{f(m1)}{f(m3)}{f(m5)}")
    print(f"{etf_label:<20}{f(s1)}{f(s3)}{f(s5)}")