"""
Advanced MCP tools for intelligent recommendations and analysis
"""

from typing import Optional
import json
import logging

from fastmcp import Context
from intelligence.recommendation import recommendation_engine
from intelligence.analysis import product_analyzer
from services.product_service import product_service
from services.browse_service import browse_service

logger = logging.getLogger(__name__)

async def get_best_in_category_tool(
    category: str,
    max_price: Optional[int] = None,
    scoring: str = "value",
    limit: int = 5,
    ctx: Optional[Context] = None
) -> str:
    """
    Get intelligently curated top products in a category.
    
    This tool uses advanced scoring algorithms to recommend the best products
    based on different criteria.
    
    Args:
        category: Product category or search term (e.g., "headphones", "laptop", "skincare")
        max_price: Maximum price in INR (optional)
        scoring: Recommendation strategy:
                 - "value": Best price-to-quality ratio (default)
                 - "quality": Highest rated with substantial reviews
                 - "popularity": Most reviewed and trending
                 - "deals": Best bargains with Prime eligibility
        limit: Number of recommendations (1-10)
    
    Returns:
        JSON string with curated recommendations including:
        - Products ranked by intelligent scoring
        - Score explanation for each product
        - Why each product was recommended
    """
    if ctx:
        ctx.info(f"Finding best {category} products (scoring: {scoring})")
    
    try:
        recommendations = await recommendation_engine.get_best_in_category(
            category=category,
            max_price=max_price,
            scoring_strategy=scoring,
            limit=limit
        )
        
        return json.dumps(recommendations, indent=2)
        
    except Exception as e:
        logger.error(f"Recommendations failed: {str(e)}")
        return json.dumps({'error': str(e)})

async def get_alternative_products_tool(
    asin: str,
    price_range: str = "similar",
    limit: int = 5,
    ctx: Optional[Context] = None
) -> str:
    """
    Find alternative products similar to a given product.
    
    Args:
        asin: ASIN of the original product
        price_range: Price range for alternatives:
                     - "cheaper": 20-50% less expensive
                     - "similar": Within ±20% of original price (default)
                     - "premium": 20-50% more expensive (higher-end alternatives)
        limit: Number of alternatives to return
    
    Returns:
        JSON string with alternative product recommendations including:
        - Original product for reference
        - Alternative products ranked by value
        - Price comparison to help decision making
    """
    if ctx:
        ctx.info(f"Finding {price_range} alternatives for: {asin}")
    
    try:
        alternatives = await recommendation_engine.get_alternatives(
            asin=asin,
            price_range=price_range,
            limit=limit
        )
        
        return json.dumps(alternatives, indent=2)
        
    except Exception as e:
        logger.error(f"Alternatives search failed: {str(e)}")
        return json.dumps({'error': str(e)})

async def analyze_reviews_tool(
    asin: str,
    ctx: Optional[Context] = None
) -> str:
    """
    Analyze customer reviews and provide insights about a product.
    
    Args:
        asin: Product ASIN
    
    Returns:
        JSON string with review analysis including:
        - Overall sentiment (Excellent, Very Good, Good, Fair, Below Average)
        - Review credibility assessment
        - Purchase recommendation based on feedback
        - Key insights from customer ratings
    """
    if ctx:
        ctx.info(f"Analyzing reviews for: {asin}")
    
    try:
        product = await product_service.get_product_details(asin)
        analysis = product_analyzer.analyze_reviews(product)
        
        result = {
            'asin': asin,
            'product_title': product.get('title'),
            'analysis': analysis
        }
        
        return json.dumps(result, indent=2)
        
    except Exception as e:
        logger.error(f"Review analysis failed: {str(e)}")
        return json.dumps({'error': str(e)})

async def get_trending_products_tool(
    category: str,
    limit: int = 10,
    ctx: Optional[Context] = None
) -> str:
    """
    Get trending/popular products in a category.
    
    Args:
        category: Product category (e.g., "electronics", "fashion", "home")
        limit: Number of trending products to return
    
    Returns:
        JSON string with currently trending products based on high ratings and review volume
    """
    if ctx:
        ctx.info(f"Getting trending products in: {category}")
    
    try:
        trending = await browse_service.get_trending_in_category(
            category=category,
            limit=limit
        )
        
        return json.dumps(trending, indent=2)
        
    except Exception as e:
        logger.error(f"Trending products fetch failed: {str(e)}")
        return json.dumps({'error': str(e)})
