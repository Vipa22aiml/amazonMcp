from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    """Application configuration with environment variable support"""
    
    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        case_sensitive=False
    )
    
    # Amazon PA API Credentials
    amazon_access_key: str = ""
    amazon_secret_key: str = ""
    amazon_associate_tag: str = ""
    amazon_marketplace: str = "IN"  # IN, US, UK, etc.
    
    # API Configuration
    amazon_host: str = "webservices.amazon.in"
    amazon_region: str = "eu-west-1"
    
    # Rate Limiting (starts at 1 TPS / 8640 TPD)
    max_requests_per_second: float = 0.9  # Conservative 0.9 to avoid throttling
    max_requests_per_day: int = 8000  # Leave buffer
    
    # Caching
    redis_url: Optional[str] = "redis://localhost:6379/0"
    cache_ttl_search: int = 3600  # 1 hour for search results
    cache_ttl_product: int = 7200  # 2 hours for product details
    cache_ttl_browse: int = 86400  # 24 hours for browse nodes
    
    # Circuit Breaker
    circuit_breaker_threshold: int = 5  # Failures before opening
    circuit_breaker_timeout: int = 60  # Seconds before retry
    
    # Mock Mode (for development without API access)
    mock_mode: bool = True
    
    # Monitoring
    enable_metrics: bool = True
    metrics_port: int = 9090
    
    @property
    def is_india_marketplace(self) -> bool:
        return self.amazon_marketplace == "IN"

# Singleton settings instance
settings = Settings()
