from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="DR_")

    openai_api_key: str = ""
    default_model: str = "gpt-4o-mini"
    writing_model: str = "gpt-4o"
    orchestrator_model: str = "gpt-4o"

    max_searches: int = 5
    max_results_per_search: int = 5
    max_scrape_urls: int = 10
    search_rate_limit_delay: float = 1.0
    scrape_concurrency: int = 5

    max_follow_up_questions: int = 3

    max_revisions: int = 2
    min_report_words: int = 1000
    revision_threshold: float = 7.0

    max_tokens_per_session: int = 100_000

    hallucination_check_enabled: bool = False

    email_enabled: bool = False
    email_address: str = ""
    email_smtp_server: str = ""
    email_app_password: str = ""

    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    log_level: str = "INFO"
