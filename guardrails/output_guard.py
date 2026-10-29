import re

from config import Settings
from logging_config import get_logger
from models.common import ValidationResult

logger = get_logger("output_guard")


class OutputGuard:

    def __init__(self, settings: Settings):
        self.settings = settings

    def validate(
        self, markdown: str, scraped_urls: list[str]
    ) -> ValidationResult:
        violations = []

        citation_issues = self._check_citations(markdown, scraped_urls)
        violations.extend(citation_issues)

        quality_issues = self._check_quality(markdown)
        violations.extend(quality_issues)

        severity = "warning" if violations else "info"
        return ValidationResult(
            is_valid=True,
            violations=violations,
            severity=severity,
        )

    def _check_citations(self, markdown: str, scraped_urls: list[str]) -> list[str]:
        issues = []

        cited_urls = re.findall(r'\[([^\]]*)\]\((https?://[^)]+)\)', markdown)
        cited_url_set = {url for _, url in cited_urls}

        unverified = cited_url_set - set(scraped_urls)
        if unverified:
            issues.append(
                f"{len(unverified)} cited URL(s) were not in scraped sources: "
                f"{', '.join(list(unverified)[:3])}"
            )

        if len(cited_url_set) < 3:
            issues.append(
                f"Only {len(cited_url_set)} unique sources cited (minimum 3 recommended)"
            )

        return issues

    def _check_quality(self, markdown: str) -> list[str]:
        issues = []

        word_count = len(markdown.split())
        if word_count < self.settings.min_report_words:
            issues.append(
                f"Report is {word_count} words (minimum {self.settings.min_report_words})"
            )

        headings = re.findall(r'^#{1,3}\s+', markdown, re.MULTILINE)
        if len(headings) < 2:
            issues.append("Report has fewer than 2 section headings")

        return issues
