"""시장 데이터 제공자 패키지."""

from __future__ import annotations

from ..config import Config
from .base import MarketDataProvider
from .kis import KISMarketData
from .mock import MockMarketData

__all__ = [
    "MarketDataProvider",
    "MockMarketData",
    "KISMarketData",
    "create_provider",
]


def create_provider(config: Config) -> MarketDataProvider:
    """설정에 따라 시장 데이터 제공자를 생성한다.

    kis 를 선택했더라도 자격증명이 없으면 get_snapshot 호출 시 명확한
    NotImplementedError 가 나도록 한다. 기본은 mock.
    """
    if (config.data_provider or "mock").lower() == "kis":
        return KISMarketData()
    return MockMarketData()
