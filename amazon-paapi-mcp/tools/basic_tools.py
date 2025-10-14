"""
Basic MCP tools for product search, details, and comparison
"""

from typing import Optional, List
import json
import logging

from fastmcp import Context
from services.search_service import search_service
from services.product_service import product_service

logger = logging.getLogger(__name__)

async def search_products_tool(
    query: str,
    category: Optional[str] = None,
    min_price: Optional[int] = None,
    max_price: Optional[int] = None,
    min_rating: Optional[float] = None,
    prime_only: bool = False,
    sort_by: str = "relevance",
    limit: int = 10,
    ctx: Optional[Context] = None
) -> str:
    """
    Search for products on Amazon India with advanced filters.
    
    Args:
        query: Search keywords (e.g., "wireless earbuds", "gaming laptop")
        category: Product category (electronics, books, fashion, beauty, sports, toys, etc.)
        min_price: Minimum price in INR
        max_price: Maximum price in INR
        min_rating: Minimum customer rating (1.0 to 5.0)
        prime_only: Only show Amazon Prime eligible products
        sort_by: Sort order - "relevance", "price_low", "price_high", "rating"
        limit: Number of results to return (1-10)
    
    Returns:
        JSON string with search results including products with prices, ratings, and affiliate links
    """
    if ctx:
        ctx.info(f"Searching Amazon for: {query}")
    
    try:
        results = await search_service.search_products(
            keywords=query,
            category=category,
            min_price=min_price,
            max_price=max_price,
            min_rating=min_rating,
            prime_only=prime_only,
            sort_by=sort_by,
            limit=limit
        )
        
        return json.dumps(results, indent=2)
        
    except Exception as e:
        logger.error(f"Search failed: {str(e)}")
        return json.dumps({'error': str(e)})

async def get_product_details_tool(
    asin: str,
    ctx: Optional[Context] = None
) -> str:
    """
    Get detailed information about a specific product.
    
    Args:
        asin: Amazon Standard Identification Number (10-character alphanumeric code)
              Example: "B08N5WRWNW"
    
    Returns:
        JSON string with complete product details including:
        - Full specifications and features
        - Pricing and availability
        - Customer ratings and review summary
        - Delivery information
        - Affiliate purchase link
    """
    if ctx:
        ctx.info(f"Fetching details for: {asin}")
    
    try:
        product = await product_service.get_product_details(asin)
        return json.dumps(product, indent=2)
        
    except Exception as e:
        logger.error(f"Get product failed: {str(e)}")
        return json.dumps({'error': str(e)})

async def compare_products_tool(
    asins: List[str],
    ctx: Optional[Context] = None
) -> str:
    """
    Compare multiple products side-by-side.
    
    Args:
        asins: List of 2 to 4 ASINs to compare
               Example: ["B08N5WRWNW", "B07VGRJDFY"]
    
    Returns:
        JSON string with comparison table showing:
        - Prices across products
        - Ratings and review counts
        - Key features
        - Prime eligibility
        - Side-by-side comparison for easy decision making
    """
    if ctx:
        ctx.info(f"Comparing {len(asins)} products")
    
    try:
        comparison = await product_service.compare_products(asins)
        return json.dumps(comparison, indent=2)
        
    except Exception as e:
        logger.error(f"Comparison failed: {str(e)}")
        return json.dumps({'error': str(e)})
