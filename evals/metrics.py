import re


def scrape_success_rate(successful: int, attempted: int) -> float:
    if attempted == 0:
        return 0.0
    return successful / attempted


def report_quality_score(critique_scores: dict) -> float:
    scores = [
        critique_scores.get("accuracy_score", 0),
        critique_scores.get("completeness_score", 0),
        critique_scores.get("structure_score", 0),
        critique_scores.get("clarity_score", 0),
        critique_scores.get("citation_score", 0),
    ]
    return (sum(scores) / len(scores)) / 10.0


def citation_accuracy(markdown: str, scraped_urls: list[str]) -> float:
    cited = set(re.findall(r'\[([^\]]*)\]\((https?://[^)]+)\)', markdown))
    cited_urls = {url for _, url in cited}
    if not cited_urls:
        return 0.0
    verified = cited_urls & set(scraped_urls)
    return len(verified) / len(cited_urls)


def token_efficiency(tokens_used: int, max_budget: int) -> float:
    if max_budget == 0:
        return 0.0
    return max(0.0, 1.0 - (tokens_used / max_budget))


def topic_coverage_from_judgement(coverage_results: list[dict]) -> float:
    if not coverage_results:
        return 0.0
    covered = sum(1 for c in coverage_results if c.get("covered", False))
    return covered / len(coverage_results)
