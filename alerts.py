import smtplib
import requests
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
from datetime import datetime

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

def send_alert(symbol, signal, price, confidence, reason,
               stop_loss=None, target1=None, target2=None, entry=None):
    """Send alert via Gmail and Ntfy with trade levels"""

    sym_clean = symbol.replace(".NS","").replace(".BO","")

    # Trade levels block
    levels_text = ""
    levels_html = ""

    if entry or stop_loss or target1:
        ep  = f"₹{entry:.2f}"    if entry     else f"₹{price:.2f}"
        sl  = f"₹{stop_loss:.2f}" if stop_loss else "—"
        t1  = f"₹{target1:.2f}"  if target1   else "—"
        t2  = f"₹{target2:.2f}"  if target2   else "—"

        sl_pct = f" (-{abs((stop_loss-price)/price*100):.1f}%)" if stop_loss else ""
        t1_pct = f" (+{abs((target1-price)/price*100):.1f}%)"  if target1  else ""
        t2_pct = f" (+{abs((target2-price)/price*100):.1f}%)"  if target2  else ""

        levels_text = f"""
─────────────────────
  Entry:    {ep}
  Stop Loss:{sl}{sl_pct}
  Target 1: {t1}{t1_pct}
  Target 2: {t2}{t2_pct}
─────────────────────"""

        levels_html = f"""
        <table style="width:100%;border-collapse:collapse;margin-top:12px">
            <tr>
                <td style="padding:8px 12px;background:#111827;
                           border-radius:6px 0 0 0;font-size:12px;
                           color:#64748b;text-transform:uppercase;
                           letter-spacing:1px">Entry</td>
                <td style="padding:8px 12px;background:#111827;
                           border-radius:0 6px 0 0;font-size:14px;
                           color:#00d4ff;font-family:monospace;
                           font-weight:700">
                    {ep}</td>
            </tr>
            <tr>
                <td style="padding:8px 12px;background:#0d1421;
                           font-size:12px;color:#64748b;
                           text-transform:uppercase;letter-spacing:1px">
                    Stop Loss</td>
                <td style="padding:8px 12px;background:#0d1421;
                           font-size:14px;color:#ff4466;
                           font-family:monospace;font-weight:700">
                    {sl}<span style="color:#64748b;font-size:11px">
                    {sl_pct}</span></td>
            </tr>
            <tr>
                <td style="padding:8px 12px;background:#111827;
                           font-size:12px;color:#64748b;
                           text-transform:uppercase;letter-spacing:1px">
                    Target 1</td>
                <td style="padding:8px 12px;background:#111827;
                           font-size:14px;color:#22c55e;
                           font-family:monospace;font-weight:700">
                    {t1}<span style="color:#64748b;font-size:11px">
                    {t1_pct}</span></td>
            </tr>
            <tr>
                <td style="padding:8px 12px;background:#0d1421;
                           border-radius:0 0 6px 6px;font-size:12px;
                           color:#64748b;text-transform:uppercase;
                           letter-spacing:1px">Target 2</td>
                <td style="padding:8px 12px;background:#0d1421;
                           border-radius:0 0 0 6px;font-size:14px;
                           color:#22c55e;font-family:monospace;font-weight:700">
                    {t2}<span style="color:#64748b;font-size:11px">
                    {t2_pct}</span></td>
            </tr>
        </table>"""

    # Signal emoji
    if "BUY" in signal:
        emoji = "🟢"
        color = "#22c55e"
    elif "SELL" in signal or "STOP" in signal or "TARGET" in signal:
        emoji = "🔴"
        color = "#ef4444"
    else:
        emoji = "🟡"
        color = "#f59e0b"

    # ── Ntfy push notification ───────────────────────────────────────────
    try:
        ntfy_body = (
            f"{signal} @ ₹{price:.2f} | Conf: {confidence:.1f}%\n"
            f"{reason[:100]}"
            f"{levels_text}"
        )
        priority_map = {
            "BUY": "high", "SELL": "urgent",
            "STOP_LOSS": "urgent", "TARGET": "high"
        }
        priority = next(
            (v for k, v in priority_map.items() if k in signal), "default"
        )
        requests.post(
            f"https://ntfy.sh/{NTFY_TOPIC}",
            data=ntfy_body.encode("utf-8"),
            headers={
                "Title":    f"{emoji} {sym_clean} — {signal}",
                "Priority": priority,
                "Tags":     "chart_increasing" if "BUY" in signal else "chart_decreasing"
            }
        )
    except Exception as e:
        print(f"❌ Ntfy failed: {e}")

    # ── Email ────────────────────────────────────────────────────────────
    try:
        html_body = f"""
<!DOCTYPE html>
<html>
<body style="background:#07090f;color:#e2e8f0;
             font-family:'Segoe UI',Arial,sans-serif;
             margin:0;padding:20px">
  <div style="max-width:480px;margin:0 auto">

    <div style="background:#0d1421;border:1px solid #1e2d45;
                border-radius:14px;padding:24px;margin-bottom:16px">

      <div style="display:flex;align-items:center;
                  justify-content:space-between;margin-bottom:16px">
        <div>
          <div style="font-size:22px;font-weight:800;
                      letter-spacing:-0.5px">{sym_clean}</div>
          <div style="font-size:11px;color:#64748b;
                      letter-spacing:2px;text-transform:uppercase">
            Signal Alert</div>
        </div>
        <div style="background:{color}22;border:1px solid {color}44;
                    border-radius:8px;padding:8px 16px;
                    font-size:16px;font-weight:800;color:{color}">
          {emoji} {signal}
        </div>
      </div>

      <div style="display:flex;gap:12px;margin-bottom:16px">
        <div style="flex:1;background:#111827;border-radius:8px;
                    padding:12px;text-align:center">
          <div style="font-size:10px;color:#64748b;letter-spacing:2px;
                      text-transform:uppercase;margin-bottom:4px">Price</div>
          <div style="font-size:20px;font-weight:700;
                      font-family:monospace;color:#00d4ff">
            ₹{price:.2f}</div>
        </div>
        <div style="flex:1;background:#111827;border-radius:8px;
                    padding:12px;text-align:center">
          <div style="font-size:10px;color:#64748b;letter-spacing:2px;
                      text-transform:uppercase;margin-bottom:4px">
            Confidence</div>
          <div style="font-size:20px;font-weight:700;
                      font-family:monospace;color:{color}">
            {confidence:.1f}%</div>
        </div>
      </div>

      {levels_html}

      <div style="margin-top:14px;padding:12px;background:#080c14;
                  border-radius:8px;font-size:12px;color:#64748b;
                  line-height:1.6">{reason}</div>

      <div style="margin-top:12px;font-size:11px;color:#334155;
                  text-align:right">
       {datetime.now().strftime('%d %b %Y %H:%M:%S IST')}</div>
    </div>

    <div style="text-align:center;font-size:10px;color:#334155">
      StockAI · Not financial advice
    </div>
  </div>
</body>
</html>"""

        subject = f"{emoji} {sym_clean} — {signal} @ ₹{price:.2f}"
        send_email(subject, html_body)

    except Exception as e:
        print(f"❌ Email alert failed: {e}")

    print(f"✅ Alert sent: {sym_clean} {signal} @ ₹{price:.2f}")

# ── Test ──────────────────────────────────────────────
if __name__ == "__main__":
    send_alert(
        symbol="RELIANCE.NS",
        signal="BUY",
        price=1341.40,
        confidence=78.5,
        reason="RSI oversold + MACD bullish crossover + Positive news sentiment"
    )