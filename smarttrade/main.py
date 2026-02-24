import os
import shutil
from colorama import init

from smarttrade_core import (
    load_portfolio,
    save_portfolio,
)
from portfolio_menu import portfolio_menu
from company_menu import company_analysis_menu

init(autoreset=True)

PORTFOLIO_JSON = "portfolio.json"

# Formatting Helpers
def clear():
    os.system("cls" if os.name == "nt" else "clear")


def fmt_money(x):
    try:
        return f"${float(x):,.2f}"
    except:
        return "--"


def banner():
    width = shutil.get_terminal_size((80, 20)).columns
    width = min(width, 100)

    line = "═" * width
    title = "SmartTrade — Fundamentals First Trading Simulator"
    subtitle = "CramerBot Insights • Live Metrics • Real Time Portfolio Analytics"

    print(line)
    print(title.center(width))
    print(subtitle.center(width))
    print(line)


def print_main_menu():
    print("\n[ Main Menu ]")
    print(" 1) Company Research")
    print(" 2) Portfolio & Analytics")
    print(" 3) Settings")
    print(" 4) Quit")

# Settings Menu
def settings_menu(portfolio, cash, txns, live_mode):

    while True:
        print("\n[ Settings ]")
        print(f"1) Toggle Live Prices (currently: {'ON' if live_mode else 'OFF'})")
        print("2) Save Portfolio")
        print("3) Load Portfolio")
        print("4) Reset Portfolio")
        print("5) Return To Main Menu")

        choice = input("Select: ").strip()

        # VALID CHOICES

        if choice == "1":
            live_mode = not live_mode
            print("Live Prices:", "ON" if live_mode else "OFF")

        elif choice == "2":
            save_portfolio(PORTFOLIO_JSON, portfolio, cash, txns)
            print("Portfolio saved.")

        elif choice == "3":
            portfolio, cash, txns = load_portfolio(PORTFOLIO_JSON)
            print("Portfolio loaded.")

        elif choice == "4":
            confirm = input("Reset portfolio to default? (y/n): ").lower()
            if confirm == "y":
                portfolio = {}
                cash = 100000.0
                txns = []
                print("Portfolio reset.")

        elif choice == "5":
            return portfolio, cash, txns, live_mode

        else:
            print("Invalid selection.")

# MAIN APPLICATION LOOP

def main():
    portfolio, cash, txns = load_portfolio(PORTFOLIO_JSON)
    live_mode = True

    clear()
    banner()
    print("Starting Cash:", fmt_money(cash))

    while True:
        print_main_menu()
        choice = input("Select: ").strip()

        # 1) COMPANY RESEARCH
        if choice == "1":
            ticker = input("Enter ticker: ").strip().upper()
            if not ticker:
                print("Please enter a ticker.")
                continue

            result = company_analysis_menu(ticker, portfolio, cash, txns)
            if result:
                portfolio, cash, txns = result

        # 2) PORTFOLIO MENU
        elif choice == "2":
            result = portfolio_menu(portfolio, cash, txns)
            if result:
                portfolio, cash, txns = result

        # 3) SETTINGS
        elif choice == "3":
            portfolio, cash, txns, live_mode = settings_menu(
                portfolio, cash, txns, live_mode
            )

        # 4) QUIT
        elif choice == "4":
            print("Goodbye.")
            break

        else:
            print("Invalid selection.")

# ENTRY POINT
if __name__ == "__main__":
    main()