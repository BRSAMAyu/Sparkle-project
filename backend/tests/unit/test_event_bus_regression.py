"""
B-003 Regression Tests: Event Bus Duplicate Class Definitions

Bug: event_bus.py had DocumentCitationFeedbackEvent defined twice (lines 795 and 1584)
with different fields — the second definition silently shadowed the first.

This test uses AST parsing to ensure all class names are unique within the module.
"""

import ast
import importlib

import pytest

import app.core.event_bus as event_bus_module


class TestNoDuplicateClassNames:
    """Ensure event_bus.py has no duplicate class definitions."""

    def test_no_duplicate_event_class_names(self):
        """B-003 regression: all class names in event_bus.py must be unique."""
        source = event_bus_module.__file__
        assert source is not None, "Cannot locate event_bus.py source"

        with open(source) as f:
            tree = ast.parse(f.read())

        class_names = [
            node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)
        ]
        seen: dict[str, int] = {}
        for name in class_names:
            seen[name] = seen.get(name, 0) + 1

        dupes = {name: count for name, count in seen.items() if count > 1}
        assert not dupes, (
            f"B-003 regression: duplicate class definitions found: {dupes}. "
            f"Each class must be defined exactly once."
        )

    def test_document_citation_feedback_event_unique(self):
        """B-003 specific: DocumentCitationFeedbackEvent must appear exactly once."""
        source = event_bus_module.__file__
        with open(source) as f:
            tree = ast.parse(f.read())

        class_names = [
            node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)
        ]
        count = class_names.count("DocumentCitationFeedbackEvent")
        assert count == 1, (
            f"DocumentCitationFeedbackEvent defined {count} times, expected 1. "
            f"B-003 regression."
        )

    def test_all_event_classes_importable(self):
        """Verify all event classes defined in the module are importable without error."""
        source = event_bus_module.__file__
        with open(source) as f:
            tree = ast.parse(f.read())

        class_names = [
            node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)
        ]
        for name in class_names:
            assert hasattr(event_bus_module, name), (
                f"Class {name} defined in source but not importable from module"
            )
