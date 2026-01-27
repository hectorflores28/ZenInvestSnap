import yfinance as yf
from decimal import Decimal

def get_current_price(ticker, asset_type):
    """
    Fetches the current price of an asset based on its type.
    For STOCK, ETF, and CRYPTO, it uses yfinance.
    """
    if asset_type in ['STOCK', 'ETF', 'CRYPTO']:
        try:
            # yfinance handles tickers like 'AAPL' or 'BTC-USD'
            # If asset is crypto, ensure ticker has '-USD' if not present, or assume user provides full ticker
            # Helper: if type is CRYPTO and no hyphen, append -USD (simple heuristic, can be improved)
            lookup_ticker = ticker
            if asset_type == 'CRYPTO' and '-' not in ticker:
                lookup_ticker = f"{ticker}-USD"
            
            ticker_obj = yf.Ticker(lookup_ticker)
            # Try fast info first
            price = ticker_obj.fast_info.last_price
            if price is None:
                 # Fallback to history
                 hist = ticker_obj.history(period="1d")
                 if not hist.empty:
                     price = hist['Close'].iloc[-1]
            
            if price:
                return Decimal(str(price))
        except Exception as e:
            print(f"Error fetching price for {ticker}: {e}")
            return None
            
    # Placeholder for other types or specific APIs (GBM, Bitso, etc.)
    # In a real app, we would route to specific API clients here.
    return None
