import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class EmailService:
    """
    Servizio per inviare segnali di trading via email.
    Utilizza Gmail SMTP con credenziali da variabili d'ambiente/secrets.
    """

    def __init__(
        self,
        sender_email: str,
        sender_password: str,
        smtp_server: str = "smtp.gmail.com",
        smtp_port: int = 587,
    ):
        """
        Inizializza il servizio email.

        Args:
            sender_email: Email del mittente (es. studiolegaleartax@gmail.com)
            sender_password: Password o app password Gmail
            smtp_server: Server SMTP di Gmail
            smtp_port: Porta SMTP (587 per TLS)
        """
        self.sender_email = sender_email
        self.sender_password = sender_password
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port

    def send_signal(
        self,
        recipient_email: str,
        signal_data: Dict,
        subject: Optional[str] = None,
    ) -> bool:
        """
        Invia un segnale di trading via email.

        Args:
            recipient_email: Email del destinatario
            signal_data: Dict con i dati del segnale (date, signal, metrics, etc.)
            subject: Oggetto della mail (default: auto-generato)

        Returns:
            True se l'email è stata inviata con successo, False altrimenti
        """
        try:
            # Costruisci il corpo dell'email
            body = self._build_email_body(signal_data)

            # Genera subject automatico se non fornito
            if subject is None:
                sig = signal_data.get("signal", "UNKNOWN")
                date = signal_data.get("date", "")
                subject = f"[FTSEMIB QUANT] {sig} - {date}"

            # Crea il messaggio
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self.sender_email
            msg["To"] = recipient_email
            msg["Date"] = datetime.now().strftime("%a, %d %b %Y %H:%M:%S +0000")

            # Allega il corpo HTML
            html_part = MIMEText(body, "html")
            msg.attach(html_part)

            # Invia via SMTP
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()  # Crittografa la connessione
                server.login(self.sender_email, self.sender_password)
                server.sendmail(self.sender_email, recipient_email, msg.as_string())

            logger.info(f"Email inviata a {recipient_email} - Segnale: {signal_data.get('signal')}")
            return True

        except smtplib.SMTPAuthenticationError:
            logger.error("Errore autenticazione SMTP - Controlla email e password")
            return False
        except smtplib.SMTPException as e:
            logger.error(f"Errore SMTP: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Errore generico nell'invio email: {str(e)}")
            return False

    def send_batch_signals(
        self,
        recipient_emails: List[str],
        signal_data: Dict,
    ) -> Dict[str, bool]:
        """
        Invia lo stesso segnale a piu destinatari.

        Args:
            recipient_emails: Lista di email destinatari
            signal_data: Dati del segnale

        Returns:
            Dict con risultato invio per ogni email
        """
        results = {}
        for email in recipient_emails:
            results[email] = self.send_signal(email, signal_data)
        return results

    @staticmethod
    def _build_email_body(signal_data: Dict) -> str:
        """
        Costruisce il corpo HTML dell'email con i dati del segnale.
        """
        signal = signal_data.get("signal", "UNKNOWN")
        date = signal_data.get("date", "N/A")
        explain = signal_data.get("explain", {})

        signal_color = "#26a69a" if signal == "LONG" else "#ef5350"

        html = f"""<html><body style="font-family:Arial;background:#0b1020;color:#e6e8ef">
        <div style="max-width:600px;margin:20px auto;padding:20px">
        <div style="background:{signal_color};color:white;padding:20px;border-radius:8px;text-align:center">
        <h1>FTSEMIB QUANT SUPERIOR</h1><h2>{signal}</h2><p>Data: {date}</p></div>
        <div style="background:#1a2332;padding:20px;margin-top:20px;border-radius:8px">
        <h3>Parametri:</h3>"""

        for key, value in explain.items():
            if isinstance(value, float):
                value = f"{value:.4f}"
            html += f"<p><strong>{key}:</strong> {value}</p>"

        html += f"</div><div style="margin-top:20px;font-size:12px;opacity:0.7">
        <p>Generato: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')} CET</p></div></div></body></html>"""
        return html
