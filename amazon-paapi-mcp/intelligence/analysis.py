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
