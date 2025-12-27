import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class DataFetcher:
    """
    Fetcher per dati OHLCV da yfinance e calcolo indicatori.
    """

    def __init__(self):
        pass

    def fetch_ohlcv(
        self,
        symbol: str,
        period: str = "1y",
        interval: str = "1d",
    ) -> List[Dict]:
        """
        Scarica dati OHLCV da Yahoo Finance.

        Args:
            symbol: Simbolo (es. FTSEMIB.MI, SPY, VI.C)
            period: Period (6mo, 1y, 2y, 5y, max)
            interval: Intervallo (1d, 1h, etc.)

        Returns:
            Lista di dict con {time, open, high, low, close, volume, date}
        """
        try:
            df = yf.download(
                symbol,
                period=period,
                interval=interval,
                progress=False,
            )
            if df.empty:
                logger.warning(f"Nessun dato per {symbol}")
                return []

            rows = []
            for idx, row in df.iterrows():
                date_str = idx.strftime("%Y-%m-%d")
                unix_ts = int(idx.timestamp())
                rows.append(
                    {
                        "date": date_str,
                        "time": unix_ts,
                        "open": float(row["Open"]),
                        "high": float(row["High"]),
                        "low": float(row["Low"]),
                        "close": float(row["Close"]),
                        "volume": int(row["Volume"]) if pd.notna(row["Volume"]) else 0,
                    }
                )
            return rows
        except Exception as e:
            logger.error(f"Errore fetch {symbol}: {str(e)}")
            return []

    def calculate_indicators(self, rows: List[Dict]) -> List[Dict]:
        """
        Calcola indicatori su liste di righe:
        - gap_open: (open - prev_close) / prev_close
        - volume moving average e z-score
        - day of week (Python: 0=Mon, 6=Sun)

        Args:
            rows: Lista di righe OHLCV

        Returns:
            Lista arricchita con indicatori
        """
        if not rows:
            return rows

        for i in range(len(rows)):
            # Gap open
            if i > 0:
                prev_close = rows[i - 1]["close"]
                curr_open = rows[i]["open"]
                if prev_close != 0:
                    rows[i]["gap_open"] = (curr_open / prev_close - 1.0)
                else:
                    rows[i]["gap_open"] = None
            else:
                rows[i]["gap_open"] = None

            # Day of week (dalla data)
            dt = datetime.strptime(rows[i]["date"], "%Y-%m-%d")
            rows[i]["dow"] = dt.weekday()  # 0=Mon, 3=Thu, 4=Fri

        # Volume z-score (rolling 20 giorni)
        vol_ma_list = []
        vol_std_list = []
        for i in range(len(rows)):
            window_start = max(0, i - 19)
            window = [r["volume"] for r in rows[window_start : i + 1]]
            if window:
                vol_ma_list.append(np.mean(window))
                vol_std_list.append(np.std(window))
            else:
                vol_ma_list.append(None)
                vol_std_list.append(None)

        for i in range(len(rows)):
            rows[i]["vol_ma"] = vol_ma_list[i]
            rows[i]["vol_std"] = vol_std_list[i]
            if vol_std_list[i] and vol_std_list[i] > 0:
                rows[i]["vol_z"] = (
                    rows[i]["volume"] - vol_ma_list[i]
                ) / vol_std_list[i]
            else:
                rows[i]["vol_z"] = None

        return rows

    def merge_data(
        self,
        ftsemib_rows: List[Dict],
        spy_rows: List[Dict],
        vix_rows: List[Dict],
    ) -> List[Dict]:
        """
        Merge dati FTSEMIB, SPY, VIX sulla base della data.
        Calcola SPY ret e VIX ret.

        Args:
            ftsemib_rows: Righe FTSEMIB con indicatori
            spy_rows: Righe SPY
            vix_rows: Righe VIX

        Returns:
            Righe FTSEMIB arricchite con SPY e VIX ret
        """
        # Build lookup dict
        spy_dict = {r["date"]: r["close"] for r in spy_rows}
        vix_dict = {r["date"]: r["close"] for r in vix_rows}

        for row in ftsemib_rows:
            date = row["date"]
            # SPY return
            if date in spy_dict:
                # SPY ret = (close - prev_close) / prev_close
                # Simplified: look for prev day
                idx = ftsemib_rows.index(row) if hasattr(ftsemib_rows, "index") else None
                if idx and idx > 0:
                    prev_date = ftsemib_rows[idx - 1]["date"]
                    if prev_date in spy_dict:
                        prev_spy = spy_dict[prev_date]
                        curr_spy = spy_dict[date]
                        row["spy_ret"] = (curr_spy / prev_spy - 1.0) if prev_spy else None
                    else:
                        row["spy_ret"] = None
                else:
                    row["spy_ret"] = None
            else:
                row["spy_ret"] = None

            # VIX return (same logic)
            if date in vix_dict:
                idx = None
                for j, r in enumerate(ftsemib_rows):
                    if r["date"] == date:
                        idx = j
                        break
                if idx and idx > 0:
                    prev_date = ftsemib_rows[idx - 1]["date"]
                    if prev_date in vix_dict:
                        prev_vix = vix_dict[prev_date]
                        curr_vix = vix_dict[date]
                        row["vix_ret"] = (curr_vix / prev_vix - 1.0) if prev_vix else None
                    else:
                        row["vix_ret"] = None
                else:
                    row["vix_ret"] = None
            else:
                row["vix_ret"] = None

        return ftsemib_rows

    def prepare_for_trading(
        self,
        period: str = "1y",
    ) -> List[Dict]:
        """
        Orchestrator: scarica FTSEMIB, SPY, VIX e prepara dati per trading.

        Args:
            period: Period per i download

        Returns:
            Liste di righe pronte per backtesting
        """
        logger.info(f"Fetching data for period {period}...")

        ftsemib = self.fetch_ohlcv("FTSEMIB.MI", period)
        spy = self.fetch_ohlcv("SPY", period)
        vix = self.fetch_ohlcv("VI.C", period)

        if not ftsemib:
            logger.error("Nessun dato FTSEMIB disponibile")
            return []

        logger.info(f"Downloaded: {len(ftsemib)} FTSEMIB, {len(spy)} SPY, {len(vix)} VIX")

        # Calcola indicatori
        ftsemib = self.calculate_indicators(ftsemib)

        # Merge
        ftsemib = self.merge_data(ftsemib, spy, vix)

        logger.info(f"Prepared {len(ftsemib)} rows for trading")
        return ftsemib
