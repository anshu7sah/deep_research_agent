import json
from unittest.mock import AsyncMock, patch

import pytest

from tools.search_tool import RateLimiter, SearchTool
from tools.tool_registry import ToolRegistry


@pytest.mark.asyncio
async def test_search_tool_returns_results():
    mock_results = [
        {"title": "Result 1", "href": "https://example.com/1", "body": "Snippet 1"},
        {"title": "Result 2", "href": "https://example.com/2", "body": "Snippet 2"},
    ]

    with patch("tools.search_tool.DDGS") as mock_ddgs:
        mock_ddgs.return_value.text.return_value = mock_results
        tool = SearchTool(rate_limit_delay=0.0)
        results = await tool.search("test query", max_results=2)

    assert len(results) == 2
    assert results[0].title == "Result 1"
    assert results[0].url == "https://example.com/1"
    assert results[1].position == 2


@pytest.mark.asyncio
async def test_search_tool_handles_error():
    with patch("tools.search_tool.DDGS") as mock_ddgs:
        mock_ddgs.return_value.text.side_effect = Exception("Rate limited")
        tool = SearchTool(rate_limit_delay=0.0)
        results = await tool.search("test query")

    assert results == []


def test_tool_registry_register_and_list():
    registry = ToolRegistry()

    def my_tool(arg: str) -> str:
        return f"result: {arg}"

    registry.register(
        my_tool,
        "A test tool",
        {"type": "object", "properties": {"arg": {"type": "string"}}, "required": ["arg"]},
    )

    assert "my_tool" in registry.get_tool_names()
    schemas = registry.get_openai_tools()
    assert len(schemas) == 1
    assert schemas[0]["function"]["name"] == "my_tool"


@pytest.mark.asyncio
async def test_tool_registry_execute():
    registry = ToolRegistry()

    def add(a: int, b: int) -> str:
        return json.dumps({"sum": a + b})

    registry.register(
        add,
        "Add two numbers",
        {
            "type": "object",
            "properties": {"a": {"type": "integer"}, "b": {"type": "integer"}},
            "required": ["a", "b"],
        },
    )

    result = await registry.execute("add", {"a": 3, "b": 4})
    assert json.loads(result)["sum"] == 7


@pytest.mark.asyncio
async def test_tool_registry_unknown_tool():
    registry = ToolRegistry()
    result = await registry.execute("nonexistent", {})
    parsed = json.loads(result)
    assert "error" in parsed


@pytest.mark.asyncio
async def test_rate_limiter():
    limiter = RateLimiter(min_delay=0.01)
    await limiter.acquire()
    await limiter.acquire()
    # Just verifying it doesn't deadlock or error
