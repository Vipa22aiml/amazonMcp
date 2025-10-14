"""Marketplace-specific configurations"""

MARKETPLACE_CONFIG = {
    "US": {
        "host": "webservices.amazon.com",
        "region": "us-east-1",
        "currency": "USD",
        "url_domain": "amazon.com"
    },
    "IN": {
        "host": "webservices.amazon.in",
        "region": "eu-west-1",
        "currency": "INR",
        "url_domain": "amazon.in"
    },
    "UK": {
        "host": "webservices.amazon.co.uk",
        "region": "eu-west-1",
        "currency": "GBP",
        "url_domain": "amazon.co.uk"
    },
    "JP": {
        "host": "webservices.amazon.co.jp",
        "region": "us-west-2",
        "currency": "JPY",
        "url_domain": "amazon.co.jp"
    }
}

def get_marketplace_config(marketplace: str) -> dict:
    """Get configuration for specific marketplace"""
    return MARKETPLACE_CONFIG.get(marketplace, MARKETPLACE_CONFIG["US"])