import logging
from datetime import datetime
from typing import Dict, Optional

logger = logging.getLogger(__name__)

def detect_signal(data: Dict) -> Optional[str]:
    """
    Detect trading signals based on market data.
    Uses simple moving average crossover strategy.
    
    Args:
        data: Dictionary with market data from get_latest_data()
    
    Returns:
        Signal type ("BUY", "SELL", None) or error message
    """
    try:
        # Check if data has error
        if "error" in data:
            logger.warning(f"Data contains error: {data['error']}")
            return None
        
        price = data.get("price", 0)
        sma_5 = data.get("sma_5", 0)
        sma_20 = data.get("sma_20", 0)
        volatility = data.get("volatility", 0)
        price_change_pct = data.get("price_change_pct", 0)
        
        # Validate data
        if not all([price, sma_5, sma_20]):
            logger.warning("Insufficient data for signal detection")
            return None
        
        signal = None
        confidence = 0.0
        
        # Strategy 1: Simple Moving Average Crossover
        # BUY signal: SMA5 > SMA20 (bullish crossover)
        if sma_5 > sma_20:
            signal = "BUY"
            confidence = ((sma_5 - sma_20) / sma_20) * 100  # % difference
        # SELL signal: SMA5 < SMA20 (bearish crossover)
        elif sma_5 < sma_20:
            signal = "SELL"
            confidence = ((sma_20 - sma_5) / sma_20) * 100
        
        # Strategy 2: Momentum filter
        # Only confirm signal if price moving in direction
        if signal == "BUY" and price_change_pct <= 0:
            # Price should be moving up for strong BUY
            if confidence < 2.0:  # Weak signal
                signal = None
        elif signal == "SELL" and price_change_pct >= 0:
            # Price should be moving down for strong SELL
            if confidence < 2.0:  # Weak signal
                signal = None
        
        # Strategy 3: Volatility filter
        # Avoid trading in very high volatility
        if volatility > price * 0.05:  # If volatility > 5% of price
            logger.info(f"High volatility detected ({volatility:.2f}), signal filtered")
            if signal and confidence < 3.0:  # Only strong signals in high volatility
                signal = None
        
        if signal:
            logger.info(f"Signal detected: {signal} (confidence: {confidence:.2f}%, price: {price:.2f})")
        else:
            logger.debug("No clear signal detected")
        
        return signal
        
    except Exception as e:
        logger.error(f"Error in signal detection: {str(e)}")
        return None


def validate_signal(signal: Optional[str]) -> bool:
    """
    Validate if signal is valid.
    
    Args:
        signal: Signal string ("BUY", "SELL", None)
    
    Returns:
        True if signal is valid, False otherwise
    """
    return signal in ["BUY", "SELL"]
