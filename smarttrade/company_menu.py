import warnings
warnings.filterwarnings("ignore", category=FutureWarning)

from colorama import Fore, Style
from live_prices import get_live_metrics_yf
from ai_tools import ai_company_summary, ai_ask_cramer
from smarttrade_core import buy_shares, sell_shares

from fundamentals_engine import (
    get_fundamentals,
    compare_sector_and_market
)

import yfinance as yf

# Formatting Helpers

def fmt_money(x):
    try:
        return f"${float(x):,.2f}"
    except:
        return "--"

def fmt_num(x):
    try:
        x = float(x)
    except:
        return "--"
    if x >= 1e12:
        return f"{x/1e12:.2f}T"
    if x >= 1e9:
        return f"{x/1e9:.2f}B"
    if x >= 1e6:
        return f"{x/1e6:.2f}M"
    return f"{x:.2f}"

def fmt_pct(x):
    try:
        return f"{float(x)*100:.2f}%"
    except:
        return "--"

# FULL FUNDAMENTALS REPORT

def show_full_fundamentals(ticker):
    data = get_fundamentals(ticker)
    t = ticker.upper()

    long_name = data.get("longName", t)
    sector = data.get("sector", "Unknown")

    try:
        tk = yf.Ticker(t)
        hist = tk.history(period="2d")

        if len(hist) >= 2:
            px_now = float(hist["Close"].iloc[-1])
            px_prev = float(hist["Close"].iloc[-2])
            diff = px_now - px_prev
            pct = (diff / px_prev) * 100 if px_prev else 0
        else:
            px_now = data.get("price") or 0
            diff = 0
            pct = 0

    except:
        px_now = data.get("price") or 0
        diff = 0
        pct = 0

    arrow = "▲" if diff > 0 else ("▼" if diff < 0 else "→")
    col = Fore.GREEN if diff > 0 else (Fore.RED if diff < 0 else Style.RESET_ALL)

    print(f"\n{long_name} ({t}) — Sector: {sector}")
    print(
        col
        + f"Price: {fmt_money(px_now)} {arrow} {fmt_money(diff)} ({pct:+.2f}%)"
        + Style.RESET_ALL
    )

    fNum = fmt_num
    fPct = fmt_pct

    print("\nValuation & Risk")
    print(f"{'Metric':<28}{'Value':>15}")
    print("-" * 45)
    print(f"{'Market Cap':<28}{fNum(data.get('marketCap')):>15}")
    print(f"{'Trailing P/E':<28}{fNum(data.get('trailingPE')):>15}")
    print(f"{'Forward P/E':<28}{fNum(data.get('forwardPE')):>15}")

    # SAFE PEG DISPLAY 
    
    peg_val = data.get("pegRatio")

    if peg_val is None:
        peg_display = "--"
    else:
        try:
            peg_float = float(peg_val)
            if peg_float <= 0 or peg_float > 200:   # remove insane PEG values
                peg_display = "--"
            else:
                peg_display = f"{peg_float:.2f}"
        except:
            peg_display = "--"

    print(f"{'PEG Ratio':<28}{peg_display:>15}")

    print(f"{'Beta':<28}{fNum(data.get('beta')):>15}")

    print("\nFinancial Health & Returns")
    print(f"{'Metric':<28}{'Value':>15}")
    print("-" * 45)
    print(f"{'Revenue (TTM)':<28}{fNum(data.get('revenueTTM')):>15}")
    print(f"{'Net Income (TTM)':<28}{fNum(data.get('incomeTTM')):>15}")
    print(f"{'Net Margin':<28}{fPct(data.get('netMargin')):>15}")
    print(f"{'ROA':<28}{fPct(data.get('roaTTM')):>15}")
    print(f"{'ROE':<28}{fPct(data.get('roeTTM')):>15}")
    print(f"{'Debt/Equity':<28}{fNum(data.get('debtToEquity')):>15}")
    print(f"{'Current Ratio':<28}{fNum(data.get('currentRatio')):>15}")

    print("\nDividends")
    print(f"{'Dividend per Share':<28}{fNum(data.get('dividendPerShare')):>15}")
    print(f"{'Dividend Yield':<28}{fPct(data.get('dividendYield')):>15}")

    print("\n" + "-" * 75)
    print("Historical Quarterly Results")
    print(f"{'Quarter':<12}{'Revenue':>16}{'Net Income':>16}{'EPS (Normalized)':>20}")
    print("-" * 75)

    quarters = data.get("quarters", [])

    for q in quarters:
        label = q.get("label")
        rev = q.get("revenue")
        inc = q.get("income")
        eps = q.get("eps")
        est = q.get("eps_est")

        rev_str = f"{rev/1e9:.3f}B" if rev else "--"
        inc_str = f"{inc/1e9:.3f}B" if inc else "--"

        if eps is None:
            eps_str = "--"
            col_eps = Style.RESET_ALL
        else:
            if est not in (None, 0):
                diff_eps = eps - est
                col_eps = Fore.GREEN if diff_eps > 0 else Fore.RED
                eps_str = f"{eps:.2f} ({diff_eps:+.2f})"
            else:
                col_eps = Style.RESET_ALL
                eps_str = f"{eps:.2f}"

        print(
            f"{label:<12}"
            f"{rev_str:>16}"
            f"{inc_str:>16}"
            f"{col_eps}{eps_str:>20}{Style.RESET_ALL}"
        )

    print("\nProjected Quarterly Results (Volatility Adjusted)")
    print(f"{'Quarter':<12}{'Revenue':>16}{'EPS':>15}")
    print("-" * 55)

    projections = data.get("projections", [])
    if projections:
        for p in projections:
            print(
                f"{p['label']:<12}"
                f"{p['revenue']/1e9:>16.3f}B"
                f"{p['eps']:>15.2f}"
            )
    else:
        print("No projection engine found.")

# MAIN COMPANY MENU 

def company_analysis_menu(ticker, portfolio, cash, txns):
    ticker = ticker.upper()

    while True:
        print("\n[ Company Research Menu ]")
        print("1) CramerBot Company Report")
        print("2) Fundamentals Report (with EPS + projections)")
        print("3) Ask CramerBot")
        print("4) Sector & Market Comparison")
        print("5) Buy/Sell Stock")
        print("6) Return to Main Menu")

        choice = input("Select: ").strip()

        if choice == "1":
            print("\nCramerBot Company Report\n")
            data = get_fundamentals(ticker)      # <-- GET FUNDAMENTALS
            print(ai_company_summary(ticker, fundamentals=data))

        elif choice == "2":
            show_full_fundamentals(ticker)

        elif choice == "3":
            q = input("Ask CramerBot a question: ").strip()
            if q:
                print("\nCramerBot Response:\n")
                print(ai_ask_cramer(ticker, q))

        elif choice == "4":
            compare_sector_and_market(ticker)

        elif choice == "5":
            px = get_live_metrics_yf(ticker)["px"]
            pos = portfolio.get(ticker)

            if pos and pos["shares"] > 0:
                print(f"You own {pos['shares']} shares.")
                print("1) Buy more")
                print("2) Sell")
                action = input("Select: ").strip()

                if action == "1":
                    qty = int(input("Shares to buy: "))
                    ok, msg, portfolio, cash, txns = buy_shares(
                        ticker, qty, px, portfolio, cash, txns
                    )
                    print(msg, "| Cash:", fmt_money(cash))

                elif action == "2":
                    qty = int(input("Shares to sell: "))
                    ok, msg, portfolio, cash, txns = sell_shares(
                        ticker, qty, px, portfolio, cash, txns
                    )
                    print(msg, "| Cash:", fmt_money(cash))

            else:
                qty = int(input("Shares to buy: "))
                ok, msg, portfolio, cash, txns = buy_shares(
                    ticker, qty, px, portfolio, cash, txns
                )
                print(msg, "| Cash:", fmt_money(cash))

        elif choice == "6":
            return portfolio, cash, txns

        else:
            print("Invalid selection.")