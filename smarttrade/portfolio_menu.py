import shutil
from colorama import Fore, Style
from smarttrade_core import (
    buy_shares,
    sell_shares,
    aggregate_metrics,
)
from live_prices import get_live_metrics_yf
from ai_tools import ai_ask_cramer
from fundamentals_live import get_portfolio_fundamentals


def fmt_money(x):
    try:
        return f"${float(x):,.2f}"
    except:
        return "--"


def fmt_pct(x):
    try:
        return f"{float(x) * 100:.2f}%"
    except:
        return "--"


def fmt_none(x):
    return "--" if x is None else str(x)


def line():
    width = shutil.get_terminal_size((80, 20)).columns
    width = min(width, 100)
    print("=" * width)

# UNIVERSAL LIVE PRICE FETCHER
def get_px_safe(ticker):
    try:
        m = get_live_metrics_yf(ticker)

        px = (
            m.get("px")
            or m.get("price")
            or m.get("current")
            or m.get("regularMarketPrice")
            or m.get("last")
        )

        if px is None:
            raise Exception("no live price")

        return float(px)

    except:
        return None

# TRADE MENU

def trade_menu(ticker, portfolio, cash, txns):
    line()
    print(f"[ Trade {ticker} ]")
    line()

    price = get_px_safe(ticker)

    print(f"Current Price: {fmt_money(price)}\n")
    print("1) Buy")
    print("2) Sell")
    print("3) Cancel\n")

    choice = input("Select: ").strip()

    if choice == "1":
        qty = int(input("Shares to buy: "))
        ok, msg, portfolio, cash, txns = buy_shares(
            ticker, qty, price, portfolio, cash, txns
        )
        print(msg)

    elif choice == "2":
        qty = int(input("Shares to sell: "))
        ok, msg, portfolio, cash, txns = sell_shares(
            ticker, qty, price, portfolio, cash, txns
        )
        print(msg)

    input("\nPress ENTER to return...")
    return portfolio, cash, txns

# PORTFOLIO VIEW
def view_portfolio(portfolio, cash, txns):
    line()
    print("[ Portfolio & Analytics ]")
    line()

    mv = 0
    live_prices = {}

    # ---------- PORTFOLIO LIVE PRICES ----------
    for t, pos in portfolio.items():
        px = get_px_safe(t) or pos["avg_cost"]
        live_prices[t] = px
        mv += px * pos["shares"]

    total_value = cash + mv

    print(
        f"Cash: {fmt_money(cash)}   |   "
        f"Portfolio MV: {fmt_money(mv)}   |   "
        f"Total Value: {fmt_money(total_value)}"
    )
    print("-" * 60)

    # ---------- HOLDINGS ----------
    print("HOLDINGS\n")

    if not portfolio:
        print("No holdings yet.")
    else:
        for t, pos in portfolio.items():
            px = live_prices[t]

            mv_t = px * pos["shares"]
            pnl = (px - pos["avg_cost"]) * pos["shares"]
            pnl_pct = pnl / (pos["avg_cost"] * pos["shares"]) if pos["avg_cost"] else 0

            color = Fore.GREEN if pnl > 0 else Fore.RED if pnl < 0 else Style.RESET_ALL

            print(
                color +
                f"{t:<5}  "
                f"Sh:{pos['shares']}  "
                f"Avg:{fmt_money(pos['avg_cost'])}  "
                f"MV:{fmt_money(mv_t)}  "
                f"P/L:{fmt_money(pnl)} ({pnl_pct:.2%})"
                + Style.RESET_ALL
            )

    # ---------- WEIGHTED METRICS ----------
    print("\n-----------  WEIGHTED METRICS (Key) -----------")
    metrics = aggregate_metrics(portfolio)

    print(f"P/E:            {fmt_none(metrics['weighted_pe'])}")
    print(f"Forward P/E:    {fmt_none(metrics['weighted_forward_pe'])}")
    print(f"PEG:            {fmt_none(metrics['weighted_peg'])}")
    print(f"ROE:            {fmt_pct(metrics['weighted_roe'])}")
    print(f"ROA:            {fmt_pct(metrics['weighted_roa'])}")
    print(f"Margin:         {fmt_pct(metrics['weighted_margin'])}")

    # ---------- SECTOR BREAKDOWN ----------
    print("\n-----------  SECTOR BREAKDOWN  -----------")
    if metrics["sector_weights"]:
        for s, w in metrics["sector_weights"].items():
            print(f" - {s}: {w * 100:.2f}%")
    else:
        print(" - No sector data available")

    # ---------- SINGLE CRAMER SUMMARY ----------
    print("\n-----------  PORTFOLIO SUMMARY (CramerBot) -----------")
    try:
        holdings_str = ", ".join(
            f"{t} ({pos['shares']} sh)"
            for t, pos in portfolio.items()
        ) or "no current holdings"

        summary_prompt = (
            "Give a concise 3–5 sentence summary of this stock portfolio. "
            f"Total value is {fmt_money(total_value)}. "
            f"Holdings: {holdings_str}. "
            "Comment on diversification, valuation (P/E, PEG), risk, and strengths/weaknesses."
        )

        cramer_text = ai_ask_cramer("PORTFOLIO", summary_prompt)
        print(cramer_text)

    except Exception as e:
        print("CramerBot summary unavailable:", e)

    line()

    return

# EXPANDED METRICS
def view_expanded_metrics(portfolio):
    metrics = aggregate_metrics(portfolio)

    line()
    print("[ Weighted Metrics (Expanded) ]")
    line()

    print(f"Weighted P/E:              {fmt_none(metrics['weighted_pe'])}")
    print(f"Weighted Forward P/E:      {fmt_none(metrics['weighted_forward_pe'])}")
    print(f"Weighted PEG:              {fmt_none(metrics['weighted_peg'])}")
    print(f"Weighted ROE:              {fmt_pct(metrics['weighted_roe'])}")
    print(f"Weighted ROA:              {fmt_pct(metrics['weighted_roa'])}")
    print(f"Weighted Net Margin:       {fmt_pct(metrics['weighted_margin'])}")
    print(f"Weighted Dividend Yield:   {fmt_pct(metrics['weighted_div_yield'])}")
    print(f"Weighted Debt/Equity:      {fmt_none(metrics['weighted_de'])}")
    print(f"Weighted Beta:             {fmt_none(metrics['weighted_beta'])}")

    print("\nSector Allocation:")
    for sec, w in metrics["sector_weights"].items():
        print(f" - {sec}: {w * 100:.2f}%")

    line()
    input("\nPress ENTER to return...")

# ASK CRAMERBOT
def ask_cramerbot():
    q = input("\nAsk CramerBot: ").strip()
    if not q:
        return

    try:
        print("\nCramerBot Says:\n")
        print(ai_ask_cramer("PORTFOLIO", q))
    except Exception as e:
        print("CramerBot unavailable:", e)

    input("\nPress ENTER to return...")

# MAIN MENU
def portfolio_menu(portfolio, cash, txns):
    while True:
        print("\n[ Portfolio Menu ]")
        print("1) View Portfolio")
        print("2) Weighted Metrics (Expanded)")
        print("3) Ask CramerBot")
        print("4) Buy/Sell Stock")
        print("5) Return to Main Menu")

        choice = input("Select: ").strip()

        if choice == "1":
            view_portfolio(portfolio, cash, txns)

        elif choice == "2":
            view_expanded_metrics(portfolio)

        elif choice == "3":
            ask_cramerbot()

        elif choice == "4":
            ticker = input("Enter ticker: ").upper().strip()
            if ticker:
                portfolio, cash, txns = trade_menu(
                    ticker, portfolio, cash, txns
                )

        elif choice == "5":
            return portfolio, cash, txns

        else:
            print("Invalid choice.")