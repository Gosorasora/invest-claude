"""설정 로딩.

`config.yaml` 이 있고 `pyyaml` 이 설치돼 있으면 그것을 읽는다.
둘 중 하나라도 없으면 안전한 기본값으로 동작한다.
환경 변수(ANTHROPIC_API_KEY, INVEST_LLM 등)로 일부 값을 덮어쓴다.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict


# 기본 분석가 가중치 (포트폴리오 매니저의 가중 투표에 사용)
DEFAULT_AGENT_WEIGHTS: Dict[str, float] = {
    "강세론자": 1.0,
    "약세론자": 1.0,
    "기술적 분석가": 1.0,
    "리스크 매니저": 1.2,  # 리스크 관리에 약간 더 무게를 둔다
}


@dataclass
class Config:
    """런타임 설정 값 모음."""

    capital: float = 10_000_000.0  # 초기 자본(원)
    rounds: int = 2  # 토론 라운드 수
    model: str = "claude-opus-4-8"  # 사용할 Claude 모델 ID
    llm: str = "auto"  # auto | mock | anthropic
    data_provider: str = "mock"  # mock | kis
    broker: str = "paper"  # paper | kis
    agent_weights: Dict[str, float] = field(default_factory=lambda: dict(DEFAULT_AGENT_WEIGHTS))


def _load_yaml(path: Path) -> dict:
    """pyyaml 이 있으면 config.yaml 을 파싱한다. 없으면 빈 dict."""
    try:
        import yaml  # type: ignore
    except Exception:
        return {}
    try:
        with path.open("r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
        return data or {}
    except Exception:
        return {}


def load_config(path: str | os.PathLike | None = None) -> Config:
    """설정을 로드한다.

    우선순위: 기본값 < config.yaml < 환경 변수.
    """
    cfg = Config()

    # 1) config.yaml 적용 (pyyaml 있을 때만)
    if path is None:
        # 패키지 기준 프로젝트 루트의 config.yaml 을 찾는다
        root = Path(__file__).resolve().parents[2]
        path = root / "config.yaml"
    yaml_path = Path(path)
    if yaml_path.exists():
        data = _load_yaml(yaml_path)
        if "capital" in data:
            cfg.capital = float(data["capital"])
        if "rounds" in data:
            cfg.rounds = int(data["rounds"])
        if "model" in data:
            cfg.model = str(data["model"])
        if "llm" in data:
            cfg.llm = str(data["llm"])
        if "data_provider" in data:
            cfg.data_provider = str(data["data_provider"])
        if "broker" in data:
            cfg.broker = str(data["broker"])
        if isinstance(data.get("agent_weights"), dict):
            # YAML 의 가중치로 덮어쓴다
            cfg.agent_weights.update(
                {str(k): float(v) for k, v in data["agent_weights"].items()}
            )

    # 2) 환경 변수 덮어쓰기
    env_llm = os.environ.get("INVEST_LLM")
    if env_llm:
        cfg.llm = env_llm.strip().lower()
    env_model = os.environ.get("INVEST_MODEL")
    if env_model:
        cfg.model = env_model.strip()

    return cfg


def has_anthropic_key() -> bool:
    """ANTHROPIC_API_KEY 가 설정되어 있는지 확인."""
    return bool(os.environ.get("ANTHROPIC_API_KEY"))
