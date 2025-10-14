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
