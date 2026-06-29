"""결정론적 모의 시장 데이터 제공자.

`hashlib.sha256(symbol)` 로 안정적인 시드를 만들어 랜덤 워크 가격 히스토리를
생성한다. time/random 기반 시드를 쓰지 않으므로 실행할 때마다 동일한 결과가
나온다(재현 가능). 외부 네트워크 호출이 전혀 없다.
"""

from __future__ import annotations

import hashlib
import math
from typing import Dict, List

from ..models import MarketSnapshot


# 데모용 종목명 매핑 (없으면 코드 그대로 사용)
_KNOWN_NAMES: Dict[str, str] = {
    "005930": "삼성전자",
    "000660": "SK하이닉스",
    "035420": "NAVER",
    "035720": "카카오",
    "005380": "현대차",
    "051910": "LG화학",
    "207940": "삼성바이오로직스",
}


class _SeededRandom:
    """sha256 시드 기반의 작고 결정론적인 PRNG (LCG).

    표준 라이브러리의 random 모듈 대신 사용해 시드/구현이 명확하고
    플랫폼과 무관하게 재현 가능하도록 한다.
    """

    def __init__(self, seed: int) -> None:
        # 0 시드 방지
        self._state = (seed % (2**63 - 1)) or 1

    def next_float(self) -> float:
        """[0, 1) 범위의 결정론적 난수."""
        # numerical recipes 계열 LCG 상수
        self._state = (self._state * 6364136223846793005 + 1442695040888963407) % (2**64)
        return (self._state >> 11) / float(2**53)


def _seed_from_symbol(symbol: str) -> int:
    digest = hashlib.sha256(symbol.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big")


def _sma(values: List[float], window: int) -> float:
    if not values:
        return 0.0
    window = min(window, len(values))
    return sum(values[-window:]) / window


def _rsi(values: List[float], period: int = 14) -> float:
    """단순 RSI 근사치."""
    if len(values) < 2:
        return 50.0
    gains = 0.0
    losses = 0.0
    window = values[-(period + 1):] if len(values) > period else values
    for prev, cur in zip(window, window[1:]):
        diff = cur - prev
        if diff >= 0:
            gains += diff
        else:
            losses -= diff
    n = max(len(window) - 1, 1)
    avg_gain = gains / n
    avg_loss = losses / n
    if avg_loss == 0:
        return 100.0 if avg_gain > 0 else 50.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


class MockMarketData:
    """결정론적 합성 시장 데이터 제공자."""

    def __init__(self, points: int = 30) -> None:
        self.points = points

    def get_snapshot(self, symbol: str) -> MarketSnapshot:
        rng = _SeededRandom(_seed_from_symbol(symbol))

        # 시작 가격: 종목별로 다르되 합리적인 범위 (10,000 ~ 200,000)
        base_price = 10_000 + rng.next_float() * 190_000

        # 종목별 드리프트(추세). -0.4% ~ +0.4% 범위.
        drift = (rng.next_float() - 0.5) * 0.008

        history: List[float] = []
        price = base_price
        for _ in range(self.points):
            # 랜덤 워크: 드리프트 + 변동성
            shock = (rng.next_float() - 0.5) * 0.04  # ±2% 일간 변동
            price = max(1.0, price * (1.0 + drift + shock))
            history.append(round(price, 1))

        last = history[-1]
        prev_close = history[-2] if len(history) >= 2 else last
        change_pct = ((last - prev_close) / prev_close * 100.0) if prev_close else 0.0

        avg_volume = int(500_000 + rng.next_float() * 9_500_000)
        # 거래량은 가격 변동 크기에 비례하도록(변동 클수록 거래 활발)
        vol_factor = 0.6 + abs(change_pct) / 5.0 + rng.next_float() * 0.8
        volume = int(avg_volume * vol_factor)

        per = round(5.0 + rng.next_float() * 35.0, 1)  # 5 ~ 40
        pbr = round(0.4 + rng.next_float() * 4.6, 2)  # 0.4 ~ 5.0

        return MarketSnapshot(
            symbol=symbol,
            name=_KNOWN_NAMES.get(symbol, symbol),
            price=round(last, 1),
            prev_close=round(prev_close, 1),
            change_pct=round(change_pct, 2),
            volume=volume,
            avg_volume=avg_volume,
            history=history,
            sma5=round(_sma(history, 5), 1),
            sma20=round(_sma(history, 20), 1),
            rsi=round(_rsi(history), 1),
            per=per,
            pbr=pbr,
        )
