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
