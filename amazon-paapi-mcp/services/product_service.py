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
