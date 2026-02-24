import yfinance as yf

# ----------------------- Safe Float ----------------------------
def safe_float(v):
    try:
        if v in (None, "", "null", "NULL"):
            return None
        return float(v)
    except:
        return None


# ----------------------- TTM Helper ----------------------------
def ttm_sum(df, field):
    """Sum last 4 quarters from a yfinance DataFrame."""
    try:
        return float(df.loc[field].iloc[:4].sum())
    except:
        return None

#  MAIN FUNDAMENTALS FUNCTION
def get_portfolio_fundamentals(ticker: str):
    """
    Returns core fundamentals for portfolio analytics:
        price, sector, trailingPE, forwardPE, pegRatio,
        beta, dividendYield, debtToEquity,
        revenueTTM, incomeTTM, netMargin,
        roeTTM, roaTTM,
        PLUS growth metrics & raw values for fallback PEG/ROE
    """

    ticker = ticker.upper()
    tk = yf.Ticker(ticker)

    # --------------- PRICE ----------------
    try:
        hist = tk.history(period="2d")
        price = float(hist["Close"].iloc[-1])
    except:
        price = None

    # --------------- INFO DICT -------------------
    try:
        info = tk.get_info()
    except:
        info = {}

    # --------- CORE ANALYST METRICS ----------
    pe = safe_float(info.get("trailingPE"))
    forward_pe = safe_float(info.get("forwardPE"))
    peg = safe_float(info.get("pegRatio"))
    beta = safe_float(info.get("beta"))
    dividend_yield = safe_float(info.get("dividendYield"))
    debt_to_equity = safe_float(info.get("debtToEquity"))
    sector = info.get("sector")

    # --------- GROWTH FIELDS NEEDED FOR PEG FALLBACK ---------
    earnings_q_growth = safe_float(info.get("earningsQuarterlyGrowth"))
    earnings_growth = safe_float(info.get("earningsGrowth"))
    revenue_growth = safe_float(info.get("revenueGrowth"))

    #     TTM CALCULATIONS FROM QUARTERLY FINANCIALS
    q_fin = tk.quarterly_financials
    q_bs = tk.quarterly_balance_sheet

    revenue_ttm = ttm_sum(q_fin, "Total Revenue")
    income_ttm = ttm_sum(q_fin, "Net Income")

    # ------------------ Profitability -------------------
    try:
        net_margin = (income_ttm / revenue_ttm) if (income_ttm and revenue_ttm) else None
    except:
        net_margin = None

    # ------------------ ROE / ROA -----------------------
    equity_labels = [
        "Total Stockholder Equity",
        "Total Shareholder Equity",
        "Stockholders Equity",
        "Common Stock Equity",
        "Total Equity",
        "Total Equity Gross Minority Interest",
    ]

    equity = None
    for label in equity_labels:
        try:
            eq = q_bs.loc[label].iloc[0]
            if eq is not None:
                equity = float(eq)
                break
        except:
            continue

    # Assets
    try:
        assets = float(q_bs.loc["Total Assets"].iloc[0])
    except:
        assets = None

    # Compute ROE and ROA
    roe = (income_ttm / equity) if (income_ttm and equity) else None
    roa = (income_ttm / assets) if (income_ttm and assets) else None

    #   RETURN RESULT DICT
    return {
        "price": price,
        "sector": sector,

        # core valuation
        "trailingPE": pe,
        "forwardPE": forward_pe,
        "pegRatio": peg,

        # beta & dividends
        "beta": beta,
        "dividendYield": dividend_yield,
        "debtToEquity": debt_to_equity,

        # TTM values
        "revenueTTM": revenue_ttm,
        "incomeTTM": income_ttm,
        "netMargin": net_margin,

        # raw fundamentals needed for fallback
        "netIncome": income_ttm,
        "totalStockholderEquity": equity,

        # growth metrics to compute PEG fallback
        "earningsQuarterlyGrowth": earnings_q_growth,
        "earningsGrowth": earnings_growth,
        "revenueGrowth": revenue_growth,

        # profitability
        "roeTTM": roe,
        "roaTTM": roa,
    }