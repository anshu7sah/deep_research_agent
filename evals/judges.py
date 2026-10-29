import json

from services.llm_client import LLMClient


async def judge_search_relevance(
    llm: LLMClient, query: str, results: list[dict]
) -> float:
    results_text = "\n".join(
        f"- {r.get('title', '')}: {r.get('snippet', '')}" for r in results[:10]
    )

    messages = [
        {
            "role": "system",
            "content": (
                "You are a search relevance judge. Rate how relevant the search results "
                "are to the query on a scale of 0-10. Return ONLY a JSON object: "
                '{"score": <number>, "reasoning": "<string>"}'
            ),
        },
        {
            "role": "user",
            "content": f"Query: {query}\n\nSearch results:\n{results_text}",
        },
    ]

    response = await llm.complete(messages=messages, temperature=0.0)
    try:
        parsed = json.loads(response["content"])
        return min(10.0, max(0.0, float(parsed["score"]))) / 10.0
    except (json.JSONDecodeError, KeyError, TypeError):
        return 0.5


async def judge_topic_coverage(
    llm: LLMClient, report_markdown: str, expected_topics: list[str]
) -> list[dict]:
    topics_str = ", ".join(expected_topics)

    messages = [
        {
            "role": "system",
            "content": (
                "You are a topic coverage judge. For each expected topic, determine if "
                "the report adequately covers it. Return ONLY a JSON object: "
                '{"coverage": [{"topic": "...", "covered": true/false, "evidence": "..."}]}'
            ),
        },
        {
            "role": "user",
            "content": (
                f"Expected topics: {topics_str}\n\nReport:\n{report_markdown[:5000]}"
            ),
        },
    ]

    response = await llm.complete(messages=messages, temperature=0.0)
    try:
        parsed = json.loads(response["content"])
        return parsed.get("coverage", [])
    except (json.JSONDecodeError, KeyError):
        return [{"topic": t, "covered": False, "evidence": ""} for t in expected_topics]
