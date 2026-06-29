"""브로커 인터페이스."""

from __future__ import annotations

from typing import Protocol

from ..models import Decision, Fill, MarketSnapshot


class Broker(Protocol):
    """매매 실행 브로커가 만족해야 하는 인터페이스."""

    def execute(self, decision: Decision, snapshot: MarketSnapshot) -> Fill:
        """의사결정을 체결하고 Fill 을 반환한다."""
        ...
