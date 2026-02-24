import time
import yfinance as yf

# Caching Layer

_CACHE = {}
_TTL = 15  # seconds

def set_ttl(seconds: int):
    """Allow user to change cache duration."""
    global _TTL
    _TTL = max(1, int(seconds))

def clear_cache():
    _CACHE.clear()

def _now():
    return int(time.time())

def _norm(t):
    """
    Normalize tickers to formats yfinance accepts.
    """
    if not t:
        return ""
    t = t.strip().upper().replace(" ", "")

    SUBS = {
        "BRK.B": "BRK-B",
        "BRK/B": "BRK-B",
        "BF.B":  "BF-B",
        "BF/B":  "BF-B",
    }
    return SUBS.get(t, t)

def _cache_get(t):
    hit = _CACHE.get(t)
    if hit and _now() - hit["ts"] <= _TTL:
        return hit
    return None

def _cache_put(t, blob):
    _CACHE[t] = blob

# MAIN LIVE PRICE ENGINE

def get_live_metrics_yf(ticker: str, retries=2, sleep_s=0.15):
    """
    Returns dict:
        {
          "px": float,
          "prev_close": float,
          "change": float (%),
          "arrow": "▲" | "▼" | "→",
          "ts": timestamp
        }

    Fully compatible with SmartTrade 2025.
    """
    t = _norm(ticker)

    # -------------- CACHE HIT --------------
    hit = _cache_get(t)
    if hit:
        return hit

    last_exc = None

    for _ in range(max(1, retries)):
        try:
            tk = yf.Ticker(t)

            # -------------- TRY FAST_INFO --------------
            px = None
            prev = None

            fi = getattr(tk, "fast_info", None)
            if fi:
                px = (
                    fi.get("last_price") or
                    fi.get("last_trade") or
                    fi.get("last_close")
                )
                prev = fi.get("previous_close")

            # -------------- FALLBACK: HISTORY --------------
            if px is None or prev is None:
                hist = tk.history(period="1mo")  
                if not hist.empty:
                    px = float(hist["Close"].iloc[-1])
                    if len(hist) >= 2:
                        prev = float(hist["Close"].iloc[-2])
                    else:
                        prev = px

            if px is None:
                raise RuntimeError("no price data found")

            px = float(px)
            prev = float(prev)

            change_pct = ((px - prev) / prev * 100) if prev else 0
            arrow = "▲" if change_pct > 0 else ("▼" if change_pct < 0 else "→")

            blob = {
                "px": round(px, 2),
                "prev_close": round(prev, 2),
                "change": round(change_pct, 2),
                "arrow": arrow,
                "ts": _now(),
            }

            _cache_put(t, blob)
            return blob

        except Exception as e:
            last_exc = e
            if sleep_s > 0:
                time.sleep(sleep_s)

    raise RuntimeError(f"[Live Price Error] Could not fetch {t}: {last_exc}")

# PRICE-ONLY COMPATIBILITY FUNCTION

def get_price_yf(ticker: str) -> float:
    """
    Legacy function for modules expecting only price.
    """
    return get_live_metrics_yf(ticker)["px"]