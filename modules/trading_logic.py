from typing import Dict, List, Tuple
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class TradingLogic:
    """
    Logica di trading FTSEMIB Quant Superior.
    Implementa i filtri e i segnali dal codice JavaScript.
    """

    ALLOWED_DAYS = {0, 1, 2, 3}  # Lun-Gio (Python: 0=Mon)

    def __init__(self, cost_bps_per_side: float = 2.0):
        """
        Args:
            cost_bps_per_side: Costo in basis points per lato (round-trip = 2x)
        """
        self.cost_bps_per_side = cost_bps_per_side

    def filter_signals(self, row: Dict) -> bool:
        """
        Filtri su SPY ret e giorno della settimana.
        
        Args:
            row: Dict con OHLCV e dati calcolati

        Returns:
            True se la row passa i filtri
        """
        # Filtro SPY ret
        if "spy_ret" in row and row["spy_ret"] is not None:
            if row["spy_ret"] < -0.005:
                return False

        # Filtro giorno della settimana (solo Lun-Gio)
        if "dow" in row:
            if row["dow"] not in self.ALLOWED_DAYS:
                return False

        return True

    def match_top3_pattern(self, row: Dict) -> bool:
        """
        Pattern TOP3: gap_open + (SPY ret positivo) + (VIX ret negativo) + (vol-z negativo)

        Args:
            row: Dict con dati calcolati

        Returns:
            True se il pattern è matched
        """
        cond = False

        # Gap open: 0% < gap < 1%
        if "gap_open" in row and row["gap_open"] is not None:
            if 0 < row["gap_open"] <= 0.01:
                cond = True

        # SPY ret: positivo >= 1%
        if cond and "spy_ret" in row and row["spy_ret"] is not None:
            if not (0 <= row["spy_ret"] <= 0.01):
                cond = False

        # VIX ret: tra -10% e -5%
        if cond and "vix_ret" in row and row["vix_ret"] is not None:
            if not (-0.10 <= row["vix_ret"] <= -0.05):
                cond = False

        # Volume z-score: tra -1.5 e -0.5
        if cond and "vol_z" in row and row["vol_z"] is not None:
            if not (-1.5 <= row["vol_z"] <= -0.5):
                cond = False

        return cond

    def calculate_overnight_pnl(
        self,
        entry_close: float,
        exit_open: float,
        cost_bps: float = None,
    ) -> Tuple[float, float, float]:
        """
        Calcola P&L overnight.

        Args:
            entry_close: Prezzo chiusura giorno entry
            exit_open: Prezzo apertura giorno exit
            cost_bps: Override di cost_bps_per_side

        Returns:
            (raw_points, cost_points, pnl_net_points)
        """
        if entry_close == 0:
            return 0, 0, 0

        bps = cost_bps if cost_bps is not None else self.cost_bps_per_side

        raw_points = exit_open - entry_close
        cost_points = (2.0 * bps / 10000.0) * entry_close
        pnl_points = raw_points - cost_points

        return raw_points, cost_points, pnl_points

    def generate_signal(
        self,
        rows: List[Dict],
        last_row: Dict = None,
    ) -> Dict:
        """
        Genera il segnale per il giorno successivo.

        Args:
            rows: Lista di rows storiche
            last_row: Ultima row disponibile (per generare il segnale domani)

        Returns:
            Dict con segnale, data, e parametri di spiegazione
        """
        signal = "FLAT"
        signal_date = None
        explain = {}

        if last_row and self.filter_signals(last_row):
            if self.match_top3_pattern(last_row):
                signal = "LONG"
                explain["gap_open"] = last_row.get("gap_open")
                explain["spy_ret"] = last_row.get("spy_ret")
                explain["vix_ret"] = last_row.get("vix_ret")
                explain["vol_z"] = last_row.get("vol_z")
                explain["dow"] = last_row.get("dow")

        signal_date = last_row.get("date") if last_row else None

        return {
            "signal": signal,
            "date": signal_date,
            "explain": explain,
        }

    def backtest(
        self,
        rows: List[Dict],
    ) -> Dict:
        """
        Esegue backtesting su liste di righe.
        Genera segnali, calcola metriche.

        Args:
            rows: Lista di righe OHLCV con indicatori calcolati

        Returns:
            Dict con trades, equity curve, e metriche
        """
        trades = []
        equity_curve = []
        markers = []
        equity_value = 1.0

        for i in range(len(rows) - 1):
            current_row = rows[i]

            # Verifica segnale
            if not self.filter_signals(current_row):
                continue

            if not self.match_top3_pattern(current_row):
                continue

            # Entry: chiusura oggi
            # Exit: apertura domani
            next_row = rows[i + 1]

            if (
                current_row.get("close") is None
                or next_row.get("open") is None
            ):
                continue

            raw_pts, cost_pts, pnl_pts = self.calculate_overnight_pnl(
                current_row["close"],
                next_row["open"],
                self.cost_bps_per_side,
            )

            # Evita divisioni per zero
            if current_row["close"] == 0:
                continue

            pnl_pct = raw_pts / current_row["close"]
            net_ret = pnl_pct - (2.0 * self.cost_bps_per_side / 10000.0)
            equity_value *= 1 + net_ret

            trade = {
                "entry_date": current_row.get("date"),
                "entry_time": current_row.get("time"),
                "exit_time": next_row.get("time"),
                "entry_close": current_row["close"],
                "exit_open": next_row["open"],
                "raw_points": raw_pts,
                "cost_points": cost_pts,
                "pnl_points": pnl_pts,
                "return_pct": net_ret * 100,
                "spy_ret": current_row.get("spy_ret"),
                "vix_ret": current_row.get("vix_ret"),
            }
            trades.append(trade)

            equity_curve.append(
                {"time": next_row.get("time"), "value": equity_value}
            )

            # Markers
            markers.append(
                {
                    "time": current_row.get("time"),
                    "position": "belowBar",
                    "shape": "arrowUp",
                    "text": "QS BUY",
                    "color": "#26a69a",
                }
            )
            markers.append(
                {
                    "time": next_row.get("time"),
                    "position": "aboveBar",
                    "shape": "arrowDown",
                    "text": "QS SELL",
                    "color": "#ef5350",
                }
            )

        # Calcola metriche
        metrics = self._calculate_metrics(trades, equity_curve)

        # Genera segnale per domani
        signal_next = self.generate_signal(rows)

        return {
            "trades": trades,
            "equity_curve": equity_curve,
            "markers": markers,
            "metrics": metrics,
            "signal_next": signal_next,
        }

    def _calculate_metrics(self, trades: List[Dict], equity: List[Dict]) -> Dict:
        """
        Calcola metriche di backtesting.
        """
        n = len(trades)
        if n == 0:
            return {
                "total_trades": 0,
                "win_rate": 0,
                "avg_trade_pct": 0,
                "avg_points": 0,
                "total_return_pct": 0,
                "cagr": 0,
            }

        returns = [t["return_pct"] for t in trades]
        wins = [t for t in trades if t["return_pct"] > 0]
        avg_trade = sum(returns) / n if n > 0 else 0
        win_rate = (len(wins) / n * 100) if n > 0 else 0
        avg_points = sum([t["pnl_points"] for t in trades]) / n if n > 0 else 0

        total_return = 0
        if equity and len(equity) > 0:
            total_return = (equity[-1]["value"] - 1) * 100

        return {
            "total_trades": n,
            "win_rate": round(win_rate, 2),
            "avg_trade_pct": round(avg_trade, 4),
            "avg_points": round(avg_points, 2),
            "total_return_pct": round(total_return, 2),
            "cagr": 0,  # Calcolato nel backend con date
        }
