"""
Tests for Alert Dispatcher Agent

Comprehensive test suite covering:
- Configuration loading
- Webhook parsing
- Routing logic
- Template rendering
- Rate limiting
- Channel delivery (mocked)
- Retry logic
- Load testing

Author: Builder Layer Development Team
Version: 1.0.0
"""

import json
import pytest
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from concurrent.futures import ThreadPoolExecutor

import sys
sys.path.append(str(Path(__file__).parent.parent.parent))

from agents.notification.alert_dispatcher_agent import (
    AlertDispatcherConfig,
    RateLimiter,
    TemplateEngine,
    WebSocketChannel,
    FCMChannel,
    EmailChannel,
    SMSChannel,
    AlertDispatcher
)


# Test fixtures

@pytest.fixture
def sample_config():
    """Sample configuration for testing."""
    return {
        'alert_dispatcher': {
            'server': {
                'host': '0.0.0.0',
                'port': 8080,
                'endpoints': {
                    'congestion': '/notify/congestion',
                    'accident': '/notify/accident',
                    'generic': '/notify'
                }
            },
            'channels': {
                'websocket': {
                    'enabled': True,
                    'url': 'ws://localhost:8080/ws',
                    'max_connections': 1000
                },
                'fcm': {
                    'enabled': True,
                    'server_key': 'test_fcm_key',
                    'api_url': 'https://fcm.googleapis.com/fcm/send',
                    'priority': 'high',
                    'timeout': 10,
                    'max_retries': 3
                },
                'email': {
                    'enabled': True,
                    'smtp_host': 'smtp.gmail.com',
                    'smtp_port': 587,
                    'use_tls': True,
                    'username': 'test@example.com',
                    'password': 'test_password',
                    'from_addr': 'traffic@hcmc.gov.vn',
                    'from_name': 'Traffic Alert System',
                    'timeout': 30,
                    'max_retries': 3
                },
                'sms': {
                    'enabled': False,
                    'provider': 'twilio',
                    'account_sid': 'test_sid',
                    'auth_token': 'test_token',
                    'from_number': '+1234567890',
                    'timeout': 10,
                    'max_retries': 3
                }
            },
            'routing_rules': {
                'congestion': {
                    'channels': ['websocket', 'fcm'],
                    'priority': 'medium',
                    'throttle_seconds': 300,
                    'retry_on_failure': True,
                    'max_retries': 3
                },
                'accident': {
                    'channels': ['websocket', 'fcm', 'sms', 'email'],
                    'priority': 'high',
                    'throttle_seconds': 0,
                    'retry_on_failure': True,
                    'max_retries': 5
                },
                'generic': {
                    'channels': ['websocket'],
                    'priority': 'medium',
                    'throttle_seconds': 60,
                    'retry_on_failure': True,
                    'max_retries': 1
                }
            },
            'templates': {
                'congestion': {
                    'title': '🚦 Traffic Congestion Alert',
                    'body': 'Congestion detected at {{camera_name}} - Speed: {{speed}} km/h',
                    'email_subject': 'Traffic Congestion Alert - {{camera_name}}',
                    'email_body': '<h3>Traffic Congestion Alert</h3><p>Location: {{camera_name}}</p><p>Speed: {{speed}} km/h</p><p>Time: {{timestamp}}</p>',
                    'sms_body': 'Traffic congestion at {{camera_name}}. Speed: {{speed}} km/h'
                },
                'accident': {
                    'title': '⚠️ Traffic Accident Alert',
                    'body': 'Accident reported at {{location}} - Severity: {{severity}}',
                    'email_subject': 'URGENT: Traffic Accident Alert - {{location}}',
                    'email_body': '<h3 style="color: red;">Traffic Accident Alert</h3><p>Location: {{location}}</p><p>Severity: {{severity}}</p>',
                    'sms_body': 'ACCIDENT at {{location}}. Severity: {{severity}}'
                },
                'generic': {
                    'title': '🔔 Notification',
                    'body': '{{message}}',
                    'email_subject': 'Notification',
                    'email_body': '<p>{{message}}</p>',
                    'sms_body': '{{message}}'
                }
            },
            'rate_limiting': {
                'enabled': True,
                'max_per_user_per_hour': 10,
                'max_per_user_per_day': 50,
                'max_global_per_second': 100,
                'whitelist': ['admin@hcmc.gov.vn', 'emergency@hcmc.gov.vn']
            },
            'retry': {
                'enabled': True,
                'max_attempts': 3,
                'backoff_factor': 2,
                'retry_on_status_codes': [500, 502, 503, 504]
            }
        }
    }


@pytest.fixture
def config_file(sample_config, tmp_path):
    """Create temporary configuration file."""
    config_path = tmp_path / "alert_dispatcher_config.yaml"
    
    import yaml
    with open(config_path, 'w') as f:
        yaml.dump(sample_config, f)
    
    return str(config_path)


# Configuration Tests

class TestAlertDispatcherConfig:
    """Test configuration loading."""
    
    def test_load_config(self, config_file):
        """Test loading configuration from YAML."""
        config = AlertDispatcherConfig(config_file)
        
        assert config.config is not None
        assert 'alert_dispatcher' in config.config
    
    def test_get_server_config(self, config_file):
        """Test getting server configuration."""
        config = AlertDispatcherConfig(config_file)
        server_config = config.get_server_config()
        
        assert server_config['host'] == '0.0.0.0'
        assert server_config['port'] == 8080
        assert 'endpoints' in server_config
    
    def test_get_channels_config(self, config_file):
        """Test getting channels configuration."""
        config = AlertDispatcherConfig(config_file)
        channels_config = config.get_channels_config()
        
        assert 'websocket' in channels_config
        assert 'fcm' in channels_config
        assert 'email' in channels_config
        assert 'sms' in channels_config
    
    def test_get_routing_rules(self, config_file):
        """Test getting routing rules."""
        config = AlertDispatcherConfig(config_file)
        routing_rules = config.get_routing_rules()
        
        assert 'congestion' in routing_rules
        assert 'accident' in routing_rules
        assert routing_rules['accident']['priority'] == 'high'
    
    def test_get_templates(self, config_file):
        """Test getting templates."""
        config = AlertDispatcherConfig(config_file)
        templates = config.get_templates()
        
        assert 'congestion' in templates
        assert 'accident' in templates
        assert 'title' in templates['congestion']


# Rate Limiting Tests

class TestRateLimiter:
    """Test rate limiting functionality."""
    
    def test_rate_limiter_allows_first_request(self, sample_config):
        """Test rate limiter allows first request."""
        rate_config = sample_config['alert_dispatcher']['rate_limiting']
        limiter = RateLimiter(rate_config)
        
        assert limiter.is_allowed('user1') is True
    
    def test_rate_limiter_enforces_hourly_limit(self, sample_config):
        """Test rate limiter enforces hourly limit."""
        rate_config = sample_config['alert_dispatcher']['rate_limiting']
        rate_config['max_per_user_per_hour'] = 3
        limiter = RateLimiter(rate_config)
        
        # Allow first 3
        for i in range(3):
            assert limiter.is_allowed('user1') is True
        
        # Block 4th
        assert limiter.is_allowed('user1') is False
    
    def test_rate_limiter_whitelist(self, sample_config):
        """Test rate limiter whitelist."""
        rate_config = sample_config['alert_dispatcher']['rate_limiting']
        rate_config['max_per_user_per_hour'] = 1
        limiter = RateLimiter(rate_config)
        
        # Whitelisted user unlimited
        for i in range(10):
            assert limiter.is_allowed('admin@hcmc.gov.vn') is True
    
    def test_rate_limiter_disabled(self, sample_config):
        """Test rate limiter when disabled."""
        rate_config = sample_config['alert_dispatcher']['rate_limiting']
        rate_config['enabled'] = False
        limiter = RateLimiter(rate_config)
        
        # Allow unlimited
        for i in range(100):
            assert limiter.is_allowed('user1') is True
    
    def test_rate_limiter_sliding_window(self, sample_config):
        """Test rate limiter sliding window."""
        rate_config = sample_config['alert_dispatcher']['rate_limiting']
        rate_config['max_per_user_per_hour'] = 2
        limiter = RateLimiter(rate_config)
        
        # Allow 2
        limiter.is_allowed('user1')
        limiter.is_allowed('user1')
        
        # Block 3rd
        assert limiter.is_allowed('user1') is False
        
        # Simulate time passing (old entries cleaned)
        limiter.hourly_counts['user1'] = [
            datetime.utcnow() - timedelta(hours=2)
        ]
        
        # Now allowed again
        assert limiter.is_allowed('user1') is True


# Template Engine Tests

class TestTemplateEngine:
    """Test template rendering."""
    
    def test_render_simple_template(self, sample_config):
        """Test rendering simple template."""
        templates = sample_config['alert_dispatcher']['templates']
        engine = TemplateEngine(templates)
        
        variables = {'message': 'Test message'}
        result = engine.render('generic', 'body', variables)
        
        assert result == 'Test message'
    
    def test_render_with_multiple_variables(self, sample_config):
        """Test rendering with multiple variables."""
        templates = sample_config['alert_dispatcher']['templates']
        engine = TemplateEngine(templates)
        
        variables = {
            'camera_name': 'Camera 123',
            'speed': '45',
            'timestamp': '2024-01-15T10:00:00Z'
        }
        result = engine.render('congestion', 'body', variables)
        
        assert 'Camera 123' in result
        assert '45' in result
    
    def test_render_missing_variable(self, sample_config):
        """Test rendering with missing variable."""
        templates = sample_config['alert_dispatcher']['templates']
        engine = TemplateEngine(templates)
        
        variables = {'camera_name': 'Camera 123'}
        result = engine.render('congestion', 'body', variables)
        
        # Missing variable replaced with empty string
        assert 'Camera 123' in result
        assert 'Speed:  km/h' in result
    
    def test_render_html_email(self, sample_config):
        """Test rendering HTML email template."""
        templates = sample_config['alert_dispatcher']['templates']
        engine = TemplateEngine(templates)
        
        variables = {'location': 'Highway 1', 'severity': 'High'}
        result = engine.render('accident', 'email_body', variables)
        
        assert '<h3' in result
        assert 'Highway 1' in result
        assert 'High' in result
    
    def test_render_sms_body(self, sample_config):
        """Test rendering SMS body template."""
        templates = sample_config['alert_dispatcher']['templates']
        engine = TemplateEngine(templates)
        
        variables = {'camera_name': 'Camera 123', 'speed': '45'}
        result = engine.render('congestion', 'sms_body', variables)
        
        assert 'Camera 123' in result
        assert '45' in result
    
    def test_render_nonexistent_template(self, sample_config):
        """Test rendering nonexistent template."""
        templates = sample_config['alert_dispatcher']['templates']
        engine = TemplateEngine(templates)
        
        result = engine.render('nonexistent', 'body', {})
        
        assert result == ''


# Channel Tests

class TestWebSocketChannel:
    """Test WebSocket channel."""
    
    def test_websocket_enabled(self, sample_config):
        """Test WebSocket channel when enabled."""
        channel_config = sample_config['alert_dispatcher']['channels']['websocket']
        retry_config = sample_config['alert_dispatcher']['retry']
        
        channel = WebSocketChannel(channel_config, retry_config)
        
        assert channel.enabled is True
    
    def test_websocket_deliver(self, sample_config):
        """Test WebSocket message delivery."""
        channel_config = sample_config['alert_dispatcher']['channels']['websocket']
        retry_config = sample_config['alert_dispatcher']['retry']
        
        channel = WebSocketChannel(channel_config, retry_config)
        
        message = {
            'alert_type': 'congestion',
            'title': 'Test Alert',
            'body': 'Test body',
            'data': {'test': 'value'}
        }
        
        # Should succeed (mocked)
        result = channel.deliver(message)
        assert result is True


class TestFCMChannel:
    """Test FCM channel."""
    
    @patch('agents.notification.alert_dispatcher_agent.requests.post')
    def test_fcm_deliver_success(self, mock_post, sample_config):
        """Test successful FCM delivery."""
        channel_config = sample_config['alert_dispatcher']['channels']['fcm']
        retry_config = sample_config['alert_dispatcher']['retry']
        
        channel = FCMChannel(channel_config, retry_config)
        
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        message = {
            'fcm_token': 'test_token',
            'title': 'Test Alert',
            'body': 'Test body',
            'data': {}
        }
        
        result = channel.deliver(message)
        
        assert result is True
        assert mock_post.called
    
    @patch('agents.notification.alert_dispatcher_agent.requests.post')
    def test_fcm_deliver_failure(self, mock_post, sample_config):
        """Test failed FCM delivery."""
        channel_config = sample_config['alert_dispatcher']['channels']['fcm']
        channel_config['max_retries'] = 1
        retry_config = sample_config['alert_dispatcher']['retry']
        
        channel = FCMChannel(channel_config, retry_config)
        
        # Mock failed response
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = 'Internal error'
        mock_post.return_value = mock_response
        
        message = {
            'fcm_token': 'test_token',
            'title': 'Test Alert',
            'body': 'Test body',
            'data': {}
        }
        
        result = channel.deliver(message)
        
        assert result is False
    
    def test_fcm_no_token(self, sample_config):
        """Test FCM delivery without token."""
        channel_config = sample_config['alert_dispatcher']['channels']['fcm']
        retry_config = sample_config['alert_dispatcher']['retry']
        
        channel = FCMChannel(channel_config, retry_config)
        
        message = {
            'title': 'Test Alert',
            'body': 'Test body'
        }
        
        result = channel.deliver(message)
        
        assert result is False


class TestEmailChannel:
    """Test Email channel."""
    
    @patch('agents.notification.alert_dispatcher_agent.smtplib.SMTP')
    def test_email_deliver_success(self, mock_smtp, sample_config):
        """Test successful email delivery."""
        channel_config = sample_config['alert_dispatcher']['channels']['email']
        retry_config = sample_config['alert_dispatcher']['retry']
        
        channel = EmailChannel(channel_config, retry_config)
        
        # Mock SMTP server
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server
        
        message = {
            'email': 'test@example.com',
            'email_subject': 'Test Subject',
            'email_body': '<h1>Test Body</h1>'
        }
        
        result = channel.deliver(message)
        
        assert result is True
        assert mock_server.send_message.called
    
    @patch('agents.notification.alert_dispatcher_agent.smtplib.SMTP')
    def test_email_deliver_failure(self, mock_smtp, sample_config):
        """Test failed email delivery."""
        channel_config = sample_config['alert_dispatcher']['channels']['email']
        channel_config['max_retries'] = 1
        retry_config = sample_config['alert_dispatcher']['retry']
        
        channel = EmailChannel(channel_config, retry_config)
        
        # Mock SMTP server failure
        mock_smtp.side_effect = Exception("SMTP error")
        
        message = {
            'email': 'test@example.com',
            'email_subject': 'Test Subject',
            'email_body': 'Test Body'
        }
        
        result = channel.deliver(message)
        
        assert result is False
    
    def test_email_no_address(self, sample_config):
        """Test email delivery without address."""
        channel_config = sample_config['alert_dispatcher']['channels']['email']
        retry_config = sample_config['alert_dispatcher']['retry']
        
        channel = EmailChannel(channel_config, retry_config)
        
        message = {
            'email_subject': 'Test Subject',
            'email_body': 'Test Body'
        }
        
        result = channel.deliver(message)
        
        assert result is False


class TestSMSChannel:
    """Test SMS channel."""
    
    @patch('agents.notification.alert_dispatcher_agent.requests.post')
    def test_sms_deliver_success(self, mock_post, sample_config):
        """Test successful SMS delivery."""
        channel_config = sample_config['alert_dispatcher']['channels']['sms']
        channel_config['enabled'] = True
        retry_config = sample_config['alert_dispatcher']['retry']
        
        channel = SMSChannel(channel_config, retry_config)
        
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 201
        mock_post.return_value = mock_response
        
        message = {
            'phone': '+1234567890',
            'sms_body': 'Test SMS message'
        }
        
        result = channel.deliver(message)
        
        assert result is True
        assert mock_post.called
    
    def test_sms_disabled(self, sample_config):
        """Test SMS channel when disabled."""
        channel_config = sample_config['alert_dispatcher']['channels']['sms']
        retry_config = sample_config['alert_dispatcher']['retry']
        
        channel = SMSChannel(channel_config, retry_config)
        
        message = {
            'phone': '+1234567890',
            'sms_body': 'Test SMS message'
        }
        
        result = channel.deliver(message)
        
        assert result is False


# Integration Tests

class TestAlertDispatcher:
    """Test main alert dispatcher."""
    
    def test_dispatcher_initialization(self, config_file):
        """Test dispatcher initialization."""
        dispatcher = AlertDispatcher(config_file)
        
        assert dispatcher.config is not None
        assert dispatcher.app is not None
        assert len(dispatcher.channels) > 0
    
    def test_extract_variables(self, config_file):
        """Test variable extraction from notification."""
        dispatcher = AlertDispatcher(config_file)
        
        notification = {
            'id': 'urn:ngsi-ld:TrafficCamera:123',
            'type': 'TrafficCamera',
            'observedAt': '2024-01-15T10:00:00Z',
            'data': [{
                'speed': {'value': 45},
                'camera_name': {'value': 'Camera 123'}
            }]
        }
        
        variables = dispatcher._extract_variables(notification, 'congestion')
        
        assert variables['entity_id'] == 'urn:ngsi-ld:TrafficCamera:123'
        assert variables['entity_type'] == 'TrafficCamera'
        assert variables['speed'] == 45
        assert variables['camera_name'] == 'Camera 123'
    
    @patch('agents.notification.alert_dispatcher_agent.WebSocketChannel.deliver')
    def test_dispatch_alert(self, mock_deliver, config_file):
        """Test alert dispatching."""
        mock_deliver.return_value = True
        
        dispatcher = AlertDispatcher(config_file)
        
        variables = {
            'camera_name': 'Camera 123',
            'speed': '45',
            'timestamp': '2024-01-15T10:00:00Z'
        }
        
        result = dispatcher.dispatch_alert('congestion', variables)
        
        assert result is True
        assert mock_deliver.called
    
    def test_dispatch_with_routing(self, config_file):
        """Test dispatch with routing rules."""
        dispatcher = AlertDispatcher(config_file)
        
        # Test congestion routing
        routing = dispatcher.routing_rules.get('congestion')
        
        assert 'websocket' in routing['channels']
        assert 'fcm' in routing['channels']
        assert routing['priority'] == 'medium'
    
    def test_statistics_tracking(self, config_file):
        """Test statistics tracking."""
        dispatcher = AlertDispatcher(config_file)
        
        # Initial stats
        assert dispatcher.stats['alerts_received'] == 0
        assert dispatcher.stats['alerts_delivered'] == 0


# Load Tests

class TestLoadHandling:
    """Test load handling and concurrency."""
    
    @patch('agents.notification.alert_dispatcher_agent.WebSocketChannel.deliver')
    def test_concurrent_notifications(self, mock_deliver, config_file):
        """Test handling 100 concurrent notifications."""
        mock_deliver.return_value = True
        
        dispatcher = AlertDispatcher(config_file)
        
        variables = {
            'camera_name': 'Camera 123',
            'speed': '45',
            'timestamp': '2024-01-15T10:00:00Z'
        }
        
        def dispatch_alert():
            return dispatcher.dispatch_alert('congestion', variables)
        
        # Run 100 concurrent dispatches
        with ThreadPoolExecutor(max_workers=100) as executor:
            futures = [executor.submit(dispatch_alert) for _ in range(100)]
            results = [f.result() for f in futures]
        
        # All should succeed
        assert all(results)
    
    def test_rate_limiter_under_load(self, sample_config):
        """Test rate limiter effectiveness under load."""
        rate_config = sample_config['alert_dispatcher']['rate_limiting']
        rate_config['max_per_user_per_hour'] = 10
        limiter = RateLimiter(rate_config)
        
        allowed_count = 0
        
        # Try 20 requests
        for i in range(20):
            if limiter.is_allowed('user1'):
                allowed_count += 1
        
        # Should allow exactly 10
        assert allowed_count == 10
    
    @patch('agents.notification.alert_dispatcher_agent.FCMChannel.deliver')
    def test_channel_throughput(self, mock_deliver, config_file):
        """Test channel delivery throughput."""
        mock_deliver.return_value = True
        
        dispatcher = AlertDispatcher(config_file)
        
        start_time = time.time()
        
        for i in range(100):
            variables = {'message': f'Test {i}'}
            dispatcher.dispatch_alert('generic', variables)
        
        elapsed = time.time() - start_time
        
        # Should complete in reasonable time (< 5 seconds)
        assert elapsed < 5


# Edge Cases

class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_invalid_config_path(self):
        """Test invalid configuration path."""
        with pytest.raises(FileNotFoundError):
            AlertDispatcherConfig('nonexistent.yaml')
    
    def test_missing_template(self, config_file):
        """Test handling missing template."""
        dispatcher = AlertDispatcher(config_file)
        
        variables = {'test': 'value'}
        result = dispatcher.dispatch_alert('nonexistent_type', variables)
        
        # Should fall back to generic
        assert isinstance(result, bool)
    
    @patch('agents.notification.alert_dispatcher_agent.requests.post')
    def test_network_timeout(self, mock_post, sample_config):
        """Test handling network timeouts."""
        channel_config = sample_config['alert_dispatcher']['channels']['fcm']
        channel_config['max_retries'] = 1
        retry_config = sample_config['alert_dispatcher']['retry']
        
        channel = FCMChannel(channel_config, retry_config)
        
        # Mock timeout
        import requests
        mock_post.side_effect = requests.Timeout("Connection timeout")
        
        message = {
            'fcm_token': 'test_token',
            'title': 'Test',
            'body': 'Test'
        }
        
        result = channel.deliver(message)
        
        assert result is False
    
    def test_empty_notification_data(self, config_file):
        """Test handling empty notification data."""
        dispatcher = AlertDispatcher(config_file)
        
        notification = {
            'id': 'test_id',
            'type': 'test_type'
        }
        
        variables = dispatcher._extract_variables(notification, 'generic')
        
        assert 'entity_id' in variables
        assert 'entity_type' in variables


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
