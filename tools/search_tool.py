import asyncio
import time

from duckduckgo_search import DDGS

from logging_config import get_logger
from models.search import SearchResult

logger = get_logger("search_tool")


class RateLimiter:

    def __init__(self, min_delay: float = 1.0):
        self._min_delay = min_delay
        self._last_request: float = 0.0
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_request
            if elapsed < self._min_delay:
                await asyncio.sleep(self._min_delay - elapsed)
            self._last_request = time.monotonic()


class SearchTool:

    def __init__(self, rate_limit_delay: float = 1.0):
        self._rate_limiter = RateLimiter(min_delay=rate_limit_delay)

    async def search(self, query: str, max_results: int = 5) -> list[SearchResult]:
        await self._rate_limiter.acquire()

        loop = asyncio.get_event_loop()
        try:
            raw_results = await loop.run_in_executor(
                None, lambda: list(DDGS().text(query, max_results=max_results))
            )
        except Exception as e:
            logger.error("search_failed", query=query, error=str(e))
            return []

        results = [
            SearchResult(
                query=query,
                title=r.get("title", ""),
                url=r.get("href", ""),
                snippet=r.get("body", ""),
                position=i + 1,
            )
            for i, r in enumerate(raw_results)
        ]

        logger.info("search_complete", query=query, num_results=len(results))
        return results
