"""Circuit breaker pattern for PA API resilience"""

from datetime import datetime, timedelta
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class CircuitState(Enum):
    CLOSED = "closed"  # Normal operation
    OPEN = "open"      # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if recovered

class CircuitBreaker:
    """
    Circuit breaker to prevent cascading failures
    
    - Opens after N consecutive failures
    - Stays open for timeout period
    - Half-opens to test recovery
    """
    
    def __init__(self, failure_threshold: int, timeout: int):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = None
    
    def allow_request(self) -> bool:
        """Check if request should be allowed"""
        if self.state == CircuitState.CLOSED:
            return True
        
        if self.state == CircuitState.OPEN:
            # Check if timeout has passed
            if self.last_failure_time:
                elapsed = (datetime.now() - self.last_failure_time).total_seconds()
                if elapsed >= self.timeout:
                    logger.info("Circuit breaker entering HALF_OPEN state")
                    self.state = CircuitState.HALF_OPEN
                    return True
            return False
        
        if self.state == CircuitState.HALF_OPEN:
            return True
        
        return False
    
    def record_success(self):
        """Record successful request"""
        if self.state == CircuitState.HALF_OPEN:
            logger.info("Circuit breaker closing after successful request")
            self.state = CircuitState.CLOSED
            self.failure_count = 0
    
    def record_failure(self):
        """Record failed request"""
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        
        if self.state == CircuitState.HALF_OPEN:
            logger.warning("Circuit breaker opening again after failure in HALF_OPEN")
            self.state = CircuitState.OPEN
        
        if self.failure_count >= self.failure_threshold and self.state == CircuitState.CLOSED:
            logger.error(f"Circuit breaker opening after {self.failure_count} failures")
            self.state = CircuitState.OPEN
    
    def get_state(self) -> dict:
        """Get current circuit breaker state"""
        return {
            'state': self.state.value,
            'failure_count': self.failure_count,
            'failure_threshold': self.failure_threshold,
        }
