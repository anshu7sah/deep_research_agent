import asyncio
import inspect
import json
from typing import Any, Callable

from logging_config import get_logger

logger = get_logger("tool_registry")


class ToolRegistry:

    def __init__(self):
        self._tools: dict[str, Callable] = {}
        self._schemas: list[dict] = []

    def register(self, func: Callable, description: str, parameters: dict) -> None:
        name = func.__name__
        self._tools[name] = func
        self._schemas.append({
            "type": "function",
            "function": {
                "name": name,
                "description": description,
                "parameters": parameters,
            },
        })
        logger.info("tool_registered", name=name)

    def get_openai_tools(self) -> list[dict]:
        return self._schemas

    async def execute(self, name: str, arguments: dict) -> str:
        if name not in self._tools:
            return json.dumps({"error": f"Unknown tool: {name}"})

        func = self._tools[name]
        try:
            if inspect.iscoroutinefunction(func):
                result = await func(**arguments)
            else:
                result = func(**arguments)

            if isinstance(result, str):
                return result
            return json.dumps(result, default=str)
        except Exception as e:
            logger.error("tool_execution_failed", tool=name, error=str(e))
            return json.dumps({"error": str(e)})

    def get_tool_names(self) -> list[str]:
        return list(self._tools.keys())
