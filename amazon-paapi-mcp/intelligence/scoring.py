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
