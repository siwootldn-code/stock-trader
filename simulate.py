"""
[stock-trader] 주말 및 테스트용 시뮬레이터
한국투자증권 API 키 없이도, 태관 님이 요청하신 3대 기능:
1. "얼마에 뭐 몇주 샀어" (매수 보고)
2. "얼마에 매도했고 수익률 %야" (익절/손절 매도 보고)
3. "손실시 ㅡ 손실 분석 및 다음 매수시 보완" (자동 원인 분석 및 필터 적용)
이 어떻게 동작하는지 3초 만에 눈으로 확인할 수 있는 시뮬레이션 스크립트입니다.
"""
import time
from notifier import Notifier
from loss_analyzer import LossAnalyzer
from strategy import TradingStrategy

def run_simulation():
    print("="*65)
    print("🧪 [stock-trader] 자동매매 및 손실 보완 엔진 시뮬레이션 시작")
    print("="*65)

    notifier = Notifier(log_path="simulation_trade_log.txt")
    analyzer = LossAnalyzer()
    strategy = TradingStrategy()

    # ----------------------------------------------------
    # 시나리오 1: 변동성 돌파 포착 및 매수 체결 보고
    # ----------------------------------------------------
    print("\n[STEP 1] 09:12:30 - 실시간 시세 감시 중 매수 시그널 포착")
    time.sleep(1)
    notifier.report_buy(
        name="SK하이닉스",
        code="000660",
        qty=3,
        price=185000,
        reason="변동성 돌파 포착 (돌파기준가: 184,500원 상향 돌파, 거래량 급증)"
    )

    # ----------------------------------------------------
    # 시나리오 2: 목표 수익률 달성 (+3.24%) 익절 매도 보고
    # ----------------------------------------------------
    print("\n[STEP 2] 09:45:10 - 목표 익절선 도달로 시장가 전량 매도")
    time.sleep(1)
    notifier.report_sell(
        name="SK하이닉스",
        code="000660",
        qty=3,
        buy_price=185000,
        sell_price=191000,
        profit_rate=3.24,
        profit_amount=18000,
        reason="목표 수익률 달성 (+3.24%)"
    )

    # ----------------------------------------------------
    # 시나리오 3: 삼성전자 손실 매도 발생 (-2.14%)
    # ----------------------------------------------------
    print("\n[STEP 3] 10:15:00 - 삼성전자 매수 후 하락으로 손절선(-2.0%) 이탈")
    time.sleep(1)
    notifier.report_buy(
        name="삼성전자",
        code="005930",
        qty=8,
        price=58000,
        reason="변동성 돌파 포착 (돌파기준가: 57,800원 돌파)"
    )

    time.sleep(1)
    notifier.report_sell(
        name="삼성전자",
        code="005930",
        qty=8,
        buy_price=58000,
        sell_price=56750,
        profit_rate=-2.16,
        profit_amount=-10000,
        reason="손절 기준가 이탈 (-2.16% <= -2.00%)"
    )

    # ----------------------------------------------------
    # 시나리오 4: [핵심] 손실 원인 자동 분석 및 다음 매수 시 보완책 도출
    # ----------------------------------------------------
    print("\n[STEP 4] 💡 손실 매매 데이터 역추적 및 원인 분석 가동")
    time.sleep(1)
    mock_loss_trade = {
        "code": "005930",
        "name": "삼성전자",
        "buy_time": "10:15:00",
        "buy_price": 58000,
        "sell_time": "10:38:20",
        "sell_price": 56750,
        "qty": 8,
        "profit_rate": -2.16,
        "loss_amount": -10000,
        "max_price_after_buy": 58100,
        "entry_volume_ratio": 0.58,   # 거래량 58% (부족)
        "kospi_change": -0.4,
        "entry_surge_rate": 1.8
    }

    analysis_res = analyzer.analyze_loss(mock_loss_trade)
    notifier.report_loss_analysis(analysis_res["formatted_report"])

    print("\n" + "="*65)
    print("✅ 시뮬레이션 완료! (결과 로그가 simulation_trade_log.txt에 저장되었습니다)")
    print(f"📁 갱신된 보완 룰셋: {analysis_res['rule_applied']}")
    print("="*65)

if __name__ == "__main__":
    run_simulation()
