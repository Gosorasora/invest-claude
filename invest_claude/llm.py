"""LLM 클라이언트.

`LLMClient` 인터페이스와 두 구현체를 제공한다.
- `MockLLM`: 외부 의존성 없이 동작하는 결정론적 규칙 기반 LLM.
- `AnthropicLLM`: ANTHROPIC_API_KEY + anthropic 패키지가 있을 때 실제 Claude 사용.

`create_llm()` 팩토리가 설정/환경에 따라 적절한 구현을 고른다.
"""

from __future__ import annotations

from typing import Protocol

from .config import Config, has_anthropic_key


class LLMClient(Protocol):
    """LLM 클라이언트가 만족해야 하는 최소 인터페이스."""

    name: str

    def complete(self, system: str, user: str) -> str:
        """system + user 프롬프트로 텍스트 응답을 생성한다."""
        ...


class MockLLM:
    """결정론적 모의 LLM.

    실제로 텍스트를 '생성'하지는 않는다. 에이전트(base.py)가 시장 숫자를
    직접 해석해 페르소나별 문장을 만들기 때문에, MockLLM 의 complete() 는
    에이전트가 넘겨준 user 프롬프트(이미 완성된 발언)를 그대로 돌려준다.
    이렇게 하면 동일 입력에 대해 항상 동일 출력을 보장한다.
    """

    name = "mock"

    def complete(self, system: str, user: str) -> str:
        return user


class AnthropicLLM:
    """실제 Claude(claude-opus-4-8 기본)를 사용하는 클라이언트.

    anthropic 패키지를 지연 임포트한다. 네트워크/SDK 오류는 잡아서
    짧은 메시지로 폴백하고 전체 실행을 중단시키지 않는다.
    """

    name = "anthropic"

    def __init__(self, model: str = "claude-opus-4-8") -> None:
        self.model = model
        # 지연 임포트: 패키지가 없으면 여기서 ImportError 발생 → 팩토리가 처리
        import anthropic  # type: ignore

        self._client = anthropic.Anthropic()

    def complete(self, system: str, user: str) -> str:
        try:
            # claude-opus-4-8 은 adaptive thinking 사용. budget_tokens 는 사용 불가.
            resp = self._client.messages.create(
                model=self.model,
                max_tokens=1024,
                system=system,
                messages=[{"role": "user", "content": user}],
            )
            parts = []
            for block in resp.content:
                if getattr(block, "type", None) == "text":
                    parts.append(block.text)
            text = "".join(parts).strip()
            return text or user
        except Exception as exc:  # 네트워크/인증 등 모든 오류를 폴백 처리
            return f"(LLM 호출 실패, 규칙 기반 분석으로 대체) {user}\n[오류: {exc}]"


def create_llm(config: Config) -> LLMClient:
    """설정에 따라 LLM 구현을 선택한다.

    - llm == "mock": 항상 MockLLM
    - llm == "anthropic": AnthropicLLM 시도, 실패 시 MockLLM 폴백
    - llm == "auto"(기본): 키 + 패키지가 모두 있으면 AnthropicLLM, 아니면 MockLLM
    """
    mode = (config.llm or "auto").lower()

    if mode == "mock":
        return MockLLM()

    want_anthropic = mode == "anthropic" or (mode == "auto" and has_anthropic_key())
    if want_anthropic:
        try:
            return AnthropicLLM(model=config.model)
        except Exception:
            # 패키지 미설치 등 → 조용히 MockLLM 으로 폴백
            return MockLLM()

    return MockLLM()
