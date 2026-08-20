import os
import smtplib
from email.mime.text import MIMEText
import yfinance as yf
from ta.momentum import RSIIndicator

SENDER_EMAIL = os.environ.get("SENDER_EMAIL")
APP_PASSWORD = os.environ.get("APP_PASSWORD")
RECEIVER_EMAIL = SENDER_EMAIL

if not SENDER_EMAIL or not APP_PASSWORD:
    print("❌ ERROR: SENDER_EMAIL 또는 APP_PASSWORD 환경 변수가 설정되지 않았습니다.")
    exit(1)

TICKERS = ["TSLA", "NVDA", "BTC-USD", "USDKRW=X"]

def send_email(subject, body):
    try:
        msg = MIMEText(body)
        msg['Subject'] = subject
        msg['From'] = SENDER_EMAIL
        msg['To'] = RECEIVER_EMAIL

        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(SENDER_EMAIL, APP_PASSWORD)
            server.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, msg.as_string())
        print("✉️ 이메일 발송 완료!")
    except Exception as e:
        print(f"❌ 이메일 발송 실패: {e}")

alerts = []

print("📊 데이터 조회 시작...")
for ticker_symbol in TICKERS:
    try:
        ticker = yf.Ticker(ticker_symbol)
        data = ticker.history(period="60d")
        
        if data.empty:
            print(f"⚠️ {ticker_symbol} 데이터 없음")
            continue

        current_price = data['Close'].iloc[-1]
        rsi_series = RSIIndicator(close=data['Close'], window=14).rsi()
        current_rsi = rsi_series.iloc[-1]
        
        print(f"- {ticker_symbol}: ${current_price:.2f} | RSI: {current_rsi:.1f}")

        if current_rsi <= 35:
            alerts.append(f"📉 [매수 추천] {ticker_symbol} - 현재가: {current_price:.2f} (RSI: {current_rsi:.1f})")
        elif current_rsi >= 65:
            alerts.append(f"📈 [매도 추천] {ticker_symbol} - 현재가: {current_price:.2f} (RSI: {current_rsi:.1f})")

    except Exception as e:
        print(f"⚠️ {ticker_symbol} 처리 중 에러: {e}")

if alerts:
    send_email(f"[AI 에이전트] {len(alerts)}개 종목 매매 신호 포착!", "\n".join(alerts))
else:
    print("✅ 조건에 맞는 종목이 없습니다.")
