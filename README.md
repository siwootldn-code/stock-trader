# 📈 stock-trader (한국투자증권 자동매매 & 손실 피드백 시스템)

UI 없이 백그라운드에서 매매를 수행하고, **매수·매도·손실 원인 분석 및 보완책**만 직관적으로 보고하는 경량 자동매매 엔진입니다.

---

## 📌 핵심 기능

1. **매수 체결 보고**: 얼마에 어떤 종목을 몇 주 샀는지 즉시 기록/출력
2. **매도 체결 보고**: 매도가, 실현 손익, 수익률(%) 산출
3. **손실 정밀 분석 & 보완**: 손실 발생 시 체결 전후 데이터(거래량, 시장 지수, 고점 등)를 역추적해 원인을 진단하고 다음 매수 시 필터링 조건을 자동으로 강화 (`adaptive_rules.json`)

---

## 🚀 빠른 시작 (3분 셋팅)

### 1. 필수 라이브러리 설치
```bash
pip install requests
```

### 2. 가상 시뮬레이션 즉시 실행 (주말/테스트용)
API 키 없이도 3대 보고 기능이 어떻게 작동하는지 바로 확인할 수 있습니다.
```bash
python simulate.py
```

### 3. 실제 자동매매 설정 (`config.py`)
한국투자증권 KIS Developers (https://apiportal.koreainvestment.com)에서 발급받은 키 입력:
```python
IS_VIRTUAL = True  # 처음에는 무조건 모의투자로 테스트!

VIRTUAL_APP_KEY = "발급받은_모의투자_APP_KEY"
VIRTUAL_APP_SECRET = "발급받은_모의투자_APP_SECRET"
VIRTUAL_CANO = "계좌번호앞8자리"
```

### 4. 실전/모의 자동매매 가동
```bash
python main.py
```
- 평일 장 시간(09:00~15:20) 동안 2초 주기로 감시하며 자동 주문을 실행합니다.
- 모든 체결 내역과 분석 리포트는 `trade_log.txt`에 영구 기록됩니다.
