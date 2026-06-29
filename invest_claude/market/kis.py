"""한국투자증권(KIS) Open API 시장 데이터 - 추후 구현용 스텁.

이 파일은 실거래 연동 시 채워 넣을 자리표시자다. 자격증명(앱키/시크릿)이
없으면 NotImplementedError 를 던진다.

참고: 토스증권은 공개 자동매매 API 가 없다. 국내에서 프로그램 매매를
하려면 한국투자증권(KIS) 의 Open API 가 사실상 표준 경로다.

KIS 인증/조회 흐름 개요:
1. OAuth 토큰 발급:
   POST https://openapi.koreainvestment.com:9443/oauth2/tokenP
   body: {"grant_type": "client_credentials", "appkey": ..., "appsecret": ...}
   -> access_token (24시간 유효) 수신
2. 시세 조회(예: 주식현재가):
   GET /uapi/domestic-stock/v1/quotations/inquiry-price
   headers: authorization=Bearer <token>, appkey, appsecret, tr_id=FHKST01010100
   params: fid_cond_mrkt_div_code=J, fid_input_iscd=<종목코드>
3. 주문 시에는 hashkey 발급(POST /uapi/hashkey)으로 본문 위변조 방지 후
   주문 API 호출.
"""

from __future__ import annotations

import os

from ..models import MarketSnapshot


class KISMarketData:
    """KIS Open API 기반 시장 데이터 제공자 (미구현 스텁)."""

    BASE_URL = "https://openapi.koreainvestment.com:9443"

    def __init__(
        self,
        app_key: str | None = None,
        app_secret: str | None = None,
    ) -> None:
        self.app_key = app_key or os.environ.get("KIS_APP_KEY")
        self.app_secret = app_secret or os.environ.get("KIS_APP_SECRET")

    def _require_credentials(self) -> None:
        if not (self.app_key and self.app_secret):
            raise NotImplementedError(
                "KIS Open API 연동은 아직 구현되지 않았습니다. "
                "KIS_APP_KEY / KIS_APP_SECRET 환경 변수를 설정하고 "
                "kis.py 의 토큰 발급 및 시세 조회 로직을 구현하세요. "
                "기본 데모는 mock 제공자를 사용합니다."
            )

    def get_snapshot(self, symbol: str) -> MarketSnapshot:  # pragma: no cover - 스텁
        self._require_credentials()
        # TODO: 위 docstring 의 흐름대로 토큰 발급 + inquiry-price 호출 후
        #       MarketSnapshot 으로 매핑한다.
        raise NotImplementedError("KIS 시세 조회는 추후 구현 예정입니다.")
