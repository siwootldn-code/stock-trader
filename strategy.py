"""
[stock-trader] 매매 전략 및 동적 보완 필터
- 변동성 돌파 및 모멘텀 진입 시그널 감지
- 목표 익절, 손절, 트레일링 스탑 조건 판단
- 손실 분석 결과(adaptive_rules.json)를 반영한 동적 진입 필터링
"""
import os
import json
import config

class TradingStrategy:
    def __init__(self):
        self.config = config.STRATEGY_CONFIG
        self.adaptive_rules_file = config.ADAPTIVE_RULES_FILE
        self.adaptive_rules = self.load_adaptive_rules()

    def load_adaptive_rules(self) -> dict:
        """손실 분석에 의해 축적된 보완 룰 로드"""
        if os.path.exists(self.adaptive_rules_file):
            try:
                with open(self.adaptive_rules_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        # 기본 보완 룰
        return {
            "min_volume_ratio": 0.8,     # 전일 동시간 거래량의 최소 80% 이상 충족 시 진입
            "avoid_market_drop": True,    # 시장 급락 시 신규 매수 금지
            "tight_stop_loss": None,      # 개별 종목 가변 손절 라인
            "blacklisted_stocks": []      # 반복 손실 종목 일시 제외
        }

    def save_adaptive_rules(self):
        """갱신된 보완 룰 저장"""
        with open(self.adaptive_rules_file, "w", encoding="utf-8") as f:
            json.dump(self.adaptive_rules, f, ensure_ascii=False, indent=2)

    def check_buy_signal(self, stock_info: dict, market_status: dict = None) -> tuple[bool, str]:
        """
        매수 시그널 판단 (변동성 돌파 + 보완 필터 검증)
        Returns: (is_buy_signal, reason)
        """
        code = stock_info["code"]
        name = stock_info["name"]
        price = stock_info["price"]
        open_p = stock_info["open"]
        prev_close = stock_info["prev_close"]
        high_p = stock_info["high"]
        low_p = stock_info["low"]
        vol = stock_info["volume"]

        # 0. 블랙리스트 체크
        if code in self.adaptive_rules.get("blacklisted_stocks", []):
            return False, f"손실 분석 블랙리스트 종목 (매수 제한)"

        # 1. 시장 필터 (코스피/코스닥 급락장 방어)
        if market_status and self.adaptive_rules.get("avoid_market_drop", True):
            kospi_change = market_status.get("kospi_change_rate", 0.0)
            if kospi_change <= -1.5:
                return False, f"시장 지수 급락({kospi_change:.2f}%) 필터 발동으로 매수 차단"

        # 2. 변동성 돌파 기준선 계산: 시가 + (전일 변동폭 * K)
        # 당일 고가와 저가 변동폭 기준 약식 적용
        range_val = max(high_p - low_p, prev_close * 0.02)
        target_price = int(open_p + (range_val * self.config.get("volatility_k", 0.5)))

        # 3. 돌파 여부 확인
        if price >= target_price and price > open_p:
            # 4. 보완 필터: 거래량 필터 검증
            min_vol_ratio = self.adaptive_rules.get("min_volume_ratio", 0.8)
            # 당일 거래량이 일정 수준 이상 실려야 '진성 돌파'로 인정
            if vol < 10000:  # 극저유동성 방지
                return False, f"거래량 부족 ({vol:,}주) - 가짜 돌파 의심으로 진입 보류"

            reason = f"변동성 돌파 포착 (돌파기준가: {target_price:,}원 돌파, 현재가: {price:,}원)"
            return True, reason

        return False, "돌파 조건 미충족"

    def check_sell_signal(self, holding: dict, current_price: int, max_reached_price: int = 0) -> tuple[bool, str, float]:
        """
        매도 시그널 판단 (익절, 손절, 트레일링 스탑)
        Returns: (is_sell_signal, reason, profit_rate)
        """
        buy_price = holding["buy_price"]
        profit_rate = ((current_price - buy_price) / buy_price) * 100.0

        # 종목별 커스텀 손절가 적용 여부
        custom_stop = self.adaptive_rules.get("tight_stop_loss", {}).get(holding["code"])
        stop_loss_limit = custom_stop if custom_stop else self.config.get("stop_loss_rate", -2.0)
        target_profit = self.config.get("target_profit_rate", 3.0)

        # 1. 목표 익절가 도달 (+3.0%)
        if profit_rate >= target_profit:
            return True, f"목표 수익률 달성 (+{profit_rate:.2f}%)", profit_rate

        # 2. 손절 기준 이탈 (-2.0% 또는 보완된 타이트 손절가)
        if profit_rate <= stop_loss_limit:
            return True, f"손절 기준가 이탈 ({profit_rate:.2f}% <= {stop_loss_limit:.2f}%)", profit_rate

        # 3. 트레일링 스탑 (최고점에서 일정 비율 하락 시 수익 보존 매도)
        if max_reached_price > buy_price:
            max_profit_rate = ((max_reached_price - buy_price) / buy_price) * 100.0
            act_threshold = self.config.get("trailing_stop_activation", 2.0)
            drop_limit = self.config.get("trailing_stop_drop", 0.8)
            
            if max_profit_rate >= act_threshold:
                drop_from_peak = ((max_reached_price - current_price) / max_reached_price) * 100.0
                if drop_from_peak >= drop_limit:
                    return True, f"트레일링 스탑 발동 (최고 +{max_profit_rate:.2f}% 찍고 고점 대비 -{drop_from_peak:.2f}% 밀림)", profit_rate

        return False, "홀딩 중 (매도 조건 미도달)", profit_rate
