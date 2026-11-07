"""
[stock-trader] 체결 보고 및 알림 모듈
- 매수 완료 보고
- 매도 완료 보고 (수익률 및 실현손익)
- 손실 분석 및 보완책 보고
- 로컬 trade_log.txt 영구 기록
"""
import datetime

class Notifier:
    def __init__(self, log_path: str = "trade_log.txt"):
        self.log_path = log_path

    def _log_to_file(self, message: str):
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}]\n{message}\n" + "-"*50 + "\n")

    def report_buy(self, name: str, code: str, qty: int, price: int, reason: str = "") -> str:
        total = qty * price
        text = (
            f"📈 [매수 체결 완료]\n"
            f"- 종목: {name} ({code})\n"
            f"- 수량: {qty}주\n"
            f"- 체결단가: {price:,}원 (총 매수금: {total:,}원)\n"
            f"- 진입 사유: {reason}"
        )
        print("\n" + text + "\n")
        self._log_to_file(text)
        return text

    def report_sell(self, name: str, code: str, qty: int, buy_price: int, sell_price: int, profit_rate: float, profit_amount: int, reason: str = "") -> str:
        is_profit = profit_rate > 0
        tag = "🎉 [익절 매도 완료]" if is_profit else "📉 [손절 매도 완료]"
        sign = "+" if profit_rate > 0 else ""
        text = (
            f"{tag}\n"
            f"- 종목: {name} ({code}) {qty}주\n"
            f"- 매입단가: {buy_price:,}원 ➔ 매도단가: {sell_price:,}원\n"
            f"- 수익률: {sign}{profit_rate:.2f}%\n"
            f"- 실현손익: {sign}{profit_amount:,}원\n"
            f"- 매도 사유: {reason}"
        )
        print("\n" + text + "\n")
        self._log_to_file(text)
        return text

    def report_loss_analysis(self, report_text: str):
        print("\n" + report_text + "\n")
        self._log_to_file(report_text)
