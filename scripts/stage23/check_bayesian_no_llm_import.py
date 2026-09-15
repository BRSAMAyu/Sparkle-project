from __future__ import annotations

from pathlib import Path


FORBIDDEN_TOKENS = (
    "openai",
    "anthropic",
    "llm_router",
    "llm_service",
    "from app.core.llm",
    "from app.services.llm",
)
TARGETS = (
    Path("backend/app/services/bayesian_routing_wire_service.py"),
    Path("backend/app/services/source_state_encoder.py"),
    Path("backend/app/learning/persistent_bayesian_learner.py"),
)


def main() -> int:
    violations: list[str] = []
    for path in TARGETS:
        text = path.read_text(encoding="utf-8").lower()
        for token in FORBIDDEN_TOKENS:
            if token in text:
                violations.append(f"{path}:{token}")

    if violations:
        raise SystemExit("FAIL bayesian no-llm import:\n" + "\n".join(violations))

    print(f"PASS bayesian no-llm import: scanned={len(TARGETS)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
