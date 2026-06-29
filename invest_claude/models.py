"""핵심 데이터 모델 정의.

이 모듈은 시스템 전반에서 사용하는 dataclass 와 enum 을 정의한다.
표준 라이브러리만 사용하며 외부 의존성이 없다.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


class Action(str, Enum):
    """매매 행동. 문자열 enum 이라 JSON 직렬화가 쉽다."""

    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"

    def __str__(self) -> str:  # pragma: no cover - 표현용
        return self.value


@dataclass
class MarketSnapshot:
    """특정 종목의 한 시점 시장 데이터 스냅샷.

    지표(이동평균, RSI 등)는 시장 데이터 제공자(provider)가 계산해 채운다.
    """

    symbol: str
    name: str
    price: float
    prev_close: float
    change_pct: float
    volume: int
    avg_volume: int
    history: List[float] = field(default_factory=list)  # 약 30개의 종가
    sma5: float = 0.0
    sma20: float = 0.0
    rsi: float = 50.0
    per: float = 0.0
    pbr: float = 0.0

    @property
    def volume_ratio(self) -> float:
        """평균 거래량 대비 현재 거래량 비율."""
        if self.avg_volume <= 0:
            return 1.0
        return self.volume / self.avg_volume


@dataclass
class Message:
    """토론(debate) 중 한 에이전트가 발언한 메시지."""

    agent_name: str
    role: str
    content: str
    stance: Optional[Action] = None
    confidence: float = 0.5


@dataclass
class Recommendation:
    """각 분석가가 토론 후 내놓는 최종 추천."""

    agent_name: str
    action: Action
    confidence: float
    target_weight: float  # 0~1, 포트폴리오 내 목표 비중
    rationale: str


@dataclass
class Decision:
    """포트폴리오 매니저가 종합한 최종 의사결정."""

    symbol: str
    action: Action
    quantity: int
    confidence: float
    rationale: str
    transcript: List[Message] = field(default_factory=list)
    recommendations: List[Recommendation] = field(default_factory=list)


@dataclass
class Fill:
    """체결 결과(주문이 실제로 체결된 내역)."""

    symbol: str
    action: Action
    quantity: int
    price: float
    cost: float  # 양수면 현금 유출(매수), 음수면 현금 유입(매도)
