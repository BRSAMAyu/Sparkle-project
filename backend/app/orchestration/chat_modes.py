from __future__ import annotations
CHAT_MODE_STANDARD = "standard"
CHAT_MODE_DEEP_ANALYSIS = "deep_analysis"
CHAT_MODE_STUDY_PLAN = "study_plan"
CHAT_MODE_ERROR_DIAGNOSIS = "error_diagnosis"
CHAT_MODE_EXPERT_AUTO = "expert_auto"
CHAT_MODE_EXPERT_PREFIX = "expert::"
CHAT_MODE_TEAM_PREFIX = "team::"


SUPPORTED_CHAT_MODES = {
    CHAT_MODE_STANDARD,
    CHAT_MODE_DEEP_ANALYSIS,
    CHAT_MODE_STUDY_PLAN,
    CHAT_MODE_ERROR_DIAGNOSIS,
    CHAT_MODE_EXPERT_AUTO,
}


def normalize_chat_mode(chat_mode: str | None) -> str:
    """Normalize incoming chat mode to a supported mode.

    Rules:
    - Empty values fallback to standard
    - Explicit expert modes keep original value if they use expert:: prefix
    - Unknown modes fallback to standard for compatibility
    """
    mode = (chat_mode or "").strip()
    if not mode:
        return CHAT_MODE_STANDARD
    if mode.startswith(CHAT_MODE_EXPERT_PREFIX):
        return mode
    if mode.startswith(CHAT_MODE_TEAM_PREFIX):
        return mode
    if mode in SUPPORTED_CHAT_MODES:
        return mode
    return CHAT_MODE_STANDARD


def is_expert_chat_mode(chat_mode: str | None) -> bool:
    mode = normalize_chat_mode(chat_mode)
    return mode == CHAT_MODE_EXPERT_AUTO or mode.startswith(CHAT_MODE_EXPERT_PREFIX)


def extract_expert_id(chat_mode: str | None) -> str | None:
    mode = normalize_chat_mode(chat_mode)
    if not mode.startswith(CHAT_MODE_EXPERT_PREFIX):
        return None
    expert_id = mode[len(CHAT_MODE_EXPERT_PREFIX):].strip()
    return expert_id or None


def parse_team_spec(chat_mode: str | None) -> dict | None:
    """Parse team::<json_spec> into a structured config."""
    mode = (chat_mode or "").strip()
    if not mode.startswith(CHAT_MODE_TEAM_PREFIX):
        return None
    raw = mode[len(CHAT_MODE_TEAM_PREFIX):].strip()
    if not raw:
        return None
    try:
        import json

        spec = json.loads(raw)
        return spec if isinstance(spec, dict) else None
    except Exception:
        return None
