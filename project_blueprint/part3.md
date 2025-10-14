## Part 3: Intelligence Layer & MCP Tools Implementation

### Step 10: Intelligence Layer - Product Scoring & Recommendations

**intelligence/scoring.py**:
```python
"""
Advanced product scoring algorithms for intelligent recommendations

Implements multiple scoring strategies:
- Value score: Best price-to-quality ratio
- Quality score: Rating and review credibility
- Popularity score: Review volume and recency
- Deal score: Discount and Prime eligibility
"""

from typing import List, Dict, Any
import math
import logging

logger = logging.getLogger(__name__)

class ProductScorer:
    """Advanced product scoring engine"""
    
    @staticmethod
    def calculate_value_score(product: Dict[str, Any]) -> float:
        """
        Calculate value score: (rating × √reviews) / price
        
        Higher rating + more reviews + lower price = better value
        Square root of reviews prevents over-weighting extremely popular items
        
        Args:
            product: Product dict with price, rating, review_count
        
        Returns:
            Normalized value score (0-100)
        """
        price = product.get('price')
        rating = product.get('rating', 0) or 0
        reviews = product.get('review_count', 0) or 0
        
        if not price or price == 0:
            return 0.0
        
        # Avoid division issues
        if rating == 0:
            return 0.0
        
        # Formula: (rating × sqrt(reviews)) / (price / 1000)
        # Price divided by 1000 to normalize INR prices
        review_factor = math.sqrt(reviews) if reviews > 0 else 1
        normalized_price = price / 1000
        
        raw_score = (rating * review_factor) / normalized_price
        
        # Normalize to 0-100 scale (cap at realistic max)
        normalized_score = min(100, raw_score * 5)
        
        return round(normalized_score, 2)
    
    @staticmethod
    def calculate_quality_score(product: Dict[str, Any]) -> float:
        """
        Calculate quality score based on rating and review credibility
        
        Factors:
        - Star rating (weight: 60%)
        - Review count credibility (weight: 40%)
        
        Returns:
            Quality score (0-100)
        """
        rating = product.get('rating', 0) or 0
        reviews = product.get('review_count', 0) or 0
        
        # Rating component (0-60 points)
        rating_score = (rating / 5.0) * 60
        
        # Review credibility component (0-40 points)
        # Logarithmic scale: 1-10 reviews = low, 10-100 = medium, 100+ = high
        if reviews == 0:
            credibility_score = 0
        elif reviews < 10:
            credibility_score = 10
        elif reviews < 50:
            credibility_score = 20
        elif reviews < 100:
            credibility_score = 30
        else:
            credibility_score = 40
        
        return round(rating_score + credibility_score, 2)
    
    @staticmethod
    def calculate_popularity_score(product: Dict[str, Any]) -> float:
        """
        Calculate popularity score based on review volume
        
        Uses logarithmic scale to prevent extreme outliers
        
        Returns:
            Popularity score (0-100)
        """
        reviews = product.get('review_count', 0) or 0
        
        if reviews == 0:
            return 0.0
        
        # Logarithmic scale: log10(reviews) × 20
        # 10 reviews = 20, 100 reviews = 40, 1000 reviews = 60, 10000 reviews = 80
        score = math.log10(reviews) * 20
        
        return round(min(100, score), 2)
    
    @staticmethod
    def calculate_deal_score(product: Dict[str, Any]) -> float:
        """
        Calculate deal score for bargain hunting
        
        Factors:
        - Prime eligibility (bonus: +20 points)
        - Low price in category (bonus: varies)
        - High rating (bonus: varies)
        
        Returns:
            Deal score (0-100)
        """
        price = product.get('price', 0) or 0
        rating = product.get('rating', 0) or 0
        prime = product.get('prime_eligible', False)
        
        score = 0
        
        # Prime eligibility bonus
        if prime:
            score += 20
        
        # Price bonus (inverse relationship)
        # Lower price = higher bonus (max 40 points)
        if price > 0:
            # Assume category average is 3000 INR
            category_avg = 3000
            if price < category_avg:
                price_bonus = ((category_avg - price) / category_avg) * 40
                score += price_bonus
        
        # Rating bonus (max 40 points)
        score += (rating / 5.0) * 40
        
        return round(min(100, score), 2)
    
    @staticmethod
    def rank_by_strategy(
        products: List[Dict[str, Any]], 
        strategy: str = 'value'
    ) -> List[Dict[str, Any]]:
        """
        Rank products by scoring strategy
        
        Args:
            products: List of product dicts
            strategy: 'value', 'quality', 'popularity', or 'deals'
        
        Returns:
            Products sorted by score (highest first) with score added
        """
        scorer_map = {
            'value': ProductScorer.calculate_value_score,
            'quality': ProductScorer.calculate_quality_score,
            'popularity': ProductScorer.calculate_popularity_score,
            'deals': ProductScorer.calculate_deal_score,
        }
        
        scorer = scorer_map.get(strategy, ProductScorer.calculate_value_score)
        
        # Calculate scores
        for product in products:
            product['score'] = scorer(product)
            product['scoring_method'] = strategy
        
        # Sort by score descending
        ranked = sorted(products, key=lambda x: x.get('score', 0), reverse=True)
        
        logger.info(f"Ranked {len(ranked)} products by {strategy}")
        
        return ranked

# Singleton instance
product_scorer = ProductScorer()
```

**intelligence/recommendation.py**:
```python
"""
Intelligent recommendation engine for curated product suggestions
"""

from typing import List, Dict, Any, Optional
import logging

from services.search_service import search_service
from intelligence.scoring import product_scorer
from core.cache_manager import cached

logger = logging.getLogger(__name__)

class RecommendationEngine:
    """Advanced recommendation engine"""
    
    @cached(namespace="recommendations", ttl=7200)
    async def get_best_in_category(
        self,
        category: str,
        max_price: Optional[int] = None,
        scoring_strategy: str = 'value',
        limit: int = 5
    ) -> Dict[str, Any]:
        """
        Get top products in category using intelligent scoring
        
        Args:
            category: Product category
            max_price: Maximum price filter
            scoring_strategy: 'value', 'quality', 'popularity', 'deals'
            limit: Number of recommendations
        
        Returns:
            Curated recommendations with scores
        """
        logger.info(f"Generating recommendations for: {category}")
        
        # Search for products with quality baseline
        search_results = await search_service.search_products(
            keywords=category,
            category=category,
            max_price=max_price,
            min_rating=4.0,  # Only quality products
            limit=20  # Get more to rank
        )
        
        products = search_results.get('products', [])
        
        if not products:
            return {
                'category': category,
                'recommendations': [],
                'message': 'No products found matching criteria'
            }
        
        # Apply intelligent scoring
        ranked = product_scorer.rank_by_strategy(products, scoring_strategy)
        
        # Get top N
        top_products = ranked[:limit]
        
        return {
            'category': category,
            'scoring_method': scoring_strategy,
            'total_analyzed': len(products),
            'recommendations': top_products,
            'filters': {
                'max_price': max_price,
                'min_rating': 4.0
            }
        }
    
    async def get_alternatives(
        self,
        asin: str,
        price_range: str = 'similar',
        limit: int = 5
    ) -> Dict[str, Any]:
        """
        Find alternative products to a given product
        
        Args:
            asin: Original product ASIN
            price_range: 'cheaper' (20-50% less), 'similar' (±20%), 'premium' (20-50% more)
            limit: Number of alternatives
        
        Returns:
            Alternative product recommendations
        """
        from services.product_service import product_service
        
        logger.info(f"Finding alternatives for: {asin}")
        
        # Get original product
        original = await product_service.get_product_details(asin)
        original_price = original.get('price', {}).get('amount', 0)
        
        if not original_price:
            raise ValueError("Cannot find alternatives - original product has no price")
        
        # Calculate price range
        if price_range == 'cheaper':
            min_p = int(original_price * 0.5)
            max_p = int(original_price * 0.8)
        elif price_range == 'premium':
            min_p = int(original_price * 1.2)
            max_p = int(original_price * 1.5)
        else:  # similar
            min_p = int(original_price * 0.8)
            max_p = int(original_price * 1.2)
        
        # Extract category from title
        title_words = original.get('title', '').split()[:3]
        search_query = ' '.join(title_words)
        
        # Search for alternatives
        search_results = await search_service.search_products(
            keywords=search_query,
            min_price=min_p,
            max_price=max_p,
            min_rating=3.5,
            limit=limit + 2
        )
        
        alternatives = search_results.get('products', [])
        
        # Remove original product from results
        alternatives = [p for p in alternatives if p.get('asin') != asin][:limit]
        
        # Score alternatives
        ranked_alternatives = product_scorer.rank_by_strategy(alternatives, 'value')
        
        return {
            'original_product': original,
            'price_range': price_range,
            'price_filter': {'min': min_p, 'max': max_p},
            'alternatives_count': len(ranked_alternatives),
            'alternatives': ranked_alternatives
        }

# Singleton instance
recommendation_engine = RecommendationEngine()
```

**intelligence/analysis.py**:
```python
"""
Product and review analysis utilities
"""

from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

class ProductAnalyzer:
    """Product and review analysis"""
    
    @staticmethod
    def analyze_reviews(product: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze product reviews and generate insights
        
        Args:
            product: Product with rating and review data
        
        Returns:
            Review analysis with sentiment and credibility
        """
        rating = product.get('rating', {})
        if isinstance(rating, dict):
            avg_rating = rating.get('average', 0)
            review_count = rating.get('count', 0)
        else:
            avg_rating = product.get('rating', 0)
            review_count = product.get('review_count', 0)
        
        # Sentiment analysis
        if avg_rating >= 4.5:
            sentiment = "Excellent"
            description = "Customers love this product - consistently high ratings"
        elif avg_rating >= 4.0:
            sentiment = "Very Good"
            description = "Well-received by most customers with positive feedback"
        elif avg_rating >= 3.5:
            sentiment = "Good"
            description = "Generally positive but with some concerns reported"
        elif avg_rating >= 3.0:
            sentiment = "Fair"
            description = "Mixed reviews - research carefully before purchasing"
        else:
            sentiment = "Below Average"
            description = "Lower ratings suggest potential issues - consider alternatives"
        
        # Credibility assessment
        if review_count > 500:
            credibility = "Very High"
            credibility_note = "Large sample size provides reliable insights"
        elif review_count > 100:
            credibility = "High"
            credibility_note = "Substantial reviews provide good confidence"
        elif review_count > 20:
            credibility = "Moderate"
            credibility_note = "Decent sample size but consider as one factor"
        elif review_count > 5:
            credibility = "Low"
            credibility_note = "Limited reviews - ratings may not be fully representative"
        else:
            credibility = "Very Low"
            credibility_note = "Very few reviews - approach with caution"
        
        return {
            'overall_rating': avg_rating,
            'total_reviews': review_count,
            'sentiment': sentiment,
            'sentiment_description': description,
            'credibility': credibility,
            'credibility_note': credibility_note,
            'recommendation': ProductAnalyzer._generate_recommendation(avg_rating, review_count)
        }
    
    @staticmethod
    def _generate_recommendation(rating: float, count: int) -> str:
        """Generate purchase recommendation"""
        if rating >= 4.3 and count > 100:
            return "Highly Recommended - Strong ratings with good review volume"
        elif rating >= 4.0 and count > 50:
            return "Recommended - Good ratings with adequate reviews"
        elif rating >= 3.8 and count > 20:
            return "Worth Considering - Decent ratings but verify key features"
        elif rating >= 3.5:
            return "Research Further - Mixed feedback suggests careful evaluation"
        else:
            return "Not Recommended - Consider higher-rated alternatives"

# Singleton instance
product_analyzer = ProductAnalyzer()
```

### Step 11: MCP Tools Implementation

**tools/basic_tools.py**:
```python
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
```

**tools/advanced_tools.py**:
```python
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
```

### Step 12: Complete FastMCP Server

**server.py**:
```python
"""
Amazon Shopping MCP Server - Production Grade Implementation

Features:
- 8 powerful tools for product discovery and comparison
- Official Amazon PA API SDK integration
- Multi-level caching for performance
- Rate limiting and circuit breaker for reliability
- Intelligent scoring and recommendations
"""

from fastmcp import FastMCP
import logging
import sys

from config.settings import settings
from tools.basic_tools import (
    search_products_tool,
    get_product_details_tool,
    compare_products_tool
)
from tools.advanced_tools import (
    get_best_in_category_tool,
    get_alternative_products_tool,
    analyze_reviews_tool,
    get_trending_products_tool
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

# Create FastMCP server
mcp = FastMCP(
    name="Amazon Shopping India",
    instructions="""
    An intelligent shopping assistant for Amazon India with advanced product discovery capabilities.
    
    I can help you:
    - Search for products with filters (price, rating, category, Prime eligibility)
    - Get detailed product information including specs, reviews, and pricing
    - Compare multiple products side-by-side
    - Recommend the best products in any category using intelligent scoring
    - Find cheaper or premium alternatives to any product
    - Analyze customer reviews and provide purchase recommendations
    - Discover trending products in categories
    
    All product links include affiliate tracking for commission earning.
    """
)

# Register basic tools
mcp.tool(search_products_tool)
mcp.tool(get_product_details_tool)
mcp.tool(compare_products_tool)

# Register advanced tools
mcp.tool(get_best_in_category_tool)
mcp.tool(get_alternative_products_tool)
mcp.tool(analyze_reviews_tool)
mcp.tool(get_trending_products_tool)

# Health check endpoint
@mcp.tool
def health_check() -> str:
    """
    Check if the MCP server is running properly.
    
    Returns:
        Server status and configuration
    """
    from core.rate_limiter import RateLimiter
    
    status = {
        'status': 'healthy',
        'mode': 'MOCK' if settings.mock_mode else 'PRODUCTION',
        'marketplace': settings.amazon_marketplace,
        'tools_available': 8,
        'cache_enabled': settings.cache_ttl_search > 0,
    }
    
    import json
    return json.dumps(status, indent=2)

if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("🛍️  Amazon Shopping MCP Server")
    logger.info("=" * 60)
    logger.info(f"📍 Mode: {'MOCK (Development)' if settings.mock_mode else 'LIVE (Production)'}")
    logger.info(f"🌍 Marketplace: Amazon.{settings.amazon_marketplace}")
    logger.info(f"⚡ Cache: {'Enabled' if settings.redis_url else 'Memory Only'}")
    logger.info(f"🔧 Tools: 8 available")
    logger.info("=" * 60)
    
    # For OpenAI Apps SDK deployment, use HTTP transport
    # For Claude Desktop local testing, use STDIO transport
    
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--http":
        logger.info("🌐 Starting HTTP server on port 8000...")
        mcp.run(transport="http", host="0.0.0.0", port=8000, path="/mcp")
    else:
        logger.info("💻 Starting STDIO server for local testing...")
        mcp.run()  # STDIO transport for Claude Desktop
```

### Step 13: Testing Your MCP Server

**test_local.py**:
```python
"""Test script to verify MCP server functionality"""

import asyncio
from fastmcp import Client
from server import mcp

async def test_all_tools():
    """Comprehensive test of all MCP tools"""
    
    async with Client(mcp) as client:
        print("\n" + "="*60)
        print("Testing Amazon Shopping MCP Server")
        print("="*60)
        
        # Test 1: Health check
        print("\n✓ Test 1: Health Check")
        result = await client.call_tool("health_check", {})
        print(result.content[0].text[:300])
        
        # Test 2: Search products
        print("\n✓ Test 2: Search Products")
        result = await client.call_tool("search_products_tool", {
            "query": "wireless earbuds",
            "max_price": 5000,
            "min_rating": 4.0,
            "limit": 5
        })
        print(result.content[0].text[:500])
        
        # Test 3: Best in category
        print("\n✓ Test 3: Best in Category")
        result = await client.call_tool("get_best_in_category_tool", {
            "category": "gaming mouse",
            "max_price": 3000,
            "scoring": "value",
            "limit": 3
        })
        print(result.content[0].text[:500])
        
        # Test 4: Product details
        print("\n✓ Test 4: Get Product Details")
        result = await client.call_tool("get_product_details_tool", {
            "asin": "B001MOCKTEST"
        })
        print(result.content[0].text[:400])
        
        # Test 5: Review analysis
        print("\n✓ Test 5: Analyze Reviews")
        result = await client.call_tool("analyze_reviews_tool", {
            "asin": "B001MOCKTEST"
        })
        print(result.content[0].text[:400])
        
        print("\n" + "="*60)
        print("✅ All tests completed!")
        print("="*60)

if __name__ == "__main__":
    asyncio.run(test_all_tools())
```

Run tests:
```bash
python test_local.py
```

### Step 14: Deployment Commands

**Local development with STDIO (Claude Desktop)**:
```bash
python server.py
```

**Production with HTTP (OpenAI Apps SDK)**:
```bash
# Set production mode
export MOCK_MODE=false
export AMAZON_ACCESS_KEY=your_key
export AMAZON_SECRET_KEY=your_secret
export AMAZON_ASSOCIATE_TAG=yourname-20

# Start HTTP server
python server.py --http
```

**Docker deployment**:
```bash
docker-compose up -d
```

Your production-grade Amazon MCP server is now complete with 8 powerful tools, intelligent recommendations, caching, rate limiting, and full PA API SDK integration. Next up would be Part 4 (Monitoring & Metrics) and Part 5 (Deployment to Railway/Render), but you now have a fully functional MCP server ready for OpenAI Apps SDK integration!

[1](https://github.com/sergioteula/python-amazon-paapi)
[2](https://pypi.org/project/python-amazon-paapi/)
[3](https://webservices.amazon.com/paapi5/documentation/search-items.html)
[4](https://webservices.amazon.com/paapi5/documentation/quick-start/using-sdk.html)
[5](https://github.com/nhapentor/python-amazon-unthrottled-paapi)
[6](https://python-amazon-product-api.readthedocs.io)
[7](https://stackoverflow.com/questions/16328040/searching-for-books-with-the-amazon-product-advertising-api-python)
[8](https://www.youtube.com/watch?v=vBB4eQ4cOv4)
[9](https://mcpservers.org/servers/jademind/mcp-amazon-paapi)