"""Token bucket rate limiter for PA API throttling"""

import asyncio
from datetime import datetime, timedelta
from typing import Optional
import logging

logger = logging.getLogger(__name__)

class RateLimiter:
    """
    Token bucket rate limiter
    
    Enforces:
    - Max requests per second (TPS limit)
    - Max requests per day (TPD limit)
    """
    
    def __init__(self, max_per_second: float, max_per_day: int):
        self.max_per_second = max_per_second
        self.max_per_day = max_per_day
        
        # Per-second tracking
        self.tokens = max_per_second
        self.last_refill = datetime.now()
        
        # Per-day tracking
        self.daily_requests = 0
        self.daily_reset = datetime.now() + timedelta(days=1)
        
        self.lock = asyncio.Lock()
    
    async def acquire(self) -> bool:
        """
        Acquire permission to make an API request
        
        Returns:
            True if request allowed, False if rate limited
        """
        async with self.lock:
            # Refill tokens based on time passed
            now = datetime.now()
            time_passed = (now - self.last_refill).total_seconds()
            self.tokens = min(
                self.max_per_second,
                self.tokens + time_passed * self.max_per_second
            )
            self.last_refill = now
            
            # Reset daily counter if needed
            if now >= self.daily_reset:
                self.daily_requests = 0
                self.daily_reset = now + timedelta(days=1)
                logger.info("Daily rate limit counter reset")
            
            # Check daily limit
            if self.daily_requests >= self.max_per_day:
                logger.warning(f"Daily rate limit reached: {self.daily_requests}/{self.max_per_day}")
                return False
            
            # Check per-second limit
            if self.tokens < 1.0:
                logger.warning("Per-second rate limit exceeded")
                return False
            
            # Consume token
            self.tokens -= 1.0
            self.daily_requests += 1
            
            return True
    
    def get_stats(self) -> dict:
        """Get current rate limit statistics"""
        return {
            'tokens_available': self.tokens,
            'daily_requests_used': self.daily_requests,
            'daily_requests_limit': self.max_per_day,
            'daily_reset_in': (self.daily_reset - datetime.now()).total_seconds(),
        }
