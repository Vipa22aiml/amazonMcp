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
