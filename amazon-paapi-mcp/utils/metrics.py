"""
Production-grade metrics collection using Prometheus

Tracks:
- API call success/failure rates
- Response latencies
- Cache hit/miss ratios
- Rate limit usage
- Tool invocation counts
"""

from prometheus_client import (
    Counter, 
    Histogram, 
    Gauge, 
    CollectorRegistry,
    start_http_server,
    generate_latest
)
import logging
import time
from functools import wraps
from typing import Callable

logger = logging.getLogger(__name__)

# Create metrics registry
registry = CollectorRegistry()

# API Call Metrics
api_calls_total = Counter(
    'amazon_paapi_calls_total',
    'Total number of Amazon PA API calls',
    ['operation', 'status'],
    registry=registry
)

api_call_duration = Histogram(
    'amazon_paapi_call_duration_seconds',
    'Duration of Amazon PA API calls',
    ['operation'],
    registry=registry,
    buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
)

# Cache Metrics
cache_operations_total = Counter(
    'cache_operations_total',
    'Total cache operations',
    ['operation', 'level', 'result'],
    registry=registry
)

cache_hit_ratio = Gauge(
    'cache_hit_ratio',
    'Cache hit ratio percentage',
    ['level'],
    registry=registry
)

# Rate Limiter Metrics
rate_limit_tokens = Gauge(
    'rate_limit_tokens_available',
    'Available rate limit tokens',
    registry=registry
)

rate_limit_daily_usage = Gauge(
    'rate_limit_daily_requests',
    'Daily requests used',
    registry=registry
)

rate_limit_rejections = Counter(
    'rate_limit_rejections_total',
    'Total requests rejected due to rate limiting',
    registry=registry
)

# Tool Invocation Metrics
tool_invocations_total = Counter(
    'mcp_tool_invocations_total',
    'Total MCP tool invocations',
    ['tool_name', 'status'],
    registry=registry
)

tool_duration = Histogram(
    'mcp_tool_duration_seconds',
    'Duration of MCP tool execution',
    ['tool_name'],
    registry=registry,
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0]
)

# Circuit Breaker Metrics
circuit_breaker_state = Gauge(
    'circuit_breaker_state',
    'Circuit breaker state (0=closed, 1=open, 2=half_open)',
    registry=registry
)

circuit_breaker_failures = Counter(
    'circuit_breaker_failures_total',
    'Total circuit breaker failures',
    registry=registry
)

# Server Health Metrics
server_health = Gauge(
    'server_health',
    'Server health status (1=healthy, 0=unhealthy)',
    registry=registry
)

active_requests = Gauge(
    'active_requests',
    'Number of currently active requests',
    registry=registry
)

class MetricsCollector:
    """Central metrics collection and reporting"""
    
    def __init__(self):
        self._cache_hits = {'memory': 0, 'redis': 0}
        self._cache_misses = {'memory': 0, 'redis': 0}
        
        # Set initial server health
        server_health.set(1)
    
    def record_api_call(self, operation: str, status: str):
        """Record an API call to PA API"""
        api_calls_total.labels(operation=operation, status=status).inc()
        
        if status == "error":
            logger.warning(f"API call failed: {operation}")
    
    def record_api_duration(self, operation: str, duration: float):
        """Record API call duration"""
        api_call_duration.labels(operation=operation).observe(duration)
    
    def record_cache_operation(self, operation: str, level: str, result: str):
        """
        Record cache operation
        
        Args:
            operation: 'get', 'set', 'delete'
            level: 'memory', 'redis'
            result: 'hit', 'miss', 'success', 'error'
        """
        cache_operations_total.labels(
            operation=operation, 
            level=level, 
            result=result
        ).inc()
        
        # Track hit/miss for ratio calculation
        if operation == 'get':
            if result == 'hit':
                self._cache_hits[level] += 1
            elif result == 'miss':
                self._cache_misses[level] += 1
            
            # Update hit ratio
            total = self._cache_hits[level] + self._cache_misses[level]
            if total > 0:
                ratio = (self._cache_hits[level] / total) * 100
                cache_hit_ratio.labels(level=level).set(ratio)
    
    def update_rate_limit_stats(self, tokens: float, daily_used: int):
        """Update rate limiter metrics"""
        rate_limit_tokens.set(tokens)
        rate_limit_daily_usage.set(daily_used)
    
    def record_rate_limit_rejection(self):
        """Record a rate limit rejection"""
        rate_limit_rejections.inc()
    
    def record_tool_invocation(self, tool_name: str, status: str):
        """Record MCP tool invocation"""
        tool_invocations_total.labels(tool_name=tool_name, status=status).inc()
    
    def record_tool_duration(self, tool_name: str, duration: float):
        """Record tool execution duration"""
        tool_duration.labels(tool_name=tool_name).observe(duration)
    
    def update_circuit_breaker_state(self, state: str):
        """
        Update circuit breaker state
        
        Args:
            state: 'closed', 'open', 'half_open'
        """
        state_map = {'closed': 0, 'open': 1, 'half_open': 2}
        circuit_breaker_state.set(state_map.get(state, 0))
    
    def record_circuit_breaker_failure(self):
        """Record circuit breaker failure"""
        circuit_breaker_failures.inc()
    
    def update_server_health(self, healthy: bool):
        """Update server health status"""
        server_health.set(1 if healthy else 0)
    
    def increment_active_requests(self):
        """Increment active request counter"""
        active_requests.inc()
    
    def decrement_active_requests(self):
        """Decrement active request counter"""
        active_requests.dec()
    
    def get_metrics_report(self) -> str:
        """Get current metrics as Prometheus text format"""
        return generate_latest(registry).decode('utf-8')

# Singleton instance
metrics = MetricsCollector()

def track_tool_execution(func: Callable):
    """Decorator to automatically track tool execution metrics"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        tool_name = func.__name__.replace('_tool', '')
        
        metrics.increment_active_requests()
        start_time = time.time()
        
        try:
            result = await func(*args, **kwargs)
            
            # Track success
            duration = time.time() - start_time
            metrics.record_tool_invocation(tool_name, 'success')
            metrics.record_tool_duration(tool_name, duration)
            
            return result
            
        except Exception as e:
            # Track failure
            duration = time.time() - start_time
            metrics.record_tool_invocation(tool_name, 'error')
            metrics.record_tool_duration(tool_name, duration)
            
            logger.error(f"Tool {tool_name} failed: {str(e)}")
            raise
            
        finally:
            metrics.decrement_active_requests()
    
    return wrapper

def start_metrics_server(port: int = 9090):
    """Start Prometheus metrics HTTP server"""
    try:
        start_http_server(port, registry=registry)
        logger.info(f"Metrics server started on port {port}")
    except Exception as e:
        logger.error(f"Failed to start metrics server: {e}")
