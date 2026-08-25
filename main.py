import os
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
import yfinance as yf
from ta.momentum import RSIIndicator

SENDER_EMAIL = os.environ.get("SENDER_EMAIL")
APP_PASSWORD = os.environ.get("APP_PASSWORD")
RECEIVER_EMAIL = SENDER_EMAIL

if not SENDER_EMAIL or not APP_PASSWORD:
    print("❌ ERROR: 환경 변수 미설정")
    exit(1)

# 보유 포트폴리오 전체 티커 목록 (SGOV 채권 ETF 포함)
TICKERS = [
    # 빅테크 & 개별주
    "TSLA", "AAPL", "NVDA", "AMZN", "GOOGL", "MU", "AMD", "AVGO", "PLTR",
    # 지수 & 테마 & 채권 ETF
    "QQQM", "MAGS", "GRID", "XLU", "GLD", "VHT", "XLE", "VTI", "SCHD", "SMH", "SPYM", "SGOV",
    # 가상자산 & 환율
    "BTC-USD", "USDKRW=X"
]

def send_email(subject, body):
    try:
        msg = MIMEText(body)
        msg['Subject'] = subject
        msg['From'] = SENDER_EMAIL
        msg['To'] = RECEIVER_EMAIL

        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(SENDER_EMAIL, APP_PASSWORD)
            server.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, msg.as_string())
        print("✉️ 리포트 이메일 발송 완료!")
    except Exception as e:
        print(f"❌ 이메일 발송 실패: {e}")

# 과거 가격을 안전하게 가져오는 함수
def get_past_price(df, days_ago):
    if len(df) > days_ago:
        return df['Close'].iloc[-(days_ago+1)]
    return None

# 수익률 계산 함수
def calc_change(curr, past):
    if past:
        return f"{(curr - past) / past * 100:+.2f}%"
    return "N/A"

report_lines = []
signals = []

for ticker_symbol in TICKERS:
    try:
        # 1년치(52주) 데이터를 조회하여 각종 지표 계산
        data = yf.Ticker(ticker_symbol).history(period="1y")
        if data.empty:
            continue

        current_price = data['Close'].iloc[-1]
        high_52w = data['High'].max()
        low_52w = data['Low'].min()
        
        # 거래일 기준 (1주=약 5일, 1개월=약 21일, 3개월=약 63일)
        price_1w = get_past_price(data, 5)
        price_1m = get_past_price(data, 21)
        price_3m = get_past_price(data, 63)
        
        change_1w = calc_change(current_price, price_1w)
        change_1m = calc_change(current_price, price_1m)
        change_3m = calc_change(current_price, price_3m)

        rsi_series = RSIIndicator(close=data['Close'], window=14).rsi()
        current_rsi = rsi_series.iloc[-1]

        # 상태 판정
        if current_rsi <= 35:
            status = "📉 [과매도 / 매수 검토]"
            signals.append(f"{ticker_symbol}(RSI:{current_rsi:.1f}) 매수")
        elif current_rsi >= 65:
            status = "📈 [과매수 / 매도 검토]"
            signals.append(f"{ticker_symbol}(RSI:{current_rsi:.1f}) 매도")
        else:
            status = "➡️ [중립]"

        line = (
            f"• {ticker_symbol}\n"
            f"  - 현재가: ${current_price:,.2f} | RSI: {current_rsi:.1f} ({status})\n"
            f"  - 52주 최고/최저: ${high_52w:,.2f} / ${low_52w:,.2f}\n"
            f"  - 변동률: 1주({change_1w}) | 1개월({change_1m}) | 3개월({change_3m})\n"
        )
        report_lines.append(line)

    except Exception as e:
        report_lines.append(f"• {ticker_symbol}: 데이터 조회 실패 ({e})\n")

now_str = datetime.now().strftime("%Y-%m-%d %H:%M UTC")
summary = f"포착된 신호: {', '.join(signals)}" if signals else "특이 신호: 없음 (모든 종목 안정적)"

email_body = f"""[ AI 시장 분석 및 포트폴리오 정기 리포트 ]
측정 시각: {now_str}
요약: {summary}

========================================
보유 포트폴리오 전체 현황 ({len(TICKERS)}개 종목)
========================================

""" + "\n".join(report_lines) + """
========================================
* RSI 35 이하: 과매도 (매수 타이밍 검토)
* RSI 65 이상: 과매수 (매도 타이밍 검토)
"""

subject = f"[정기 리포트] 전체 포트폴리오 현황 ({f'{len(signals)}개 특이신호!' if signals else '이상 없음'})"
send_email(subject, email_body)
