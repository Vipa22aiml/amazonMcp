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
