"""
config.py — Configuration and API key management.

Reads optional settings from environment variables or a .env file.
All settings have safe defaults so the tool works without any configuration.
"""

import os


class Config:
    """Central configuration object."""

    # OpenAI API key — optional, only needed for LLM-assisted extraction
    OPENAI_API_KEY: str = os.environ.get("OPENAI_API_KEY", "")

    # Model to use for LLM extraction
    OPENAI_MODEL: str = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

    # Default matching tolerance (dollars)
    DEFAULT_TOLERANCE: float = float(os.environ.get("MATCH_TOLERANCE", "0.01"))

    # Minimum fuzzy match score (0-100) to consider a name match valid
    FUZZY_THRESHOLD: int = int(os.environ.get("FUZZY_THRESHOLD", "70"))

    # Maximum number of invoices for brute-force subset-sum (above this, use DP)
    BRUTE_FORCE_LIMIT: int = int(os.environ.get("BRUTE_FORCE_LIMIT", "20"))

    @classmethod
    def has_openai_key(cls) -> bool:
        """Return True if an OpenAI API key is configured."""
        return bool(cls.OPENAI_API_KEY)


# Module-level singleton
config = Config()
