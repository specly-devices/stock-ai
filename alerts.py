import smtplib
import requests
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

load_dotenv()

GMAIL_ADDRESS = os.getenv("GMAIL_ADDRESS")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
ALERT_EMAIL = os.getenv("ALERT_EMAIL")
NTFY_TOPIC = os.getenv("NTFY_TOPIC")

def send_ntfy(title, message, priority="default"):
    """Send push notification via Ntfy"""
    try:
        requests.post(
            f"https://ntfy.sh/{NTFY_TOPIC}",
            data=message.encode("utf-8"),
            headers={
                "Title": title.encode("utf-8"),
                "Priority": priority,  # min, low, default, high, urgent
                "Tags": "chart_with_upwards_trend",
                "Content-Type": "text/plain; charset=utf-8"
            }
        )
        print(f"✅ Ntfy alert sent: {title}")
    except Exception as e:
        print(f"❌ Ntfy failed: {e}")

def send_email(subject, body):
    """Send email alert via Gmail"""
    try:
        msg = MIMEMultipart()
        msg["From"]    = GMAIL_ADDRESS
        msg["To"]      = ALERT_EMAIL
        msg["Subject"] = subject

        if body.strip().startswith("<!DOCTYPE") or body.strip().startswith("<html"):
            msg.attach(MIMEText(body, "html"))
        else:
            msg.attach(MIMEText(body, "plain"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
            server.send_message(msg)
        print(f"✅ Email alert sent: {subject}")
    except Exception as e:
        print(f"❌ Email failed: {e}")

def send_alert(symbol, signal, price, confidence, reason):
    """
    Main alert function — sends both Ntfy and Email
    signal: BUY / SELL / HOLD
    """
    emoji = {"BUY": "🟢", "SELL": "🔴", "HOLD": "🟡"}.get(signal, "⚪")
    priority = {"BUY": "high", "SELL": "urgent", "HOLD": "default"}.get(signal, "default")

    title = f"{emoji} {signal}: {symbol}"
    message = (
        f"Signal: {signal}\n"
        f"Stock: {symbol}\n"
        f"Price: ₹{price}\n"
        f"Confidence: {confidence}%\n"
        f"Reason: {reason}"
    )

    send_ntfy(title, message, priority)
    send_email(title, message)

# ── Test ──────────────────────────────────────────────
if __name__ == "__main__":
    send_alert(
        symbol="RELIANCE.NS",
        signal="BUY",
        price=1341.40,
        confidence=78.5,
        reason="RSI oversold + MACD bullish crossover + Positive news sentiment"
    )