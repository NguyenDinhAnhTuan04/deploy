"""
Test Suite for API Gateway Agent

This module contains comprehensive tests for the API Gateway Agent including:
- Unit tests for authentication, rate limiting, routing
- Integration tests for full request lifecycle
- Load tests for performance validation

Author: Multi-Agent System Team
Date: 2025-11-02
"""

import asyncio
import gzip
import json
import time
from datetime import datetime, timedelta
from typing import Dict, Any
from unittest.mock import Mock, patch, MagicMock, AsyncMock

import httpx
import jwt
import pytest
from fastapi.testclient import TestClient

# Import components to test
from agents.integration.api_gateway_agent import (
    APIGatewayConfig,
    TokenBucketRateLimiter,
    ResponseCache,
    CircuitBreaker,
    AuthenticationMiddleware,
    RateLimitingMiddleware,
    APIGatewayAgent,
    AuthMethod,
    RateLimitAlgorithm,
    CacheStatus,
    CircuitState,
    APIKey,
    JWTConfig,
    RouteConfig,
    create_app
)


# Test Fixtures

@pytest.fixture
def config_path():
    """Path to test configuration file"""
    return "config/api_gateway_config.yaml"


@pytest.fixture
def mock_config():
    """Mock configuration for testing"""
    return {
        'api_gateway': {
            'server': {
                'host': '0.0.0.0',
                'port': 8000,
                'workers': 1
            },
            'authentication': {
                'enabled': True,
                'methods': [
                    {
                        'type': 'api_key',
                        'header': 'X-API-Key',
                        'enabled': True,
                        'keys': [
                            {
                                'key': 'test-key-123',
                                'owner': 'test-user',
                                'description': 'Test API key',
                                'rate_limit': 100,
                                'enabled': True
                            }
                        ]
                    },
                    {
                        'type': 'jwt',
                        'enabled': True,
                        'secret': 'test-secret',
                        'algorithm': 'HS256',
                        'issuer': 'test-issuer',
                        'audience': 'test-audience',
                        'token_header': 'Authorization',
                        'token_prefix': 'Bearer',
                        'expiration': 3600
                    }
                ]
            },
            'rate_limiting': {
                'enabled': True,
                'algorithm': 'token_bucket',
                'default_limit': 100,
                'burst_size': 20,
                'storage': 'memory',
                'endpoint_limits': [
                    {
                        'path': '/api/test',
                        'method': 'POST',
                        'limit': 50
                    }
                ]
            },
            'routes': [
                {
                    'name': 'test_route',
                    'path': '/api/test',
                    'path_type': 'exact',
                    'backend': 'http://backend:8080/api/test',
                    'methods': ['GET', 'POST'],
                    'auth_required': True,
                    'timeout': 30,
                    'cache': {
                        'enabled': True,
                        'ttl': 300
                    }
                },
                {
                    'name': 'public_route',
                    'path': '/public',
                    'path_type': 'exact',
                    'backend': 'http://backend:8080/public',
                    'methods': ['GET'],
                    'auth_required': False,
                    'timeout': 30,
                    'cache': {
                        'enabled': False
                    }
                }
            ],
            'cors': {
                'enabled': True,
                'allowed_origins': ['*'],
                'allowed_methods': ['GET', 'POST', 'PATCH', 'DELETE'],
                'allowed_headers': ['*']
            },
            'caching': {
                'enabled': True,
                'default_ttl': 300,
                'max_ttl': 3600,
                'storage': 'memory',
                'compression': {
                    'enabled': True,
                    'min_size': 1024,
                    'algorithm': 'gzip',
                    'level': 6
                }
            },
            'circuit_breaker': {
                'enabled': True,
                'failure_threshold': 5,
                'recovery_timeout': 60,
                'half_open_requests': 3
            },
            'logging': {
                'level': 'INFO',
                'format': 'json',
                'output': 'stdout'
            }
        }
    }


@pytest.fixture
def gateway_config(tmp_path, mock_config):
    """Create temporary configuration file"""
    import yaml
    config_file = tmp_path / "api_gateway_config.yaml"
    with open(config_file, 'w') as f:
        yaml.dump(mock_config, f)
    return str(config_file)


# Configuration Tests

class TestAPIGatewayConfig:
    """Tests for APIGatewayConfig class"""
    
    def test_config_loads_successfully(self, config_path):
        """Test configuration file loads successfully"""
        config = APIGatewayConfig(config_path)
        assert config.config is not None
        assert 'api_gateway' in config.config
    
    def test_config_has_required_sections(self, config_path):
        """Test configuration has all required sections"""
        config = APIGatewayConfig(config_path)
        assert config.get_server_config() is not None
        assert config.get_authentication_config() is not None
        assert config.get_rate_limiting_config() is not None
        assert config.get_routes() is not None
        assert config.get_cors_config() is not None
    
    def test_env_var_expansion(self, tmp_path):
        """Test environment variable expansion in config"""
        import os
        import yaml
        
        os.environ['TEST_PORT'] = '9000'
        
        config_data = {
            'api_gateway': {
                'server': {
                    'port': '${TEST_PORT:-8000}'
                }
            }
        }
        
        config_file = tmp_path / "test_config.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(config_data, f)
        
        config = APIGatewayConfig(str(config_file))
        server_config = config.get_server_config()
        # YAML parser converts string numbers to int
        assert server_config['port'] == 9000 or server_config['port'] == '9000'
    
    def test_invalid_config_file(self):
        """Test handling of invalid configuration file"""
        with pytest.raises(FileNotFoundError):
            APIGatewayConfig("nonexistent_config.yaml")


# Rate Limiter Tests

class TestTokenBucketRateLimiter:
    """Tests for TokenBucketRateLimiter class"""
    
    def test_rate_limiter_initializes(self):
        """Test rate limiter initializes correctly"""
        config = {
            'enabled': True,
            'default_limit': 100,
            'burst_size': 20,
            'storage': 'memory'
        }
        limiter = TokenBucketRateLimiter(config)
        assert limiter.enabled is True
        assert limiter.default_limit == 100
    
    @pytest.mark.asyncio
    async def test_rate_limit_allows_request(self):
        """Test rate limiter allows request within limit"""
        config = {
            'enabled': True,
            'default_limit': 100,
            'burst_size': 20,
            'storage': 'memory'
        }
        limiter = TokenBucketRateLimiter(config)
        
        allowed, info = await limiter.check_rate_limit('test-key', 100, 'GET', '/')
        assert allowed is True
        assert info['limit'] == 100
        assert info['remaining'] > 0
    
    @pytest.mark.asyncio
    async def test_rate_limit_blocks_excessive_requests(self):
        """Test rate limiter blocks excessive requests"""
        config = {
            'enabled': True,
            'default_limit': 10,
            'burst_size': 0,
            'storage': 'memory'
        }
        limiter = TokenBucketRateLimiter(config)
        
        # Make 10 successful requests
        for i in range(10):
            allowed, info = await limiter.check_rate_limit('test-key', 10, 'GET', '/')
            assert allowed is True
        
        # 11th request should be blocked
        allowed, info = await limiter.check_rate_limit('test-key', 10, 'GET', '/')
        assert allowed is False
    
    @pytest.mark.asyncio
    async def test_rate_limit_refills_tokens(self):
        """Test rate limiter refills tokens over time"""
        config = {
            'enabled': True,
            'default_limit': 60,  # 1 per second
            'burst_size': 0,
            'storage': 'memory'
        }
        limiter = TokenBucketRateLimiter(config)
        
        # Use all tokens
        for i in range(60):
            await limiter.check_rate_limit('test-key', 60, 'GET', '/')
        
        # Wait for refill
        await asyncio.sleep(2)
        
        # Should allow requests again
        allowed, info = await limiter.check_rate_limit('test-key', 60, 'GET', '/')
        assert allowed is True
    
    @pytest.mark.asyncio
    async def test_endpoint_specific_limits(self):
        """Test endpoint-specific rate limits"""
        config = {
            'enabled': True,
            'default_limit': 100,
            'burst_size': 20,
            'storage': 'memory',
            'endpoint_limits': [
                {
                    'path': '/api/restricted',
                    'method': 'POST',
                    'limit': 10
                }
            ]
        }
        limiter = TokenBucketRateLimiter(config)
        
        # Default limit
        allowed, info = await limiter.check_rate_limit('test-key', None, 'GET', '/api/test')
        assert info['limit'] == 100
        
        # Endpoint-specific limit
        allowed, info = await limiter.check_rate_limit('test-key', None, 'POST', '/api/restricted')
        assert info['limit'] == 10


# Response Cache Tests

class TestResponseCache:
    """Tests for ResponseCache class"""
    
    def test_cache_initializes(self):
        """Test cache initializes correctly"""
        config = {
            'enabled': True,
            'default_ttl': 300,
            'max_ttl': 3600,
            'storage': 'memory',
            'compression': {
                'enabled': True,
                'min_size': 1024
            }
        }
        cache = ResponseCache(config)
        assert cache.enabled is True
        assert cache.default_ttl == 300
    
    @pytest.mark.asyncio
    async def test_cache_miss(self):
        """Test cache miss returns None"""
        config = {
            'enabled': True,
            'default_ttl': 300,
            'storage': 'memory'
        }
        cache = ResponseCache(config)
        
        route_config = {
            'cache': {
                'enabled': True,
                'ttl': 300
            }
        }
        
        response, status = await cache.get('GET', '/test', {}, {}, None, route_config)
        assert response is None
        assert status == CacheStatus.MISS
    
    @pytest.mark.asyncio
    async def test_cache_set_and_get(self):
        """Test setting and getting cached response"""
        config = {
            'enabled': True,
            'default_ttl': 300,
            'storage': 'memory',
            'compression': {
                'enabled': False
            }
        }
        cache = ResponseCache(config)
        
        route_config = {
            'cache': {
                'enabled': True,
                'ttl': 300
            }
        }
        
        # Set cache
        test_response = b'{"test": "data"}'
        await cache.set('GET', '/test', {}, {}, None, test_response, route_config)
        
        # Get cache
        response, status = await cache.get('GET', '/test', {}, {}, None, route_config)
        assert response == test_response
        assert status == CacheStatus.HIT
    
    @pytest.mark.asyncio
    async def test_cache_compression(self):
        """Test response compression in cache"""
        config = {
            'enabled': True,
            'default_ttl': 300,
            'storage': 'memory',
            'compression': {
                'enabled': True,
                'min_size': 100,
                'algorithm': 'gzip',
                'level': 6
            }
        }
        cache = ResponseCache(config)
        
        route_config = {
            'cache': {
                'enabled': True,
                'ttl': 300,
                'compress': True
            }
        }
        
        # Large response that should be compressed
        large_response = b'{"data": "' + (b'x' * 2000) + b'"}'
        await cache.set('GET', '/test', {}, {}, None, large_response, route_config)
        
        # Get cache (should be decompressed)
        response, status = await cache.get('GET', '/test', {}, {}, None, route_config)
        assert response == large_response
        assert status == CacheStatus.HIT
    
    @pytest.mark.asyncio
    async def test_cache_bypass_disabled(self):
        """Test cache bypass when disabled"""
        config = {
            'enabled': False,
            'storage': 'memory'
        }
        cache = ResponseCache(config)
        
        route_config = {
            'cache': {
                'enabled': True
            }
        }
        
        response, status = await cache.get('GET', '/test', {}, {}, None, route_config)
        assert response is None
        assert status == CacheStatus.BYPASS


# Circuit Breaker Tests

class TestCircuitBreaker:
    """Tests for CircuitBreaker class"""
    
    def test_circuit_breaker_initializes(self):
        """Test circuit breaker initializes correctly"""
        config = {
            'enabled': True,
            'failure_threshold': 5,
            'recovery_timeout': 60,
            'half_open_requests': 3
        }
        breaker = CircuitBreaker(config)
        assert breaker.enabled is True
        assert breaker.failure_threshold == 5
    
    @pytest.mark.asyncio
    async def test_circuit_closed_allows_requests(self):
        """Test closed circuit allows requests"""
        config = {
            'enabled': True,
            'failure_threshold': 5,
            'recovery_timeout': 60
        }
        breaker = CircuitBreaker(config)
        
        async def success_func():
            return "success"
        
        result = await breaker.call('http://backend', success_func)
        assert result == "success"
    
    @pytest.mark.asyncio
    async def test_circuit_opens_on_failures(self):
        """Test circuit opens after threshold failures"""
        config = {
            'enabled': True,
            'failure_threshold': 3,
            'recovery_timeout': 60
        }
        breaker = CircuitBreaker(config)
        
        async def failure_func():
            raise Exception("Backend error")
        
        # Cause 3 failures
        for i in range(3):
            with pytest.raises(Exception):
                await breaker.call('http://backend', failure_func)
        
        # Circuit should now be open
        state = breaker._get_backend_state('http://backend')
        assert state.state == CircuitState.OPEN
        
        # Next call should fail immediately with circuit open error
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await breaker.call('http://backend', failure_func)
        assert exc_info.value.status_code == 503
    
    @pytest.mark.asyncio
    async def test_circuit_half_open_recovery(self):
        """Test circuit enters half-open state after timeout"""
        config = {
            'enabled': True,
            'failure_threshold': 2,
            'recovery_timeout': 1,  # 1 second
            'half_open_requests': 2
        }
        breaker = CircuitBreaker(config)
        
        async def failure_func():
            raise Exception("Backend error")
        
        # Open circuit
        for i in range(2):
            with pytest.raises(Exception):
                await breaker.call('http://backend', failure_func)
        
        # Wait for recovery timeout
        await asyncio.sleep(1.5)
        
        # Successful request should close circuit
        async def success_func():
            return "success"
        
        result = await breaker.call('http://backend', success_func)
        assert result == "success"
        
        # Make another successful request
        result = await breaker.call('http://backend', success_func)
        assert result == "success"
        
        # Circuit should be closed now
        state = breaker._get_backend_state('http://backend')
        assert state.state == CircuitState.CLOSED


# Authentication Tests

class TestAuthentication:
    """Tests for authentication middleware"""
    
    def test_api_key_validation(self, gateway_config):
        """Test API key authentication"""
        config = APIGatewayConfig(gateway_config)
        
        # Create mock app and middleware
        from fastapi import FastAPI, Request
        app = FastAPI()
        
        @app.get("/test")
        async def test_endpoint(request: Request):
            return {"authenticated": getattr(request.state, 'authenticated', False)}
        
        app.add_middleware(AuthenticationMiddleware, config=config)
        
        client = TestClient(app)
        
        # Request with valid API key
        response = client.get("/test", headers={"X-API-Key": "test-key-123"})
        assert response.status_code == 200
        data = response.json()
        assert data['authenticated'] is True
    
    def test_jwt_validation(self, gateway_config):
        """Test JWT authentication"""
        config = APIGatewayConfig(gateway_config)
        
        # Generate valid JWT
        secret = "test-secret"
        payload = {
            'sub': 'test-user',
            'iss': 'test-issuer',
            'aud': 'test-audience',
            'exp': datetime.utcnow() + timedelta(hours=1),
            'iat': datetime.utcnow()
        }
        token = jwt.encode(payload, secret, algorithm='HS256')
        
        # Create mock app and middleware
        from fastapi import FastAPI, Request
        app = FastAPI()
        
        @app.get("/test")
        async def test_endpoint(request: Request):
            return {"authenticated": getattr(request.state, 'authenticated', False)}
        
        app.add_middleware(AuthenticationMiddleware, config=config)
        
        client = TestClient(app)
        
        # Request with valid JWT
        response = client.get("/test", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200
        data = response.json()
        assert data['authenticated'] is True
    
    def test_invalid_credentials(self, gateway_config):
        """Test authentication with invalid credentials"""
        config = APIGatewayConfig(gateway_config)
        
        from fastapi import FastAPI, Request
        app = FastAPI()
        
        @app.get("/test")
        async def test_endpoint(request: Request):
            return {"authenticated": getattr(request.state, 'authenticated', False)}
        
        app.add_middleware(AuthenticationMiddleware, config=config)
        
        client = TestClient(app)
        
        # Request without credentials
        response = client.get("/test")
        assert response.status_code == 200
        data = response.json()
        assert data['authenticated'] is False


# Integration Tests

class TestAPIGatewayIntegration:
    """Integration tests for API Gateway"""
    
    @pytest.mark.asyncio
    async def test_gateway_initializes(self, gateway_config):
        """Test gateway initializes correctly"""
        gateway = APIGatewayAgent(gateway_config)
        assert gateway.app is not None
        assert len(gateway.routes) > 0
        await gateway.close()
    
    def test_authenticated_request_flow(self, gateway_config):
        """Test complete authenticated request flow"""
        gateway = APIGatewayAgent(gateway_config)
        client = TestClient(gateway.app)
        
        # Mock backend response
        with patch.object(gateway.http_client, 'request', new_callable=AsyncMock) as mock_request:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.content = b'{"result": "success"}'
            mock_response.headers = {'content-type': 'application/json'}
            mock_request.return_value = mock_response
            
            # Make authenticated request
            response = client.get(
                "/api/test",
                headers={"X-API-Key": "test-key-123"}
            )
            
            assert response.status_code == 200
            assert 'X-RateLimit-Limit' in response.headers
            assert 'X-Cache-Status' in response.headers
    
    def test_unauthenticated_request_rejected(self, gateway_config):
        """Test unauthenticated request is rejected"""
        gateway = APIGatewayAgent(gateway_config)
        client = TestClient(gateway.app)
        
        # Request to protected route without auth
        response = client.get("/api/test")
        assert response.status_code == 401
    
    def test_public_route_accessible(self, gateway_config):
        """Test public route is accessible without auth"""
        gateway = APIGatewayAgent(gateway_config)
        client = TestClient(gateway.app)
        
        with patch.object(gateway.http_client, 'request', new_callable=AsyncMock) as mock_request:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.content = b'{"data": "public"}'
            mock_response.headers = {'content-type': 'application/json'}
            mock_request.return_value = mock_response
            
            # Request to public route
            response = client.get("/public")
            assert response.status_code == 200
    
    def test_rate_limiting_enforcement(self, gateway_config):
        """Test rate limiting is enforced"""
        gateway = APIGatewayAgent(gateway_config)
        client = TestClient(gateway.app)
        
        # Set very low rate limit
        gateway.rate_limiter.default_limit = 5
        
        with patch.object(gateway.http_client, 'request', new_callable=AsyncMock) as mock_request:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.content = b'{"result": "success"}'
            mock_response.headers = {'content-type': 'application/json'}
            mock_request.return_value = mock_response
            
            # Make 5 successful requests
            for i in range(5):
                response = client.get(
                    "/api/test",
                    headers={"X-API-Key": "test-key-123"}
                )
                assert response.status_code == 200
            
            # 6th request should be rate limited
            response = client.get(
                "/api/test",
                headers={"X-API-Key": "test-key-123"}
            )
            assert response.status_code == 429
            assert 'Retry-After' in response.headers
    
    def test_response_caching(self, gateway_config):
        """Test response caching works"""
        gateway = APIGatewayAgent(gateway_config)
        client = TestClient(gateway.app)
        
        call_count = 0
        
        async def mock_request_func(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.content = b'{"result": "cached"}'
            mock_response.headers = {'content-type': 'application/json'}
            return mock_response
        
        with patch.object(gateway.http_client, 'request', new_callable=AsyncMock, side_effect=mock_request_func):
            # First request - cache miss
            response1 = client.get(
                "/api/test",
                headers={"X-API-Key": "test-key-123"}
            )
            assert response1.status_code == 200
            assert response1.headers.get('X-Cache-Status') == 'MISS'
            assert call_count == 1
            
            # Second request - cache hit
            response2 = client.get(
                "/api/test",
                headers={"X-API-Key": "test-key-123"}
            )
            assert response2.status_code == 200
            assert response2.headers.get('X-Cache-Status') == 'HIT'
            assert call_count == 1  # Backend not called again
    
    def test_route_not_found(self, gateway_config):
        """Test 404 for non-existent route"""
        gateway = APIGatewayAgent(gateway_config)
        client = TestClient(gateway.app)
        
        response = client.get("/nonexistent")
        assert response.status_code == 404


# Load Tests

class TestAPIGatewayLoad:
    """Load tests for API Gateway performance"""
    
    @pytest.mark.asyncio
    async def test_high_volume_requests(self, gateway_config):
        """Test gateway handles high volume requests"""
        gateway = APIGatewayAgent(gateway_config)
        
        # Disable rate limiting for load test
        gateway.rate_limiter.enabled = False
        
        client = TestClient(gateway.app)
        
        async def mock_request_func(*args, **kwargs):
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.content = b'{"result": "success"}'
            mock_response.headers = {'content-type': 'application/json'}
            return mock_response
        
        with patch.object(gateway.http_client, 'request', new_callable=AsyncMock, side_effect=mock_request_func):
            start_time = time.time()
            
            # Make 1000 requests
            for i in range(1000):
                response = client.get(
                    "/public"
                )
                assert response.status_code == 200
            
            duration = time.time() - start_time
            
            # Should handle 1000 requests in reasonable time (< 10 seconds)
            assert duration < 10.0
            
            # Calculate throughput
            throughput = 1000 / duration
            print(f"Throughput: {throughput:.2f} requests/second")
            
            await gateway.close()
    
    @pytest.mark.asyncio
    async def test_concurrent_requests(self, gateway_config):
        """Test gateway handles concurrent requests"""
        gateway = APIGatewayAgent(gateway_config)
        gateway.rate_limiter.enabled = False
        
        async def mock_request_func(*args, **kwargs):
            await asyncio.sleep(0.01)  # Simulate backend delay
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.content = b'{"result": "success"}'
            mock_response.headers = {'content-type': 'application/json'}
            return mock_response
        
        with patch.object(gateway.http_client, 'request', new_callable=AsyncMock, side_effect=mock_request_func):
            client = TestClient(gateway.app)
            
            async def make_request():
                return client.get("/public")
            
            start_time = time.time()
            
            # Make 100 concurrent requests
            tasks = [make_request() for _ in range(100)]
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            
            duration = time.time() - start_time
            
            # Count successful responses
            success_count = sum(1 for r in responses if not isinstance(r, Exception) and r.status_code == 200)
            
            # Most requests should succeed
            assert success_count >= 95
            
            # Should complete in reasonable time (< 5 seconds with concurrency)
            assert duration < 5.0
            
            await gateway.close()
    
    @pytest.mark.asyncio
    async def test_cache_performance(self, gateway_config):
        """Test cache improves performance"""
        gateway = APIGatewayAgent(gateway_config)
        gateway.rate_limiter.enabled = False
        
        client = TestClient(gateway.app)
        
        backend_calls = 0
        
        async def mock_request_func(*args, **kwargs):
            nonlocal backend_calls
            backend_calls += 1
            await asyncio.sleep(0.1)  # Simulate slow backend
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.content = b'{"result": "success"}'
            mock_response.headers = {'content-type': 'application/json'}
            return mock_response
        
        with patch.object(gateway.http_client, 'request', new_callable=AsyncMock, side_effect=mock_request_func):
            # First request - cache miss (slow)
            start_time = time.time()
            response1 = client.get("/api/test", headers={"X-API-Key": "test-key-123"})
            first_duration = time.time() - start_time
            
            assert response1.status_code == 200
            assert backend_calls == 1
            
            # Second request - cache hit (fast)
            start_time = time.time()
            response2 = client.get("/api/test", headers={"X-API-Key": "test-key-123"})
            second_duration = time.time() - start_time
            
            assert response2.status_code == 200
            assert backend_calls == 1  # No additional backend call
            
            # Cached response should be much faster
            assert second_duration < first_duration * 0.1
            
            await gateway.close()


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
