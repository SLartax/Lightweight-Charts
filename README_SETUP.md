# FTSEMIB Quant Superior - Setup Guida

## Struttura del Progetto

```
Lightweight-Charts/
├── modules/
│   ├── __init__.py           # Package init
│   ├── email_service.py      # Gmail SMTP module
│   ├── trading_logic.py      # Trading logic & backtesting
│   ├── data_fetcher.py       # Yahoo Finance data fetching
│   └── main.py               # Flask API backend
├── requirements.txt          # Python dependencies
├── .env.example              # Environment template
└── README_SETUP.md           # This file
```

## Configurazione Veloce

### 1. GitHub Secrets (OBBLIGATORIO)

Per inviare segnali via email da GitHub Actions, configura questi secrets:

**Accedi a:** Repository > Settings > Secrets and variables > Actions

#### Secret Richiesti:

**SENDER_EMAIL**
- Valore: `studiolegaleartax@gmail.com`
- Descrizione: Email mittente (Gmail)

**SENDER_PASSWORD**
- Valore: Genera una password App-Specific Gmail
  1. Accedi a https://myaccount.google.com/security
  2. Vai a "App passwords" (Se 2FA è abilitato)
  3. Genera password per "Mail" e "Windows Computer"
  4. Copia la password di 16 caratteri (senza spazi)
  5. Incolla come SENDER_PASSWORD

**RECIPIENT_EMAIL**
- Valore: `pioggiamarrone@gmail.com`
- Descrizione: Email destinatario segnali

**API_KEY** (opzionale)
- Per future estensioni (es. Trading APIs)

### 2. Environment Locale (.env)

Per eseguire localmente, crea un file `.env` nella root:

```bash
# Email Configuration
SENDER_EMAIL=studiolegaleartax@gmail.com
SENDER_PASSWORD=xxxx xxxx xxxx xxxx
RECIPIENT_EMAIL=pioggiamarrone@gmail.com

# Flask Configuration
PORT=5000
DEBUG=true

# Trading Configuration
SEND_EMAIL=true
COST_BPS=2
```

### 3. Installazione Locale

```bash
# Clone repo
git clone https://github.com/SLartax/Lightweight-Charts.git
cd Lightweight-Charts

# Virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# oppure
venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Run Flask backend
python modules/main.py
```

## Moduli

### EmailService (modules/email_service.py)
```python
from modules.email_service import EmailService

email_svc = EmailService(
    sender_email="studiolegaleartax@gmail.com",
    sender_password="xxxx xxxx xxxx xxxx"
)

signal_data = {
    "signal": "LONG",
    "date": "2025-12-27",
    "metrics": {"win_rate": 55.0, "avg_trade_pct": 0.081},
    "explain": {"gap_open": 0.005, "spy_ret": 0.004}
}

email_svc.send_signal("pioggiamarrone@gmail.com", signal_data)
```

### TradingLogic (modules/trading_logic.py)
```python
from modules.trading_logic import TradingLogic

logic = TradingLogic(cost_bps_per_side=2.0)
result = logic.backtest(rows)  # rows = list of OHLCV dicts

print(result["metrics"])       # Metriche
print(result["signal_next"])   # Prossimo segnale
print(result["equity_curve"])  # Curva equity
```

### DataFetcher (modules/data_fetcher.py)
```python
from modules.data_fetcher import DataFetcher

fetcher = DataFetcher()
rows = fetcher.prepare_for_trading(period="1y")
# Scarica FTSEMIB, SPY, VIX e prepara dati
```

### Flask API (modules/main.py)
```
GET /health
Rispostax: {"status": "ok", "service": "FTSEMIB Quant Superior"}

GET /api/quant-superior?symbol=FTSEMIB.MI&period=1y&limit=1200&cost_bps=2
Risposta: JSON con candles, volume, equity, markers, metrics, signal_next
```

## Utilizzo in Lightweight Charts

Integrazione nel codice HTML/JavaScript:

```javascript
// Endpoint locale
const apiBase = "http://localhost:5000";

fetch(`${apiBase}/api/quant-superior?symbol=FTSEMIB.MI&period=1y`)
  .then(r => r.json())
  .then(bundle => {
    candles.setData(bundle.candles);
    volume.setData(bundle.volume);
    eq.setData(bundle.equity);
    candles.setMarkers(bundle.markers);
    // Display metrics, signal_next, etc.
  });
```

## GitHub Actions Workflow (Opzionale)

Creare `.github/workflows/send_signal.yml` per automatizzare:

```yaml
name: FTSEMIB Quant Signal

on:
  schedule:
    - cron: '0 17 * * 1-4'  # 17:30 CET, Lun-Gio

jobs:
  send_signal:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      - run: pip install -r requirements.txt
      - run: python -c "
          from modules.data_fetcher import DataFetcher
          from modules.trading_logic import TradingLogic
          from modules.email_service import EmailService
          
          fetcher = DataFetcher()
          rows = fetcher.prepare_for_trading('1y')
          logic = TradingLogic()
          result = logic.backtest(rows)
          
          if result['signal_next']['signal'] != 'FLAT':
              email = EmailService('${{ secrets.SENDER_EMAIL }}', '${{ secrets.SENDER_PASSWORD }}')
              email.send_signal('${{ secrets.RECIPIENT_EMAIL }}', {
                  'signal': result['signal_next']['signal'],
                  'date': result['signal_next']['date'],
                  'metrics': result['metrics'],
                  'explain': result['signal_next']['explain']
              })
          "
        env:
          SENDER_EMAIL: ${{ secrets.SENDER_EMAIL }}
          SENDER_PASSWORD: ${{ secrets.SENDER_PASSWORD }}
          RECIPIENT_EMAIL: ${{ secrets.RECIPIENT_EMAIL }}
```

## Troubleshooting

### "Authentication failed"
- Verifica SENDER_EMAIL e SENDER_PASSWORD
- Assicurati di usare la password App-Specific, non la password Gmail
- Abilita "Less secure app access" se non usi 2FA

### "No data available"
- Yahoo Finance potrebbe essere offline
- Prova con un periodo diverso
- Controlla il log di DataFetcher

### "Email not sent"
- Verifica che RECIPIENT_EMAIL sia corretto
- Controlla i log di EmailService
- Assicurati che il server SMTP di Gmail sia raggiungibile

## Prossimi Step

1. **Aggiungere autenticazione API** per proteggere l'endpoint
2. **Implementare caching** con Redis per il data fetching
3. **Aggiungere more pattern** di trading
4. **Migliorare metriche** con CAGR, Sharpe Ratio, Max Drawdown
5. **Integrare con TradingView Alerts** via webhook

## Contatti

- Email: studiolegaleartax@gmail.com
- Repo: https://github.com/SLartax/Lightweight-Charts
