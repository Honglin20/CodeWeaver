"""Configuration management for CodeWeaver."""
import os
from pathlib import Path
from typing import Optional
from dataclasses import dataclass


@dataclass
class Config:
    """CodeWeaver configuration."""

    # Memory settings
    MAX_MEMORY_ENTRIES: int = int(os.getenv('CODEWEAVER_MAX_MEMORY', '1000'))
    MEMORY_CACHE_SIZE: int = int(os.getenv('CODEWEAVER_CACHE_SIZE', '100'))

    # LLM settings
    DEFAULT_MODEL: str = os.getenv('CODEWEAVER_MODEL', 'deepseek-chat')
    DEFAULT_MAX_TOKENS: int = int(os.getenv('CODEWEAVER_MAX_TOKENS', '2000'))
    DEFAULT_TEMPERATURE: float = float(os.getenv('CODEWEAVER_TEMPERATURE', '0.7'))

    # API settings
    API_KEY: Optional[str] = os.getenv('CODEWEAVER_API_KEY')
    API_BASE: Optional[str] = os.getenv('CODEWEAVER_API_BASE')
    API_TIMEOUT: int = int(os.getenv('CODEWEAVER_API_TIMEOUT', '60'))

    # Performance settings
    CACHE_ENABLED: bool = os.getenv('CODEWEAVER_CACHE', 'true').lower() == 'true'
    LAZY_LOADING: bool = os.getenv('CODEWEAVER_LAZY_LOAD', 'true').lower() == 'true'

    # Logging settings
    LOG_LEVEL: str = os.getenv('CODEWEAVER_LOG_LEVEL', 'INFO')
    LOG_FILE: Optional[Path] = Path(os.getenv('CODEWEAVER_LOG_FILE')) if os.getenv('CODEWEAVER_LOG_FILE') else None

    # Validation settings
    STRICT_VALIDATION: bool = os.getenv('CODEWEAVER_STRICT', 'false').lower() == 'true'
    VALIDATE_ON_LOAD: bool = os.getenv('CODEWEAVER_VALIDATE_ON_LOAD', 'true').lower() == 'true'

    @classmethod
    def from_file(cls, config_file: Path) -> 'Config':
        """Load configuration from file.

        Args:
            config_file: Path to configuration file (YAML or JSON)

        Returns:
            Config instance
        """
        # TODO: Implement file-based configuration
        return cls()

    def to_dict(self) -> dict:
        """Convert configuration to dictionary."""
        return {
            'MAX_MEMORY_ENTRIES': self.MAX_MEMORY_ENTRIES,
            'MEMORY_CACHE_SIZE': self.MEMORY_CACHE_SIZE,
            'DEFAULT_MODEL': self.DEFAULT_MODEL,
            'DEFAULT_MAX_TOKENS': self.DEFAULT_MAX_TOKENS,
            'DEFAULT_TEMPERATURE': self.DEFAULT_TEMPERATURE,
            'API_TIMEOUT': self.API_TIMEOUT,
            'CACHE_ENABLED': self.CACHE_ENABLED,
            'LAZY_LOADING': self.LAZY_LOADING,
            'LOG_LEVEL': self.LOG_LEVEL,
            'STRICT_VALIDATION': self.STRICT_VALIDATION,
            'VALIDATE_ON_LOAD': self.VALIDATE_ON_LOAD,
        }


# Global configuration instance
config = Config()
