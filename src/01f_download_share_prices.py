"""Download daily share prices for Seven & i, its peers and a market benchmark (Yahoo Finance)."""
import yfinance as yf
from config import RAW

OUT = RAW / "prices"
OUT.mkdir(parents=True, exist_ok=True)

TICKERS = {
    "3382.T": "Seven & i Holdings",
    "1306.T": "TOPIX ETF (Japanese market benchmark)",
    "ATD.TO": "Alimentation Couche-Tard",
    "CASY": "Casey's General Stores (US convenience peer)",
    "MUSA": "Murphy USA (US convenience peer)",
    "2651.T": "Lawson (delisted 2024; may be unavailable)",
}

for ticker, name in TICKERS.items():
    df = yf.download(ticker, start="2015-01-01", auto_adjust=False, progress=False)
    if df.empty:
        print(f"  {ticker} ({name}): no data")
        continue
    df.columns = df.columns.get_level_values(0)
    df.to_csv(OUT / f"{ticker.replace('.', '_')}.csv")
    print(f"  {ticker} ({name}): {len(df):,} days, {df.index.min():%Y-%m-%d} to {df.index.max():%Y-%m-%d}")
