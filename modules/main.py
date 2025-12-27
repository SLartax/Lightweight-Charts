import os
import logging
from flask import Flask, jsonify, request
from modules.data_fetcher import DataFetcher
from modules.trading_logic import TradingLogic
from modules.email_service import EmailService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

app = Flask(__name__)


@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint."""
    return jsonify({"status": "ok", "service": "FTSEMIB Quant Superior"})


@app.route("/api/quant-superior", methods=["GET"])
def quant_superior():
    """
    Main trading API endpoint.
    Query params:
    - symbol: FTSEMIB.MI
    - period: 1y, 2y, 5y, max
    - limit: number of rows to display
    - cost_bps: basis points per side (default 2)
    """
    try:
        # Get parameters
        symbol = request.args.get("symbol", "FTSEMIB.MI")
        period = request.args.get("period", "1y")
        limit = int(request.args.get("limit", "1200"))
        cost_bps = float(request.args.get("cost_bps", "2"))

        logger.info(
            f"Request: symbol={symbol}, period={period}, limit={limit}, cost_bps={cost_bps}"
        )

        # Fetch data
        fetcher = DataFetcher()
        rows = fetcher.prepare_for_trading(period)

        if not rows:
            return jsonify({"error": "No data available"}), 400

        # Slice by limit
        if len(rows) > limit:
            rows = rows[-limit:]

        # Run backtesting
        logic = TradingLogic(cost_bps_per_side=cost_bps)
        result = logic.backtest(rows)

        # Send signal via email if enabled
        send_email = os.getenv("SEND_EMAIL", "false").lower() == "true"
        if send_email and result["signal_next"]["signal"] != "FLAT":
            email_svc = EmailService(
                os.getenv("SENDER_EMAIL"),
                os.getenv("SENDER_PASSWORD"),
            )
            signal_data = {
                "signal": result["signal_next"]["signal"],
                "date": result["signal_next"]["date"],
                "metrics": result["metrics"],
                "explain": result["signal_next"]["explain"],
            }
            email_svc.send_signal(
                os.getenv("RECIPIENT_EMAIL"),
                signal_data,
            )
            logger.info("Email segnale inviato")

        # Format response for Lightweight Charts
        return jsonify(
            {
                "candles": [
                    {
                        "time": r["time"],
                        "open": float(r["open"]),
                        "high": float(r["high"]),
                        "low": float(r["low"]),
                        "close": float(r["close"]),
                    }
                    for r in rows
                ],
                "volume": [
                    {
                        "time": r["time"],
                        "value": r["volume"],
                        "color": "rgba(38,166,154,0.5)"
                        if r["close"] > r["open"]
                        else "rgba(239,83,80,0.5)",
                    }
                    for r in rows
                ],
                "equity": result["equity_curve"],
                "markers": result["markers"],
                "metrics": result["metrics"],
                "signal_next": result["signal_next"],
                "meta": {
                    "symbol": symbol,
                    "tf": "1d",
                    "rows": len(rows),
                    "source": "yfinance",
                },
            }
        )

    except Exception as e:
        logger.error(f"Error in quant_superior: {str(e)}")
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    debug = os.getenv("DEBUG", "false").lower() == "true"
    app.run(host="0.0.0.0", port=port, debug=debug)
