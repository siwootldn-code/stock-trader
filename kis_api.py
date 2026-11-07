"""
[stock-trader] 한국투자증권 Open API (KIS Developers) REST 클라이언트
- OAuth2 토큰 발급 및 로컬 캐싱 (1일 유효)
- 현재가 시세 조회, 계좌 잔고 및 예수금 조회
- 시장가/지정가 매수 및 매도 주문
"""
import os
import json
import time
import datetime
import requests
import config

class KisApi:
    def __init__(self):
        self.base_url = config.BASE_URL
        self.app_key = config.APP_KEY
        self.app_secret = config.APP_SECRET
        self.cano = config.CANO
        self.acnt_prdt_cd = config.ACNT_PRDT_CD
        self.is_virtual = config.IS_VIRTUAL
        self.token_file = "token_virtual.json" if self.is_virtual else "token_prod.json"
        self.access_token = None
        self.token_expired_at = 0

    def get_token(self, force_refresh=False):
        """접근 토큰 발급 또는 로컬 캐시에서 로드"""
        now = time.time()
        
        # 1. 파일에서 캐시된 토큰 로드 시도
        if not force_refresh and os.path.exists(self.token_file):
            try:
                with open(self.token_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if data.get("expired_at", 0) > now + 600:  # 만료 10분 전까지 재사용
                        self.access_token = data["access_token"]
                        self.token_expired_at = data["expired_at"]
                        return self.access_token
            except Exception:
                pass

        # 2. 신규 토큰 발급 요청
        url = f"{self.base_url}/oauth2/tokenP"
        headers = {"content-type": "application/json"}
        body = {
            "grant_type": "client_credentials",
            "appkey": self.app_key,
            "appsecret": self.app_secret
        }
        
        try:
            res = requests.post(url, headers=headers, json=body, timeout=10)
            if res.status_code == 200:
                res_data = res.json()
                self.access_token = res_data["access_token"]
                expires_in = int(res_data.get("expires_in", 86400))
                self.token_expired_at = now + expires_in
                
                # 파일에 저장
                with open(self.token_file, "w", encoding="utf-8") as f:
                    json.dump({
                        "access_token": self.access_token,
                        "expired_at": self.token_expired_at,
                        "issued_at": datetime.datetime.now().isoformat()
                    }, f, indent=2)
                return self.access_token
            else:
                raise RuntimeError(f"토큰 발급 실패: {res.status_code} {res.text}")
        except Exception as e:
            raise RuntimeError(f"KIS API 토큰 요청 중 오류 발생: {e}")

    def _get_headers(self, tr_id: str):
        """공통 요청 헤더 구성"""
        token = self.get_token()
        return {
            "content-type": "application/json; charset=utf-8",
            "authorization": f"Bearer {token}",
            "appkey": self.app_key,
            "appsecret": self.app_secret,
            "tr_id": tr_id,
            "custtype": "P"
        }

    def get_current_price(self, stock_code: str) -> dict:
        """
        주식 현재가 시세 조회
        tr_id: FHKST01010100
        """
        url = f"{self.base_url}/uapi/domestic-stock/v1/quotations/inquire-price"
        headers = self._get_headers(tr_id="FHKST01010100")
        params = {
            "fid_cond_mrkt_div_code": "J",  # 주식
            "fid_input_iscd": stock_code
        }
        
        res = requests.get(url, headers=headers, params=params, timeout=5)
        if res.status_code != 200:
            raise RuntimeError(f"현재가 조회 실패 ({stock_code}): {res.text}")
            
        data = res.json()
        if data.get("rt_cd") != "0":
            raise RuntimeError(f"API 오류 ({stock_code}): {data.get('msg1')}")
            
        output = data.get("output", {})
        return {
            "code": stock_code,
            "name": config.TARGET_STOCKS.get(stock_code, stock_code),
            "price": int(output.get("stck_prpr", 0)),          # 현재가
            "open": int(output.get("stck_oprc", 0)),           # 시가
            "high": int(output.get("stck_hgpr", 0)),           # 고가
            "low": int(output.get("stck_lwpr", 0)),            # 저가
            "prev_close": int(output.get("stck_sdpr", 0)),     # 전일 종가
            "change_rate": float(output.get("prdy_ctrt", 0.0)),# 전일 대비율 (%)
            "volume": int(output.get("acml_vol", 0)),          # 누적 거래량
            "trading_value": int(output.get("acml_tr_pbmn", 0)) # 누적 거래대금 (원)
        }

    def get_balance(self) -> dict:
        """
        계좌 잔고 및 보유 종목 조회
        tr_id: VTTC8434R (모의투자) / TTTC8434R (실전투자)
        """
        tr_id = "VTTC8434R" if self.is_virtual else "TTTC8434R"
        url = f"{self.base_url}/uapi/domestic-stock/v1/trading/inquire-balance"
        headers = self._get_headers(tr_id=tr_id)
        params = {
            "CANO": self.cano,
            "ACNT_PRDT_CD": self.acnt_prdt_cd,
            "AFHR_FLG": "N",
            "OFR_HNTS_DVSN": "00",
            "UNPR_DVSN": "01",
            "FUND_STTL_ICLD_YN": "N",
            "FNCG_AMT_AUTO_RDPT_YN": "N",
            "PRCS_DVSN": "00",
            "CTX_AREA_FK100": "",
            "CTX_AREA_NK100": ""
        }
        
        res = requests.get(url, headers=headers, params=params, timeout=5)
        if res.status_code != 200:
            raise RuntimeError(f"잔고 조회 실패: {res.text}")
            
        data = res.json()
        if data.get("rt_cd") != "0":
            raise RuntimeError(f"API 오류 (잔고): {data.get('msg1')}")
            
        stock_list = []
        for item in data.get("output1", []):
            qty = int(item.get("hldg_qty", 0))
            if qty > 0:
                stock_list.append({
                    "code": item.get("pdno"),
                    "name": item.get("prdt_name"),
                    "qty": qty,
                    "buy_price": float(item.get("pchs_avg_pric", 0.0)),   # 평균 매입단가
                    "current_price": int(item.get("prpr", 0)),            # 현재가
                    "eval_profit": int(item.get("evlu_pfls_amt", 0)),      # 평가손익 금액
                    "profit_rate": float(item.get("evlu_pfls_rt", 0.0))    # 평가수익률 (%)
                })
                
        summary = data.get("output2", [{}])[0]
        cash = int(summary.get("dnca_tot_amt", 0))  # 예수금
        eval_total = int(summary.get("tot_evlu_amt", 0))  # 총 평가금액
        
        return {
            "cash": cash,
            "eval_total": eval_total,
            "stocks": stock_list
        }

    def order_buy(self, stock_code: str, qty: int, price: int = 0, order_type: str = "01") -> dict:
        """
        주식 현금 매수 주문
        tr_id: VTTC0802U (모의투자 매수) / TTTC0802U (실전투자 매수)
        order_type: '01' (시장가), '00' (지정가)
        """
        tr_id = "VTTC0802U" if self.is_virtual else "TTTC0802U"
        url = f"{self.base_url}/uapi/domestic-stock/v1/trading/order-cash"
        headers = self._get_headers(tr_id=tr_id)
        
        body = {
            "CANO": self.cano,
            "ACNT_PRDT_CD": self.acnt_prdt_cd,
            "PDNO": stock_code,
            "ORD_DVSN": order_type,
            "ORD_QTY": str(qty),
            "ORD_UNPR": str(price) if order_type == "00" else "0"
        }
        
        res = requests.post(url, headers=headers, json=body, timeout=5)
        if res.status_code != 200:
            raise RuntimeError(f"매수 주문 실패 ({stock_code}): {res.text}")
            
        data = res.json()
        if data.get("rt_cd") != "0":
            raise RuntimeError(f"주문 거부 ({stock_code}): {data.get('msg1')}")
            
        output = data.get("output", {})
        return {
            "order_no": output.get("ODNO"),
            "time": output.get("ORD_TMD"),
            "code": stock_code,
            "qty": qty,
            "type": "BUY"
        }

    def order_sell(self, stock_code: str, qty: int, price: int = 0, order_type: str = "01") -> dict:
        """
        주식 현금 매도 주문
        tr_id: VTTC0801U (모의투자 매도) / TTTC0801U (실전투자 매도)
        order_type: '01' (시장가), '00' (지정가)
        """
        tr_id = "VTTC0801U" if self.is_virtual else "TTTC0801U"
        url = f"{self.base_url}/uapi/domestic-stock/v1/trading/order-cash"
        headers = self._get_headers(tr_id=tr_id)
        
        body = {
            "CANO": self.cano,
            "ACNT_PRDT_CD": self.acnt_prdt_cd,
            "PDNO": stock_code,
            "ORD_DVSN": order_type,
            "ORD_QTY": str(qty),
            "ORD_UNPR": str(price) if order_type == "00" else "0"
        }
        
        res = requests.post(url, headers=headers, json=body, timeout=5)
        if res.status_code != 200:
            raise RuntimeError(f"매도 주문 실패 ({stock_code}): {res.text}")
            
        data = res.json()
        if data.get("rt_cd") != "0":
            raise RuntimeError(f"주문 거부 ({stock_code}): {data.get('msg1')}")
            
        output = data.get("output", {})
        return {
            "order_no": output.get("ODNO"),
            "time": output.get("ORD_TMD"),
            "code": stock_code,
            "qty": qty,
            "type": "SELL"
        }
