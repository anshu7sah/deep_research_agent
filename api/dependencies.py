from functools import lru_cache

from api.session_store import SessionStore
from config import Settings
from services.llm_client import LLMClient

_store = SessionStore()


@lru_cache
def get_settings() -> Settings:
    return Settings()


def get_llm_client() -> LLMClient:
    return LLMClient(get_settings())


def get_store() -> SessionStore:
    return _store
