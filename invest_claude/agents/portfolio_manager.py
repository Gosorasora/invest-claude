"""포트폴리오 매니저(Portfolio Manager) 에이전트.

분석가들의 토론 기록과 추천을 종합해 최종 의사결정(Decision)을 만든다.
확신도 가중 투표로 순(net) 매수 성향을 계산하고, 리스크 매니저의 목표
비중과 가용 현금/현재가를 고려해 수량을 산정한다.
"""

from __future__ import annotations

from typing import Dict, List

from ..llm import LLMClient
from ..models import Action, Decision, MarketSnapshot, Message, Recommendation


class PortfolioManager:
    name = "포트폴리오 매니저"
    role = "최종 의사결정자"

    def __init__(self, llm: LLMClient, agent_weights: Dict[str, float] | None = None) -> None:
        self.llm = llm
        self.agent_weights = agent_weights or {}

    def system_prompt(self) -> str:
        return (
            "당신은 포트폴리오 매니저입니다. 강세론자·약세론자·기술적 분석가·"
            "리스크 매니저의 토론을 종합해 최종 BUY/SELL/HOLD 와 수량을 결정합니다. "
            "확신도 가중 투표 결과와 리스크 한도를 균형 있게 반영하세요."
        )

    def _weight(self, agent_name: str) -> float:
        return self.agent_weights.get(agent_name, 1.0)

    def decide(
        self,
        snapshot: MarketSnapshot,
        transcript: List[Message],
        recommendations: List[Recommendation],
        cash: float,
        current_shares: int = 0,
    ) -> Decision:
        """최종 의사결정 산출.

        절차:
        1. 각 추천에 (가중치 × 확신도) 부호 점수를 부여(BUY +, SELL -, HOLD 0).
        2. 점수 합을 가중치 합으로 정규화해 net conviction(-1~+1)을 구한다.
        3. net > 임계 → BUY, net < -임계 → SELL, 그 외 HOLD.
        4. BUY 면 리스크 매니저 목표 비중과 net conviction 으로 투자 금액을
           정하고, 가용 현금을 넘지 않도록 수량을 계산한다.
        """
        weighted_signal = 0.0
        weight_total = 0.0
        for rec in recommendations:
            w = self._weight(rec.agent_name)
            weight_total += w
            if rec.action == Action.BUY:
                weighted_signal += w * rec.confidence
            elif rec.action == Action.SELL:
                weighted_signal -= w * rec.confidence
            # HOLD 는 0

        net = (weighted_signal / weight_total) if weight_total else 0.0

        # 리스크 매니저의 목표 비중을 상한으로 사용(없으면 보수적 기본값)
        risk_weight = next(
            (r.target_weight for r in recommendations if r.agent_name == "리스크 매니저"),
            0.1,
        )

        threshold = 0.15
        quantity = 0
        if net > threshold:
            action = Action.BUY
            # 투자 비중 = net conviction 으로 스케일하되 리스크 한도 이내
            invest_fraction = min(risk_weight, max(0.0, net) * risk_weight / 0.5)
            invest_fraction = max(0.0, min(invest_fraction, risk_weight))
            budget = cash * invest_fraction
            price = max(1.0, snapshot.price)
            quantity = int(budget // price)
            if quantity <= 0:
                # 예산이 1주도 안 되면 HOLD 로 전환
                action = Action.HOLD
        elif net < -threshold:
            action = Action.SELL
            quantity = current_shares  # 보유분 전량 매도(없으면 0)
        else:
            action = Action.HOLD
            quantity = 0

        confidence = round(min(0.95, abs(net) + 0.3), 2)

        # 근거 요약
        votes = ", ".join(
            f"{r.agent_name}={r.action}({r.confidence:.0%})" for r in recommendations
        )
        rationale_core = (
            f"종합 컨빅션 {net:+.2f} (임계 ±{threshold}). 투표: {votes}. "
            f"리스크 한도 비중 {risk_weight:.0%}. → 최종 {action}"
            + (f" {quantity}주" if action != Action.HOLD else "")
        )
        rationale = self.llm.complete(self.system_prompt(), rationale_core)

        return Decision(
            symbol=snapshot.symbol,
            action=action,
            quantity=quantity,
            confidence=confidence,
            rationale=rationale,
            transcript=list(transcript),
            recommendations=list(recommendations),
        )
