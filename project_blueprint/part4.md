## Part 4: Monitoring, Metrics & Production Readiness

### Step 15: Prometheus Metrics Implementation

**utils/metrics.py**:
```python
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
```

### Step 16: Enhanced Core Components with Metrics

**Update core/paapi_client.py** (add metrics tracking):
```python
# Add these imports at the top
from utils.metrics import metrics
import time

# In PAAPIClient.search_items method, wrap API call:
async def search_items(self, ...):
    # ... existing code ...
    
    start_time = time.time()
    
    try:
        # ... existing API call code ...
        
        # Record metrics
        duration = time.time() - start_time
        metrics.record_api_call("search_items", "success")
        metrics.record_api_duration("search_items", duration)
        
        # ... rest of existing code ...
        
    except ApiException as e:
        duration = time.time() - start_time
        metrics.record_api_call("search_items", "error")
        metrics.record_api_duration("search_items", duration)
        # ... rest of error handling ...
```

**Update core/cache_manager.py** (add metrics tracking):
```python
# Add import
from utils.metrics import metrics

# In CacheManager.get method:
async def get(self, key: str, namespace: str = "default") -> Optional[Any]:
    cache_key = self._generate_key(key, namespace)
    
    # Try L1 (memory) first
    if cache_key in self.memory_cache:
        metrics.record_cache_operation('get', 'memory', 'hit')
        return self.memory_cache[cache_key]
    
    metrics.record_cache_operation('get', 'memory', 'miss')
    
    # Try L2 (Redis)
    if self.redis_client:
        try:
            value = await self.redis_client.get(cache_key)
            if value:
                metrics.record_cache_operation('get', 'redis', 'hit')
                # ... rest of code ...
            else:
                metrics.record_cache_operation('get', 'redis', 'miss')
        except Exception as e:
            metrics.record_cache_operation('get', 'redis', 'error')
            # ... rest of error handling ...
```

**Update core/rate_limiter.py** (add metrics tracking):
```python
# Add import
from utils.metrics import metrics

# In RateLimiter.acquire method:
async def acquire(self) -> bool:
    async with self.lock:
        # ... existing refill code ...
        
        # Update metrics
        metrics.update_rate_limit_stats(self.tokens, self.daily_requests)
        
        # Check limits
        if self.daily_requests >= self.max_per_day:
            metrics.record_rate_limit_rejection()
            return False
        
        if self.tokens < 1.0:
            metrics.record_rate_limit_rejection()
            return False
        
        # ... rest of code ...
```

**Update core/circuit_breaker.py** (add metrics tracking):
```python
# Add import
from utils.metrics import metrics

# In CircuitBreaker methods:
def record_success(self):
    if self.state == CircuitState.HALF_OPEN:
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        metrics.update_circuit_breaker_state('closed')

def record_failure(self):
    self.failure_count += 1
    metrics.record_circuit_breaker_failure()
    
    if self.state == CircuitState.HALF_OPEN:
        self.state = CircuitState.OPEN
        metrics.update_circuit_breaker_state('open')
    
    if self.failure_count >= self.failure_threshold and self.state == CircuitState.CLOSED:
        self.state = CircuitState.OPEN
        metrics.update_circuit_breaker_state('open')
```

### Step 17: Structured Logging

**utils/logger.py**:
```python
"""
Structured logging configuration for production
"""

import logging
import sys
import json
from datetime import datetime
from typing import Any, Dict

class StructuredLogger(logging.Formatter):
    """JSON structured logging formatter"""
    
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }
        
        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        # Add extra fields
        if hasattr(record, 'extra'):
            log_data.update(record.extra)
        
        return json.dumps(log_data)

def setup_logging(level: str = "INFO", structured: bool = False):
    """
    Configure application logging
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        structured: Use JSON structured logging for production
    """
    log_level = getattr(logging, level.upper(), logging.INFO)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    
    # Set formatter
    if structured:
        formatter = StructuredLogger()
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # Suppress noisy third-party loggers
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('boto3').setLevel(logging.WARNING)
    logging.getLogger('botocore').setLevel(logging.WARNING)
    
    logging.info(f"Logging configured: level={level}, structured={structured}")
```

### Step 18: Health Check Endpoint

**utils/health.py**:
```python
"""
Comprehensive health check for production monitoring
"""

from typing import Dict, Any
import logging
from datetime import datetime

from config.settings import settings
from core.paapi_client import paapi_client
from core.cache_manager import cache_manager

logger = logging.getLogger(__name__)

class HealthChecker:
    """Production health check system"""
    
    async def check_health(self) -> Dict[str, Any]:
        """
        Perform comprehensive health check
        
        Returns:
            Health status with component details
        """
        health_status = {
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'components': {}
        }
        
        # Check API client
        api_status = await self._check_api_client()
        health_status['components']['amazon_paapi'] = api_status
        
        # Check cache
        cache_status = await self._check_cache()
        health_status['components']['cache'] = cache_status
        
        # Check rate limiter
        rate_limiter_status = self._check_rate_limiter()
        health_status['components']['rate_limiter'] = rate_limiter_status
        
        # Determine overall status
        unhealthy_components = [
            name for name, comp in health_status['components'].items()
            if comp['status'] != 'healthy'
        ]
        
        if unhealthy_components:
            health_status['status'] = 'degraded' if len(unhealthy_components) == 1 else 'unhealthy'
            health_status['unhealthy_components'] = unhealthy_components
        
        return health_status
    
    async def _check_api_client(self) -> Dict[str, Any]:
        """Check Amazon PA API client status"""
        if settings.mock_mode:
            return {
                'status': 'healthy',
                'mode': 'mock',
                'message': 'Running in mock mode for development'
            }
        
        try:
            # Check circuit breaker state
            circuit_state = paapi_client.circuit_breaker.get_state()
            
            if circuit_state['state'] == 'open':
                return {
                    'status': 'unhealthy',
                    'mode': 'production',
                    'circuit_breaker': circuit_state,
                    'message': 'Circuit breaker is open due to failures'
                }
            
            return {
                'status': 'healthy',
                'mode': 'production',
                'circuit_breaker': circuit_state,
                'message': 'API client operational'
            }
            
        except Exception as e:
            logger.error(f"API health check failed: {e}")
            return {
                'status': 'unhealthy',
                'error': str(e)
            }
    
    async def _check_cache(self) -> Dict[str, Any]:
        """Check cache system status"""
        try:
            # Test cache write/read
            test_key = "__health_check__"
            test_value = {"timestamp": datetime.utcnow().isoformat()}
            
            await cache_manager.set(test_key, test_value, namespace="health")
            retrieved = await cache_manager.get(test_key, namespace="health")
            
            if retrieved:
                await cache_manager.delete(test_key, namespace="health")
                
                return {
                    'status': 'healthy',
                    'message': 'Cache operational',
                    'redis_available': cache_manager.redis_client is not None
                }
            else:
                return {
                    'status': 'degraded',
                    'message': 'Cache read failed',
                    'redis_available': cache_manager.redis_client is not None
                }
                
        except Exception as e:
            logger.error(f"Cache health check failed: {e}")
            return {
                'status': 'degraded',
                'message': 'Cache error - using memory fallback',
                'error': str(e)
            }
    
    def _check_rate_limiter(self) -> Dict[str, Any]:
        """Check rate limiter status"""
        try:
            stats = paapi_client.rate_limiter.get_stats()
            
            # Check if approaching limits
            daily_usage_pct = (stats['daily_requests_used'] / stats['daily_requests_limit']) * 100
            
            if daily_usage_pct > 90:
                status = 'warning'
                message = f"Daily limit at {daily_usage_pct:.1f}%"
            elif daily_usage_pct > 95:
                status = 'critical'
                message = f"Daily limit critically high at {daily_usage_pct:.1f}%"
            else:
                status = 'healthy'
                message = f"Rate limits normal ({daily_usage_pct:.1f}% used)"
            
            return {
                'status': status,
                'message': message,
                'stats': stats
            }
            
        except Exception as e:
            logger.error(f"Rate limiter health check failed: {e}")
            return {
                'status': 'unknown',
                'error': str(e)
            }

# Singleton instance
health_checker = HealthChecker()
```

### Step 19: Update Server with Monitoring

**Update server.py** with metrics and health endpoints:
```python
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
```

### Step 20: Monitoring Dashboard Configuration

**monitoring/grafana-dashboard.json** (Grafana dashboard for metrics):
```json
{
  "dashboard": {
    "title": "Amazon MCP Server Monitoring",
    "panels": [
      {
        "title": "API Calls per Minute",
        "targets": [
          {
            "expr": "rate(amazon_paapi_calls_total[1m])"
          }
        ]
      },
      {
        "title": "API Success Rate",
        "targets": [
          {
            "expr": "sum(rate(amazon_paapi_calls_total{status='success'}[5m])) / sum(rate(amazon_paapi_calls_total[5m])) * 100"
          }
        ]
      },
      {
        "title": "Cache Hit Ratio",
        "targets": [
          {
            "expr": "cache_hit_ratio"
          }
        ]
      },
      {
        "title": "Rate Limit Usage",
        "targets": [
          {
            "expr": "rate_limit_daily_requests"
          }
        ]
      },
      {
        "title": "Tool Invocation Rate",
        "targets": [
          {
            "expr": "rate(mcp_tool_invocations_total[1m])"
          }
        ]
      },
      {
        "title": "P95 Response Time",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(mcp_tool_duration_seconds_bucket[5m]))"
          }
        ]
      }
    ]
  }
}
```

**monitoring/alerts.yml** (Prometheus alerting rules):
```yaml
groups:
  - name: amazon_mcp_alerts
    interval: 30s
    rules:
      - alert: HighErrorRate
        expr: rate(amazon_paapi_calls_total{status="error"}[5m]) > 0.1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High PA API error rate detected"
          description: "Error rate is {{ $value }} per second"
      
      - alert: RateLimitApproaching
        expr: rate_limit_daily_requests > 8000
        for: 1m
        labels:
          severity: warning
        annotations:
          summary: "Daily rate limit approaching"
          description: "Used {{ $value }} of 8640 daily requests"
      
      - alert: CircuitBreakerOpen
        expr: circuit_breaker_state == 1
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Circuit breaker is OPEN"
          description: "API calls are being blocked due to failures"
      
      - alert: LowCacheHitRatio
        expr: cache_hit_ratio < 50
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Cache hit ratio is low"
          description: "Cache hit ratio is {{ $value }}%"
```

This completes Part 4 with production-grade monitoring, metrics collection, structured logging, health checks, and alerting configuration. Your MCP server is now fully observable and production-ready!

Would you like Part 5 (Deployment to Railway/Render + Docker configuration)?