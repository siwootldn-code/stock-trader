import json
import urllib.request
import time
from loss_analyzer import LossAnalyzer

STOCKS = {
    "005930": "삼성전자",
    "000660": "SK하이닉스",
    "005380": "현대차",
    "035420": "NAVER",
    "068270": "셀트리온"
}

def fetch_stock_data(code, count=20):
    url = f"https://m.stock.naver.com/api/stock/{code}/price?count={count}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            # data is descending by date, reverse to ascending
            candles = []
            for item in reversed(data):
                candles.append({
                    "date": item["localTradedAt"],
                    "open": int(item["openPrice"].replace(",", "")),
                    "high": int(item["highPrice"].replace(",", "")),
                    "low": int(item["lowPrice"].replace(",", "")),
                    "close": int(item["closePrice"].replace(",", "")),
                    "volume": int(item["accumulatedTradingVolume"])
                })
            return candles
    except Exception as e:
        print(f"Error fetching {code}: {e}")
        return []

def run_backtest():
    print("="*65)
    print("📊 [stock-trader] 최근 실제 국내 주식 시장 데이터 기반 가상 매매 가동")
    print("   대상: 코스피 시총 대표 5종목 (삼성전자, SK하이닉스, 현대차, NAVER, 셀트리온)")
    print("   전략: 변동성 돌파 (k=0.5) + 목표 익절(+3%) / 손절(-2%) + 손실 시 자동 룰 보완")
    print("="*65)

    analyzer = LossAnalyzer()
    all_trades = []
    capital = 10000000  # 가상 시작 자본금 1,000만원
    allocated_per_trade = 2000000 # 종목당 200만원 배정

    # 보완 룰 초기 상태
    current_rule = {
        "min_volume_ratio": 0.8,
        "max_surge_rate": 4.0,
        "tight_stop_loss": -2.0
    }

    # Fetch data for all stocks
    stock_candles = {}
    for code, name in STOCKS.items():
        candles = fetch_stock_data(code, count=20)
        if len(candles) >= 5:
            stock_candles[code] = candles

    # Collect trade opportunities across dates
    # We iterate day by day
    dates = []
    for candles in stock_candles.values():
        for c in candles[1:]: # skip day 0 as we need prev day for range
            if c["date"] not in dates:
                dates.append(c["date"])
    dates.sort()

    trade_count = 0
    win_count = 0
    loss_count = 0
    total_profit_amount = 0

    # Let's run over the last 10 trading days
    eval_dates = dates[-10:]

    for cur_date in eval_dates:
        for code, candles in stock_candles.items():
            name = STOCKS[code]
            # find candle index for cur_date
            idx = next((i for i, c in enumerate(candles) if c["date"] == cur_date), None)
            if idx is None or idx < 1:
                continue

            prev = candles[idx - 1]
            cur = candles[idx]

            # 변동성 돌파 타겟 계산
            target_range = prev["high"] - prev["low"]
            target_price = int(cur["open"] + target_range * 0.5)

            # 거래량 비율 계산 (전일 거래량 대비)
            vol_ratio = cur["volume"] / prev["volume"] if prev["volume"] > 0 else 1.0

            # 룰 필터링 체크 (손실 보완으로 상향된 룰셋 적용 여부)
            if vol_ratio < current_rule["min_volume_ratio"]:
                # 거래량 미달로 진입 차단된 케이스
                continue

            # 돌파 발생 여부 (장중 최고가가 타겟가를 넘었는가)
            if cur["high"] >= target_price:
                # 매수 체결
                buy_price = target_price
                qty = allocated_per_trade // buy_price
                if qty == 0:
                    continue

                total_buy_val = buy_price * qty
                trade_count += 1

                print(f"\n[{cur_date}] 📈 [매수 체결 보고]")
                print(f"  - 종목: {name} ({code}) {qty}주")
                print(f"  - 매수가: {buy_price:,}원 (총 {total_buy_val:,}원)")
                print(f"  - 진입 시그널: 변동성 돌파 달성 (당일 시가 {cur['open']:,}원 + 변동폭 {int(target_range*0.5):,}원)")

                # 매도 가격 결정 (익절 +3%, 손절 -2%, 혹은 종가 청산)
                potential_profit = (cur["high"] - buy_price) / buy_price * 100
                potential_loss = (cur["low"] - buy_price) / buy_price * 100

                stop_loss_val = current_rule.get("tight_stop_loss", {}).get(code, -2.0) if isinstance(current_rule.get("tight_stop_loss"), dict) else -2.0
                if potential_profit >= 3.0:
                    sell_price = int(buy_price * 1.03)
                    profit_rate = 3.0
                    profit_amt = int((sell_price - buy_price) * qty)
                    is_win = True
                elif potential_loss <= stop_loss_val:
                    sell_price = int(buy_price * (1 + stop_loss_val/100))
                    profit_rate = stop_loss_val
                    profit_amt = int((sell_price - buy_price) * qty)
                    is_win = False
                else:
                    sell_price = cur["close"]
                    profit_rate = round((sell_price - buy_price) / buy_price * 100, 2)
                    profit_amt = int((sell_price - buy_price) * qty)
                    is_win = profit_rate > 0

                total_profit_amount += profit_amt

                if is_win:
                    win_count += 1
                    print(f"[{cur_date}] 🎉 [매도 보고 - 익절]")
                    print(f"  - 종목: {name} {qty}주 전량 매도")
                    print(f"  - 매수가: {buy_price:,}원 ➔ 매도가: {sell_price:,}원")
                    print(f"  - 수익률: +{profit_rate:.2f}% (실현손익: +{profit_amt:,}원)")
                else:
                    loss_count += 1
                    print(f"[{cur_date}] 📉 [매도 보고 - 손절/손실]")
                    print(f"  - 종목: {name} {qty}주 전량 매도")
                    print(f"  - 매수가: {buy_price:,}원 ➔ 매도가: {sell_price:,}원")
                    print(f"  - 수익률: {profit_rate:.2f}% (실현손익: {profit_amt:,}원)")

                    # 손실 분석 가동 및 보완책 자동 갱신
                    trade_info = {
                        "code": code,
                        "name": name,
                        "buy_price": buy_price,
                        "sell_price": sell_price,
                        "qty": qty,
                        "profit_rate": profit_rate,
                        "loss_amount": abs(profit_amt),
                        "max_price_after_buy": cur["high"],
                        "entry_volume_ratio": vol_ratio,
                        "kospi_change": 0.0,
                        "entry_surge_rate": (cur["high"] - cur["open"]) / cur["open"] * 100
                    }
                    analysis = analyzer.analyze_loss(trade_info)
                    print(f"\n  💡 [손실 원인 정밀 진단]")
                    print(f"     진단 유형: {analysis['diagnosis_type']}")
                    print(f"     상세 원인: {analysis['cause_summary']}")
                    print(f"  🛡️ [다음 매수 시 자동 보완책]")
                    print(f"     {analysis['countermeasure']}")

                    # 룰 업데이트
                    if "min_volume_ratio" in analysis["rule_applied"]:
                        current_rule["min_volume_ratio"] = analysis["rule_applied"]["min_volume_ratio"]
                    if "tight_stop_loss" in analysis["rule_applied"]:
                        current_rule["tight_stop_loss"] = analysis["rule_applied"]["tight_stop_loss"]
                    print(f"     ➔ 현재 시스템 적용 필터: 최소 거래량 기준 {int(current_rule['min_volume_ratio']*100)}% 이상 돌파 시만 진입")

    print("\n" + "="*65)
    print("🏁 [가상 매매 최종 성과 리포트]")
    print(f"  - 총 매매 횟수: {trade_count}회 (승: {win_count}회, 패: {loss_count}회)")
    win_rate = (win_count / trade_count * 100) if trade_count > 0 else 0
    print(f"  - 승률: {win_rate:.1f}%")
    print(f"  - 누적 실현 손익: {total_profit_amount:+,}원")
    print("="*65)

if __name__ == "__main__":
    run_backtest()
