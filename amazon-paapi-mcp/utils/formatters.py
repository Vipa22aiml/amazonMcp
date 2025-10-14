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
