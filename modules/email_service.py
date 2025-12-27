import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)

def send_email(
    sender: str,
    recipient: str,
    password: str,
    subject: str,
    body: str,
    smtp_server: str = "smtp.gmail.com",
    smtp_port: int = 587
) -> bool:
    """
    Send email notification for trading signals.
    
    Args:
        sender: Sender email address
        recipient: Recipient email address
        password: Sender email password
        subject: Email subject
        body: Email body (plain text)
        smtp_server: SMTP server address
        smtp_port: SMTP port number
    
    Returns:
        True if email sent successfully, False otherwise
    """
    try:
        logger.info(f"Attempting to send email from {sender} to {recipient}")
        
        # Create email message
        message = MIMEMultipart()
        message["From"] = sender
        message["To"] = recipient
        message["Subject"] = subject
        
        # Add body
        message.attach(MIMEText(body, "plain"))
        
        # Connect to SMTP server and send
        with smtplib.SMTP(smtp_server, smtp_port, timeout=10) as server:
            server.starttls()  # Enable TLS encryption
            server.login(sender, password)
            server.send_message(message)
        
        logger.info(f"Email sent successfully to {recipient}")
        return True
        
    except smtplib.SMTPAuthenticationError as e:
        logger.error(f"SMTP Authentication failed: {str(e)}")
        return False
    except smtplib.SMTPException as e:
        logger.error(f"SMTP Error: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Error sending email: {str(e)}")
        return False


def send_signal_alert(
    signal_type: str,
    price: float,
    timestamp: str,
    sender: str,
    recipient: str,
    password: str,
    additional_info: Optional[Dict] = None
) -> bool:
    """
    Send trading signal alert email.
    
    Args:
        signal_type: Type of signal ("BUY", "SELL")
        price: Current price
        timestamp: Signal detection timestamp
        sender: Sender email
        recipient: Recipient email
        password: Sender password
        additional_info: Additional market data
    
    Returns:
        True if sent successfully
    """
    try:
        # Create subject
        subject = f"[17:30 CET] Lightweight Charts Signal: {signal_type}"
        
        # Create detailed body
        body = f"""Trading Signal Alert - Lightweight Charts Analysis

Signal Type: {signal_type}
Price: ${price:.2f}
Time: {timestamp}

"""
        
        if additional_info:
            if "sma_5" in additional_info:
                body += f"SMA(5): ${additional_info['sma_5']:.2f}\n"
            if "sma_20" in additional_info:
                body += f"SMA(20): ${additional_info['sma_20']:.2f}\n"
            if "volatility" in additional_info:
                body += f"Volatility: {additional_info['volatility']:.2f}\n"
            if "volume" in additional_info:
                body += f"Volume: {additional_info['volume']:,}\n"
        
        body += "\n" + "="*50
        body += "\nSystem: Lightweight Charts Precision Analysis"
        body += "\nDo not reply to this email.\n"
        
        return send_email(sender, recipient, password, subject, body)
        
    except Exception as e:
        logger.error(f"Error in send_signal_alert: {str(e)}")
        return False
