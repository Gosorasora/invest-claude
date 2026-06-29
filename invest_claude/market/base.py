"""시장 데이터 제공자 인터페이스."""

from __future__ import annotations

from typing import Protocol

from ..models import MarketSnapshot


class MarketDataProvider(Protocol):
    """종목 코드로 시장 스냅샷을 반환하는 제공자."""

    def get_snapshot(self, symbol: str) -> MarketSnapshot:
        ...
