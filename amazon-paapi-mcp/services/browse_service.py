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
