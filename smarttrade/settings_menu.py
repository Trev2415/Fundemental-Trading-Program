from colorama import Fore, Style
from smarttrade_core import load_portfolio, save_portfolio
import os
import sys

PORTFOLIO_JSON = "portfolio.json"

def settings_menu(portfolio, cash, txns, live_mode):
    while True:
        print("\n[ Settings ]")
        print("1) Save portfolio")
        print("2) Load portfolio")
        print("3) Toggle live prices")
        print("4) Reset portfolio")
        print("5) Return to main menu")

        choice = input("Select: ").strip()

        # 1) SAVE PORTFOLIO
        if choice == "1":
            save_portfolio(PORTFOLIO_JSON, portfolio, cash, txns)
            print("Portfolio saved successfully.")

        # 2) LOAD PORTFOLIO
        elif choice == "2":
            portfolio, cash, txns = load_portfolio(PORTFOLIO_JSON)
            print("Portfolio loaded. Cash:", f"${cash:,.2f}")

        # 3) TOGGLE LIVE PRICE MODE
        elif choice == "3":
            live_mode = not live_mode
            print("Live prices are now:", "ON" if live_mode else "OFF")

        # 4) RESET PORTFOLIO
        elif choice == "4":
            confirm = input(
                Fore.RED + "Reset portfolio to default? (y/n): " + Style.RESET_ALL
            ).lower()

            if confirm == "y":
                portfolio = {}
                cash = 100000.0
                txns = []
                print(Fore.YELLOW + "Portfolio has been reset." + Style.RESET_ALL)
            else:
                print("Reset cancelled.")

        # 5) RETURN TO MAIN MENU
        elif choice == "5":
            return portfolio, cash, txns, live_mode

        # INVALID INPUT
        else:
            print("Invalid selection. Try again.")