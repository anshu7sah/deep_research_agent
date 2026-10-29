from orchestration.code_orchestrator import CodeOrchestrator
from orchestration.llm_orchestrator import LLMOrchestrator


def get_orchestrator(mode: str, **kwargs):
    if mode == "code":
        return CodeOrchestrator(**kwargs)
    elif mode == "llm":
        return LLMOrchestrator(**kwargs)
    raise ValueError(f"Unknown orchestration mode: {mode}")
