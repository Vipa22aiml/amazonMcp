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
