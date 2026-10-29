import asyncio
import re

import trafilatura

from logging_config import get_logger
from models.search import ScrapedContent

logger = get_logger("scrape_tool")


class ScrapeTool:

    async def scrape(self, url: str) -> ScrapedContent:
        try:
            content = await self._scrape_with_trafilatura(url)
            if content and content.success:
                return content
        except Exception as e:
            logger.warning("trafilatura_failed", url=url, error=str(e))

        try:
            return await self._scrape_with_crawl4ai(url)
        except Exception:
            pass

        return ScrapedContent(
            url=url,
            title="",
            content="",
            word_count=0,
            scrape_method="failed",
            success=False,
            error="All scraping methods failed",
        )

    async def _scrape_with_trafilatura(self, url: str) -> ScrapedContent | None:
        downloaded = await asyncio.to_thread(trafilatura.fetch_url, url)
        if not downloaded:
            return None

        text = trafilatura.extract(downloaded, include_links=True, include_tables=True)
        if not text or len(text) < 100:
            return None

        title = self._extract_title(downloaded)
        word_count = len(text.split())

        logger.info("scraped", url=url, method="trafilatura", words=word_count)

        return ScrapedContent(
            url=url,
            title=title,
            content=text,
            word_count=word_count,
            scrape_method="trafilatura",
            success=True,
        )

    async def _scrape_with_crawl4ai(self, url: str) -> ScrapedContent:
        try:
            from crawl4ai import AsyncWebCrawler

            async with AsyncWebCrawler() as crawler:
                result = await crawler.arun(url=url)
                text = result.markdown or ""
                if len(text) < 100:
                    raise ValueError("Content too short")

                logger.info("scraped", url=url, method="crawl4ai", words=len(text.split()))

                return ScrapedContent(
                    url=url,
                    title=result.metadata.get("title", "") if result.metadata else "",
                    content=text,
                    word_count=len(text.split()),
                    scrape_method="crawl4ai",
                    success=True,
                )
        except ImportError:
            logger.warning("crawl4ai_not_installed")
            raise
        except Exception as e:
            logger.error("crawl4ai_failed", url=url, error=str(e))
            return ScrapedContent(
                url=url,
                title="",
                content="",
                word_count=0,
                scrape_method="crawl4ai",
                success=False,
                error=str(e),
            )

    def _extract_title(self, html: str) -> str:
        match = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
        return match.group(1).strip() if match else ""
