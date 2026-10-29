import asyncio
import json
import random
import time

import openai
from pydantic import BaseModel

from config import Settings
from logging_config import get_logger
from models.common import TokenUsage

logger = get_logger("llm_client")


class MaxRetriesExceededError(Exception):
    pass


class LLMClient:

    def __init__(self, settings: Settings):
        self.settings = settings
        self.client = openai.AsyncOpenAI(api_key=settings.openai_api_key)
        self._total_usage = TokenUsage()

    @property
    def total_usage(self) -> TokenUsage:
        return self._total_usage

    async def complete(
        self,
        messages: list[dict],
        model: str | None = None,
        tools: list[dict] | None = None,
        temperature: float = 0.7,
    ) -> dict:
        model = model or self.settings.default_model

        kwargs: dict = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
        }
        if tools:
            kwargs["tools"] = tools

        start = time.time()
        response = await self._call_with_retry(
            lambda: self.client.chat.completions.create(**kwargs)
        )
        duration = time.time() - start

        usage = self._extract_usage(response)
        self._accumulate_usage(usage)

        message = response.choices[0].message

        tool_calls = None
        if message.tool_calls:
            tool_calls = [
                {
                    "id": tc.id,
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in message.tool_calls
            ]

        logger.info(
            "llm_call",
            model=model,
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            duration=round(duration, 2),
            has_tool_calls=tool_calls is not None,
        )

        return {
            "content": message.content,
            "tool_calls": tool_calls,
            "usage": usage,
            "model": model,
            "duration_seconds": duration,
        }

    async def complete_structured(
        self,
        messages: list[dict],
        response_model: type[BaseModel],
        model: str | None = None,
        temperature: float = 0.7,
    ) -> BaseModel:
        model = model or self.settings.default_model

        start = time.time()
        response = await self._call_with_retry(
            lambda: self.client.beta.chat.completions.parse(
                model=model,
                messages=messages,
                response_format=response_model,
                temperature=temperature,
            )
        )
        duration = time.time() - start

        usage = self._extract_usage(response)
        self._accumulate_usage(usage)

        parsed = response.choices[0].message.parsed

        logger.info(
            "llm_structured_call",
            model=model,
            output_type=response_model.__name__,
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            duration=round(duration, 2),
        )

        return parsed

    async def _call_with_retry(self, func, max_retries: int = 3, base_delay: float = 1.0):
        for attempt in range(max_retries):
            try:
                return await func()
            except openai.RateLimitError:
                delay = base_delay * (2 ** attempt) + random.uniform(0, 0.5)
                logger.warning("rate_limited", attempt=attempt, delay=round(delay, 2))
                await asyncio.sleep(delay)
            except openai.APIConnectionError:
                delay = base_delay * (2 ** attempt)
                logger.warning("connection_error", attempt=attempt, delay=round(delay, 2))
                await asyncio.sleep(delay)
            except openai.APIStatusError as e:
                if e.status_code >= 500:
                    delay = base_delay * (2 ** attempt)
                    logger.warning("server_error", status=e.status_code, attempt=attempt)
                    await asyncio.sleep(delay)
                else:
                    raise
        raise MaxRetriesExceededError(f"Failed after {max_retries} attempts")

    def _extract_usage(self, response) -> TokenUsage:
        if response.usage:
            return TokenUsage(
                input_tokens=response.usage.prompt_tokens,
                output_tokens=response.usage.completion_tokens,
            )
        return TokenUsage()

    def _accumulate_usage(self, usage: TokenUsage) -> None:
        self._total_usage.input_tokens += usage.input_tokens
        self._total_usage.output_tokens += usage.output_tokens
