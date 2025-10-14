Production-Grade Amazon MCP Server Blueprint (Official PA API SDK)
Based on the best practices you've outlined and the official Amazon PA API Python SDK, here's the complete production architecture :





Tech Stack Selection
Official Amazon SDK: paapi5-python-sdk (Amazon's official Python SDK for PA API 5.0)
MCP Framework: FastMCP for rapid Python MCP development
Caching: Redis for distributed caching + in-memory fallback
Async Processing: asyncio for concurrent request handling
Monitoring: Prometheus metrics for production observability


amazon-paapi-mcp/
├── server.py                      # Main FastMCP server entrypoint
├── config/
│   ├── __init__.py
│   ├── settings.py                # Environment configuration
│   └── marketplace.py             # Marketplace-specific configs
├── core/
│   ├── __init__.py
│   ├── paapi_client.py           # Official SDK wrapper with connection pooling
│   ├── cache_manager.py          # Multi-level caching (Redis + memory)
│   ├── rate_limiter.py           # Request rate limiting & throttling
│   └── circuit_breaker.py        # Fault tolerance for API failures
├── services/
│   ├── __init__.py
│   ├── search_service.py         # SearchItems operations
│   ├── product_service.py        # GetItems operations
│   ├── browse_service.py         # GetBrowseNodes operations
│   └── variation_service.py      # GetVariations operations
├── intelligence/
│   ├── __init__.py
│   ├── scoring.py                # Product scoring algorithms
│   ├── recommendation.py         # Intelligent recommendations
│   └── analysis.py               # Review & pricing analysis
├── tools/
│   ├── __init__.py
│   ├── basic_tools.py            # Search, details, compare
│   └── advanced_tools.py         # Best-in-category, alternatives
├── models/
│   ├── __init__.py
│   ├── product.py                # Product data models
│   └── responses.py              # API response schemas
├── utils/
│   ├── __init__.py
│   ├── formatters.py             # Response formatting
│   ├── validators.py             # Input validation
│   └── metrics.py                # Prometheus metrics
├── tests/
│   ├── test_paapi_client.py
│   ├── test_services.py
│   └── test_tools.py
├── requirements.txt
├── docker-compose.yml            # Redis + app
├── Dockerfile
└── README.md

## Production-Grade Amazon MCP Server Blueprint (Official PA API SDK)

Based on the best practices you've outlined and the official Amazon PA API Python SDK, here's the complete production architecture :[1][2][3]

### Tech Stack Selection

**Official Amazon SDK**: `paapi5-python-sdk` (Amazon's official Python SDK for PA API 5.0)[3][1]
**MCP Framework**: FastMCP for rapid Python MCP development[4][5]
**Caching**: Redis for distributed caching + in-memory fallback[6]
**Async Processing**: asyncio for concurrent request handling[7]
**Monitoring**: Prometheus metrics for production observability[6]

### Complete Project Structure

```
amazon-paapi-mcp/
├── server.py                      # Main FastMCP server entrypoint
├── config/
│   ├── __init__.py
│   ├── settings.py                # Environment configuration
│   └── marketplace.py             # Marketplace-specific configs
├── core/
│   ├── __init__.py
│   ├── paapi_client.py           # Official SDK wrapper with connection pooling
│   ├── cache_manager.py          # Multi-level caching (Redis + memory)
│   ├── rate_limiter.py           # Request rate limiting & throttling
│   └── circuit_breaker.py        # Fault tolerance for API failures
├── services/
│   ├── __init__.py
│   ├── search_service.py         # SearchItems operations
│   ├── product_service.py        # GetItems operations
│   ├── browse_service.py         # GetBrowseNodes operations
│   └── variation_service.py      # GetVariations operations
├── intelligence/
│   ├── __init__.py
│   ├── scoring.py                # Product scoring algorithms
│   ├── recommendation.py         # Intelligent recommendations
│   └── analysis.py               # Review & pricing analysis
├── tools/
│   ├── __init__.py
│   ├── basic_tools.py            # Search, details, compare
│   └── advanced_tools.py         # Best-in-category, alternatives
├── models/
│   ├── __init__.py
│   ├── product.py                # Product data models
│   └── responses.py              # API response schemas
├── utils/
│   ├── __init__.py
│   ├── formatters.py             # Response formatting
│   ├── validators.py             # Input validation
│   └── metrics.py                # Prometheus metrics
├── tests/
│   ├── test_paapi_client.py
│   ├── test_services.py
│   └── test_tools.py
├── requirements.txt
├── docker-compose.yml            # Redis + app
├── Dockerfile
└── README.md
```

### Step 1: Install Dependencies

**requirements.txt**:
```txt
# Official Amazon PA API SDK
paapi5-python-sdk>=1.0.0

# MCP Framework
fastmcp>=2.0.0

# Async & HTTP
aiohttp>=3.9.0
httpx>=0.25.0

# Caching
redis>=5.0.0
cachetools>=5.3.0

# Rate Limiting
ratelimit>=2.2.1

# Monitoring
prometheus-client>=0.19.0

# Configuration
python-dotenv>=1.0.0
pydantic>=2.5.0
pydantic-settings>=2.1.0

# Testing
pytest>=7.4.0
pytest-asyncio>=0.21.0
pytest-mock>=3.12.0
```

Install:
```bash
pip install -r requirements.txt
```

### Step 2: Configuration Layer

**config/settings.py**:
```python
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
```

**config/marketplace.py**:
```python
"""Marketplace-specific configurations"""

MARKETPLACE_CONFIG = {
    "US": {
        "host": "webservices.amazon.com",
        "region": "us-east-1",
        "currency": "USD",
        "url_domain": "amazon.com"
    },
    "IN": {
        "host": "webservices.amazon.in",
        "region": "eu-west-1",
        "currency": "INR",
        "url_domain": "amazon.in"
    },
    "UK": {
        "host": "webservices.amazon.co.uk",
        "region": "eu-west-1",
        "currency": "GBP",
        "url_domain": "amazon.co.uk"
    },
    "JP": {
        "host": "webservices.amazon.co.jp",
        "region": "us-west-2",
        "currency": "JPY",
        "url_domain": "amazon.co.jp"
    }
}

def get_marketplace_config(marketplace: str) -> dict:
    """Get configuration for specific marketplace"""
    return MARKETPLACE_CONFIG.get(marketplace, MARKETPLACE_CONFIG["US"])
```

**.env**:
```bash
# Amazon PA API Credentials (empty until you get API access)
AMAZON_ACCESS_KEY=
AMAZON_SECRET_KEY=
AMAZON_ASSOCIATE_TAG=yourname-20
AMAZON_MARKETPLACE=IN

# Development Mode
MOCK_MODE=true

# Redis (optional for local development)
REDIS_URL=redis://localhost:6379/0

# Rate Limits
MAX_REQUESTS_PER_SECOND=0.9
MAX_REQUESTS_PER_DAY=8000
```

### Step 3: Core PA API Client (Official SDK Integration)

**core/paapi_client.py**:
```python
"""Production-grade Amazon PA API client using official SDK"""

from paapi5_python_sdk.api.default_api import DefaultApi
from paapi5_python_sdk.models.search_items_request import SearchItemsRequest
from paapi5_python_sdk.models.search_items_resource import SearchItemsResource
from paapi5_python_sdk.models.get_items_request import GetItemsRequest
from paapi5_python_sdk.models.get_items_resource import GetItemsResource
from paapi5_python_sdk.models.partner_type import PartnerType
from paapi5_python_sdk.rest import ApiException

from typing import List, Optional, Dict, Any
import asyncio
from datetime import datetime, timedelta

from config.settings import settings
from config.marketplace import get_marketplace_config
from core.rate_limiter import RateLimiter
from core.circuit_breaker import CircuitBreaker
from utils.metrics import metrics
import logging

logger = logging.getLogger(__name__)

class PAAPIClient:
    """
    Production-ready Amazon Product Advertising API client
    
    Features:
    - Official SDK integration with automatic request signing
    - Rate limiting to stay within API quotas
    - Circuit breaker for fault tolerance
    - Connection pooling and reuse
    - Comprehensive error handling
    """
    
    def __init__(self):
        self.marketplace_config = get_marketplace_config(settings.amazon_marketplace)
        self.rate_limiter = RateLimiter(
            max_per_second=settings.max_requests_per_second,
            max_per_day=settings.max_requests_per_day
        )
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=settings.circuit_breaker_threshold,
            timeout=settings.circuit_breaker_timeout
        )
        
        # Initialize SDK API client
        if not settings.mock_mode:
            self.api = DefaultApi(
                access_key=settings.amazon_access_key,
                secret_key=settings.amazon_secret_key,
                host=self.marketplace_config['host'],
                region=self.marketplace_config['region']
            )
        else:
            self.api = None
            logger.warning("Running in MOCK MODE - using fake data")
    
    async def search_items(
        self,
        keywords: str,
        search_index: str = "All",
        item_count: int = 10,
        min_price: Optional[int] = None,
        max_price: Optional[int] = None,
        min_saving_percent: Optional[int] = None,
        delivery_flags: Optional[List[str]] = None,
        resources: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Search for items on Amazon using SearchItems operation
        
        Args:
            keywords: Search keywords
            search_index: Category (Books, Electronics, All, etc.)
            item_count: Number of results (1-10)
            min_price: Minimum price in cents/paise
            max_price: Maximum price in cents/paise
            min_saving_percent: Minimum discount percentage
            delivery_flags: ['Prime', 'FreeShipping']
            resources: Specific resources to fetch
        
        Returns:
            Dict with search results and metadata
        """
        # Check rate limits
        if not await self.rate_limiter.acquire():
            raise Exception("Rate limit exceeded - try again later")
        
        # Check circuit breaker
        if not self.circuit_breaker.allow_request():
            raise Exception("Circuit breaker open - API temporarily unavailable")
        
        if settings.mock_mode:
            return self._mock_search_items(keywords, item_count)
        
        # Default resources for optimal response size
        if resources is None:
            resources = [
                SearchItemsResource.IMAGES_PRIMARY_LARGE,
                SearchItemsResource.ITEMINFO_TITLE,
                SearchItemsResource.ITEMINFO_BYLINEINFO,
                SearchItemsResource.ITEMINFO_FEATURES,
                SearchItemsResource.OFFERS_LISTINGS_PRICE,
                SearchItemsResource.OFFERS_LISTINGS_DELIVERYINFO_ISPRIMEELIGIBLE,
                SearchItemsResource.CUSTOMERREVIEWS_STARRATING,
                SearchItemsResource.CUSTOMERREVIEWS_COUNT,
            ]
        
        try:
            # Build request object
            request = SearchItemsRequest(
                partner_tag=settings.amazon_associate_tag,
                partner_type=PartnerType.ASSOCIATES,
                keywords=keywords,
                search_index=search_index,
                item_count=min(item_count, 10),  # API limit
                resources=resources
            )
            
            # Add optional filters
            if min_price:
                request.min_price = min_price
            if max_price:
                request.max_price = max_price
            if min_saving_percent:
                request.min_saving_percent = min_saving_percent
            if delivery_flags:
                request.delivery_flags = delivery_flags
            
            # Execute API call (synchronous SDK call in thread pool)
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                self.api.search_items,
                request
            )
            
            # Record success
            self.circuit_breaker.record_success()
            metrics.record_api_call("search_items", "success")
            
            # Parse and return results
            return self._parse_search_response(response)
            
        except ApiException as e:
            self.circuit_breaker.record_failure()
            metrics.record_api_call("search_items", "error")
            logger.error(f"PA API Error: {e.status} - {e.body}")
            raise Exception(f"Amazon API Error: {e.body}")
        
        except Exception as e:
            self.circuit_breaker.record_failure()
            metrics.record_api_call("search_items", "error")
            logger.error(f"Unexpected error: {str(e)}")
            raise
    
    async def get_items(
        self,
        asins: List[str],
        resources: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Get detailed information for specific items using GetItems operation
        
        Args:
            asins: List of ASINs (max 10 per request for batching)
            resources: Specific resources to fetch
        
        Returns:
            Dict with item details mapped by ASIN
        """
        # Check rate limits
        if not await self.rate_limiter.acquire():
            raise Exception("Rate limit exceeded")
        
        if not self.circuit_breaker.allow_request():
            raise Exception("Circuit breaker open")
        
        if settings.mock_mode:
            return self._mock_get_items(asins)
        
        # Default resources for detailed product info
        if resources is None:
            resources = [
                GetItemsResource.IMAGES_PRIMARY_LARGE,
                GetItemsResource.IMAGES_VARIANTS_LARGE,
                GetItemsResource.ITEMINFO_TITLE,
                GetItemsResource.ITEMINFO_BYLINEINFO,
                GetItemsResource.ITEMINFO_FEATURES,
                GetItemsResource.ITEMINFO_PRODUCTINFO,
                GetItemsResource.ITEMINFO_TECHNICALINFO,
                GetItemsResource.OFFERS_LISTINGS_PRICE,
                GetItemsResource.OFFERS_LISTINGS_DELIVERYINFO,
                GetItemsResource.OFFERS_LISTINGS_AVAILABILITY,
                GetItemsResource.CUSTOMERREVIEWS_STARRATING,
                GetItemsResource.CUSTOMERREVIEWS_COUNT,
            ]
        
        try:
            request = GetItemsRequest(
                partner_tag=settings.amazon_associate_tag,
                partner_type=PartnerType.ASSOCIATES,
                item_ids=asins[:10],  # API limit: 10 items per request
                resources=resources
            )
            
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                self.api.get_items,
                request
            )
            
            self.circuit_breaker.record_success()
            metrics.record_api_call("get_items", "success")
            
            return self._parse_get_items_response(response)
            
        except ApiException as e:
            self.circuit_breaker.record_failure()
            metrics.record_api_call("get_items", "error")
            logger.error(f"PA API Error: {e.status} - {e.body}")
            raise Exception(f"Amazon API Error: {e.body}")
        
        except Exception as e:
            self.circuit_breaker.record_failure()
            metrics.record_api_call("get_items", "error")
            raise
    
    def _parse_search_response(self, response) -> Dict[str, Any]:
        """Parse SearchItems API response into structured dict"""
        results = {
            'items': [],
            'search_url': response.search_result.search_url if response.search_result else None,
            'total_results': response.search_result.total_result_count if response.search_result else 0,
        }
        
        if response.search_result and response.search_result.items:
            for item in response.search_result.items:
                results['items'].append(self._parse_item(item))
        
        if response.errors:
            results['errors'] = [
                {'code': e.code, 'message': e.message}
                for e in response.errors
            ]
        
        return results
    
    def _parse_get_items_response(self, response) -> Dict[str, Any]:
        """Parse GetItems API response"""
        results = {'items': {}}
        
        if response.items_result and response.items_result.items:
            for item in response.items_result.items:
                parsed = self._parse_item_detailed(item)
                results['items'][item.asin] = parsed
        
        return results
    
    def _parse_item(self, item) -> Dict[str, Any]:
        """Parse item into clean dict structure"""
        # Extract price
        price = None
        currency = self.marketplace_config['currency']
        if item.offers and item.offers.listings:
            listing = item.offers.listings[0]
            if listing.price:
                price = listing.price.amount
        
        # Extract rating
        rating = None
        review_count = 0
        if item.customer_reviews:
            rating = item.customer_reviews.star_rating
            review_count = item.customer_reviews.count or 0
        
        # Build affiliate URL
        affiliate_url = f"https://www.{self.marketplace_config['url_domain']}/dp/{item.asin}?tag={settings.amazon_associate_tag}"
        
        return {
            'asin': item.asin,
            'title': item.item_info.title.display_value if item.item_info and item.item_info.title else "N/A",
            'price': price,
            'currency': currency,
            'rating': rating,
            'review_count': review_count,
            'image_url': item.images.primary.large.url if item.images and item.images.primary else None,
            'affiliate_url': affiliate_url,
            'detail_page_url': item.detail_page_url,
            'prime_eligible': item.offers.listings[0].delivery_info.is_prime_eligible if item.offers and item.offers.listings else False,
        }
    
    def _parse_item_detailed(self, item) -> Dict[str, Any]:
        """Parse item with full details"""
        basic = self._parse_item(item)
        
        # Add detailed fields
        if item.item_info:
            if item.item_info.features:
                basic['features'] = item.item_info.features.display_values
            if item.item_info.by_line_info and item.item_info.by_line_info.brand:
                basic['brand'] = item.item_info.by_line_info.brand.display_value
        
        # Delivery info
        if item.offers and item.offers.listings:
            listing = item.offers.listings[0]
            if listing.delivery_info:
                basic['delivery_message'] = listing.delivery_info.shipping_charge.display_amount if listing.delivery_info.shipping_charge else "FREE"
            if listing.availability:
                basic['availability'] = listing.availability.message
        
        return basic
    
    def _mock_search_items(self, keywords: str, count: int) -> Dict[str, Any]:
        """Generate mock search results for development"""
        return {
            'items': [
                {
                    'asin': f'B0{i:02d}MOCK{keywords[:3].upper()}',
                    'title': f'{keywords} - Mock Product {i+1}',
                    'price': 1500 + (i * 500),
                    'currency': 'INR',
                    'rating': 4.0 + (i * 0.1),
                    'review_count': 50 + (i * 25),
                    'image_url': f'https://via.placeholder.com/500?text=Product+{i+1}',
                    'affiliate_url': f'https://amazon.in/dp/B0{i:02d}MOCK{keywords[:3].upper()}?tag={settings.amazon_associate_tag}',
                    'detail_page_url': f'https://amazon.in/dp/B0{i:02d}MOCK',
                    'prime_eligible': i % 2 == 0,
                }
                for i in range(count)
            ],
            'total_results': count,
            'search_url': f'https://amazon.in/s?k={keywords}'
        }
    
    def _mock_get_items(self, asins: List[str]) -> Dict[str, Any]:
        """Generate mock product details"""
        return {
            'items': {
                asin: {
                    'asin': asin,
                    'title': f'Mock Product {asin}',
                    'price': 2999,
                    'currency': 'INR',
                    'rating': 4.3,
                    'review_count': 150,
                    'image_url': 'https://via.placeholder.com/500',
                    'affiliate_url': f'https://amazon.in/dp/{asin}?tag={settings.amazon_associate_tag}',
                    'detail_page_url': f'https://amazon.in/dp/{asin}',
                    'prime_eligible': True,
                    'features': ['Feature 1', 'Feature 2', 'Feature 3'],
                    'brand': 'MockBrand',
                    'delivery_message': 'FREE',
                    'availability': 'In Stock',
                }
                for asin in asins
            }
        }

# Singleton instance
paapi_client = PAAPIClient()
```

### Step 4: Rate Limiter (Critical for Production)

**core/rate_limiter.py**:
```python
"""Token bucket rate limiter for PA API throttling"""

import asyncio
from datetime import datetime, timedelta
from typing import Optional
import logging

logger = logging.getLogger(__name__)

class RateLimiter:
    """
    Token bucket rate limiter
    
    Enforces:
    - Max requests per second (TPS limit)
    - Max requests per day (TPD limit)
    """
    
    def __init__(self, max_per_second: float, max_per_day: int):
        self.max_per_second = max_per_second
        self.max_per_day = max_per_day
        
        # Per-second tracking
        self.tokens = max_per_second
        self.last_refill = datetime.now()
        
        # Per-day tracking
        self.daily_requests = 0
        self.daily_reset = datetime.now() + timedelta(days=1)
        
        self.lock = asyncio.Lock()
    
    async def acquire(self) -> bool:
        """
        Acquire permission to make an API request
        
        Returns:
            True if request allowed, False if rate limited
        """
        async with self.lock:
            # Refill tokens based on time passed
            now = datetime.now()
            time_passed = (now - self.last_refill).total_seconds()
            self.tokens = min(
                self.max_per_second,
                self.tokens + time_passed * self.max_per_second
            )
            self.last_refill = now
            
            # Reset daily counter if needed
            if now >= self.daily_reset:
                self.daily_requests = 0
                self.daily_reset = now + timedelta(days=1)
                logger.info("Daily rate limit counter reset")
            
            # Check daily limit
            if self.daily_requests >= self.max_per_day:
                logger.warning(f"Daily rate limit reached: {self.daily_requests}/{self.max_per_day}")
                return False
            
            # Check per-second limit
            if self.tokens < 1.0:
                logger.warning("Per-second rate limit exceeded")
                return False
            
            # Consume token
            self.tokens -= 1.0
            self.daily_requests += 1
            
            return True
    
    def get_stats(self) -> dict:
        """Get current rate limit statistics"""
        return {
            'tokens_available': self.tokens,
            'daily_requests_used': self.daily_requests,
            'daily_requests_limit': self.max_per_day,
            'daily_reset_in': (self.daily_reset - datetime.now()).total_seconds(),
        }
```

### Step 5: Circuit Breaker (Fault Tolerance)

**core/circuit_breaker.py**:
```python
"""Circuit breaker pattern for PA API resilience"""

from datetime import datetime, timedelta
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class CircuitState(Enum):
    CLOSED = "closed"  # Normal operation
    OPEN = "open"      # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if recovered

class CircuitBreaker:
    """
    Circuit breaker to prevent cascading failures
    
    - Opens after N consecutive failures
    - Stays open for timeout period
    - Half-opens to test recovery
    """
    
    def __init__(self, failure_threshold: int, timeout: int):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = None
    
    def allow_request(self) -> bool:
        """Check if request should be allowed"""
        if self.state == CircuitState.CLOSED:
            return True
        
        if self.state == CircuitState.OPEN:
            # Check if timeout has passed
            if self.last_failure_time:
                elapsed = (datetime.now() - self.last_failure_time).total_seconds()
                if elapsed >= self.timeout:
                    logger.info("Circuit breaker entering HALF_OPEN state")
                    self.state = CircuitState.HALF_OPEN
                    return True
            return False
        
        if self.state == CircuitState.HALF_OPEN:
            return True
        
        return False
    
    def record_success(self):
        """Record successful request"""
        if self.state == CircuitState.HALF_OPEN:
            logger.info("Circuit breaker closing after successful request")
            self.state = CircuitState.CLOSED
            self.failure_count = 0
    
    def record_failure(self):
        """Record failed request"""
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        
        if self.state == CircuitState.HALF_OPEN:
            logger.warning("Circuit breaker opening again after failure in HALF_OPEN")
            self.state = CircuitState.OPEN
        
        if self.failure_count >= self.failure_threshold and self.state == CircuitState.CLOSED:
            logger.error(f"Circuit breaker opening after {self.failure_count} failures")
            self.state = CircuitState.OPEN
    
    def get_state(self) -> dict:
        """Get current circuit breaker state"""
        return {
            'state': self.state.value,
            'failure_count': self.failure_count,
            'failure_threshold': self.failure_threshold,
        }
```

This is Part 1 of the production blueprint. Would you like me to continue with:
- Part 2: Caching layer (Redis + memory)
- Part 3: Service layer (search, product, intelligence)
- Part 4: MCP tools implementation
- Part 5: Monitoring, testing & deployment?

The architecture follows all best practices you mentioned: SDK-based (no manual auth), async processing, circuit breaker, rate limiting, and production-ready error handling.[3][7][6]

[1](https://webservices.amazon.com/paapi5/documentation/quick-start/using-sdk.html)
[2](https://webservices.amazon.com/paapi5/documentation/with-sdk.html)
[3](https://github.com/Telefonica/amazon-paapi5-sdk)
[4](https://github.com/jlowin/fastmcp)
[5](https://gofastmcp.com/tutorials/create-mcp-server)
[6](https://snyk.io/articles/5-best-practices-for-building-mcp-servers/)
[7](https://composio.dev/blog/mcp-server-step-by-step-guide-to-building-from-scrtch)
[8](https://pypi.org/project/python-amazon-paapi/)
[9](https://libraries.io/pypi/amazon-paapi5-python-sdk)
[10](https://pypi.org/project/amightygirl.paapi5-python-sdk/)
[11](https://github.com/denisneuf/python-amazon-ad-api)
[12](https://github.com/sergioteula/python-amazon-paapi)
[13](https://www.piwheels.org/project/qempo-paapi5-python-sdk/)
[14](https://www.youtube.com/watch?v=vBB4eQ4cOv4)
[15](https://pypi.org/project/amazon-paapi5/)
[16](https://github.com/RajpurohitHitesh/amazon-paapi5-php-sdk)
[17](https://python-amazon-ad-api.readthedocs.io)
[18](https://stackoverflow.com/questions/59488297/how-to-use-amazon-product-advertising-api-5-with-python)
[19](https://webservices.amazon.com/paapi5/documentation/)
[20](https://python-amazon-paapi.readthedocs.io)
[21](https://advertising.amazon.com/API/docs/en-us/guides/usage-examples/2025-03-step-by-step-guide-authorization-amazon-ads-api-requests-using-python)
[22](https://mcpservers.org/servers/jademind/mcp-amazon-paapi)
[23](https://www.youtube.com/watch?v=yyxTBFSLw-g)