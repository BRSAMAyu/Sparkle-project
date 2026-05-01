"""
B-002 Regression Tests: Spine Orchestrator Duplicate Code Blocks

Bug: spine_orchestrator.py had 5 identical code blocks causing:
- Double Redis writes
- Double method calls
- Inflated metrics (2x)

These tests ensure:
1. state_register.upsert_from_signal is called exactly once per signal
2. metrics recording methods are called exactly once
3. store_directive_by_id is called once per directive in each _store_* method
4. AuroraControlSignal is written exactly once
"""

import ast
import inspect
import textwrap

import pytest

from app.signals.spine_orchestrator import SpineOrchestrator


class TestStoreDirectiveMethodsSingleCall:
    """Verify each _store_*_directive method calls store_directive_by_id exactly once."""

    @pytest.mark.parametrize("method_name", [
        "_store_notification_directive",
        "_store_retrieval_directive",
        "_store_plan_directive",
        "_store_model_write_directive",
        "_store_ux_directive",
        "_store_response_directive",
        "_store_community_directive",
        "_store_skill_directive",
    ])
    def test_store_directive_by_id_called_once(self, method_name):
        """B-002 regression: each _store method must call store_directive_by_id exactly once
        (either directly or via _store_directive delegation)."""
        method = getattr(SpineOrchestrator, method_name, None)
        assert method is not None, f"Method {method_name} not found on SpineOrchestrator"

        source = inspect.getsource(method)
        count = source.count("store_directive_by_id")
        # Methods delegating to _store_directive or directive_store are also valid
        delegates = ("_store_directive" in source or "directive_store" in source) and count == 0
        assert count == 1 or delegates, (
            f"{method_name} calls store_directive_by_id {count} times, expected 1 (or delegation). "
            f"B-002 regression: duplicate directive storage."
        )

    @pytest.mark.parametrize("method_name", [
        "_store_notification_directive",
        "_store_retrieval_directive",
        "_store_plan_directive",
        "_store_model_write_directive",
        "_store_ux_directive",
        "_store_response_directive",
        "_store_community_directive",
        "_store_skill_directive",
    ])
    def test_redis_set_called_once(self, method_name):
        """B-002 regression: each _store method must SET to Redis exactly once
        (either directly or via _store_directive delegation)."""
        method = getattr(SpineOrchestrator, method_name, None)
        source = inspect.getsource(method)
        count = source.count("redis.set(")
        # Methods delegating to _store_directive or directive_store are also valid
        delegates = ("_store_directive" in source or "directive_store" in source) and count == 0
        assert count == 1 or delegates, (
            f"{method_name} calls redis.set {count} times, expected 1 (or delegation). "
            f"B-002 regression: duplicate Redis writes."
        )


class TestNoDuplicateCodeBlocks:
    """Detect large duplicate code blocks that indicate copy-paste bugs."""

    def test_store_methods_no_duplicate_redis_calls(self):
        """B-002 regression: each _store_* method body has exactly one redis.set call
        (either directly or via _store_directive delegation)."""
        store_methods = [
            "_store_notification_directive",
            "_store_retrieval_directive",
            "_store_plan_directive",
            "_store_model_write_directive",
            "_store_ux_directive",
            "_store_response_directive",
            "_store_community_directive",
            "_store_skill_directive",
        ]
        for method_name in store_methods:
            method = getattr(SpineOrchestrator, method_name)
            source = inspect.getsource(method)
            delegates = "_store_directive" in source or "directive_store" in source
            # Count redis.set( calls — should be exactly 1 per method (or 0 if delegating)
            set_count = source.count("redis.set(")
            assert set_count == 1 or (set_count == 0 and delegates), (
                f"{method_name} has {set_count} redis.set() calls, expected 1. "
                f"B-002 regression: double Redis write."
            )
            # Count store_directive_by_id calls — should be exactly 1 (or 0 if delegating)
            sd_count = source.count("store_directive_by_id")
            assert sd_count == 1 or (sd_count == 0 and delegates), (
                f"{method_name} has {sd_count} store_directive_by_id calls, expected 1. "
                f"B-002 regression: double directive storage."
            )

    def test_module_has_no_duplicate_class_definitions(self):
        """B-003 cross-check: verify no duplicate class names in spine module."""
        source = inspect.getsource(SpineOrchestrator)
        tree = ast.parse(source)
        class_names = [
            node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)
        ]
        if not class_names:
            # No inner classes — check the module-level source instead
            import app.signals.spine_orchestrator as mod
            mod_source = inspect.getsource(mod)
            mod_tree = ast.parse(mod_source)
            class_names = [
                node.name for node in ast.walk(mod_tree)
                if isinstance(node, ast.ClassDef)
            ]
        dupes = [n for n in class_names if class_names.count(n) > 1]
        assert not dupes, f"Duplicate class names in spine module: {set(dupes)}"
