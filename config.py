"""
[stock-trader] 설정 파일
한국투자증권(KIS) Open API 계정 정보 및 매매 전략 파라미터
"""
import os

# ==========================================
# 1. 한국투자증권(KIS) 계정 및 API 키 설정
# KIS Developers (https://apiportal.koreainvestment.com) 발급 키
# ==========================================
# 모의투자 여부 (True: 모의투자, False: 실전투자)
# * 처음에는 반드시 True(모의투자)로 충분히 검증 후 False로 전환하세요!
IS_VIRTUAL = True

# 모의투자 API 키
VIRTUAL_APP_KEY = os.getenv("KIS_VIRTUAL_APP_KEY", "YOUR_VIRTUAL_APP_KEY")
VIRTUAL_APP_SECRET = os.getenv("KIS_VIRTUAL_APP_SECRET", "YOUR_VIRTUAL_APP_SECRET")
VIRTUAL_CANO = os.getenv("KIS_VIRTUAL_CANO", "00000000")  # 계좌번호 앞 8자리
VIRTUAL_ACNT_PRDT_CD = "01"  # 계좌 상품코드 (기본 01)

# 실전투자 API 키
PROD_APP_KEY = os.getenv("KIS_PROD_APP_KEY", "YOUR_PROD_APP_KEY")
PROD_APP_SECRET = os.getenv("KIS_PROD_APP_SECRET", "YOUR_PROD_APP_SECRET")
PROD_CANO = os.getenv("KIS_PROD_CANO", "00000000")  # 계좌번호 앞 8자리
PROD_ACNT_PRDT_CD = "01"

# 현재 환경에 따른 활성 설정 반환
APP_KEY = VIRTUAL_APP_KEY if IS_VIRTUAL else PROD_APP_KEY
APP_SECRET = VIRTUAL_APP_SECRET if IS_VIRTUAL else PROD_APP_SECRET
CANO = VIRTUAL_CANO if IS_VIRTUAL else PROD_CANO
ACNT_PRDT_CD = VIRTUAL_ACNT_PRDT_CD if IS_VIRTUAL else PROD_ACNT_PRDT_CD
BASE_URL = "https://openapivts.koreainvestment.com:29443" if IS_VIRTUAL else "https://openapi.koreainvestment.com:9443"

# ==========================================
# 2. 매매 대상 종목 및 자금 관리
# ==========================================
# 감시 및 매매 대상 종목 리스트 (종목코드: 종목명)
TARGET_STOCKS = {
    "005930": "삼성전자",
    "000660": "SK하이닉스",
    "035420": "NAVER",
    "005380": "현대차",
    "068270": "셀트리온",
}

# 1회 매수 투입 금액 (단위: 원)
BUY_AMOUNT_PER_STOCK = 500_000  # 종목당 50만원씩 매수

# 최대 동시 보유 종목 수
MAX_HOLD_COUNT = 3

# ==========================================
# 3. 기본 매매 규칙 (전략 파라미터)
# ==========================================
STRATEGY_CONFIG = {
    "target_profit_rate": 3.0,     # 목표 익절률 (+3.0%)
    "stop_loss_rate": -2.0,        # 목표 손절률 (-2.0%)
    "trailing_stop_activation": 2.0, # 트레일링 스탑 발동 기준 (+2.0% 도달 시)
    "trailing_stop_drop": 0.8,     # 고점 대비 하락 폭 (-0.8% 하락 시 익절 청산)
    "volatility_k": 0.5,           # 변동성 돌파 K값 (0.5)
}

# 손실 분석 후 자동 저장/적용되는 동적 보완 룰 파일 경로
ADAPTIVE_RULES_FILE = "adaptive_rules.json"
