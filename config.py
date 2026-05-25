"""Application configuration loaded from environment variables."""

import os
from dataclasses import dataclass, field


@dataclass
class Config:
    """Centralized configuration for the AI PR Reviewer."""

    # GitHub
    github_token: str = field(default_factory=lambda: os.environ.get("GITHUB_TOKEN", ""))
    github_webhook_secret: str = field(
        default_factory=lambda: os.environ.get("GITHUB_WEBHOOK_SECRET", "")
    )

    # LLM
    llm_api_key: str = field(default_factory=lambda: os.environ.get("LLM_API_KEY", ""))
    llm_api_base: str = field(
        default_factory=lambda: os.environ.get(
            "LLM_API_BASE", "https://api.openai.com/v1"
        )
    )
    llm_model: str = field(
        default_factory=lambda: os.environ.get("LLM_MODEL", "gpt-4o")
    )
    llm_max_tokens: int = field(
        default_factory=lambda: int(os.environ.get("LLM_MAX_TOKENS", "4096"))
    )
    llm_temperature: float = field(
        default_factory=lambda: float(os.environ.get("LLM_TEMPERATURE", "0.3"))
    )

    # Server
    host: str = field(default_factory=lambda: os.environ.get("HOST", "0.0.0.0"))
    port: int = field(default_factory=lambda: int(os.environ.get("PORT", "8000")))

    def validate(self) -> list[str]:
        """Check that required configuration values are set.

        Returns:
            A list of missing configuration keys (empty if all good).
        """
        missing: list[str] = []
        if not self.github_token:
            missing.append("GITHUB_TOKEN")
        if not self.llm_api_key:
            missing.append("LLM_API_KEY")
        return missing
