"""에이전트 패키지.

기본 분석가 로스터와 포트폴리오 매니저를 노출한다.
"""

from __future__ import annotations

from typing import List

from ..llm import LLMClient
from .base import BaseAgent
from .bear import BearAgent
from .bull import BullAgent
from .portfolio_manager import PortfolioManager
from .risk import RiskAgent
from .technical import TechnicalAgent

__all__ = [
    "BaseAgent",
    "BullAgent",
    "BearAgent",
    "TechnicalAgent",
    "RiskAgent",
    "PortfolioManager",
    "default_analysts",
    "default_portfolio_manager",
]


def default_analysts(llm: LLMClient) -> List[BaseAgent]:
    """라운드로빈 발언 순서대로 기본 분석가 로스터를 반환한다.

    순서: 강세론자 → 약세론자 → 기술적 분석가 → 리스크 매니저
    """
    return [
        BullAgent(llm),
        BearAgent(llm),
        TechnicalAgent(llm),
        RiskAgent(llm),
    ]


def default_portfolio_manager(llm: LLMClient, agent_weights=None) -> PortfolioManager:
    return PortfolioManager(llm, agent_weights=agent_weights)
