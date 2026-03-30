"""
Concurrency tests for DynamicToolRegistry.

Tests thread-safety of concurrent tool registration and access.
"""
from __future__ import annotations

import asyncio
from unittest.mock import MagicMock

import pytest

from app.orchestration.dynamic_tool_registry import DynamicToolRegistry
from app.tools.base import BaseTool, ToolCategory


# Create a test tool class
class MockTool(BaseTool):
    """Mock tool for testing."""
    def __init__(self, name: str):
        self._name = name
        self._description = f"Test tool {name}"
        self._category = ToolCategory.TASK
        self._parameters_schema = {}

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    @property
    def category(self) -> ToolCategory:
        return self._category

    @property
    def parameters_schema(self) -> dict:
        return self._parameters_schema

    async def execute(self, **kwargs):
        return {"result": f"Executed {self._name}"}


@pytest.fixture
def clean_registry():
    """Create a fresh registry for testing."""
    registry = DynamicToolRegistry()
    registry.clear_all()
    return registry


@pytest.mark.asyncio
async def test_concurrent_tool_registration_is_safe(clean_registry):
    """Test that concurrent tool registration is thread-safe."""
    tools = [MockTool(f"tool_{i}") for i in range(10)]

    # Register tools concurrently
    async def register_tool(tool):
        clean_registry.register_tool(tool)

    tasks = [register_tool(tool) for tool in tools]
    await asyncio.gather(*tasks)

    # All tools should be registered
    assert len(clean_registry._tools) == 10
    for i in range(10):
        assert f"tool_{i}" in clean_registry._tools


@pytest.mark.asyncio
async def test_register_duplicate_tool_is_idempotent(clean_registry):
    """Test that registering the same tool twice is idempotent."""
    tool = MockTool("test_tool")

    # Register same tool twice
    clean_registry.register_tool(tool)
    clean_registry.register_tool(tool)

    # Should only have one entry
    assert len(clean_registry._tools) == 1
    assert "test_tool" in clean_registry._tools


@pytest.mark.asyncio
async def test_get_tool_returns_correct_tool(clean_registry):
    """Test that get_tool returns the correct tool by name."""
    tool1 = MockTool("tool_a")
    tool2 = MockTool("tool_b")

    clean_registry.register_tool(tool1)
    clean_registry.register_tool(tool2)

    # Get specific tools
    retrieved_a = clean_registry.get_tool("tool_a")
    retrieved_b = clean_registry.get_tool("tool_b")

    assert retrieved_a.name == "tool_a"
    assert retrieved_b.name == "tool_b"


@pytest.mark.asyncio
async def test_get_nonexistent_tool_returns_none(clean_registry):
    """Test that get_tool returns None for non-existent tool."""
    result = clean_registry.get_tool("nonexistent_tool")

    assert result is None


@pytest.mark.asyncio
async def test_get_all_tools_returns_all_tools(clean_registry):
    """Test that get_all_tools returns all registered tools."""
    tools = [MockTool(f"tool_{i}") for i in range(3)]

    for tool in tools:
        clean_registry.register_tool(tool)

    all_tools = clean_registry.get_all_tools()

    assert len(all_tools) == 3
    tool_names = {t.name for t in all_tools}
    for i in range(3):
        assert f"tool_{i}" in tool_names


@pytest.mark.asyncio
async def test_concurrent_register_and_get_tool(clean_registry):
    """Test concurrent registration and retrieval of specific tools."""
    tools = [MockTool(f"tool_{i}") for i in range(5)]

    results = []

    async def register_or_get(index):
        if index % 2 == 0:
            # Register tool
            clean_registry.register_tool(tools[index])
        else:
            # Try to get tool (may not exist yet)
            tool = clean_registry.get_tool(f"tool_{index}")
            results.append(tool)

    tasks = [register_or_get(i) for i in range(5)]
    await asyncio.gather(*tasks)

    # Should complete without errors
    assert len(clean_registry._tools) >= 2  # At least the even-indexed ones


@pytest.mark.asyncio
async def test_tool_registry_handles_high_concurrency(clean_registry):
    """Test that tool registry handles high concurrency without errors."""
    # Create many tools
    tools = [MockTool(f"tool_{i}") for i in range(100)]

    # Register all concurrently
    async def register_tool(tool):
        clean_registry.register_tool(tool)
        # Also try to get it immediately
        return clean_registry.get_tool(tool.name)

    tasks = [register_tool(tool) for tool in tools]
    results = await asyncio.gather(*tasks)

    # All tools should be accessible
    assert len(results) == 100
    for tool in results:
        assert tool is not None
        assert tool.name.startswith("tool_")

    # Registry should have all tools
    assert len(clean_registry._tools) == 100


@pytest.mark.asyncio
async def test_unregister_tool(clean_registry):
    """Test that unregister_tool removes tool from registry."""
    tool = MockTool("test_tool")
    clean_registry.register_tool(tool)

    assert "test_tool" in clean_registry._tools

    result = clean_registry.unregister_tool("test_tool")

    assert result is True
    assert "test_tool" not in clean_registry._tools


@pytest.mark.asyncio
async def test_unregister_nonexistent_tool(clean_registry):
    """Test that unregister_tool returns False for non-existent tool."""
    result = clean_registry.unregister_tool("nonexistent_tool")

    assert result is False


@pytest.mark.asyncio
async def test_get_tools_by_category(clean_registry):
    """Test that get_tools_by_category filters correctly."""
    # Create tools with different categories
    task_tool = MockTool("task_tool")
    knowledge_tool = MockTool("knowledge_tool")

    # Modify categories
    task_tool._category = ToolCategory.TASK
    knowledge_tool._category = ToolCategory.KNOWLEDGE

    clean_registry.register_tool(task_tool)
    clean_registry.register_tool(knowledge_tool)

    task_tools = clean_registry.get_tools_by_category(ToolCategory.TASK)
    knowledge_tools = clean_registry.get_tools_by_category(ToolCategory.KNOWLEDGE)

    assert len(task_tools) == 1
    assert task_tools[0].name == "task_tool"
    assert len(knowledge_tools) == 1
    assert knowledge_tools[0].name == "knowledge_tool"


@pytest.mark.asyncio
async def test_clear_all_removes_all_tools(clean_registry):
    """Test that clear_all removes all tools."""
    tools = [MockTool(f"tool_{i}") for i in range(5)]

    for tool in tools:
        clean_registry.register_tool(tool)

    assert len(clean_registry._tools) == 5

    clean_registry.clear_all()

    assert len(clean_registry._tools) == 0


@pytest.mark.asyncio
async def test_get_stats_returns_correct_info(clean_registry):
    """Test that get_stats returns registry statistics."""
    tools = [MockTool(f"tool_{i}") for i in range(5)]

    for tool in tools:
        clean_registry.register_tool(tool)

    stats = clean_registry.get_stats()

    assert stats["total_tools"] == 5
    assert len(stats["tools"]) == 5
    assert "task" in stats["categories"]


@pytest.mark.asyncio
async def test_list_tools_returns_tool_info(clean_registry):
    """Test that list_tools returns tool information."""
    tool = MockTool("test_tool")
    clean_registry.register_tool(tool)

    tools_info = clean_registry.list_tools(verbose=True)

    assert len(tools_info) == 1
    assert tools_info[0]["name"] == "test_tool"
    assert "description" in tools_info[0]
