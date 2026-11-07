"""
[stock-trader] 메인 자동매매 실행 루프
- 장 시작 전 계좌 잔고 및 예수금 확인
- 감시 대상 종목 실시간 시세 폴링
- 전략 시그널에 따른 자동 매수/매도 실행
- 매매 발생 시 즉시 보고 및 손실 시 자동 원인 분석/보완
"""
import sys
import time
import datetime
import config
from kis_api import KisApi
from strategy import TradingStrategy
from loss_analyzer import LossAnalyzer
from notifier import Notifier

def is_market_open() -> bool:
    """국내 주식 정규장 시간 체크 (평일 09:00 ~ 15:20)"""
    now = datetime.datetime.now()
    if now.weekday() >= 5:  # 토, 일
        return False
    market_start = now.replace(hour=9, minute=0, second=0, microsecond=0)
    market_end = now.replace(hour=15, minute=20, second=0, microsecond=0)
    return market_start <= now <= market_end

def main():
    print("="*60)
    mode_str = "모의투자" if config.IS_VIRTUAL else "실전투자"
    print(f"🚀 [stock-trader] 한국투자증권 자동매매 시스템 시작 ({mode_str} 모드)")
    print("="*60)

    api = KisApi()
    strategy = TradingStrategy()
    analyzer = LossAnalyzer()
    notifier = Notifier()

    # 1. 초기 토큰 및 잔고 확인
    try:
        token = api.get_token()
        print("✅ KIS API 토큰 인증 성공")
        balance = api.get_balance()
        print(f"💰 예수금: {balance['cash']:,}원 | 총 평가금: {balance['eval_total']:,}원")
        print(f"📦 현재 보유 종목 수: {len(balance['stocks'])}개")
        for s in balance["stocks"]:
            print(f"   - {s['name']} ({s['code']}): {s['qty']}주 (평단가: {s['buy_price']:,.0f}원, 수익률: {s['profit_rate']:+.2f}%)")
    except Exception as e:
        print(f"❌ 초기화 오류: {e}")
        print("💡 config.py에 APP_KEY, APP_SECRET, CANO(계좌번호)가 정확히 입력되었는지 확인하세요.")
        return

    # 종목별 보유 정보 추적 맵
    holdings_tracker = {}
    for s in balance["stocks"]:
        holdings_tracker[s["code"]] = {
            "buy_price": s["buy_price"],
            "qty": s["qty"],
            "buy_time": datetime.datetime.now().strftime("%H:%M:%S"),
            "max_price": s["current_price"],
            "entry_volume_ratio": 1.0,
            "entry_surge_rate": 2.0
        }

    print("\n👀 실시간 시세 감시 및 자동매매 루프 가동 중... (Ctrl+C 로 종료)")

    while True:
        try:
            now = datetime.datetime.now()
            # 장 운영 시간 외에는 대기 안내
            if not is_market_open():
                print(f"[{now.strftime('%H:%M:%S')}] 현재 정규장 운영 시간이 아닙니다 (평일 09:00~15:20). 60초 대기 중...")
                time.sleep(60)
                continue

            # 2. 잔고 최신화
            try:
                balance = api.get_balance()
            except Exception as e:
                print(f"⚠️ 잔고 조회 지연: {e}")
                time.sleep(3)
                continue

            current_holding_codes = {s["code"] for s in balance["stocks"]}

            # 3. 보유 종목 매도 조건 체크
            for s in balance["stocks"]:
                code = s["code"]
                name = s["name"]
                qty = s["qty"]
                buy_price = int(s["buy_price"])
                curr_price = s["current_price"]

                # 추적기 데이터 갱신
                tracker = holdings_tracker.get(code, {
                    "buy_price": buy_price,
                    "qty": qty,
                    "buy_time": "09:00:00",
                    "max_price": curr_price,
                    "entry_volume_ratio": 1.0,
                    "entry_surge_rate": 2.0
                })
                tracker["max_price"] = max(tracker.get("max_price", curr_price), curr_price)
                holdings_tracker[code] = tracker

                is_sell, reason, profit_rate = strategy.check_sell_signal(
                    holding={"code": code, "buy_price": buy_price},
                    current_price=curr_price,
                    max_reached_price=tracker["max_price"]
                )

                if is_sell:
                    # 시장가 매도 주문 실행
                    try:
                        res = api.order_sell(code, qty, order_type="01")
                        profit_amount = int((curr_price - buy_price) * qty)
                        
                        # 체결 보고
                        notifier.report_sell(
                            name=name, code=code, qty=qty,
                            buy_price=buy_price, sell_price=curr_price,
                            profit_rate=profit_rate, profit_amount=profit_amount,
                            reason=reason
                        )

                        # 손실 시 -> 자동 원인 분석 및 보완 룰 적용
                        if profit_rate < 0:
                            trade_data = {
                                "code": code,
                                "name": name,
                                "buy_time": tracker.get("buy_time", ""),
                                "buy_price": buy_price,
                                "sell_time": datetime.datetime.now().strftime("%H:%M:%S"),
                                "sell_price": curr_price,
                                "qty": qty,
                                "profit_rate": profit_rate,
                                "loss_amount": profit_amount,
                                "max_price_after_buy": tracker["max_price"],
                                "entry_volume_ratio": tracker.get("entry_volume_ratio", 1.0),
                                "entry_surge_rate": tracker.get("entry_surge_rate", 2.0)
                            }
                            analysis = analyzer.analyze_loss(trade_data)
                            notifier.report_loss_analysis(analysis["formatted_report"])

                        if code in holdings_tracker:
                            del holdings_tracker[code]

                    except Exception as e:
                        print(f"❌ {name} 매도 주문 실패: {e}")

                time.sleep(0.3)  # TR Limit 보호

            # 4. 신규 매수 조건 체크 (최대 보유 종목 수 미만일 때만)
            if len(current_holding_codes) < config.MAX_HOLD_COUNT:
                for code, name in config.TARGET_STOCKS.items():
                    if code in current_holding_codes:
                        continue  # 이미 보유 중인 종목 제외

                    try:
                        price_info = api.get_current_price(code)
                        is_buy, reason = strategy.check_buy_signal(price_info)

                        if is_buy:
                            curr_price = price_info["price"]
                            # 매수 수량 계산 (1회 설정 금액 / 현재가)
                            buy_qty = max(1, config.BUY_AMOUNT_PER_STOCK // curr_price)
                            
                            # 시장가 매수 주문
                            order_res = api.order_buy(code, buy_qty, order_type="01")
                            
                            notifier.report_buy(
                                name=name, code=code, qty=buy_qty,
                                price=curr_price, reason=reason
                            )

                            holdings_tracker[code] = {
                                "buy_price": curr_price,
                                "qty": buy_qty,
                                "buy_time": datetime.datetime.now().strftime("%H:%M:%S"),
                                "max_price": curr_price,
                                "entry_volume_ratio": price_info["volume"] / max(1, price_info["prev_close"]),
                                "entry_surge_rate": ((curr_price - price_info["open"]) / price_info["open"]) * 100.0
                            }
                            break  # 1회 루프당 1종목씩 분할 매수
                    except Exception as e:
                        # 일시적 시세 조회 실패 무시
                        pass

                    time.sleep(0.3)  # TR Limit 보호

            time.sleep(2)  # 주기적 폴링 간격 (2초)

        except KeyboardInterrupt:
            print("\n🛑 자동매매 시스템을 안전하게 종료합니다.")
            break
        except Exception as e:
            print(f"⚠️ 루프 예외 발생: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()
