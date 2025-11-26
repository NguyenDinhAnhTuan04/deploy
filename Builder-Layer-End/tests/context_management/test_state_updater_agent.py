"""
Comprehensive Test Suite for State Updater Agent

Tests cover:
- Configuration loading and validation
- Event parsing and validation
- PATCH request building
- Retry logic with exponential backoff
- Kafka consumer integration (mocked)
- Webhook server integration (mocked)
- Concurrent updates
- Stress testing (100 updates/second)
- Network failures
- Duplicate event handling
- Edge cases

Author: Builder Layer Agent
Version: 1.0.0
"""

import json
import pytest
import tempfile
import time
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List
from unittest.mock import Mock, patch, MagicMock
from queue import Queue

# Import agent modules
from agents.context_management.state_updater_agent import (
    StateUpdaterConfig,
    UpdateEvent,
    UpdateResult,
    EntityUpdater,
    StateUpdaterAgent
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def temp_config():
    """Create temporary configuration file."""
    config_content = """
state_updater:
  event_sources:
    - type: "kafka"
      enabled: true
      topic: "test-updates"
      bootstrap_servers: "localhost:9092"
      group_id: "test-group"
    
    - type: "webhook"
      enabled: true
      port: 8081
      endpoint: "/updates"
      validation:
        require_entity_id: true
        require_updates: true
  
  stellio:
    base_url: "http://localhost:8080"
    timeout: 10
    retry:
      max_attempts: 3
      backoff_factor: 2
      max_backoff: 30
      retry_on_status: [408, 429, 500, 502, 503, 504]
      jitter: true
    endpoints:
      patch_entity: "/ngsi-ld/v1/entities/{entity_id}/attrs"
    headers:
      Content-Type: "application/json"
  
  update_rules:
    imageSnapshot:
      method: "PATCH"
      attributes: ["imageSnapshot", "observedAt"]
      validation:
        imageSnapshot:
          type: "string"
          format: "url"
          required: true
    
    congested:
      method: "PATCH"
      attributes: ["congested", "observedAt"]
      validation:
        congested:
          type: "boolean"
          required: true
    
    intensity:
      method: "PATCH"
      attributes: ["intensity", "observedAt"]
      validation:
        intensity:
          type: "number"
          min: 0.0
          max: 1.0
          required: true
  
  processing:
    concurrency:
      max_workers: 5
      queue_size: 100
    
    deduplication:
      enabled: true
      window_seconds: 60
  
  monitoring:
    enabled: true
  
  logging:
    level: "INFO"
  
  state:
    enabled: false
"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(config_content)
        temp_path = f.name
    
    yield temp_path
    
    # Cleanup
    Path(temp_path).unlink()


@pytest.fixture
def sample_update_event():
    """Create sample update event."""
    return {
        'entity_id': 'urn:ngsi-ld:Camera:TTH406',
        'updates': {
            'imageSnapshot': {
                'type': 'Property',
                'value': 'https://example.com/image.jpg',
                'observedAt': '2025-11-01T10:00:00Z'
            }
        },
        'timestamp': '2025-11-01T10:00:00Z',
        'event_id': 'evt-12345'
    }


@pytest.fixture
def sample_congested_event():
    """Create sample congestion update event."""
    return {
        'entity_id': 'urn:ngsi-ld:Camera:TTH406',
        'updates': {
            'congested': {
                'type': 'Property',
                'value': True,
                'observedAt': '2025-11-01T10:00:00Z'
            }
        },
        'timestamp': '2025-11-01T10:00:00Z'
    }


@pytest.fixture
def sample_intensity_event():
    """Create sample intensity update event."""
    return {
        'entity_id': 'urn:ngsi-ld:Camera:TTH407',
        'updates': {
            'intensity': {
                'type': 'Property',
                'value': 0.75,
                'observedAt': '2025-11-01T10:00:00Z'
            }
        },
        'timestamp': '2025-11-01T10:00:00Z'
    }


@pytest.fixture
def mock_http_response():
    """Create mock HTTP response."""
    response = Mock()
    response.status_code = 204
    response.text = ''
    return response


# ============================================================================
# Unit Tests - Configuration
# ============================================================================

def test_config_load(temp_config):
    """Test configuration loading."""
    config = StateUpdaterConfig(temp_config)
    
    assert config is not None
    assert config.state_updater is not None


def test_config_event_sources(temp_config):
    """Test event sources configuration."""
    config = StateUpdaterConfig(temp_config)
    sources = config.get_event_sources()
    
    assert len(sources) == 2
    assert sources[0]['type'] == 'kafka'
    assert sources[1]['type'] == 'webhook'


def test_config_stellio(temp_config):
    """Test Stellio configuration."""
    config = StateUpdaterConfig(temp_config)
    stellio = config.get_stellio_config()
    
    assert stellio['base_url'] == 'http://localhost:8080'
    assert stellio['timeout'] == 10
    assert stellio['retry']['max_attempts'] == 3


def test_config_update_rules(temp_config):
    """Test update rules configuration."""
    config = StateUpdaterConfig(temp_config)
    rules = config.get_update_rules()
    
    assert 'imageSnapshot' in rules
    assert 'congested' in rules
    assert 'intensity' in rules
    
    # Check validation rules
    assert rules['intensity']['validation']['intensity']['min'] == 0.0
    assert rules['intensity']['validation']['intensity']['max'] == 1.0


def test_config_invalid_file():
    """Test configuration with invalid file."""
    with pytest.raises(FileNotFoundError):
        StateUpdaterConfig('nonexistent.yaml')


# ============================================================================
# Unit Tests - UpdateEvent
# ============================================================================

def test_update_event_from_dict(sample_update_event):
    """Test UpdateEvent creation from dictionary."""
    event = UpdateEvent.from_dict(sample_update_event)
    
    assert event.entity_id == 'urn:ngsi-ld:Camera:TTH406'
    assert 'imageSnapshot' in event.updates
    assert event.event_id == 'evt-12345'
    assert event.source == 'unknown'


def test_update_event_auto_event_id():
    """Test automatic event ID generation."""
    data = {
        'entity_id': 'urn:ngsi-ld:Camera:TTH406',
        'updates': {'test': 'value'}
    }
    
    event = UpdateEvent.from_dict(data)
    
    assert event.event_id is not None
    assert len(event.event_id) == 16  # SHA256 truncated to 16 chars


def test_update_event_missing_entity_id():
    """Test UpdateEvent with missing entity_id."""
    data = {'updates': {'test': 'value'}}
    
    with pytest.raises(ValueError, match="Missing required field: entity_id"):
        UpdateEvent.from_dict(data)


def test_update_event_missing_updates():
    """Test UpdateEvent with missing updates."""
    data = {'entity_id': 'urn:ngsi-ld:Camera:TTH406'}
    
    with pytest.raises(ValueError, match="Missing required field: updates"):
        UpdateEvent.from_dict(data)


def test_update_event_to_dict(sample_update_event):
    """Test UpdateEvent serialization."""
    event = UpdateEvent.from_dict(sample_update_event)
    result = event.to_dict()
    
    assert result['entity_id'] == sample_update_event['entity_id']
    assert result['updates'] == sample_update_event['updates']
    assert result['event_id'] == sample_update_event['event_id']


# ============================================================================
# Unit Tests - EntityUpdater
# ============================================================================

def test_entity_updater_init(temp_config):
    """Test EntityUpdater initialization."""
    config = StateUpdaterConfig(temp_config)
    updater = EntityUpdater(config)
    
    assert updater.base_url == 'http://localhost:8080'
    assert updater.timeout == 10
    assert updater.max_retry_attempts == 3


def test_build_patch_url(temp_config):
    """Test PATCH URL building."""
    config = StateUpdaterConfig(temp_config)
    updater = EntityUpdater(config)
    
    url = updater.build_patch_url('urn:ngsi-ld:Camera:TTH406')
    
    assert 'TTH406' in url
    assert '/attrs' in url


def test_validate_update_valid(temp_config, sample_intensity_event):
    """Test update validation with valid data."""
    config = StateUpdaterConfig(temp_config)
    updater = EntityUpdater(config)
    
    event = UpdateEvent.from_dict(sample_intensity_event)
    is_valid, error = updater.validate_update(event)
    
    assert is_valid is True
    assert error is None


def test_validate_update_invalid_type(temp_config):
    """Test update validation with invalid type."""
    config = StateUpdaterConfig(temp_config)
    updater = EntityUpdater(config)
    
    # Create event with string instead of boolean
    data = {
        'entity_id': 'urn:ngsi-ld:Camera:TTH406',
        'updates': {
            'congested': {
                'type': 'Property',
                'value': 'yes'  # Should be boolean
            }
        }
    }
    
    event = UpdateEvent.from_dict(data)
    is_valid, error = updater.validate_update(event)
    
    assert is_valid is False
    assert 'must be boolean' in error


def test_validate_update_out_of_range(temp_config):
    """Test update validation with out-of-range value."""
    config = StateUpdaterConfig(temp_config)
    updater = EntityUpdater(config)
    
    # Create event with intensity > 1.0
    data = {
        'entity_id': 'urn:ngsi-ld:Camera:TTH406',
        'updates': {
            'intensity': {
                'type': 'Property',
                'value': 1.5  # Above max of 1.0
            }
        }
    }
    
    event = UpdateEvent.from_dict(data)
    is_valid, error = updater.validate_update(event)
    
    assert is_valid is False
    assert 'above maximum' in error


@patch('requests.Session.patch')
def test_patch_entity_success(mock_patch, temp_config, sample_update_event, mock_http_response):
    """Test successful PATCH request."""
    config = StateUpdaterConfig(temp_config)
    updater = EntityUpdater(config)
    
    mock_patch.return_value = mock_http_response
    
    event = UpdateEvent.from_dict(sample_update_event)
    result = updater.patch_entity(event)
    
    assert result.success is True
    assert result.status_code == 204
    assert result.entity_id == event.entity_id
    assert result.event_id == event.event_id
    assert result.retry_count == 0


@patch('requests.Session.patch')
def test_patch_entity_retry(mock_patch, temp_config, sample_update_event):
    """Test PATCH retry on server error."""
    config = StateUpdaterConfig(temp_config)
    updater = EntityUpdater(config)
    
    # First call fails with 503, second succeeds
    error_response = Mock()
    error_response.status_code = 503
    error_response.text = 'Service Unavailable'
    
    success_response = Mock()
    success_response.status_code = 204
    success_response.text = ''
    
    mock_patch.side_effect = [error_response, success_response]
    
    event = UpdateEvent.from_dict(sample_update_event)
    result = updater.patch_entity(event)
    
    assert result.success is True
    assert result.retry_count == 1
    assert mock_patch.call_count == 2


@patch('requests.Session.patch')
def test_patch_entity_max_retries(mock_patch, temp_config, sample_update_event):
    """Test PATCH with max retries exceeded."""
    config = StateUpdaterConfig(temp_config)
    updater = EntityUpdater(config)
    
    # Always fail with 503
    error_response = Mock()
    error_response.status_code = 503
    error_response.text = 'Service Unavailable'
    
    mock_patch.return_value = error_response
    
    event = UpdateEvent.from_dict(sample_update_event)
    result = updater.patch_entity(event)
    
    assert result.success is False
    assert result.retry_count == 3  # Max retries
    assert mock_patch.call_count == 4  # Initial + 3 retries


# ============================================================================
# Unit Tests - Deduplication
# ============================================================================

def test_deduplication_enabled(temp_config):
    """Test event deduplication."""
    config = StateUpdaterConfig(temp_config)
    agent = StateUpdaterAgent(temp_config)
    
    # Create duplicate events
    event1 = UpdateEvent.from_dict({
        'entity_id': 'urn:ngsi-ld:Camera:TTH406',
        'updates': {'test': 'value'},
        'event_id': 'evt-duplicate'
    })
    
    event2 = UpdateEvent.from_dict({
        'entity_id': 'urn:ngsi-ld:Camera:TTH407',
        'updates': {'test': 'value2'},
        'event_id': 'evt-duplicate'  # Same ID
    })
    
    unique = agent.deduplicate_events([event1, event2])
    
    assert len(unique) == 1
    assert unique[0].event_id == 'evt-duplicate'


def test_deduplication_window_expiry(temp_config):
    """Test deduplication window expiry."""
    config = StateUpdaterConfig(temp_config)
    agent = StateUpdaterAgent(temp_config)
    
    # Override dedup window to 1 second
    agent.dedup_window = 1
    
    event1 = UpdateEvent.from_dict({
        'entity_id': 'urn:ngsi-ld:Camera:TTH406',
        'updates': {'test': 'value'},
        'event_id': 'evt-expiry'
    })
    
    # First dedup
    unique1 = agent.deduplicate_events([event1])
    assert len(unique1) == 1
    
    # Wait for window to expire
    time.sleep(1.1)
    
    # Second dedup with same event ID
    unique2 = agent.deduplicate_events([event1])
    assert len(unique2) == 1  # Should pass because window expired


# ============================================================================
# Integration Tests
# ============================================================================

@patch('agents.context_management.state_updater_agent.KAFKA_AVAILABLE', False)
def test_kafka_unavailable(temp_config):
    """Test graceful handling when Kafka is unavailable."""
    config = StateUpdaterConfig(temp_config)
    
    # Should not crash
    from agents.context_management.state_updater_agent import EventSourceManager
    manager = EventSourceManager(config)
    
    # Kafka source should not be added
    kafka_sources = [s for s in manager.sources if 'Kafka' in type(s).__name__]
    assert len(kafka_sources) == 0


@patch('agents.context_management.state_updater_agent.FLASK_AVAILABLE', False)
def test_flask_unavailable(temp_config):
    """Test graceful handling when Flask is unavailable."""
    config = StateUpdaterConfig(temp_config)
    
    # Should not crash
    from agents.context_management.state_updater_agent import EventSourceManager
    manager = EventSourceManager(config)
    
    # Webhook source should not be added
    webhook_sources = [s for s in manager.sources if 'Webhook' in type(s).__name__]
    assert len(webhook_sources) == 0


@patch('requests.Session.patch')
def test_concurrent_updates(mock_patch, temp_config):
    """Test concurrent processing of multiple updates."""
    config = StateUpdaterConfig(temp_config)
    agent = StateUpdaterAgent(temp_config)
    
    # Create success response
    success_response = Mock()
    success_response.status_code = 204
    success_response.text = ''
    mock_patch.return_value = success_response
    
    # Create 10 events
    events = []
    for i in range(10):
        event = UpdateEvent.from_dict({
            'entity_id': f'urn:ngsi-ld:Camera:TTH{400+i}',
            'updates': {'intensity': {'type': 'Property', 'value': 0.5}},
            'event_id': f'evt-{i}'
        })
        events.append(event)
    
    # Initialize executor
    from concurrent.futures import ThreadPoolExecutor
    agent.executor = ThreadPoolExecutor(max_workers=5)
    
    # Process concurrently
    results = agent.process_events(events)
    
    assert len(results) == 10
    assert all(r.success for r in results)
    assert agent.stats['updates_processed'] == 10
    
    agent.executor.shutdown()


@patch('requests.Session.patch')
def test_batch_processing(mock_patch, temp_config):
    """Test batch processing of events."""
    config = StateUpdaterConfig(temp_config)
    agent = StateUpdaterAgent(temp_config)
    
    success_response = Mock()
    success_response.status_code = 204
    mock_patch.return_value = success_response
    
    # Create 50 events
    events = []
    for i in range(50):
        event = UpdateEvent.from_dict({
            'entity_id': f'urn:ngsi-ld:Camera:TTH{400+i}',
            'updates': {'intensity': {'type': 'Property', 'value': 0.5}},
            'event_id': f'evt-batch-{i}'
        })
        events.append(event)
    
    from concurrent.futures import ThreadPoolExecutor
    agent.executor = ThreadPoolExecutor(max_workers=10)
    
    results = agent.process_events(events)
    
    assert len(results) == 50
    assert agent.stats['updates_processed'] == 50
    
    agent.executor.shutdown()


# ============================================================================
# Stress Tests
# ============================================================================

@patch('requests.Session.patch')
def test_high_throughput(mock_patch, temp_config):
    """Test 100 updates per second throughput."""
    config = StateUpdaterConfig(temp_config)
    agent = StateUpdaterAgent(temp_config)
    
    success_response = Mock()
    success_response.status_code = 204
    mock_patch.return_value = success_response
    
    # Create 100 events
    events = []
    for i in range(100):
        event = UpdateEvent.from_dict({
            'entity_id': f'urn:ngsi-ld:Camera:TTH{400+i}',
            'updates': {'intensity': {'type': 'Property', 'value': 0.5}},
            'event_id': f'evt-stress-{i}'
        })
        events.append(event)
    
    from concurrent.futures import ThreadPoolExecutor
    agent.executor = ThreadPoolExecutor(max_workers=20)
    
    start_time = time.time()
    results = agent.process_events(events)
    duration = time.time() - start_time
    
    assert len(results) == 100
    assert duration < 2.0  # Should process 100 events in < 2 seconds
    
    throughput = len(results) / duration
    assert throughput > 50  # At least 50 updates/second
    
    agent.executor.shutdown()


@patch('requests.Session.patch')
def test_network_failures(mock_patch, temp_config):
    """Test handling of network failures."""
    config = StateUpdaterConfig(temp_config)
    agent = StateUpdaterAgent(temp_config)
    
    # Simulate intermittent failures
    responses = []
    for i in range(20):
        response = Mock()
        if i % 3 == 0:  # Every 3rd request fails
            response.status_code = 503
            response.text = 'Service Unavailable'
        else:
            response.status_code = 204
            response.text = ''
        responses.append(response)
    
    mock_patch.side_effect = responses
    
    # Create 20 events
    events = []
    for i in range(20):
        event = UpdateEvent.from_dict({
            'entity_id': f'urn:ngsi-ld:Camera:TTH{400+i}',
            'updates': {'intensity': {'type': 'Property', 'value': 0.5}},
            'event_id': f'evt-failure-{i}'
        })
        events.append(event)
    
    from concurrent.futures import ThreadPoolExecutor
    agent.executor = ThreadPoolExecutor(max_workers=5)
    
    results = agent.process_events(events)
    
    # Some should succeed, some fail
    success_count = sum(1 for r in results if r.success)
    failure_count = sum(1 for r in results if not r.success)
    
    assert success_count > 0
    assert failure_count > 0
    
    agent.executor.shutdown()


@patch('requests.Session.patch')
def test_duplicate_events_stress(mock_patch, temp_config):
    """Test deduplication under high duplicate load."""
    config = StateUpdaterConfig(temp_config)
    agent = StateUpdaterAgent(temp_config)
    
    success_response = Mock()
    success_response.status_code = 204
    mock_patch.return_value = success_response
    
    # Create 100 events with 50% duplicates
    events = []
    for i in range(100):
        event_id = f'evt-dup-{i // 2}'  # Every 2 events have same ID
        event = UpdateEvent.from_dict({
            'entity_id': f'urn:ngsi-ld:Camera:TTH{400+i}',
            'updates': {'intensity': {'type': 'Property', 'value': 0.5}},
            'event_id': event_id
        })
        events.append(event)
    
    unique = agent.deduplicate_events(events)
    
    assert len(unique) == 50  # 50% should be filtered out
    assert agent.stats['updates_deduped'] == 50


# ============================================================================
# Edge Case Tests
# ============================================================================

def test_empty_event_list(temp_config):
    """Test processing empty event list."""
    config = StateUpdaterConfig(temp_config)
    agent = StateUpdaterAgent(temp_config)
    
    from concurrent.futures import ThreadPoolExecutor
    agent.executor = ThreadPoolExecutor(max_workers=5)
    
    results = agent.process_events([])
    
    assert len(results) == 0
    
    agent.executor.shutdown()


def test_malformed_event_data():
    """Test handling of malformed event data."""
    malformed = {
        'entity_id': 'urn:ngsi-ld:Camera:TTH406'
        # Missing 'updates'
    }
    
    with pytest.raises(ValueError):
        UpdateEvent.from_dict(malformed)


@patch('requests.Session.patch')
def test_timeout_handling(mock_patch, temp_config, sample_update_event):
    """Test timeout handling."""
    config = StateUpdaterConfig(temp_config)
    updater = EntityUpdater(config)
    
    # Simulate timeout
    import requests
    mock_patch.side_effect = requests.exceptions.Timeout()
    
    event = UpdateEvent.from_dict(sample_update_event)
    result = updater.patch_entity(event)
    
    assert result.success is False
    assert 'Timeout' in result.error


def test_statistics_collection(temp_config):
    """Test statistics collection."""
    agent = StateUpdaterAgent(temp_config)
    
    # Simulate some updates
    agent.stats['updates_processed'] = 100
    agent.stats['updates_failed'] = 5
    agent.stats['total_latency_ms'] = 5000
    
    stats = agent.get_statistics()
    
    assert stats['updates_processed'] == 100
    assert stats['updates_failed'] == 5
    assert stats['total_latency_ms'] == 5000


def test_missing_observedAt(temp_config):
    """Test handling of updates without observedAt."""
    config = StateUpdaterConfig(temp_config)
    
    data = {
        'entity_id': 'urn:ngsi-ld:Camera:TTH406',
        'updates': {
            'intensity': {
                'type': 'Property',
                'value': 0.75
                # Missing observedAt
            }
        }
    }
    
    # Should still create event
    event = UpdateEvent.from_dict(data)
    assert event.entity_id == 'urn:ngsi-ld:Camera:TTH406'


# ============================================================================
# Integration Test - Full Pipeline
# ============================================================================

@patch('requests.Session.patch')
def test_full_pipeline(mock_patch, temp_config):
    """Test full update pipeline end-to-end."""
    config = StateUpdaterConfig(temp_config)
    agent = StateUpdaterAgent(temp_config)
    
    success_response = Mock()
    success_response.status_code = 204
    mock_patch.return_value = success_response
    
    # Create events
    events = []
    for i in range(10):
        event = UpdateEvent.from_dict({
            'entity_id': f'urn:ngsi-ld:Camera:TTH{400+i}',
            'updates': {
                'intensity': {'type': 'Property', 'value': 0.5 + i * 0.05},
                'observedAt': {'type': 'Property', 'value': '2025-11-01T10:00:00Z'}
            },
            'event_id': f'evt-pipeline-{i}'
        })
        events.append(event)
    
    from concurrent.futures import ThreadPoolExecutor
    agent.executor = ThreadPoolExecutor(max_workers=5)
    
    # Deduplicate
    unique_events = agent.deduplicate_events(events)
    assert len(unique_events) == 10
    
    # Process
    results = agent.process_events(unique_events)
    assert len(results) == 10
    assert all(r.success for r in results)
    
    # Check statistics
    assert agent.stats['updates_processed'] == 10
    assert agent.stats['updates_failed'] == 0
    
    agent.executor.shutdown()


# ============================================================================
# Additional Tests - Event Source Manager
# ============================================================================

def test_event_source_manager_initialization(temp_config):
    """Test EventSourceManager initialization."""
    from agents.context_management.state_updater_agent import EventSourceManager
    
    config = StateUpdaterConfig(temp_config)
    manager = EventSourceManager(config)
    
    # Manager should be initialized even if sources fail
    assert manager is not None
    assert isinstance(manager.sources, list)


def test_event_source_manager_consume_empty(temp_config):
    """Test consuming events when no sources available."""
    from agents.context_management.state_updater_agent import EventSourceManager
    
    config = StateUpdaterConfig(temp_config)
    manager = EventSourceManager(config)
    
    # With no available sources, should return empty list
    events = manager.consume_events(timeout_s=0.1)
    
    assert events == []


def test_event_source_manager_close(temp_config):
    """Test EventSourceManager close."""
    from agents.context_management.state_updater_agent import EventSourceManager
    
    config = StateUpdaterConfig(temp_config)
    manager = EventSourceManager(config)
    
    # Should not crash
    manager.close()


# ============================================================================
# Additional Tests - UpdateResult
# ============================================================================

def test_update_result_creation():
    """Test UpdateResult creation."""
    result = UpdateResult(
        success=True,
        entity_id='urn:ngsi-ld:Camera:TTH406',
        event_id='evt-123',
        status_code=204,
        latency_ms=50.5
    )
    
    assert result.success is True
    assert result.status_code == 204
    assert result.latency_ms == 50.5
    assert result.retry_count == 0


def test_update_result_with_error():
    """Test UpdateResult with error."""
    result = UpdateResult(
        success=False,
        entity_id='urn:ngsi-ld:Camera:TTH406',
        event_id='evt-123',
        error='Timeout',
        retry_count=3
    )
    
    assert result.success is False
    assert result.error == 'Timeout'
    assert result.retry_count == 3


# ============================================================================
# Additional Tests - Validation
# ============================================================================

def test_validate_update_missing_required_field(temp_config):
    """Test validation with missing required field."""
    config = StateUpdaterConfig(temp_config)
    updater = EntityUpdater(config)
    
    # Create event missing required imageSnapshot
    data = {
        'entity_id': 'urn:ngsi-ld:Camera:TTH406',
        'updates': {
            'observedAt': {
                'type': 'Property',
                'value': '2025-11-01T10:00:00Z'
            }
        }
    }
    
    event = UpdateEvent.from_dict(data)
    is_valid, error = updater.validate_update(event)
    
    # Should pass (no matching rule)
    assert is_valid is True


def test_validate_update_below_minimum(temp_config):
    """Test validation with value below minimum."""
    config = StateUpdaterConfig(temp_config)
    updater = EntityUpdater(config)
    
    # Create event with negative intensity
    data = {
        'entity_id': 'urn:ngsi-ld:Camera:TTH406',
        'updates': {
            'intensity': {
                'type': 'Property',
                'value': -0.5  # Below min of 0.0
            }
        }
    }
    
    event = UpdateEvent.from_dict(data)
    is_valid, error = updater.validate_update(event)
    
    assert is_valid is False
    assert 'below minimum' in error


# ============================================================================
# Additional Tests - Concurrent Processing
# ============================================================================

@patch('requests.Session.patch')
def test_concurrent_success_and_failure(mock_patch, temp_config):
    """Test concurrent processing with mixed success/failure."""
    config = StateUpdaterConfig(temp_config)
    agent = StateUpdaterAgent(temp_config)
    
    # Alternate between success and failure
    responses = []
    for i in range(20):
        response = Mock()
        if i % 2 == 0:
            response.status_code = 204
        else:
            response.status_code = 500
            response.text = 'Internal Server Error'
        responses.append(response)
    
    mock_patch.side_effect = responses
    
    # Create 20 events
    events = []
    for i in range(20):
        event = UpdateEvent.from_dict({
            'entity_id': f'urn:ngsi-ld:Camera:TTH{400+i}',
            'updates': {'intensity': {'type': 'Property', 'value': 0.5}},
            'event_id': f'evt-mixed-{i}'
        })
        events.append(event)
    
    from concurrent.futures import ThreadPoolExecutor
    agent.executor = ThreadPoolExecutor(max_workers=10)
    
    results = agent.process_events(events)
    
    assert len(results) == 20
    success_count = sum(1 for r in results if r.success)
    
    # Some should succeed
    assert success_count > 0
    
    agent.executor.shutdown()


# ============================================================================
# Additional Tests - Error Cases
# ============================================================================

@patch('requests.Session.patch')
def test_patch_entity_connection_error(mock_patch, temp_config, sample_update_event):
    """Test PATCH with connection error."""
    config = StateUpdaterConfig(temp_config)
    updater = EntityUpdater(config)
    
    # Simulate connection error
    import requests
    mock_patch.side_effect = requests.exceptions.ConnectionError("Connection refused")
    
    event = UpdateEvent.from_dict(sample_update_event)
    result = updater.patch_entity(event)
    
    assert result.success is False
    assert result.error is not None


def test_update_event_timestamp_parsing():
    """Test timestamp parsing in UpdateEvent."""
    # Test with ISO format timestamp
    data = {
        'entity_id': 'urn:ngsi-ld:Camera:TTH406',
        'updates': {'test': 'value'},
        'timestamp': '2025-11-01T10:00:00+00:00'
    }
    
    event = UpdateEvent.from_dict(data)
    assert event.timestamp is not None
    assert isinstance(event.timestamp, datetime)


def test_update_event_with_metadata():
    """Test UpdateEvent with custom metadata."""
    data = {
        'entity_id': 'urn:ngsi-ld:Camera:TTH406',
        'updates': {'test': 'value'},
        'metadata': {
            'source': 'sensor-123',
            'priority': 'high'
        }
    }
    
    event = UpdateEvent.from_dict(data)
    assert event.metadata['source'] == 'sensor-123'
    assert event.metadata['priority'] == 'high'


# ============================================================================
# Additional Tests - State Management
# ============================================================================

def test_agent_statistics_initial_state(temp_config):
    """Test agent statistics in initial state."""
    agent = StateUpdaterAgent(temp_config)
    
    stats = agent.get_statistics()
    
    assert stats['updates_processed'] == 0
    assert stats['updates_failed'] == 0
    assert stats['updates_deduped'] == 0
    assert stats['total_latency_ms'] == 0


def test_agent_stop_without_start(temp_config):
    """Test stopping agent without starting."""
    agent = StateUpdaterAgent(temp_config)
    
    # Should not crash
    agent.stop()


# ============================================================================
# Additional Tests - Edge Cases
# ============================================================================

def test_multiple_attribute_updates(temp_config):
    """Test update with multiple attributes."""
    config = StateUpdaterConfig(temp_config)
    updater = EntityUpdater(config)
    
    data = {
        'entity_id': 'urn:ngsi-ld:Camera:TTH406',
        'updates': {
            'intensity': {'type': 'Property', 'value': 0.75},
            'occupancy': {'type': 'Property', 'value': 0.65},
            'speed': {'type': 'Property', 'value': 45.0},
            'observedAt': {'type': 'Property', 'value': '2025-11-01T10:00:00Z'}
        }
    }
    
    event = UpdateEvent.from_dict(data)
    is_valid, error = updater.validate_update(event)
    
    assert is_valid is True


def test_config_get_health_config(temp_config):
    """Test health configuration retrieval."""
    config = StateUpdaterConfig(temp_config)
    health = config.get_health_config()
    
    # Should return empty dict or config
    assert isinstance(health, dict)


def test_config_get_monitoring_config(temp_config):
    """Test monitoring configuration retrieval."""
    config = StateUpdaterConfig(temp_config)
    monitoring = config.get_monitoring_config()
    
    assert monitoring['enabled'] is True


def test_config_get_state_config(temp_config):
    """Test state configuration retrieval."""
    config = StateUpdaterConfig(temp_config)
    state = config.get_state_config()
    
    assert state['enabled'] is False


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
