give part 2:
## Part 2: Caching Layer & Service Architecture

### Step 6: Multi-Level Caching System

**core/cache_manager.py**:
```python
"""
Multi-level caching system for Amazon PA API responses

Architecture:
- L1: In-memory cache (cachetools LRU) for ultra-fast access
- L2: Redis cache for distributed caching across instances
- Automatic fallback from Redis to memory if Redis unavailable
"""

from typing import Optional, Any, Callable
import json
import hashlib
import functools
import logging
from datetime import timedelta

try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logging.warning("Redis not available - using memory cache only")

from cachetools import TTLCache
from config.settings import settings

logger = logging.getLogger(__name__)

class CacheManager:
    """
    Production-grade multi-level cache manager
    
    Features:
    - L1 in-memory cache with LRU eviction
    - L2 Redis cache for persistence
    - Automatic serialization/deserialization
    - Cache key generation with namespace support
    - TTL management per cache operation
    """
    
    def __init__(self):
        # L1: In-memory cache (max 1000 items)
        self.memory_cache = TTLCache(maxsize=1000, ttl=settings.cache_ttl_search)
        
        # L2: Redis cache
        self.redis_client = None
        if REDIS_AVAILABLE and settings.redis_url:
            try:
                self.redis_client = redis.from_url(
                    settings.redis_url,
                    encoding="utf-8",
                    decode_responses=True
                )
                logger.info("Redis cache initialized successfully")
            except Exception as e:
                logger.warning(f"Redis initialization failed: {e}. Using memory cache only.")
    
    async def get(self, key: str, namespace: str = "default") -> Optional[Any]:
        """
        Get value from cache (checks L1 then L2)
        
        Args:
            key: Cache key
            namespace: Cache namespace for organization
        
        Returns:
            Cached value or None if not found
        """
        cache_key = self._generate_key(key, namespace)
        
        # Try L1 (memory) first
        if cache_key in self.memory_cache:
            logger.debug(f"Cache HIT (memory): {cache_key}")
            return self.memory_cache[cache_key]
        
        # Try L2 (Redis)
        if self.redis_client:
            try:
                value = await self.redis_client.get(cache_key)
                if value:
                    logger.debug(f"Cache HIT (redis): {cache_key}")
                    # Deserialize and populate L1
                    deserialized = json.loads(value)
                    self.memory_cache[cache_key] = deserialized
                    return deserialized
            except Exception as e:
                logger.warning(f"Redis GET error: {e}")
        
        logger.debug(f"Cache MISS: {cache_key}")
        return None
    
    async def set(
        self, 
        key: str, 
        value: Any, 
        namespace: str = "default",
        ttl: Optional[int] = None
    ):
        """
        Set value in both cache levels
        
        Args:
            key: Cache key
            value: Value to cache (must be JSON serializable)
            namespace: Cache namespace
            ttl: Time to live in seconds (uses default if None)
        """
        cache_key = self._generate_key(key, namespace)
        ttl = ttl or settings.cache_ttl_search
        
        # Set in L1 (memory)
        self.memory_cache[cache_key] = value
        
        # Set in L2 (Redis)
        if self.redis_client:
            try:
                serialized = json.dumps(value)
                await self.redis_client.setex(
                    cache_key,
                    timedelta(seconds=ttl),
                    serialized
                )
                logger.debug(f"Cache SET: {cache_key} (TTL: {ttl}s)")
            except Exception as e:
                logger.warning(f"Redis SET error: {e}")
    
    async def delete(self, key: str, namespace: str = "default"):
        """Delete key from all cache levels"""
        cache_key = self._generate_key(key, namespace)
        
        # Delete from L1
        if cache_key in self.memory_cache:
            del self.memory_cache[cache_key]
        
        # Delete from L2
        if self.redis_client:
            try:
                await self.redis_client.delete(cache_key)
                logger.debug(f"Cache DELETE: {cache_key}")
            except Exception as e:
                logger.warning(f"Redis DELETE error: {e}")
    
    async def clear_namespace(self, namespace: str):
        """Clear all keys in a namespace"""
        pattern = f"{namespace}:*"
        
        if self.redis_client:
            try:
                keys = await self.redis_client.keys(pattern)
                if keys:
                    await self.redis_client.delete(*keys)
                    logger.info(f"Cleared {len(keys)} keys from namespace: {namespace}")
            except Exception as e:
                logger.warning(f"Redis CLEAR error: {e}")
    
    def _generate_key(self, key: str, namespace: str) -> str:
        """Generate namespaced cache key with hash"""
        return f"{namespace}:{self._hash_key(key)}"
    
    def _hash_key(self, key: str) -> str:
        """Generate deterministic hash for cache key"""
        return hashlib.md5(key.encode()).hexdigest()
    
    async def close(self):
        """Close Redis connection"""
        if self.redis_client:
            await self.redis_client.close()
            logger.info("Redis connection closed")

# Singleton instance
cache_manager = CacheManager()

# Decorator for automatic caching
def cached(namespace: str = "default", ttl: Optional[int] = None):
    """
    Decorator to automatically cache function results
    
    Usage:
        @cached(namespace="products", ttl=3600)
        async def get_product(asin: str):
            return await expensive_api_call(asin)
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key from function name and arguments
            key_data = {
                'func': func.__name__,
                'args': args,
                'kwargs': kwargs
            }
            cache_key = json.dumps(key_data, sort_keys=True)
            
            # Try to get from cache
            cached_result = await cache_manager.get(cache_key, namespace)
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            result = await func(*args, **kwargs)
            await cache_manager.set(cache_key, result, namespace, ttl)
            
            return result
        
        return wrapper
    return decorator
```

### Step 7: Service Layer (Business Logic)

**services/search_service.py**:
```python
"""
Search service for Amazon product search operations

Handles:
- SearchItems API operation
- Price filtering and sorting
- Category-based search
- Prime/delivery filtering
"""

from typing import List, Optional, Dict, Any
import logging

from core.paapi_client import paapi_client
from core.cache_manager import cached
from config.settings import settings
from utils.formatters import format_search_results

logger = logging.getLogger(__name__)

class SearchService:
    """Service for product search operations"""
    
    @cached(namespace="search", ttl=3600)
    async def search_products(
        self,
        keywords: str,
        category: Optional[str] = None,
        min_price: Optional[int] = None,
        max_price: Optional[int] = None,
        min_rating: Optional[float] = None,
        prime_only: bool = False,
        sort_by: str = "relevance",
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        Search for products with filters
        
        Args:
            keywords: Search query
            category: Product category (maps to SearchIndex)
            min_price: Minimum price in currency units (INR/USD)
            max_price: Maximum price in currency units
            min_rating: Minimum customer rating (1.0-5.0)
            prime_only: Only show Prime-eligible products
            sort_by: Sort order (relevance, price_low, price_high, rating)
            limit: Max results to return
        
        Returns:
            Formatted search results with metadata
        """
        logger.info(f"Searching: '{keywords}' in {category or 'All'}")
        
        # Map category to Amazon SearchIndex
        search_index = self._map_category_to_index(category)
        
        # Convert price to cents/paise for API
        api_min_price = (min_price * 100) if min_price else None
        api_max_price = (max_price * 100) if max_price else None
        
        # Set delivery flags
        delivery_flags = ["Prime"] if prime_only else None
        
        # Call PA API
        try:
            response = await paapi_client.search_items(
                keywords=keywords,
                search_index=search_index,
                item_count=min(limit, 10),  # PA API limit per request
                min_price=api_min_price,
                max_price=api_max_price,
                delivery_flags=delivery_flags
            )
            
            items = response.get('items', [])
            
            # Apply rating filter (PA API doesn't support this natively)
            if min_rating:
                items = [
                    item for item in items 
                    if item.get('rating') and item['rating'] >= min_rating
                ]
            
            # Apply sorting
            items = self._sort_items(items, sort_by)
            
            # Format results
            return format_search_results(
                items=items[:limit],
                query=keywords,
                total_count=len(items),
                filters={
                    'category': category,
                    'min_price': min_price,
                    'max_price': max_price,
                    'min_rating': min_rating,
                    'prime_only': prime_only,
                }
            )
            
        except Exception as e:
            logger.error(f"Search failed: {str(e)}")
            raise
    
    def _map_category_to_index(self, category: Optional[str]) -> str:
        """Map friendly category names to Amazon SearchIndex values"""
        if not category:
            return "All"
        
        category_map = {
            # Electronics & Tech
            'electronics': 'Electronics',
            'tech': 'Electronics',
            'computers': 'Computers',
            'laptops': 'Computers',
            'mobile': 'Electronics',
            'phones': 'Electronics',
            'cameras': 'Electronics',
            'audio': 'Electronics',
            'headphones': 'Electronics',
            
            # Home & Kitchen
            'home': 'Home',
            'kitchen': 'Kitchen',
            'furniture': 'Furniture',
            'appliances': 'Appliances',
            
            # Fashion
            'fashion': 'Fashion',
            'clothing': 'Fashion',
            'shoes': 'Shoes',
            'watches': 'Watches',
            'jewelry': 'Jewelry',
            
            # Beauty & Health
            'beauty': 'Beauty',
            'skincare': 'Beauty',
            'health': 'HealthPersonalCare',
            'supplements': 'HealthPersonalCare',
            
            # Sports & Fitness
            'sports': 'SportingGoods',
            'fitness': 'SportingGoods',
            'gym': 'SportingGoods',
            
            # Books & Media
            'books': 'Books',
            'movies': 'Movies',
            'music': 'Music',
            
            # Toys & Games
            'toys': 'Toys',
            'games': 'VideoGames',
            
            # Others
            'automotive': 'Automotive',
            'baby': 'Baby',
            'grocery': 'Grocery',
            'pet': 'PetSupplies',
        }
        
        return category_map.get(category.lower(), 'All')
    
    def _sort_items(self, items: List[Dict[str, Any]], sort_by: str) -> List[Dict[str, Any]]:
        """Sort items based on criteria"""
        if sort_by == "price_low":
            return sorted(
                items, 
                key=lambda x: x.get('price', float('inf'))
            )
        
        elif sort_by == "price_high":
            return sorted(
                items, 
                key=lambda x: x.get('price', 0),
                reverse=True
            )
        
        elif sort_by == "rating":
            return sorted(
                items,
                key=lambda x: (x.get('rating', 0), x.get('review_count', 0)),
                reverse=True
            )
        
        # Default: relevance (API order)
        return items

# Singleton instance
search_service = SearchService()
```

**services/product_service.py**:
```python
"""
Product service for detailed product operations

Handles:
- GetItems API operation
- Product comparison
- Batch product retrieval
"""

from typing import List, Dict, Any
import logging

from core.paapi_client import paapi_client
from core.cache_manager import cached
from utils.formatters import format_product_details, format_comparison

logger = logging.getLogger(__name__)

class ProductService:
    """Service for product detail operations"""
    
    @cached(namespace="products", ttl=7200)
    async def get_product_details(self, asin: str) -> Dict[str, Any]:
        """
        Get detailed information about a single product
        
        Args:
            asin: Amazon Standard Identification Number
        
        Returns:
            Formatted product details
        """
        logger.info(f"Fetching product details: {asin}")
        
        try:
            response = await paapi_client.get_items([asin])
            items = response.get('items', {})
            
            if asin not in items:
                raise ValueError(f"Product {asin} not found")
            
            return format_product_details(items[asin])
            
        except Exception as e:
            logger.error(f"Failed to get product {asin}: {str(e)}")
            raise
    
    @cached(namespace="products_batch", ttl=7200)
    async def get_multiple_products(self, asins: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        Get details for multiple products (batch operation)
        
        Args:
            asins: List of ASINs (max 10 for single request)
        
        Returns:
            Dict mapping ASIN to product details
        """
        logger.info(f"Fetching {len(asins)} products in batch")
        
        # PA API allows max 10 items per request
        if len(asins) > 10:
            logger.warning(f"Requested {len(asins)} items, limiting to 10")
            asins = asins[:10]
        
        try:
            response = await paapi_client.get_items(asins)
            items = response.get('items', {})
            
            # Format each product
            formatted = {
                asin: format_product_details(details)
                for asin, details in items.items()
            }
            
            return formatted
            
        except Exception as e:
            logger.error(f"Failed to get products: {str(e)}")
            raise
    
    async def compare_products(self, asins: List[str]) -> Dict[str, Any]:
        """
        Compare multiple products side-by-side
        
        Args:
            asins: List of 2-4 ASINs to compare
        
        Returns:
            Formatted comparison table
        """
        if len(asins) < 2:
            raise ValueError("Need at least 2 products to compare")
        
        if len(asins) > 4:
            logger.warning("Limiting comparison to 4 products")
            asins = asins[:4]
        
        logger.info(f"Comparing {len(asins)} products")
        
        # Get all product details
        products = await self.get_multiple_products(asins)
        
        # Format as comparison
        return format_comparison(list(products.values()))

# Singleton instance
product_service = ProductService()
```

**services/browse_service.py**:
```python
"""
Browse service for category and navigation operations

Handles:
- GetBrowseNodes API operation
- Category hierarchies
- Trending products by category
"""

from typing import Optional, Dict, Any, List
import logging

from core.paapi_client import paapi_client
from core.cache_manager import cached
from services.search_service import search_service

logger = logging.getLogger(__name__)

class BrowseService:
    """Service for browsing categories and trends"""
    
    async def get_trending_in_category(
        self,
        category: str,
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        Get trending/popular products in a category
        
        Uses search with high review count as proxy for trending
        
        Args:
            category: Category name
            limit: Number of products to return
        
        Returns:
            List of trending products
        """
        logger.info(f"Getting trending products in: {category}")
        
        # Search with broad keywords, sort by popularity (review count)
        # This is a proxy for "trending" since PA API doesn't expose Best Sellers
        results = await search_service.search_products(
            keywords=category,
            category=category,
            min_rating=4.0,  # Only well-rated items
            sort_by="rating",  # Sorts by rating × review_count
            limit=limit
        )
        
        return {
            'category': category,
            'trending_products': results['items'],
            'note': 'Based on high ratings and review volume'
        }
    
    async def get_deals_in_category(
        self,
        category: str,
        max_price: Optional[int] = None,
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        Get deals/discounted products in a category
        
        Args:
            category: Category name
            max_price: Maximum price filter
            limit: Number of deals to return
        
        Returns:
            List of deals
        """
        logger.info(f"Getting deals in: {category}")
        
        # Search with Prime eligibility (often has deals)
        results = await search_service.search_products(
            keywords=f"{category} deals",
            category=category,
            max_price=max_price,
            prime_only=True,
            sort_by="price_low",
            limit=limit
        )
        
        return {
            'category': category,
            'deals': results['items'],
            'filters': {
                'max_price': max_price,
                'prime_only': True
            }
        }

# Singleton instance
browse_service = BrowseService()
```

### Step 8: Utility Formatters

**utils/formatters.py**:
```python
"""Response formatters for consistent output structure"""

from typing import List, Dict, Any
from config.settings import settings

def format_search_results(
    items: List[Dict[str, Any]],
    query: str,
    total_count: int,
    filters: Dict[str, Any]
) -> Dict[str, Any]:
    """Format search results for MCP tool response"""
    return {
        'query': query,
        'total_results': total_count,
        'returned_count': len(items),
        'filters_applied': {k: v for k, v in filters.items() if v is not None},
        'products': [
            {
                'asin': item['asin'],
                'title': item['title'],
                'price': {
                    'amount': item['price'],
                    'currency': item['currency'],
                    'formatted': f"{item['currency']} {item['price']}" if item['price'] else "N/A"
                },
                'rating': item.get('rating'),
                'reviews': item.get('review_count', 0),
                'prime': item.get('prime_eligible', False),
                'image': item.get('image_url'),
                'affiliate_link': item['affiliate_url'],
            }
            for item in items
        ],
        'marketplace': settings.amazon_marketplace
    }

def format_product_details(product: Dict[str, Any]) -> Dict[str, Any]:
    """Format detailed product information"""
    return {
        'asin': product['asin'],
        'title': product['title'],
        'brand': product.get('brand', 'N/A'),
        'price': {
            'amount': product['price'],
            'currency': product['currency'],
            'formatted': f"{product['currency']} {product['price']}" if product['price'] else "N/A"
        },
        'rating': {
            'average': product.get('rating'),
            'count': product.get('review_count', 0),
            'summary': _rating_summary(product.get('rating'), product.get('review_count', 0))
        },
        'features': product.get('features', []),
        'images': {
            'primary': product.get('image_url'),
        },
        'availability': product.get('availability', 'Unknown'),
        'delivery': {
            'message': product.get('delivery_message', 'N/A'),
            'prime_eligible': product.get('prime_eligible', False)
        },
        'links': {
            'affiliate': product['affiliate_url'],
            'detail_page': product.get('detail_page_url')
        },
        'marketplace': settings.amazon_marketplace
    }

def format_comparison(products: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Format product comparison table"""
    comparison_fields = [
        'title', 'brand', 'price', 'rating', 'review_count', 
        'prime_eligible', 'features'
    ]
    
    comparison_table = []
    for product in products:
        row = {
            'asin': product['asin'],
            'title': product['title'][:50] + '...' if len(product['title']) > 50 else product['title'],
            'brand': product.get('brand', 'N/A'),
            'price': product['price'],
            'currency': product['currency'],
            'rating': product.get('rating', 'N/A'),
            'reviews': product.get('review_count', 0),
            'prime': '✓' if product.get('prime_eligible') else '✗',
            'features_count': len(product.get('features', [])),
            'affiliate_link': product['affiliate_url']
        }
        comparison_table.append(row)
    
    return {
        'products_compared': len(products),
        'comparison': comparison_table,
        'fields': comparison_fields
    }

def _rating_summary(rating: float, count: int) -> str:
    """Generate human-readable rating summary"""
    if not rating:
        return "No ratings yet"
    
    if rating >= 4.5:
        sentiment = "Excellent"
    elif rating >= 4.0:
        sentiment = "Very Good"
    elif rating >= 3.5:
        sentiment = "Good"
    elif rating >= 3.0:
        sentiment = "Fair"
    else:
        sentiment = "Below Average"
    
    credibility = "High credibility" if count > 100 else "Moderate credibility" if count > 20 else "Limited reviews"
    
    return f"{sentiment} ({rating}/5.0 from {count} reviews) - {credibility}"
```

### Step 9: Redis Setup (Docker Compose)

**docker-compose.yml**:
```yaml
version: '3.8'

services:
  redis:
    image: redis:7-alpine
    container_name: amazon-mcp-redis
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 3s
      retries: 3

  app:
    build: .
    container_name: amazon-mcp-server
    ports:
      - "8000:8000"
    environment:
      - REDIS_URL=redis://redis:6379/0
      - MOCK_MODE=false
    env_file:
      - .env
    depends_on:
      redis:
        condition: service_healthy
    volumes:
      - ./:/app

volumes:
  redis_data:
```

Start Redis for local development:
```bash
docker-compose up -d redis
```

This completes Part 2 with production-grade caching (multi-level), service layer architecture, and proper response formatting. The caching system will dramatically reduce your PA API calls and help you stay within rate limits.[1][2]

Would you like Part 3 next (Intelligence layer + MCP tools implementation)?

[1](https://snyk.io/articles/5-best-practices-for-building-mcp-servers/)
[2](https://composio.dev/blog/mcp-server-step-by-step-guide-to-building-from-scrtch)