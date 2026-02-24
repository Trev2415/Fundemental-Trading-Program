import json
import warnings
from collections import defaultdict
from fundamentals_live import get_portfolio_fundamentals

warnings.filterwarnings("ignore")

# PORTFOLIO SAVE / LOAD
def save_portfolio(path, portfolio, cash, txns):
    blob = {
        "portfolio": portfolio,
        "cash": cash,
        "transactions": txns
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(blob, f, indent=2)


def load_portfolio(path):
    try:
        with open(path, encoding="utf-8") as f:
            blob = json.load(f)
            return (
                blob.get("portfolio", {}),
                blob.get("cash", 100000.0),
                blob.get("transactions", [])
            )
    except FileNotFoundError:
        return {}, 100000.0, []

# BUY / SELL
def buy_shares(ticker, shares, price, portfolio, cash, txns):
    cost = round(shares * price, 2)

    if cost > cash:
        return False, "Insufficient cash", portfolio, cash, txns

    pos = portfolio.get(ticker, {"shares": 0, "avg_cost": 0.0})
    new_shares = pos["shares"] + shares
    if new_shares <= 0:
        return False, "Invalid share count", portfolio, cash, txns

    new_cost_basis = (
        pos["shares"] * pos["avg_cost"] + cost
    ) / new_shares

    portfolio[ticker] = {
        "shares": new_shares,
        "avg_cost": round(new_cost_basis, 4)
    }

    cash = round(cash - cost, 2)
    txns.append({
        "type": "BUY",
        "ticker": ticker,
        "shares": shares,
        "price": price
    })

    return True, "Filled", portfolio, cash, txns


def sell_shares(ticker, shares, price, portfolio, cash, txns):
    pos = portfolio.get(ticker)

    if not pos or shares > pos["shares"]:
        return False, "Not enough shares", portfolio, cash, txns

    proceeds = round(shares * price, 2)
    pos["shares"] -= shares

    if pos["shares"] == 0:
        del portfolio[ticker]
    else:
        portfolio[ticker] = pos

    cash = round(cash + proceeds, 2)
    txns.append({
        "type": "SELL",
        "ticker": ticker,
        "shares": shares,
        "price": price
    })

    return True, "Filled", portfolio, cash, txns

# WEIGHTED HELPERS
def safe_round(val, decimals=2):
    """Rounds values safely with consistent formatting."""
    try:
        return round(float(val), decimals)
    except:
        return None

# PEG CALCULATION
def compute_fallback_peg(f):
    """
    PEG must use **positive growth only**.
    Negative or zero growth → PEG is invalid → return None.
    """

    pe = f.get("trailingPE")

    if pe is None or pe <= 0:
        return None

    growth_keys = [
        "earningsQuarterlyGrowth",
        "earningsGrowth",
        "revenueGrowth"
    ]

    for g in growth_keys:
        growth = f.get(g)

        if growth is not None and growth > 0.01:
            return safe_round(pe / growth, 2)

    return None


def compute_fallback_roe(f):
    """Compute ROE manually if missing."""
    net = f.get("netIncome")
    eq = f.get("totalStockholderEquity")

    if net is None or eq is None or eq == 0:
        return None

    return safe_round(net / eq, 2)

# WEIGHTED PORTFOLIO METRICS
def aggregate_metrics(portfolio):
    """
    Computes fully weighted analytics for:
    P/E, Forward P/E, PEG, ROE, ROA, Net Margin, Beta, Debt/Equity,
    Dividend Yield, Sector weights
    """

    if not portfolio:
        return {
            "weighted_pe": None,
            "weighted_forward_pe": None,
            "weighted_peg": None,
            "weighted_roe": None,
            "weighted_roa": None,
            "weighted_margin": None,
            "weighted_beta": None,
            "weighted_de": None,
            "weighted_div_yield": None,
            "sector_weights": {},
            "holdings": 0,
        }

    fundamentals = {}
    mv_map = {}
    total_mv = 0

    # ---- Load fundamentals ----
    for t, pos in portfolio.items():
        f = get_portfolio_fundamentals(t)

        if not f or f.get("price") is None:
            continue

        # Auto-compute missing PEG/ROE
        if f.get("pegRatio") is None:
            f["pegRatio"] = compute_fallback_peg(f)

        # Remove unrealistic PEG values:
        peg = f.get("pegRatio")
        if peg is not None:
            try:
                peg = float(peg)
                if peg <= 0 or peg > 200:  
                    f["pegRatio"] = None
            except:
                f["pegRatio"] = None

        # ROE fallback
        if f.get("roeTTM") is None:
            f["roeTTM"] = compute_fallback_roe(f)

        # ---- CLEAN DIVIDEND YIELD ----
        dy = f.get("dividendYield")
        if dy is not None:
            try:
                dy = float(dy)

                if 1 < dy < 100:
                    dy = dy / 100

                if dy < 0 or dy > 0.20:
                    dy = None

                f["dividendYield"] = dy

            except:
                f["dividendYield"] = None

        mv = pos["shares"] * f["price"]
        mv_map[t] = mv
        fundamentals[t] = f
        total_mv += mv

    if total_mv == 0:
        return {
            "weighted_pe": None,
            "weighted_forward_pe": None,
            "weighted_peg": None,
            "weighted_roe": None,
            "weighted_roa": None,
            "weighted_margin": None,
            "weighted_beta": None,
            "weighted_de": None,
            "weighted_div_yield": None,
            "sector_weights": {},
            "holdings": len(fundamentals),
        }

    # ---- Convert MV → weights ----
    weights = {t: mv / total_mv for t, mv in mv_map.items()}

    # ---- Weighted average helper ----
    def wavg(field):
        total = 0
        for t, w in weights.items():
            val = fundamentals[t].get(field)
            if val is not None:
                try:
                    v = float(val)
                    total += v * w
                except:
                    pass
        return safe_round(total, 2) if total != 0 else None

    # ---- Weighted metrics ----
    weighted_pe = wavg("trailingPE")
    weighted_forward_pe = wavg("forwardPE")
    weighted_peg = wavg("pegRatio")
    weighted_roe = wavg("roeTTM")
    weighted_roa = wavg("roaTTM")
    weighted_margin = wavg("netMargin")
    weighted_beta = safe_round(wavg("beta"), 3)
    weighted_de = wavg("debtToEquity")
    weighted_div_yield = wavg("dividendYield")

    # ---- Sector weights ----
    sector_map = defaultdict(float)
    for t, w in weights.items():
        sec = fundamentals[t].get("sector", "Unknown")
        sector_map[sec] += w

    sector_map = {k: safe_round(v, 3) for k, v in sector_map.items()}

    return {
        "weighted_pe": weighted_pe,
        "weighted_forward_pe": weighted_forward_pe,
        "weighted_peg": weighted_peg,
        "weighted_roe": weighted_roe,
        "weighted_roa": weighted_roa,
        "weighted_margin": weighted_margin,
        "weighted_beta": weighted_beta,
        "weighted_de": weighted_de,
        "weighted_div_yield": weighted_div_yield,
        "sector_weights": sector_map,
        "holdings": len(weights),
    }