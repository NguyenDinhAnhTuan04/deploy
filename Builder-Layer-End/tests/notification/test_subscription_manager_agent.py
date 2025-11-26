"""
Comprehensive Test Suite for Subscription Manager Agent

Tests cover:
- Configuration loading and validation
- Subscription creation (CRUD operations)
- Expiry checking and auto-renewal logic
- Health monitoring
- Stellio API integration (mocked)
- Template-based creation
- Edge cases and error handling

Author: Builder Layer Development Team
Version: 1.0.0
"""

import json
import pytest
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any
from unittest.mock import Mock, patch, MagicMock

# Import agent modules
from agents.notification.subscription_manager_agent import (
    SubscriptionConfig,
    SubscriptionManager
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def temp_config():
    """Create temporary configuration file."""
    config_content = """
subscription_manager:
  stellio:
    base_url: "http://localhost:8080"
    timeout: 10
    max_retries: 3
    retry_backoff_factor: 2
    
    endpoints:
      create: "/ngsi-ld/v1/subscriptions"
      get: "/ngsi-ld/v1/subscriptions/{subscription_id}"
      update: "/ngsi-ld/v1/subscriptions/{subscription_id}"
      delete: "/ngsi-ld/v1/subscriptions/{subscription_id}"
      list: "/ngsi-ld/v1/subscriptions"
    
    headers:
      Content-Type: "application/ld+json"
      Accept: "application/ld+json"
  
  monitoring:
    enabled: true
    check_interval: 300
    
    auto_renew:
      enabled: true
      renew_before_days: 7
      default_extension_days: 365
  
  subscriptions:
    - name: "test-subscription-1"
      description: "Test subscription for congestion alerts"
      enabled: true
      
      entities:
        - type: "Camera"
      
      watched_attributes:
        - "congested"
        - "intensity"
      
      q: "congested==true"
      
      notification:
        endpoint:
          uri: "http://alert-dispatcher:8080/notify"
          accept: "application/json"
        
        format: "normalized"
        
        attributes:
          - "congested"
          - "intensity"
      
      throttling: 60
      
      expires_at: "2026-11-01T00:00:00Z"
    
    - name: "test-subscription-2"
      description: "Test subscription disabled"
      enabled: false
      
      entities:
        - type: "Device"
      
      notification:
        endpoint:
          uri: "http://test:8080/notify"
          accept: "application/json"
  
  templates:
    - name: "basic-watch"
      template:
        entities:
          - type: "{entity_type}"
        
        watched_attributes:
          - "{attribute_name}"
        
        notification:
          endpoint:
            uri: "{notification_endpoint}"
            accept: "application/json"
        
        throttling: 60
        
        expires_at: "{expiry_date}"
  
  statistics:
    enabled: true
    collection_interval: 60
"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(config_content)
        temp_path = f.name
    
    yield temp_path
    
    # Cleanup
    Path(temp_path).unlink()


@pytest.fixture
def sample_subscription():
    """Create sample subscription definition."""
    return {
        'name': 'test-subscription',
        'description': 'Test subscription',
        'entities': [{'type': 'Camera'}],
        'watched_attributes': ['congested'],
        'notification': {
            'endpoint': {
                'uri': 'http://test:8080/notify',
                'accept': 'application/json'
            },
            'format': 'normalized'
        },
        'throttling': 60,
        'expires_at': '2026-11-01T00:00:00Z'
    }


# ============================================================================
# Unit Tests - Configuration
# ============================================================================

def test_config_load(temp_config):
    """Test configuration loading."""
    config = SubscriptionConfig(temp_config)
    
    assert config is not None
    assert config.subscription_manager is not None


def test_config_stellio(temp_config):
    """Test Stellio configuration."""
    config = SubscriptionConfig(temp_config)
    stellio = config.get_stellio_config()
    
    assert stellio['base_url'] == 'http://localhost:8080'
    assert stellio['timeout'] == 10
    assert stellio['max_retries'] == 3


def test_config_monitoring(temp_config):
    """Test monitoring configuration."""
    config = SubscriptionConfig(temp_config)
    monitoring = config.get_monitoring_config()
    
    assert monitoring['enabled'] is True
    assert monitoring['check_interval'] == 300
    assert monitoring['auto_renew']['enabled'] is True


def test_config_subscriptions(temp_config):
    """Test subscription definitions."""
    config = SubscriptionConfig(temp_config)
    subscriptions = config.get_subscriptions()
    
    assert len(subscriptions) == 2
    assert subscriptions[0]['name'] == 'test-subscription-1'
    assert subscriptions[0]['enabled'] is True


def test_config_templates(temp_config):
    """Test template definitions."""
    config = SubscriptionConfig(temp_config)
    templates = config.get_templates()
    
    assert len(templates) == 1
    assert templates[0]['name'] == 'basic-watch'


def test_config_invalid_file():
    """Test configuration with invalid file."""
    with pytest.raises(FileNotFoundError):
        SubscriptionConfig('nonexistent.yaml')


# ============================================================================
# Unit Tests - Subscription Manager
# ============================================================================

def test_manager_init(temp_config):
    """Test manager initialization."""
    manager = SubscriptionManager(temp_config)
    
    assert manager.base_url == 'http://localhost:8080'
    assert manager.timeout == 10
    assert manager.auto_renew_enabled is True


def test_build_subscription_payload(temp_config, sample_subscription):
    """Test subscription payload building."""
    manager = SubscriptionManager(temp_config)
    
    payload = manager.build_subscription_payload(sample_subscription)
    
    assert payload['type'] == 'Subscription'
    assert 'id' in payload
    assert payload['entities'] == sample_subscription['entities']
    assert payload['watchedAttributes'] == sample_subscription['watched_attributes']


def test_build_payload_with_query(temp_config):
    """Test payload with query filter."""
    manager = SubscriptionManager(temp_config)
    
    sub_def = {
        'entities': [{'type': 'Camera'}],
        'q': 'congested==true',
        'notification': {
            'endpoint': {'uri': 'http://test:8080/notify'}
        }
    }
    
    payload = manager.build_subscription_payload(sub_def)
    
    assert payload['q'] == 'congested==true'


def test_build_payload_with_temporal_query(temp_config):
    """Test payload with temporal query."""
    manager = SubscriptionManager(temp_config)
    
    sub_def = {
        'entities': [{'type': 'Device'}],
        'temporal_q': {
            'timerel': 'after',
            'time': '2025-01-01T00:00:00Z'
        },
        'notification': {
            'endpoint': {'uri': 'http://test:8080/notify'}
        }
    }
    
    payload = manager.build_subscription_payload(sub_def)
    
    assert 'temporalQ' in payload
    assert payload['temporalQ']['timerel'] == 'after'


def test_build_payload_with_geo_query(temp_config):
    """Test payload with geo-query."""
    manager = SubscriptionManager(temp_config)
    
    sub_def = {
        'entities': [{'type': 'Vehicle'}],
        'geo_q': {
            'georel': 'near;maxDistance==500',
            'geometry': 'Point',
            'coordinates': [40.0, -3.0]
        },
        'notification': {
            'endpoint': {'uri': 'http://test:8080/notify'}
        }
    }
    
    payload = manager.build_subscription_payload(sub_def)
    
    assert 'geoQ' in payload
    assert payload['geoQ']['georel'] == 'near;maxDistance==500'


# ============================================================================
# Unit Tests - CRUD Operations
# ============================================================================

@patch('requests.Session.post')
def test_create_subscription_success(mock_post, temp_config, sample_subscription):
    """Test successful subscription creation."""
    manager = SubscriptionManager(temp_config)
    
    # Mock successful response
    mock_response = Mock()
    mock_response.status_code = 201
    mock_response.headers = {'Location': '/ngsi-ld/v1/subscriptions/sub123'}
    mock_post.return_value = mock_response
    
    subscription_id = manager.create_subscription(sample_subscription)
    
    assert subscription_id == 'sub123'
    assert manager.stats['subscriptions_created'] == 1
    assert manager.stats['subscriptions_active'] == 1


@patch('requests.Session.post')
def test_create_subscription_duplicate(mock_post, temp_config, sample_subscription):
    """Test duplicate subscription creation."""
    manager = SubscriptionManager(temp_config)
    
    # Mock 409 Conflict
    mock_response = Mock()
    mock_response.status_code = 409
    mock_response.text = 'Subscription already exists'
    mock_post.return_value = mock_response
    
    subscription_id = manager.create_subscription(sample_subscription)
    
    assert subscription_id is None


@patch('requests.Session.post')
def test_create_subscription_failure(mock_post, temp_config, sample_subscription):
    """Test failed subscription creation."""
    manager = SubscriptionManager(temp_config)
    
    # Mock 500 error
    mock_response = Mock()
    mock_response.status_code = 500
    mock_response.text = 'Internal server error'
    mock_post.return_value = mock_response
    
    subscription_id = manager.create_subscription(sample_subscription)
    
    assert subscription_id is None
    assert manager.stats['subscriptions_failed'] == 1


@patch('requests.Session.get')
def test_get_subscription_success(mock_get, temp_config):
    """Test getting subscription details."""
    manager = SubscriptionManager(temp_config)
    
    # Mock successful response
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        'id': 'sub123',
        'type': 'Subscription',
        'status': 'active'
    }
    mock_get.return_value = mock_response
    
    subscription = manager.get_subscription('sub123')
    
    assert subscription is not None
    assert subscription['id'] == 'sub123'
    assert subscription['status'] == 'active'


@patch('requests.Session.get')
def test_get_subscription_not_found(mock_get, temp_config):
    """Test getting non-existent subscription."""
    manager = SubscriptionManager(temp_config)
    
    # Mock 404 response
    mock_response = Mock()
    mock_response.status_code = 404
    mock_get.return_value = mock_response
    
    subscription = manager.get_subscription('nonexistent')
    
    assert subscription is None


@patch('requests.Session.get')
def test_list_subscriptions(mock_get, temp_config):
    """Test listing subscriptions."""
    manager = SubscriptionManager(temp_config)
    
    # Mock successful response
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = [
        {'id': 'sub1', 'type': 'Subscription'},
        {'id': 'sub2', 'type': 'Subscription'}
    ]
    mock_get.return_value = mock_response
    
    subscriptions = manager.list_subscriptions()
    
    assert len(subscriptions) == 2


@patch('requests.Session.patch')
def test_update_subscription_success(mock_patch, temp_config):
    """Test subscription update."""
    manager = SubscriptionManager(temp_config)
    
    # Mock successful response
    mock_response = Mock()
    mock_response.status_code = 204
    mock_patch.return_value = mock_response
    
    updates = {'expiresAt': '2027-11-01T00:00:00Z'}
    success = manager.update_subscription('sub123', updates)
    
    assert success is True
    assert manager.stats['subscriptions_updated'] == 1


@patch('requests.Session.delete')
def test_delete_subscription_success(mock_delete, temp_config):
    """Test subscription deletion."""
    manager = SubscriptionManager(temp_config)
    
    # Add to registry
    manager.subscription_registry['test-sub'] = 'sub123'
    manager.stats['subscriptions_active'] = 1
    
    # Mock successful response
    mock_response = Mock()
    mock_response.status_code = 204
    mock_delete.return_value = mock_response
    
    success = manager.delete_subscription('sub123')
    
    assert success is True
    assert manager.stats['subscriptions_deleted'] == 1
    assert 'test-sub' not in manager.subscription_registry


# ============================================================================
# Unit Tests - Expiry and Renewal
# ============================================================================

def test_check_expiry_soon(temp_config):
    """Test checking subscription expiring soon."""
    manager = SubscriptionManager(temp_config)
    
    # Create subscription expiring in 5 days
    expires_at = (datetime.utcnow() + timedelta(days=5)).isoformat() + 'Z'
    subscription = {'expiresAt': expires_at}
    
    is_expiring, expiry_date = manager.check_expiry(subscription)
    
    assert is_expiring is True
    assert expiry_date is not None


def test_check_expiry_not_soon(temp_config):
    """Test checking subscription not expiring soon."""
    manager = SubscriptionManager(temp_config)
    
    # Create subscription expiring in 30 days
    expires_at = (datetime.utcnow() + timedelta(days=30)).isoformat() + 'Z'
    subscription = {'expiresAt': expires_at}
    
    is_expiring, expiry_date = manager.check_expiry(subscription)
    
    assert is_expiring is False


def test_check_expiry_no_expiry(temp_config):
    """Test checking subscription with no expiry."""
    manager = SubscriptionManager(temp_config)
    
    subscription = {}  # No expiresAt field
    
    is_expiring, expiry_date = manager.check_expiry(subscription)
    
    assert is_expiring is False
    assert expiry_date is None


@patch('requests.Session.patch')
def test_renew_subscription(mock_patch, temp_config):
    """Test subscription renewal."""
    manager = SubscriptionManager(temp_config)
    
    # Mock successful response
    mock_response = Mock()
    mock_response.status_code = 204
    mock_patch.return_value = mock_response
    
    success = manager.renew_subscription('sub123')
    
    assert success is True
    assert manager.stats['auto_renewals'] == 1


# ============================================================================
# Unit Tests - Health Monitoring
# ============================================================================

@patch('requests.Session.get')
def test_check_health_active(mock_get, temp_config):
    """Test health check for active subscription."""
    manager = SubscriptionManager(temp_config)
    
    # Mock subscription response (not expiring)
    expires_at = (datetime.utcnow() + timedelta(days=30)).isoformat() + 'Z'
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        'id': 'sub123',
        'status': 'active',
        'expiresAt': expires_at
    }
    mock_get.return_value = mock_response
    
    healthy = manager.check_subscription_health('sub123')
    
    assert healthy is True


@patch('requests.Session.get')
@patch('requests.Session.patch')
def test_check_health_expiring_auto_renew(mock_patch, mock_get, temp_config):
    """Test health check with auto-renewal."""
    manager = SubscriptionManager(temp_config)
    
    # Mock subscription response (expiring soon)
    expires_at = (datetime.utcnow() + timedelta(days=5)).isoformat() + 'Z'
    mock_get_response = Mock()
    mock_get_response.status_code = 200
    mock_get_response.json.return_value = {
        'id': 'sub123',
        'status': 'active',
        'expiresAt': expires_at
    }
    mock_get.return_value = mock_get_response
    
    # Mock renewal response
    mock_patch_response = Mock()
    mock_patch_response.status_code = 204
    mock_patch.return_value = mock_patch_response
    
    healthy = manager.check_subscription_health('sub123')
    
    assert healthy is True
    assert manager.stats['auto_renewals'] == 1


@patch('requests.Session.get')
def test_check_health_not_found(mock_get, temp_config):
    """Test health check for non-existent subscription."""
    manager = SubscriptionManager(temp_config)
    
    # Mock 404 response
    mock_response = Mock()
    mock_response.status_code = 404
    mock_get.return_value = mock_response
    
    healthy = manager.check_subscription_health('nonexistent')
    
    assert healthy is False


# ============================================================================
# Integration Tests
# ============================================================================

@patch('requests.Session.post')
def test_create_all_subscriptions(mock_post, temp_config):
    """Test creating all subscriptions from config."""
    manager = SubscriptionManager(temp_config)
    
    # Mock successful responses
    mock_response = Mock()
    mock_response.status_code = 201
    mock_response.headers = {'Location': '/ngsi-ld/v1/subscriptions/sub123'}
    mock_post.return_value = mock_response
    
    created = manager.create_all_subscriptions()
    
    # Only 1 enabled subscription in config
    assert created == 1


@patch('requests.Session.delete')
def test_delete_all_subscriptions(mock_delete, temp_config):
    """Test deleting all subscriptions."""
    manager = SubscriptionManager(temp_config)
    
    # Add subscriptions to registry
    manager.subscription_registry['sub1'] = 'id1'
    manager.subscription_registry['sub2'] = 'id2'
    
    # Mock successful responses
    mock_response = Mock()
    mock_response.status_code = 204
    mock_delete.return_value = mock_response
    
    deleted = manager.delete_all_subscriptions()
    
    assert deleted == 2
    assert len(manager.subscription_registry) == 0


@patch('requests.Session.get')
def test_monitor_subscriptions(mock_get, temp_config):
    """Test monitoring subscriptions."""
    manager = SubscriptionManager(temp_config)
    
    # Add subscriptions to registry
    manager.subscription_registry['test-sub'] = 'sub123'
    
    # Mock subscription response
    expires_at = (datetime.utcnow() + timedelta(days=30)).isoformat() + 'Z'
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        'id': 'sub123',
        'status': 'active',
        'expiresAt': expires_at
    }
    mock_get.return_value = mock_response
    
    manager.monitor_subscriptions()
    
    assert manager.stats['health_checks'] == 1


# ============================================================================
# Template Tests
# ============================================================================

@patch('requests.Session.post')
def test_create_from_template(mock_post, temp_config):
    """Test creating subscription from template."""
    manager = SubscriptionManager(temp_config)
    
    # Mock successful response
    mock_response = Mock()
    mock_response.status_code = 201
    mock_response.headers = {'Location': '/ngsi-ld/v1/subscriptions/sub123'}
    mock_post.return_value = mock_response
    
    parameters = {
        'entity_type': 'Camera',
        'attribute_name': 'congested',
        'notification_endpoint': 'http://test:8080/notify',
        'expiry_date': '2026-11-01T00:00:00Z'
    }
    
    subscription_id = manager.create_from_template('basic-watch', parameters)
    
    assert subscription_id == 'sub123'


def test_create_from_invalid_template(temp_config):
    """Test creating from non-existent template."""
    manager = SubscriptionManager(temp_config)
    
    parameters = {'entity_type': 'Camera'}
    
    subscription_id = manager.create_from_template('nonexistent', parameters)
    
    assert subscription_id is None


# ============================================================================
# Edge Case Tests
# ============================================================================

@patch('requests.Session.post')
def test_create_subscription_network_error(mock_post, temp_config, sample_subscription):
    """Test subscription creation with network error."""
    manager = SubscriptionManager(temp_config)
    
    # Mock network error
    mock_post.side_effect = Exception("Connection refused")
    
    subscription_id = manager.create_subscription(sample_subscription)
    
    assert subscription_id is None
    assert manager.stats['subscriptions_failed'] == 1


def test_statistics(temp_config):
    """Test getting statistics."""
    manager = SubscriptionManager(temp_config)
    
    # Modify stats
    manager.stats['subscriptions_created'] = 5
    manager.stats['subscriptions_active'] = 3
    
    stats = manager.get_statistics()
    
    assert stats['subscriptions_created'] == 5
    assert stats['subscriptions_active'] == 3


def test_build_payload_minimal(temp_config):
    """Test building minimal subscription payload."""
    manager = SubscriptionManager(temp_config)
    
    minimal_def = {
        'entities': [{'type': 'Device'}],
        'notification': {
            'endpoint': {'uri': 'http://test:8080/notify'}
        }
    }
    
    payload = manager.build_subscription_payload(minimal_def)
    
    assert payload['type'] == 'Subscription'
    assert 'id' in payload
    assert payload['entities'] == minimal_def['entities']


@patch('requests.Session.post')
def test_create_subscription_retry(mock_post, temp_config, sample_subscription):
    """Test subscription creation with retry."""
    manager = SubscriptionManager(temp_config)
    manager.max_retries = 2
    
    # Mock first attempt fails, second succeeds
    mock_response_fail = Mock()
    mock_response_fail.status_code = 500
    mock_response_fail.text = 'Error'
    
    mock_response_success = Mock()
    mock_response_success.status_code = 201
    mock_response_success.headers = {'Location': '/ngsi-ld/v1/subscriptions/sub123'}
    
    mock_post.side_effect = [mock_response_fail, mock_response_success]
    
    subscription_id = manager.create_subscription(sample_subscription)
    
    assert subscription_id == 'sub123'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
