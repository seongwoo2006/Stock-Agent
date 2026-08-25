import os
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
import yfinance as yf
from ta.momentum import RSIIndicator
from ta.volatility import BollingerBands

SENDER_EMAIL = os.environ.get("SENDER_EMAIL")
APP_PASSWORD = os.environ.get("APP_PASSWORD")
RECEIVER_EMAIL = SENDER_EMAIL

if not SENDER_EMAIL or not APP_PASSWORD:
    print("❌ ERROR: 환경 변수 미설정")
    exit(1)

# 보유 포트폴리오 전체 티커 목록
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

def get_past_price(df, days_ago):
    if len(df) > days_ago:
        return df['Close'].iloc[-(days_ago+1)]
    return None

def calc_change(curr, past):
    if past:
        return f"{(curr - past) / past * 100:+.2f}%"
    return "N/A"

report_lines = []
signals = []

for ticker_symbol in TICKERS:
    try:
        # 1년치(52주) 데이터 수집
        data = yf.Ticker(ticker_symbol).history(period="1y")
        if data.empty:
            continue

        current_price = data['Close'].iloc[-1]
        high_52w = data['High'].max()
        low_52w = data['Low'].min()
        
        # 1) 수익률 (1주, 1개월, 3개월)
        price_1w = get_past_price(data, 5)
        price_1m = get_past_price(data, 21)
        price_3m = get_past_price(data, 63)
        change_1w = calc_change(current_price, price_1w)
        change_1m = calc_change(current_price, price_1m)
        change_3m = calc_change(current_price, price_3m)

        # 2) RSI 지표
        rsi_series = RSIIndicator(close=data['Close'], window=14).rsi()
        current_rsi = rsi_series.iloc[-1]

        # 3) 200일 이동평균선 (장기 추세)
        sma200 = data['Close'].rolling(window=200).mean().iloc[-1]
        trend_str = "상승추세 ↗️" if (sma200 and current_price >= sma200) else "하락추세 ↘️"

        # 4) 볼린저 밴드 (20일 기준)
        bb = BollingerBands(close=data['Close'], window=20, window_dev=2)
        bb_h = bb.bollinger_hband().iloc[-1]
        bb_l = bb.bollinger_lband().iloc[-1]
        
        bb_status = "보통"
        if current_price <= bb_l:
            bb_status = "밴드 하단 이탈(반등 가능성)"
        elif current_price >= bb_h:
            bb_status = "밴드 상단 돌파(과열)"

        # 매매 신호 통합 판정
        rsi_signal = None
        if current_rsi <= 35:
            rsi_signal = "과매도"
            signals.append(f"{ticker_symbol} 매수 검토 (RSI {current_rsi:.1f})")
        elif current_rsi >= 65:
            rsi_signal = "과매수"
            signals.append(f"{ticker_symbol} 매도 검토 (RSI {current_rsi:.1f})")

        # 항목별 리포트 작성
        line = (
            f"• {ticker_symbol}\n"
            f"  - 현재가: ${current_price:,.2f} | 200일선: {trend_str}\n"
            f"  - RSI: {current_rsi:.1f} ({rsi_signal if rsi_signal else '중립'})\n"
            f"  - 볼린저 밴드: {bb_status} (상단 ${bb_h:,.2f} / 하단 ${bb_l:,.2f})\n"
            f"  - 52주 최고/최저: ${high_52w:,.2f} / ${low_52w:,.2f}\n"
            f"  - 기간별 변동률: 1주({change_1w}) | 1개월({change_1m}) | 3개월({change_3m})\n"
        )
        report_lines.append(line)

    except Exception as e:
        report_lines.append(f"• {ticker_symbol}: 데이터 조회 실패 ({e})\n")

now_str = datetime.now().strftime("%Y-%m-%d %H:%M UTC")
summary = f"포착된 주요 신호: {', '.join(signals)}" if signals else "특이 신호: 없음 (모든 종목 안정적)"

# 용어 설명 섹션을 맨 마지막에 포함
email_body = f"""[ AI 시장 종합 분석 및 포트폴리오 리포트 ]
측정 시각: {now_str}
요약: {summary}

==================================================
보유 포트폴리오 전체 현황 ({len(TICKERS)}개 종목)
==================================================

""" + "\n".join(report_lines) + """
==================================================
💡 [지표 및 용어 상세 설명]
==================================================
1. RSI (상대강도지수)
   - 주가의 매수/매도 강도를 0~100 수치로 나타낸 지표입니다.
   - 35 이하: 과매도 상태로, 단기 저평가 구간 (매수 고려)
   - 65 이상: 과매수 상태로, 단기 고평가 구간 (매도/이익실현 고려)

2. 200일선 (장기 추세)
   - 최근 200일간 주가의 평균값으로, 대세 상승/하락을 구분합니다.
   - 상승추세 ↗️: 현재가가 200일선 위 (장기적 우상향 구도)
   - 하락추세 ↘️: 현재가가 200일선 아래 (장기적 우하향 구도)

3. 볼린저 밴드 (Bollinger Bands)
   - 주가가 통계적으로 움직일 수 있는 표준 범위(상단~하단)입니다.
   - 밴드 하단 이탈: 주가가 지나치게 떨어져 기술적 반등이 나올 가능성 높음
   - 밴드 상단 돌파: 단기적으로 시세가 과열되어 조정이 올 가능성 높음

4. 52주 최고/최저 & 변동률
   - 1년(52주) 중 가장 높았던 가격과 낮았던 가격의 범위입니다.
   - 1주/1개월/3개월 수익률을 통해 최근 단기 및 중기 흐름을 파악합니다.
"""

subject = f"[종합 리포트] 포트폴리오 전체 분석 ({f'{len(signals)}개 특이신호!' if signals else '이상 없음'})"
send_email(subject, email_body)
