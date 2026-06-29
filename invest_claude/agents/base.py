"""분석가 에이전트의 베이스 클래스.

각 에이전트는 페르소나(강세/약세/기술적/리스크)를 가지며,
- speak(): 스냅샷 + 지금까지의 토론 기록을 받아 한 번 발언(Message)한다.
- recommend(): 토론 종료 후 최종 추천(Recommendation)을 낸다.

MockLLM 사용 시에도 발언이 '대화처럼' 느껴지도록, 각 에이전트는 직전
발언자의 입장을 언급한다. AnthropicLLM 사용 시에는 시스템 프롬프트로
실제 Claude 가 페르소나에 맞게 응답한다.
"""

from __future__ import annotations

from typing import List, Optional

from ..llm import LLMClient
from ..models import Action, MarketSnapshot, Message, Recommendation


class BaseAgent:
    """모든 분석가 에이전트의 공통 베이스."""

    #: 페르소나 이름 (한국어). 하위 클래스에서 지정.
    name: str = "분석가"
    #: 역할 설명
    role: str = "투자 분석가"

    def __init__(self, llm: LLMClient) -> None:
        self.llm = llm

    # ------------------------------------------------------------------
    # 하위 클래스가 반드시 구현해야 하는 부분
    # ------------------------------------------------------------------
    def system_prompt(self) -> str:
        """이 페르소나의 시스템 프롬프트(실제 LLM 용)."""
        raise NotImplementedError

    def _analyze(self, snapshot: MarketSnapshot) -> tuple[Action, float, str]:
        """규칙 기반 분석.

        반환: (입장, 확신도 0~1, 근거 문장)
        하위 클래스가 페르소나에 맞게 구현한다.
        """
        raise NotImplementedError

    # ------------------------------------------------------------------
    # 공통 동작
    # ------------------------------------------------------------------
    def speak(self, snapshot: MarketSnapshot, transcript: List[Message]) -> Message:
        """토론에서 한 번 발언한다.

        규칙 기반 분석으로 입장/확신/근거를 만들고, 직전 발언자에 대한
        반응 문구를 덧붙여 대화처럼 보이게 한다. 그 결과 문자열을 LLM 의
        complete() 에 통과시킨다(MockLLM 은 그대로 반환, AnthropicLLM 은
        Claude 가 다듬는다).
        """
        stance, confidence, rationale = self._analyze(snapshot)

        reaction = self._react_to_previous(transcript, stance)
        body = rationale if not reaction else f"{reaction} {rationale}"

        user_prompt = body
        content = self.llm.complete(self.system_prompt(), user_prompt)

        return Message(
            agent_name=self.name,
            role=self.role,
            content=content,
            stance=stance,
            confidence=round(confidence, 2),
        )

    def recommend(self, snapshot: MarketSnapshot, transcript: List[Message]) -> Recommendation:
        """토론 종료 후 최종 추천을 생성한다."""
        stance, confidence, rationale = self._analyze(snapshot)
        target_weight = self._target_weight(stance, confidence)
        return Recommendation(
            agent_name=self.name,
            action=stance,
            confidence=round(confidence, 2),
            target_weight=round(target_weight, 3),
            rationale=rationale,
        )

    # ------------------------------------------------------------------
    # 보조 메서드
    # ------------------------------------------------------------------
    def _react_to_previous(
        self, transcript: List[Message], my_stance: Action
    ) -> str:
        """직전(다른 에이전트) 발언에 대한 반응 문구를 만든다."""
        prev = self._last_other_message(transcript)
        if prev is None:
            return ""
        if prev.stance is None:
            return f"{prev.agent_name}님 의견을 들었습니다만,"
        if prev.stance == my_stance:
            return f"{prev.agent_name}님의 {prev.stance} 의견에 동의합니다."
        if my_stance == Action.HOLD:
            return f"{prev.agent_name}님은 {prev.stance}를 말씀하셨지만, 저는 신중론입니다."
        return f"{prev.agent_name}님의 {prev.stance} 주장과 달리,"

    def _last_other_message(self, transcript: List[Message]) -> Optional[Message]:
        for msg in reversed(transcript):
            if msg.agent_name != self.name:
                return msg
        return None

    def _target_weight(self, stance: Action, confidence: float) -> float:
        """입장과 확신도로부터 목표 비중(0~1)을 산출한다."""
        if stance == Action.BUY:
            # 확신이 높을수록 큰 비중. 최대 40%.
            return min(0.4, 0.1 + confidence * 0.3)
        if stance == Action.SELL:
            return 0.0  # 매도 입장은 비중 0 을 권고
        return 0.05  # HOLD: 소량 유지
