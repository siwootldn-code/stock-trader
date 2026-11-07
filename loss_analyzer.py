"""
[stock-trader] 손실 분석 및 전략 자동 보완 엔진
- 손실 매도 발생 시 거래 데이터(체결가, 진입시점 거래량, 최고가, 보유시간 등) 역추적
- 4대 손실 패턴(가짜돌파, 시장급락, 고점추격, 횡보휩소) 자동 진단
- 다음 매수 시 보완책(Adaptive Filter) 자동 도출 및 룰셋(adaptive_rules.json) 즉시 갱신
- 태관 님이 직관적으로 받아볼 수 있는 요약 브리핑 생성
"""
import os
import json
import datetime
import config

class LossAnalyzer:
    def __init__(self):
        self.rules_file = config.ADAPTIVE_RULES_FILE
        self.history_file = "loss_analysis_history.json"

    def analyze_loss(self, trade_data: dict) -> dict:
        """
        손실 거래 정밀 분석 및 보완책 수립
        trade_data 형식:
        {
            "code": "005930",
            "name": "삼성전자",
            "buy_time": "09:15:20",
            "buy_price": 58000,
            "sell_time": "09:42:10",
            "sell_price": 56800,
            "qty": 8,
            "profit_rate": -2.07,
            "loss_amount": -9600,
            "max_price_after_buy": 58200,   # 매수 후 최고가
            "entry_volume_ratio": 0.65,      # 진입 시점 거래량 비율 (전일대비)
            "kospi_change": -0.85,          # 보유 중 코스피 등락폭
            "entry_surge_rate": 6.2         # 매수 당시 시가 대비 상승률
        }
        """
        code = trade_data["code"]
        name = trade_data["name"]
        profit_rate = trade_data["profit_rate"]
        loss_amount = trade_data["loss_amount"]
        buy_price = trade_data["buy_price"]
        sell_price = trade_data["sell_price"]
        max_p = trade_data.get("max_price_after_buy", buy_price)
        vol_ratio = trade_data.get("entry_volume_ratio", 1.0)
        kospi_chg = trade_data.get("kospi_change", 0.0)
        surge_rate = trade_data.get("entry_surge_rate", 2.0)

        diagnosis_type = ""
        cause_summary = ""
        countermeasure = ""
        rule_update = {}

        # 1. 원인 판별 트리
        # Case A: 시장 급락 연동
        if kospi_chg <= -1.0:
            diagnosis_type = "시장 지수 급락 연동 (Market Drop)"
            cause_summary = f"진입 후 코스피 지수가 {kospi_chg:.2f}% 급락하며 외인/기관의 동반 매도세에 밀려 하락했습니다."
            countermeasure = "코스피 지수가 5분봉 20선 아래로 꺾이거나 지수 -1.0% 이하 구간에서는 모든 신규 매수를 자동 차단하도록 필터를 강화합니다."
            rule_update = {"avoid_market_drop": True, "kospi_drop_threshold": -1.0}

        # Case B: 거래량 미달 가짜 돌파 (Fakeout)
        elif vol_ratio < 0.9 and max_p <= buy_price * 1.005:
            diagnosis_type = "거래량 미달 가짜 돌파 (Fakeout / Bull Trap)"
            cause_summary = f"돌파 시점 거래량이 직전 평균 대비 {vol_ratio*100:.0f}% 수준으로 후속 매수세가 붙지 않아 상단 매물벽에 즉시 반락했습니다."
            countermeasure = f"변동성 돌파 기준선 통과 시, 최소 거래량 충족 기준을 기존 80%에서 120%로 상향하여 확실한 수급 유입 시에만 진입하도록 보완합니다."
            rule_update = {"min_volume_ratio": 1.2}

        # Case C: 고점 과열 추격 매수 (Chasing Highs)
        elif surge_rate >= 5.0:
            diagnosis_type = "고점 과열 추격 매수 (Overheated Entry)"
            cause_summary = f"시가 대비 이미 +{surge_rate:.1f}% 이상 급등한 시점에서 진입하여 단기 차익 실현 매물의 타겟이 되었습니다."
            countermeasure = "당일 시가 대비 +4.5% 이상 이미 급등한 종목은 돌파가 나오더라도 진입 대상에서 제외(추격 매수 금지)합니다."
            rule_update = {"max_entry_surge_rate": 4.5}

        # Case D: 횡보장 휩소 및 지지선 이탈 (Whipsaw)
        else:
            diagnosis_type = "박스권 횡보 휩소 (Box Whipsaw)"
            cause_summary = f"방향성 없는 횡보 구간에서 일시적 호가 흔들림에 손절선(-2.0%)이 건드려졌습니다."
            countermeasure = f"{name}({code}) 종목의 손절폭을 -1.5%로 더 타이트하게 묶어 불필요한 손실 금액을 최소화하고, 당일 재진입을 1회로 제한합니다."
            rule_update = {"tight_stop_loss": {code: -1.5}}

        # 2. 보완 룰셋에 자동 반영
        self._apply_rule_update(rule_update)

        # 3. 분석 이력 저장
        analysis_result = {
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "trade": trade_data,
            "diagnosis_type": diagnosis_type,
            "cause_summary": cause_summary,
            "countermeasure": countermeasure,
            "rule_applied": rule_update
        }
        self._save_history(analysis_result)

        # 4. 태관 님 보고용 브리핑 텍스트 포맷팅
        report_text = self._format_report(trade_data, diagnosis_type, cause_summary, countermeasure)
        analysis_result["formatted_report"] = report_text
        return analysis_result

    def _apply_rule_update(self, rule_update: dict):
        """adaptive_rules.json 파일에 새 보완 룰 머지"""
        rules = {}
        if os.path.exists(self.rules_file):
            try:
                with open(self.rules_file, "r", encoding="utf-8") as f:
                    rules = json.load(f)
            except Exception:
                pass
        
        for k, v in rule_update.items():
            if isinstance(v, dict) and isinstance(rules.get(k), dict):
                rules[k].update(v)
            else:
                rules[k] = v

        with open(self.rules_file, "w", encoding="utf-8") as f:
            json.dump(rules, f, ensure_ascii=False, indent=2)

    def _save_history(self, result: dict):
        history = []
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, "r", encoding="utf-8") as f:
                    history = json.load(f)
            except Exception:
                pass
        history.append(result)
        with open(self.history_file, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)

    def _format_report(self, trade: dict, diagnosis: str, cause: str, countermeasure: str) -> str:
        name = trade["name"]
        code = trade["code"]
        qty = trade["qty"]
        buy_p = trade["buy_price"]
        sell_p = trade["sell_price"]
        profit_rate = trade["profit_rate"]
        loss_amount = trade["loss_amount"]

        lines = [
            f"📉 [손실 매도 및 원인 분석]",
            f"- 종목: {name} ({code}) {qty}주 매도 완료",
            f"- 매입가: {buy_p:,}원 ➔ 매도가: {sell_p:,}원",
            f"- 실현손익: {loss_amount:,}원 ({profit_rate:+.2f}%)",
            f"",
            f"🔍 손실 원인 분석 ({diagnosis})",
            f"  {cause}",
            f"",
            f"🛡️ 다음 매수 시 보완책 (시스템 자동 적용)",
            f"  {countermeasure}"
        ]
        return "\n".join(lines)
