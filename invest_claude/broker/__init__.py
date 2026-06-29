"""브로커 패키지."""

from __future__ import annotations

from ..config import Config
from .base import Broker
from .paper import PaperBroker
from .portfolio import Portfolio, Position

__all__ = [
    "Broker",
    "PaperBroker",
    "Portfolio",
    "Position",
    "create_broker",
]


def create_broker(config: Config) -> PaperBroker:
    """설정에 따라 브로커를 생성한다.

    현재 KIS 실거래는 미구현이므로 항상 PaperBroker 를 사용한다.
    (config.broker == 'kis' 여도 안전하게 모의 투자로 동작)
    """
    return PaperBroker(starting_cash=config.capital)
