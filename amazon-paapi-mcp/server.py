"""
Amazon Shopping MCP Server - Production Grade Implementation
"""

from fastmcp import FastMCP
import logging
import sys
import asyncio

from config.settings import settings
from utils.logger import setup_logging
from utils.metrics import metrics, start_metrics_server, track_tool_execution
from utils.health import health_checker

# Configure logging
setup_logging(
    level="INFO" if not settings.mock_mode else "DEBUG",
    structured=not settings.mock_mode  # JSON logs in production
)

logger = logging.getLogger(__name__)

# Import tools
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

# Register tools with metrics tracking
@mcp.tool
@track_tool_execution
async def search_products(
    query: str,
    category: str = None,
    min_price: int = None,
    max_price: int = None,
    min_rating: float = None,
    prime_only: bool = False,
    sort_by: str = "relevance",
    limit: int = 10
) -> str:
    """Search for products on Amazon India with advanced filters."""
    return await search_products_tool(
        query, category, min_price, max_price,
        min_rating, prime_only, sort_by, limit
    )

@mcp.tool
@track_tool_execution
async def get_product_details(asin: str) -> str:
    """Get detailed information about a specific product."""
    return await get_product_details_tool(asin)

@mcp.tool
@track_tool_execution
async def compare_products(asins: list) -> str:
    """Compare multiple products side-by-side."""
    return await compare_products_tool(asins)

@mcp.tool
@track_tool_execution
async def get_best_in_category(
    category: str,
    max_price: int = None,
    scoring: str = "value",
    limit: int = 5
) -> str:
    """Get intelligently curated top products in a category."""
    return await get_best_in_category_tool(category, max_price, scoring, limit)

@mcp.tool
@track_tool_execution
async def get_alternative_products(
    asin: str,
    price_range: str = "similar",
    limit: int = 5
) -> str:
    """Find alternative products similar to a given product."""
    return await get_alternative_products_tool(asin, price_range, limit)

@mcp.tool
@track_tool_execution
async def analyze_reviews(asin: str) -> str:
    """Analyze customer reviews and provide insights about a product."""
    return await analyze_reviews_tool(asin)

@mcp.tool
@track_tool_execution
async def get_trending_products(category: str, limit: int = 10) -> str:
    """Get trending/popular products in a category."""
    return await get_trending_products_tool(category, limit)

# Monitoring endpoints
@mcp.tool
async def health_check() -> str:
    """Check if the MCP server is running properly."""
    health = await health_checker.check_health()
    import json
    return json.dumps(health, indent=2)

@mcp.tool
def get_metrics() -> str:
    """Get Prometheus metrics for monitoring."""
    return metrics.get_metrics_report()

# Startup tasks
async def startup():
    """Initialize server components"""
    logger.info("Initializing Amazon Shopping MCP Server...")
    
    # Start metrics server if enabled
    if settings.enable_metrics:
        start_metrics_server(settings.metrics_port)
    
    # Set initial health status
    metrics.update_server_health(True)
    
    logger.info("Server initialization complete")

# Shutdown tasks
async def shutdown():
    """Cleanup server resources"""
    logger.info("Shutting down server...")
    
    from core.cache_manager import cache_manager
    await cache_manager.close()
    
    logger.info("Server shutdown complete")

if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("🛍️  Amazon Shopping MCP Server")
    logger.info("=" * 60)
    logger.info(f"📍 Mode: {'MOCK (Development)' if settings.mock_mode else 'LIVE (Production)'}")
    logger.info(f"🌍 Marketplace: Amazon.{settings.amazon_marketplace}")
    logger.info(f"⚡ Cache: {'Redis + Memory' if settings.redis_url else 'Memory Only'}")
    logger.info(f"📊 Metrics: {'Enabled on port ' + str(settings.metrics_port) if settings.enable_metrics else 'Disabled'}")
    logger.info(f"🔧 Tools: 10 available (8 shopping + 2 monitoring)")
    logger.info("=" * 60)
    
    # Run startup tasks
    asyncio.run(startup())
    
    try:
        # For OpenAI Apps SDK deployment, use HTTP transport
        # For Claude Desktop local testing, use STDIO transport
        import sys
        if len(sys.argv) > 1 and sys.argv[1] == "--http":
            logger.info("🌐 Starting HTTP server on port 8000...")
            mcp.run(transport="http", host="0.0.0.0", port=8000, path="/mcp")
        else:
            logger.info("💻 Starting STDIO server for local testing...")
            mcp.run()
    finally:
        # Run shutdown tasks
        asyncio.run(shutdown())