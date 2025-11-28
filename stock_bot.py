import os
import pandas as pd
from io import StringIO

import yfinance as yf
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()

NAME_TO_SYMBOL = {
    "apple": "AAPL",
    "google": "GOOGL",
    "alphabet": "GOOGL",
    "microsoft": "MSFT",
    "tesla": "TSLA",
    "amazon": "AMZN",
    "nvidia": "NVDA",
    "meta": "META",
    "facebook": "META",
    "netflix": "NFLX",
}

def get_stock_symbol(company_or_symbol: str) -> str:
    q = company_or_symbol.strip()
    if not q:
        return q

    key = q.lower()

    if key in NAME_TO_SYMBOL:
        return NAME_TO_SYMBOL[key]

    looks_like_ticker = (
        q == q.upper()
        and len(q) <= 10
        and all(c.isalnum() or c in ".-" for c in q)
    )
    if looks_like_ticker:
        return q

    # 3) Otherwise, attempt Yahoo search via yfinance
    try:
        results = yf.Search(q, max_results=10).quotes  # list of dicts
        if results:
            # Prefer an EQUITY result if available
            best = next(
                (r for r in results if str(r.get("quoteType", "")).upper() == "EQUITY"),
                results[0],
            )
            symbol = best.get("symbol")
            if symbol:
                return symbol
    except Exception:
        pass

    return q.upper()

def safe_float(x):
    try:
        if x is None:
            return None
        return float(str(x).replace(",", "").strip())
    except Exception:
        return None

def build_stock_message(query: str) -> str:
    symbol = get_stock_symbol(query)
    t = yf.Ticker(symbol)

    fast = getattr(t, "fast_info", {}) or {}
    hist = t.history(period="5d", interval="1d")

    if hist is None or hist.empty:
        raise RuntimeError(f"No price history returned (symbol may be invalid): {symbol}")

    current_price = safe_float(fast.get("last_price")) or safe_float(fast.get("lastPrice"))
    if current_price is None:
        current_price = float(hist["Close"].iloc[-1])

    if len(hist) >= 2:
        prev_close = float(hist["Close"].iloc[-2])
    else:
        prev_close = float(hist["Close"].iloc[-1])

    day_low = safe_float(fast.get("day_low")) or safe_float(fast.get("dayLow"))
    day_high = safe_float(fast.get("day_high")) or safe_float(fast.get("dayHigh"))
    if day_low is None:
        day_low = float(hist["Low"].iloc[-1])
    if day_high is None:
        day_high = float(hist["High"].iloc[-1])

    change = current_price - prev_close
    pct_change = (change / prev_close) * 100 if prev_close else None

    if pct_change is None:
        emoji = "❓"
    elif abs(pct_change) < 0.01:  # treat tiny moves as flat
        emoji = "➖"
    elif pct_change > 0:
        emoji = "🔺"
    else:
        emoji = "🔻"

    sign = "+" if change > 0 else ""

    summary = {
        "Current Price": f"${current_price:.2f}",
        "Previous Close": f"${prev_close:.2f}",
        "Change": f"{sign}${change:.2f} ({sign}{pct_change:.2f}%)" if pct_change is not None else "N/A",
        "Day Range": f"{day_low:.2f} - {day_high:.2f}",
    }
    _df = pd.DataFrame(list(summary.items()), columns=["Attribute", "Value"])

    buf = StringIO()
    buf.write(f"Company: {query}\n")
    buf.write(f"Symbol: {symbol}\n")
    buf.write(f"Current Price: ${current_price:.2f}\n")
    buf.write(f"Previous Close: ${prev_close:.2f}\n")
    if pct_change is not None:
        buf.write(f"Change: {emoji} {sign}${change:.2f} ({sign}{pct_change:.2f}%)\n")
    else:
        buf.write("Change: ❓ N/A\n")
    buf.write(f"Day's Range: ${day_low:.2f} - ${day_high:.2f}\n")

    return buf.getvalue()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Welcome to the Stock Market Bot!\n"
        "Use: /stock <company or symbol>\n"
        "Examples: /stock netflix   or   /stock NFLX"
    )

async def stock(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text("Usage: /stock <company or symbol> (e.g., /stock netflix)")
        return

    query = " ".join(context.args).strip()

    try:
        msg = build_stock_message(query)
        await update.message.reply_text(msg)
    except Exception as e:
        await update.message.reply_text(f"Error fetching stock data: {e}")

def main() -> None:
    if not TOKEN:
        raise RuntimeError(
            "Missing TELEGRAM_BOT_TOKEN.\n"
            "PowerShell: $env:TELEGRAM_BOT_TOKEN='your_token_here'\n"
        )

    app = ApplicationBuilder().token(TOKEN).job_queue(None).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stock", stock))

    print("Bot running... Ctrl+C to stop.")
    app.run_polling()

if __name__ == "__main__":
    main()
