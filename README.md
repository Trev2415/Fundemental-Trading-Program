# SmartTrade – Deliverable 2

### To Run Program:
cd .\smarttrade; py .\main.py


## Executive Summary
Most new retail investors rely on hype, news headlines, or social media rather than objective financial analysis. This behavior increases speculative trading and leads to poor outcomes especially for beginners who lack the tools to evaluate companies properly. SmartTrade seeks to fix this by combining **financial education**, **fundamental analysis**, **portfolio tracking**, and **AI-driven market insights** into a single simulation platform.

Deliverable 2 significantly expands the prototype created in Deliverable 1. The program now features deeper menu systems, expanded company and portfolio analytics, historical price analysis, S&P 500 and sector comparison tools, additional financial ratios, and a redesigned save/load/settings system. Most importantly, SmartTrade now integrates **Generative AI**, which summarizes company fundamentals, news, macroeconomic conditions, sector risks/catalysts, and overall portfolio strengths and weaknesses.

SmartTrade now functions as a guided learning environment where users analyze companies, simulate trades, compare investments to benchmarks, and learn long-term investing principles through AI-powered insights. These enhancements transform the program from a simple lookup tool into a full educational investment simulator.

---

## Statement of Scope (Revised for Deliverable 2)
The scope for Deliverable 2 expands significantly beyond the original functionality. SmartTrade now includes:

### 1. Advanced Company Analysis Menu
- Multi-period historical price lookup  
- Company performance comparison vs S&P 500 index  
- Company performance comparison vs Sector ETF  
- Extra metrics panel including:  
  - ROE  
  - ROA  
  - PEG  
  - Net Margin  
  - Beta  
  - Debt-to-Equity trend  
- AI sector summary describing long-term outlook, catalysts, and risks  
- AI fundamentals summary using both fundamentals + Yahoo Finance news  

### 2. Expanded Portfolio Analytics
- Weighted P/E  
- Weighted Forward P/E  
- Weighted PEG  
- Weighted ROE  
- Weighted ROA  
- Weighted Net Margin  
- Weighted Beta  
- Weighted Debt/Equity  
- Weighted Dividend Yield  
- Sector diversification chart/data   
- AI portfolio summary (strengths, weaknesses, concentration risk, style bias)  

### 3. Generative AI Integration
AI now provides:
- Company summary (fundamentals + news + macro)
- Sector summary (catalysts, risks, macro themes)
- Portfolio SWOT analysis
- Education-style explanations for financial metrics

### 4. New Save/Load/Settings Menu
A new **Settings Menu** was added with:
- Save Slot 1 / Save Slot 2 / Save Slot 3  
- Load Saved Game  
- Restart Simulation  
- Toggle Live Pricing  
- Quit Application  

###  Out of Scope
The following remain out-of-scope:
- Real brokerage integration  
- Real-money execution  
- Options/futures  
- Tax accounting  
- Fully automated trading algorithms  

---

# Inputs, Processes, and Outputs (Updated IPO)

## Inputs
- Stock ticker symbols  
- Quantity of shares  
- User’s menu selections  
- User prompts for AI summaries  
- Time period for historical price lookup  
- Save/load slot choices  
- Toggle selections for settings  

## Processes
1. **Load Fundamentals**  
   Uses Yahoo Finance to pull PE, ROE, ROA, PEG, margins, beta, debt/equity, dividends, and sector.

2. **Historical & Benchmark Analysis**  
   Pulls time-series prices, S&P 500 index prices, and sector ETF data.

3. **Portfolio Calculations**  
   - Total market value  
   - Profit/loss  
   - Weighted valuation metrics  
   - Sector exposure  
   - Index/mutual fund comparison  

4. **AI Summaries**  
   - Fundamental interpretation  
   - Macro & news interpretation  
   - Sector risk/catalyst reporting  
   - Portfolio strengths/weaknesses  

5. **Simulation Engine**  
   Buy/sell shares and update portfolio JSON.

6. **Save/Load System**  
   Stores and loads user data in JSON files.

7. **Settings Engine**  
   Restart, toggle live prices, quit program, choose save slots.

## Outputs
- Company dashboard  
- Historical chart data  
- Comparison results vs S&P 500 and sector  
- Expanded portfolio metrics  
- AI-written summaries  
- Updated portfolio state  
- Profit/loss breakdown  

---

# Function Dictionary (Updated)

| Function Name | Inputs | Process | Outputs | AI? |
|---------------|--------|---------|---------|-----|
| `get_live_metrics_yf()` | ticker | Fetch live price data | dict with price info | No |
| `get_portfolio_fundamentals()` | portfolio OR ticker | Fetches PE, ROE, ROA, PEG, margins, beta, etc. | Stores fundamentals in portfolio | No |
| `aggregate_metrics()` | portfolio | Calculates weighted metrics | dict of weighted metrics | No |
| `view_portfolio()` | portfolio, cash | Displays holdings & weighted metrics | Portfolio dashboard | No |
| `view_expanded_metrics()` | portfolio | Shows full detailed metrics | Advanced metrics screen | No |
| `view_historical_prices()` | ticker, period | Pulls past price history | List or formatted display | No |
| `compare_vs_sp500()` | ticker | Fetches SPY/S&P data for comparison | Relative performance | No |
| `compare_vs_sector()` | ticker | Locate sector ETF and compare | Sector-relative performance | No |
| `extra_metrics_menu()` | ticker | Display ROE/ROA/PEG/margin trends | Extended company metrics | No |
| `ai_company_summary()` | ticker, fundament., news | AI summarizing valuation, catalysts, risks | Text summary | YES |
| `ai_sector_summary()` | sector | Summaries of outlook & risks | Text summary | YES |
| `ai_portfolio_summary()` | portfolio dict | AI-generated SWOT & risk analysis | Text summary | YES |
| `settings_menu()` | user input | Save/load/restart/toggle settings | Updated state | No |
| `save_portfolio()` | slot # | Writes JSON | Confirmation message | No |
| `load_portfolio()` | slot # | Loads JSON | Portfolio dict | No |

---

# Generative AI Integration

## Purpose
The goal of integrating AI is to turn SmartTrade into an educational financial assistant. AI helps users interpret raw data, understand fundamentals, and recognize market trends that might otherwise be confusing.

## AI Attributes (4 Required, 5 Given)
1. **Fundamentals-Aware**  
   AI interprets metrics like PE, ROE, ROA, margins, debt/equity, and PEG.

2. **Macro-Sensitive**  
   AI uses news headlines and economic context from Yahoo Finance.

3. **Sector-Contextual**  
   AI evaluates industry outlook, supply chain risks, revenue tailwinds, etc.

4. **Portfolio-Evaluative**  
   AI points out overexposure, diversification problems, and risk balance.

5. **Educational** *(bonus attribute)*  
   AI can explain investment concepts in plain English.

## New AI Function Example

```python
def ai_company_summary(ticker, fundamentals, news_blob):
    prompt = f"""
    Analyze {ticker} using the following information:

    Fundamentals:
    {fundamentals}

    Recent News:
    {news_blob}

    Provide a 4–6 sentence summary addressing:
    - valuation (cheap/expensive relative to history)
    - financial health and key weaknesses
    - catalysts and upcoming risks
    - macroeconomic influences on the company
    """

    return ai_ask_cramer("ANALYSIS", prompt)

```
## Documentation Updates

- IPO now includes AI processes.
- Function dictionary lists all AI functions.
- Menu system incorporates AI prompts at both company and portfolio levels.

# Conclusion & Discussion

## Overall Experience
This project was both challenging and rewarding. Developing SmartTrade pushed my understanding of Python, data management, APIs, and generative AI integration. Watching the program evolve from a simple fundamentals lookup tool into a multi-layered investment simulator was extremely satisfying and intrinsically rewarding it made me push the bounds of what I thought I could do.

## What I Enjoyed
- Integrating real financial data from Yahoo Finance  
- Building expanded portfolio metrics and weighting calculations  
- Creating new menu systems and improving UI flow  
- Using AI to automatically summarize real market information  

## What Was Difficult
- Debugging missing data in Yahoo Finance  
- Cleaning fundamentals such as ROE, ROA, and PEG  
- Designing a menu structure that balances complexity and usability  
- Ensuring accuracy and mathematical correctness in weighted portfolio metrics
- Overall Live Metrics was the hardest most difficult thing I think I've ever done  

## Original Vision vs Final Product
Originally, SmartTrade was intended to be a simple fundamentals lookup engine with a trade simulator.  
The final product is far more advanced:

- AI financial analyst integration  
- Sector/index comparison tools  
- Historical charting and performance benchmarking  
- Weighted portfolio analytics and expanded financial ratios  
- Enhanced company fundamentals engine  
- Full settings/save/load/menu overhaul  

The project grew in scope as my understanding of financial data and technical capabilities increased.

## Lessons Learned
- Clear modular design makes large projects maintainable  
- IPO planning is essential for controlling project complexity  
- Generative AI requires thoughtful prompt engineering to be effective  
- Debugging live financial APIs teaches patience and adaptability  
- Iterative development leads to significantly better final results  