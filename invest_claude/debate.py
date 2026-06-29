"""토론방(DebateRoom) 오케스트레이터.

여러 분석가가 여러 라운드에 걸쳐 라운드로빈으로 발언한다. 각 발언자는
지금까지의 전체 토론 기록(transcript)을 보고 발언하므로 서로 '대화'한다.
모든 라운드가 끝나면 각 분석가가 추천을 내고, 포트폴리오 매니저가 종합해
최종 Decision 을 만든다.
"""

from __future__ import annotations

from typing import List, Sequence

from .agents.base import BaseAgent
from .agents.portfolio_manager import PortfolioManager
from .models import Decision, MarketSnapshot, Message, Recommendation


class DebateRoom:
    def __init__(
        self,
        analysts: Sequence[BaseAgent],
        portfolio_manager: PortfolioManager,
        rounds: int = 2,
    ) -> None:
        self.analysts = list(analysts)
        self.portfolio_manager = portfolio_manager
        self.rounds = max(1, rounds)

    def run(
        self,
        snapshot: MarketSnapshot,
        cash: float,
        current_shares: int = 0,
    ) -> Decision:
        """한 종목에 대한 토론 전체를 실행하고 Decision 을 반환한다."""
        transcript: List[Message] = []

        # 여러 라운드 라운드로빈 발언
        for _ in range(self.rounds):
            for analyst in self.analysts:
                msg = analyst.speak(snapshot, transcript)
                transcript.append(msg)

        # 각 분석가의 최종 추천
        recommendations: List[Recommendation] = [
            analyst.recommend(snapshot, transcript) for analyst in self.analysts
        ]

        # 포트폴리오 매니저 종합
        decision = self.portfolio_manager.decide(
            snapshot=snapshot,
            transcript=transcript,
            recommendations=recommendations,
            cash=cash,
            current_shares=current_shares,
        )
        return decision
