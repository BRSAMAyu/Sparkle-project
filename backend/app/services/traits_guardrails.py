from __future__ import annotations

from typing import Any


def resolve_trait_vs_dynamic(trait: Any, dynamic_state: Any) -> Any:
    """Rule AM: dynamic state always wins when trait and session state conflict."""
    _ = trait
    return dynamic_state
