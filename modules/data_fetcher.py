import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

def get_latest_data(symbol: str = "SPY", period: str = "5d") -> dict:
    """
    Fetch latest market data using yfinance.
    
    Args:
        symbol: Stock symbol (default: SPY)
        period: Period for data fetch (5d, 1mo, 3mo, etc.)
    
    Returns:
        Dictionary with market data and analysis
    """
    try:
        logger.info(f"Fetching data for {symbol}...")
        
        # Download data from yfinance
        data = yf.download(symbol, period=period, progress=False)
        
        if data.empty:
            logger.warning(f"No data retrieved for {symbol}")
            return {"error": f"No data for {symbol}", "price": 0, "timestamp": datetime.now().isoformat()}
        
        # Get latest values
        latest = data.iloc[-1]
        previous = data.iloc[-2] if len(data) > 1 else latest
        
        # Calculate simple indicators
        sma_20 = data['Close'].rolling(window=20).mean().iloc[-1] if len(data) >= 20 else data['Close'].mean()
        sma_5 = data['Close'].rolling(window=5).mean().iloc[-1] if len(data) >= 5 else data['Close'].mean()
        
        # Calculate volatility (Standard Deviation)
        volatility = data['Close'].rolling(window=20).std().iloc[-1] if len(data) >= 20 else 0
        
        # Price change
        price_change = latest['Close'] - previous['Close']
        price_change_pct = (price_change / previous['Close'] * 100) if previous['Close'] != 0 else 0
        
        result = {
            "symbol": symbol,
            "timestamp": datetime.now().isoformat(),
            "price": float(latest['Close']),
            "high": float(latest['High']),
            "low": float(latest['Low']),
            "volume": int(latest['Volume']),
            "sma_5": float(sma_5),
            "sma_20": float(sma_20),
            "volatility": float(volatility),
            "price_change": float(price_change),
            "price_change_pct": float(price_change_pct),
            "data_points": len(data)
        }
        
        logger.info(f"Data fetched successfully. Price: {result['price']}")
        return result
        
    except Exception as e:
        logger.error(f"Error fetching data: {str(e)}")
        return {"error": str(e), "price": 0, "timestamp": datetime.now().isoformat()}


def get_multiple_symbols(symbols: list) -> dict:
    """
    Fetch data for multiple symbols.
    
    Args:
        symbols: List of stock symbols
    
    Returns:
        Dictionary with data for all symbols
    """
    results = {}
    for symbol in symbols:
        results[symbol] = get_latest_data(symbol)
    return results
