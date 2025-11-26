"""
Tests for Health Check Agent

Comprehensive test suite covering:
- Configuration loading
- Service checks (HTTP, TCP, Cypher, SPARQL, Kafka)
- Data quality checks (count, age, validation)
- Performance checks (timing)
- Status aggregation
- Alert triggering
- Prometheus metrics

Author: Builder Layer Development Team
Version: 1.0.0
"""

import json
import pytest
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import sys
sys.path.append(str(Path(__file__).parent.parent.parent))

from agents.monitoring.health_check_agent import (
    HealthCheckConfig,
    ServiceChecker,
    DataQualityChecker,
    PerformanceChecker,
    HealthAggregator,
    AlertManager,
    PrometheusExporter,
    HealthCheckAgent
)


# Test fixtures

@pytest.fixture
def sample_config(tmp_path):
    """Create sample configuration file."""
    config = {
        'health_check': {
            'interval': 60,
            'checks': [
                {
                    'name': 'test_http',
                    'type': 'http',
                    'enabled': True,
                    'url': 'http://localhost:8080/health',
                    'timeout': 5,
                    'expected_status': 200,
                    'critical': True
                },
                {
                    'name': 'test_tcp',
                    'type': 'tcp',
                    'enabled': True,
                    'host': 'localhost',
                    'port': 7687,
                    'timeout': 5,
                    'critical': True
                }
            ],
            'data_quality_checks': [
                {
                    'name': 'test_count',
                    'type': 'cypher_count',
                    'enabled': False,
                    'query': 'MATCH (c:Camera) RETURN count(c) as count',
                    'threshold': {'min': 100},
                    'critical': True
                }
            ],
            'performance_checks': [
                {
                    'name': 'test_timing',
                    'type': 'http_timing',
                    'enabled': True,
                    'url': 'http://localhost:8080/api',
                    'threshold': {'max': 1000},
                    'critical': False
                }
            ],
            'alerting': {
                'enabled': True,
                'triggers': {
                    'on_state_change': True
                },
                'channels': [
                    {
                        'type': 'webhook',
                        'enabled': True,
                        'url': 'http://localhost:8080/alert',
                        'payload': {
                            'status': '{{status}}',
                            'message': '{{description}}'
                        }
                    }
                ],
                'rate_limit': {
                    'enabled': True,
                    'cooldown_seconds': 60
                }
            },
            'prometheus': {
                'enabled': False
            },
            'api': {
                'host': '0.0.0.0',
                'port': 8082
            },
            'status': {
                'rules': [
                    {'condition': 'all_critical_ok', 'status': 'GREEN'},
                    {'condition': 'any_critical_failed', 'status': 'RED'}
                ]
            }
        }
    }
    
    config_path = tmp_path / 'health_check_config.yaml'
    import yaml
    with open(config_path, 'w') as f:
        yaml.dump(config, f)
    
    return str(config_path)


# Configuration Tests

class TestHealthCheckConfig:
    """Test configuration loading."""
    
    def test_load_config(self, sample_config):
        """Test loading configuration from YAML."""
        config = HealthCheckConfig(sample_config)
        
        assert config.config is not None
        assert 'health_check' in config.config
    
    def test_get_checks(self, sample_config):
        """Test getting service checks."""
        config = HealthCheckConfig(sample_config)
        checks = config.get_checks()
        
        assert len(checks) == 2
        assert checks[0]['name'] == 'test_http'
        assert checks[1]['name'] == 'test_tcp'
    
    def test_get_data_quality_checks(self, sample_config):
        """Test getting data quality checks."""
        config = HealthCheckConfig(sample_config)
        checks = config.get_data_quality_checks()
        
        assert len(checks) == 1
        assert checks[0]['name'] == 'test_count'
    
    def test_get_performance_checks(self, sample_config):
        """Test getting performance checks."""
        config = HealthCheckConfig(sample_config)
        checks = config.get_performance_checks()
        
        assert len(checks) == 1
        assert checks[0]['name'] == 'test_timing'
    
    def test_get_interval(self, sample_config):
        """Test getting check interval."""
        config = HealthCheckConfig(sample_config)
        interval = config.get_interval()
        
        assert interval == 60
    
    def test_invalid_config_path(self):
        """Test invalid configuration path."""
        with pytest.raises(FileNotFoundError):
            HealthCheckConfig('nonexistent.yaml')


# Service Checker Tests

class TestServiceChecker:
    """Test service availability checks."""
    
    def test_initialization(self):
        """Test service checker initialization."""
        checker = ServiceChecker()
        assert checker is not None
    
    @patch('requests.request')
    def test_check_http_success(self, mock_request):
        """Test HTTP check success."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_request.return_value = mock_response
        
        checker = ServiceChecker()
        config = {
            'name': 'test_http',
            'type': 'http',
            'url': 'http://localhost:8080/health',
            'method': 'GET',
            'timeout': 5,
            'expected_status': 200
        }
        
        result = checker.check(config)
        
        assert result['name'] == 'test_http'
        assert result['status'] == 'OK'
        assert result['status_code'] == 200
        assert result['response_time_ms'] >= 0
    
    @patch('requests.request')
    def test_check_http_failure(self, mock_request):
        """Test HTTP check failure."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_request.return_value = mock_response
        
        checker = ServiceChecker()
        config = {
            'name': 'test_http',
            'type': 'http',
            'url': 'http://localhost:8080/health',
            'method': 'GET',
            'timeout': 5,
            'expected_status': 200
        }
        
        result = checker.check(config)
        
        assert result['status'] == 'FAILED'
        assert result['status_code'] == 500
    
    @patch('socket.socket')
    def test_check_tcp_success(self, mock_socket):
        """Test TCP check success."""
        mock_sock_instance = Mock()
        mock_sock_instance.connect_ex.return_value = 0
        mock_socket.return_value = mock_sock_instance
        
        checker = ServiceChecker()
        config = {
            'name': 'test_tcp',
            'type': 'tcp',
            'host': 'localhost',
            'port': 7687,
            'timeout': 5
        }
        
        result = checker.check(config)
        
        assert result['name'] == 'test_tcp'
        assert result['status'] == 'OK'
    
    @patch('socket.socket')
    def test_check_tcp_failure(self, mock_socket):
        """Test TCP check failure."""
        mock_sock_instance = Mock()
        mock_sock_instance.connect_ex.return_value = 1
        mock_socket.return_value = mock_sock_instance
        
        checker = ServiceChecker()
        config = {
            'name': 'test_tcp',
            'type': 'tcp',
            'host': 'localhost',
            'port': 7687,
            'timeout': 5
        }
        
        result = checker.check(config)
        
        assert result['status'] == 'FAILED'
    
    @patch('requests.post')
    def test_check_sparql_success(self, mock_post):
        """Test SPARQL check success."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'results': {'bindings': [{'s': {'value': 'test'}}]}
        }
        mock_post.return_value = mock_response
        
        checker = ServiceChecker()
        config = {
            'name': 'test_sparql',
            'type': 'sparql',
            'url': 'http://localhost:3030/sparql',
            'query': 'ASK { ?s ?p ?o }',
            'timeout': 10
        }
        
        result = checker.check(config)
        
        assert result['status'] == 'OK'
        assert 'results' in result


# Data Quality Checker Tests

class TestDataQualityChecker:
    """Test data quality checks."""
    
    def test_initialization(self):
        """Test data quality checker initialization."""
        checker = DataQualityChecker()
        assert checker is not None
    
    @patch('requests.request')
    def test_check_http_json(self, mock_request):
        """Test HTTP JSON check."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'totalCount': 720}
        mock_request.return_value = mock_response
        
        checker = DataQualityChecker()
        config = {
            'name': 'test_json',
            'type': 'http_json',
            'url': 'http://localhost:8080/entities?count=true',
            'method': 'GET',
            'timeout': 10,
            'json_path': '$.totalCount',
            'threshold': {'min': 700}
        }
        
        result = checker.check(config)
        
        assert result['status'] == 'OK'
        assert result['value'] == 720
    
    def test_evaluate_threshold_ok(self):
        """Test threshold evaluation - OK."""
        checker = DataQualityChecker()
        
        status = checker._evaluate_threshold(750, {'min': 700, 'max': 800})
        assert status == 'OK'
    
    def test_evaluate_threshold_failed_min(self):
        """Test threshold evaluation - failed min."""
        checker = DataQualityChecker()
        
        status = checker._evaluate_threshold(650, {'min': 700})
        assert status == 'FAILED'
    
    def test_evaluate_threshold_failed_max(self):
        """Test threshold evaluation - failed max."""
        checker = DataQualityChecker()
        
        status = checker._evaluate_threshold(850, {'max': 800})
        assert status == 'FAILED'
    
    def test_evaluate_threshold_warning(self):
        """Test threshold evaluation - warning."""
        checker = DataQualityChecker()
        
        # Value between warn_min and min triggers warning
        status = checker._evaluate_threshold(690, {'min': 700, 'warn_min': 680})
        assert status == 'WARNING'
    
    def test_extract_json_value(self):
        """Test JSON value extraction."""
        checker = DataQualityChecker()
        
        data = {'totalCount': 720, 'nested': {'value': 42}}
        value = checker._extract_json_value(data, '$.totalCount')
        
        assert value == 720


# Performance Checker Tests

class TestPerformanceChecker:
    """Test performance checks."""
    
    def test_initialization(self):
        """Test performance checker initialization."""
        checker = PerformanceChecker()
        assert checker is not None
    
    @patch('requests.request')
    def test_check_http_timing(self, mock_request):
        """Test HTTP timing check."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_request.return_value = mock_response
        
        checker = PerformanceChecker()
        config = {
            'name': 'test_timing',
            'type': 'http_timing',
            'url': 'http://localhost:8080/api',
            'method': 'GET',
            'timeout': 10,
            'threshold': {'max': 1000, 'warn_max': 500}
        }
        
        result = checker.check(config)
        
        assert result['status'] in ['OK', 'WARNING', 'FAILED']
        assert result['response_time_ms'] >= 0
    
    def test_evaluate_timing_threshold_ok(self):
        """Test timing threshold - OK."""
        checker = PerformanceChecker()
        
        status = checker._evaluate_timing_threshold(300, {'max': 1000, 'warn_max': 500})
        assert status == 'OK'
    
    def test_evaluate_timing_threshold_warning(self):
        """Test timing threshold - warning."""
        checker = PerformanceChecker()
        
        status = checker._evaluate_timing_threshold(700, {'max': 1000, 'warn_max': 500})
        assert status == 'WARNING'
    
    def test_evaluate_timing_threshold_failed(self):
        """Test timing threshold - failed."""
        checker = PerformanceChecker()
        
        status = checker._evaluate_timing_threshold(1500, {'max': 1000})
        assert status == 'FAILED'


# Health Aggregator Tests

class TestHealthAggregator:
    """Test health status aggregation."""
    
    def test_initialization(self, sample_config):
        """Test health aggregator initialization."""
        config = HealthCheckConfig(sample_config)
        aggregator = HealthAggregator(config)
        
        assert aggregator is not None
    
    def test_aggregate_all_ok(self, sample_config):
        """Test aggregation - all OK."""
        config = HealthCheckConfig(sample_config)
        aggregator = HealthAggregator(config)
        
        check_results = [
            {'name': 'check1', 'status': 'OK', 'critical': True},
            {'name': 'check2', 'status': 'OK', 'critical': False}
        ]
        
        result = aggregator.aggregate(check_results)
        
        assert result['status'] == 'GREEN'
        assert result['summary']['ok'] == 2
        assert result['summary']['failed'] == 0
    
    def test_aggregate_critical_failed(self, sample_config):
        """Test aggregation - critical failed."""
        config = HealthCheckConfig(sample_config)
        aggregator = HealthAggregator(config)
        
        check_results = [
            {'name': 'check1', 'status': 'FAILED', 'critical': True},
            {'name': 'check2', 'status': 'OK', 'critical': False}
        ]
        
        result = aggregator.aggregate(check_results)
        
        assert result['status'] == 'RED'
        assert result['summary']['critical_failed'] == 1
    
    def test_aggregate_non_critical_failed(self, sample_config):
        """Test aggregation - non-critical failed."""
        config = HealthCheckConfig(sample_config)
        aggregator = HealthAggregator(config)
        
        check_results = [
            {'name': 'check1', 'status': 'OK', 'critical': True},
            {'name': 'check2', 'status': 'FAILED', 'critical': False}
        ]
        
        result = aggregator.aggregate(check_results)
        
        assert result['status'] == 'YELLOW'
        assert result['summary']['failed'] == 1
    
    def test_aggregate_warnings(self, sample_config):
        """Test aggregation - warnings."""
        config = HealthCheckConfig(sample_config)
        aggregator = HealthAggregator(config)
        
        check_results = [
            {'name': 'check1', 'status': 'OK', 'critical': True},
            {'name': 'check2', 'status': 'WARNING', 'critical': False}
        ]
        
        result = aggregator.aggregate(check_results)
        
        assert result['status'] == 'YELLOW'
        assert result['summary']['warning'] == 1


# Alert Manager Tests

class TestAlertManager:
    """Test alert management."""
    
    def test_initialization(self, sample_config):
        """Test alert manager initialization."""
        config = HealthCheckConfig(sample_config)
        manager = AlertManager(config)
        
        assert manager is not None
    
    def test_should_alert_state_change(self, sample_config):
        """Test alert on state change."""
        config = HealthCheckConfig(sample_config)
        manager = AlertManager(config)
        
        # First status
        manager.last_status = 'GREEN'
        
        # Status changed
        health_status = {'status': 'RED'}
        should_alert = manager.should_alert(health_status)
        
        assert should_alert is True
    
    def test_should_alert_no_change(self, sample_config):
        """Test no alert when status unchanged."""
        config = HealthCheckConfig(sample_config)
        manager = AlertManager(config)
        
        manager.last_status = 'GREEN'
        
        health_status = {'status': 'GREEN'}
        should_alert = manager.should_alert(health_status)
        
        assert should_alert is False
    
    @patch('requests.request')
    def test_send_webhook_alert(self, mock_request, sample_config):
        """Test sending webhook alert."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_request.return_value = mock_response
        
        config = HealthCheckConfig(sample_config)
        manager = AlertManager(config)
        
        health_status = {
            'status': 'RED',
            'description': 'Critical service failed',
            'timestamp': '2025-11-01T10:00:00Z'
        }
        
        manager.send_alert(health_status)
        
        # Webhook should be called
        assert mock_request.called
    
    def test_render_template(self, sample_config):
        """Test template rendering."""
        config = HealthCheckConfig(sample_config)
        manager = AlertManager(config)
        
        template = {'status': '{{status}}', 'desc': '{{description}}'}
        health_status = {'status': 'RED', 'description': 'Failed'}
        
        result = manager._render_template(template, health_status)
        
        assert result['status'] == 'RED'
        assert result['desc'] == 'Failed'
    
    def test_map_severity(self, sample_config):
        """Test severity mapping."""
        config = HealthCheckConfig(sample_config)
        manager = AlertManager(config)
        
        assert manager._map_severity('RED') == 'critical'
        assert manager._map_severity('YELLOW') == 'warning'
        assert manager._map_severity('GREEN') == 'info'


# Integration Tests

class TestHealthCheckAgent:
    """Test main health check agent."""
    
    def test_initialization(self, sample_config):
        """Test agent initialization."""
        agent = HealthCheckAgent(sample_config)
        
        assert agent.config is not None
        assert agent.service_checker is not None
        assert agent.data_quality_checker is not None
        assert agent.performance_checker is not None
    
    @patch('requests.request')
    @patch('socket.socket')
    def test_run_checks(self, mock_socket, mock_request, sample_config):
        """Test running all checks."""
        # Mock HTTP response
        mock_http_response = Mock()
        mock_http_response.status_code = 200
        mock_request.return_value = mock_http_response
        
        # Mock TCP socket
        mock_sock_instance = Mock()
        mock_sock_instance.connect_ex.return_value = 0
        mock_socket.return_value = mock_sock_instance
        
        agent = HealthCheckAgent(sample_config)
        health_status = agent.run_checks()
        
        assert 'status' in health_status
        assert 'checks' in health_status
        assert 'summary' in health_status
        assert health_status['status'] in ['GREEN', 'YELLOW', 'RED']
    
    def test_api_health_endpoint(self, sample_config):
        """Test API health endpoint."""
        agent = HealthCheckAgent(sample_config)
        
        with agent.app.test_client() as client:
            # Mock checks
            with patch.object(agent, 'run_checks') as mock_run:
                mock_run.return_value = {
                    'status': 'GREEN',
                    'checks': [],
                    'summary': {'total': 0, 'ok': 0, 'failed': 0}
                }
                
                response = client.get('/health')
                
                assert response.status_code == 200
                data = json.loads(response.data)
                assert data['status'] == 'GREEN'
    
    def test_api_metrics_endpoint(self, sample_config):
        """Test API metrics endpoint."""
        agent = HealthCheckAgent(sample_config)
        
        with agent.app.test_client() as client:
            response = client.get('/metrics')
            
            # Should return 503 if Prometheus not available
            assert response.status_code in [200, 503]


# Edge Cases

class TestEdgeCases:
    """Test edge cases and error scenarios."""
    
    @patch('requests.request')
    def test_http_check_timeout(self, mock_request):
        """Test HTTP check timeout."""
        import requests
        mock_request.side_effect = requests.Timeout("Connection timeout")
        
        checker = ServiceChecker()
        config = {
            'name': 'test_timeout',
            'type': 'http',
            'url': 'http://localhost:8080/slow',
            'timeout': 1
        }
        
        result = checker.check(config)
        
        assert result['status'] == 'ERROR'
        assert 'timeout' in result.get('error', '').lower()
    
    @patch('requests.request')
    def test_http_check_connection_error(self, mock_request):
        """Test HTTP check connection error."""
        import requests
        mock_request.side_effect = requests.ConnectionError("Connection refused")
        
        checker = ServiceChecker()
        config = {
            'name': 'test_connection',
            'type': 'http',
            'url': 'http://localhost:9999/health',
            'timeout': 5
        }
        
        result = checker.check(config)
        
        assert result['status'] == 'ERROR'
    
    def test_unknown_check_type(self):
        """Test unknown check type."""
        checker = ServiceChecker()
        config = {
            'name': 'test_unknown',
            'type': 'unknown_type',
            'url': 'http://localhost:8080'
        }
        
        result = checker.check(config)
        
        assert result['status'] == 'ERROR'
        assert 'unknown' in result.get('error', '').lower()
    
    def test_empty_check_results(self, sample_config):
        """Test aggregation with empty results."""
        config = HealthCheckConfig(sample_config)
        aggregator = HealthAggregator(config)
        
        result = aggregator.aggregate([])
        
        assert result['status'] == 'GREEN'
        assert result['summary']['total'] == 0


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
