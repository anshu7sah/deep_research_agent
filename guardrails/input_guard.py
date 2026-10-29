import re

from config import Settings
from logging_config import get_logger
from models.common import ValidationResult
from services.llm_client import LLMClient

logger = get_logger("input_guard")

INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?previous\s+instructions",
    r"ignore\s+(all\s+)?prior",
    r"disregard\s+(your|all|previous)",
    r"you\s+are\s+now",
    r"new\s+instructions?:",
    r"system\s*prompt",
    r"<\s*system\s*>",
    r"\[INST\]",
    r"<<\s*SYS\s*>>",
    r"override\s+(your|all|the)",
]

UNSAFE_PATTERNS = [
    r"how\s+to\s+(make|build|create)\s+(a\s+)?(bomb|explosive|weapon)",
    r"synthesize?\s+(meth|cocaine|heroin|fentanyl)",
    r"hack\s+into\s+(someone|their|a\s+person)",
]


class InputGuard:

    def __init__(self, settings: Settings, llm_client: LLMClient | None = None):
        self.settings = settings
        self.llm = llm_client

    async def validate(self, query: str) -> ValidationResult:
        length_check = self._check_length(query)
        if not length_check.is_valid:
            return length_check

        injection_check = self._check_injection(query)
        if not injection_check.is_valid:
            return injection_check

        safety_check = self._check_safety(query)
        if not safety_check.is_valid:
            return safety_check

        return ValidationResult(is_valid=True)

    def _check_length(self, query: str) -> ValidationResult:
        query = query.strip()
        if len(query) < 5:
            return ValidationResult(
                is_valid=False,
                violations=["Query is too short (minimum 5 characters)"],
                severity="error",
            )
        if len(query) > 2000:
            return ValidationResult(
                is_valid=False,
                violations=["Query is too long (maximum 2000 characters)"],
                severity="error",
            )
        return ValidationResult(is_valid=True)

    def _check_injection(self, query: str) -> ValidationResult:
        lower_query = query.lower()
        for pattern in INJECTION_PATTERNS:
            if re.search(pattern, lower_query):
                logger.warning("injection_detected", pattern=pattern)
                return ValidationResult(
                    is_valid=False,
                    violations=["Query contains potentially malicious instructions"],
                    severity="error",
                )
        return ValidationResult(is_valid=True)

    def _check_safety(self, query: str) -> ValidationResult:
        lower_query = query.lower()
        for pattern in UNSAFE_PATTERNS:
            if re.search(pattern, lower_query):
                logger.warning("unsafe_query_detected", pattern=pattern)
                return ValidationResult(
                    is_valid=False,
                    violations=["Query requests potentially harmful information"],
                    severity="error",
                )
        return ValidationResult(is_valid=True)
