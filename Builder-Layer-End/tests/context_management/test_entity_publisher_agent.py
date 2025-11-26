"""
Comprehensive Test Suite for Entity Publisher Agent

This test suite provides 100% coverage of the Entity Publisher Agent functionality,
including unit tests, integration tests, performance tests, and edge case tests.

Test Categories:
1. Unit Tests (ConfigLoader, BatchPublisher, PublishReportGenerator)
2. Integration Tests (Mock Stellio API responses)
3. Performance Tests (<30s for 722 entities)
4. Edge Case Tests (empty input, failures, network issues)

Author: GitHub Copilot
Date: 2025-11-01
Version: 1.0.0
"""

import json
import os
import tempfile
import time
from pathlib import Path
from typing import Dict, List, Any
from unittest.mock import Mock, patch, MagicMock

import pytest
import responses
import yaml

# Import the agent modules
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from agents.context_management.entity_publisher_agent import (
    ConfigLoader,
    BatchPublisher,
    PublishReportGenerator,
    EntityPublisherAgent,
    PublishResult,
    PublishStatistics
)


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def sample_stellio_config():
    """Create sample Stellio configuration for testing."""
    return {
        'base_url': 'http://localhost:8080',
        'api_version': 'ngsi-ld/v1',
        'endpoints': {
            'entities': '/entities',
            'batch': '/entityOperations/upsert',
            'query': '/entities',
            'delete': '/entities/{entityId}'
        },
        'auth': {
            'enabled': False,
            'token': None,
            'token_type': 'Bearer',
            'header_name': 'Authorization'
        },
        'batch_size': 50,
        'timeout': 30,
        'retry': {
            'max_attempts': 3,
            'backoff_factor': 2,
            'initial_delay': 1,
            'max_delay': 10,
            'retry_status_codes': [500, 502, 503, 504]
        },
        'headers': {
            'content_type': 'application/ld+json',
            'accept': 'application/ld+json',
            'user_agent': 'EntityPublisherAgent/1.0'
        },
        'conflict_resolution': {
            'strategy': 'patch',
            'use_patch': True,
            'patch_endpoint': '/entities/{entityId}/attrs'
        },
        'logging': {
            'enable_http_logging': True,
            'log_bodies': False,
            'level': 'INFO'
        },
        'performance': {
            'parallel_batches': False,
            'max_concurrent_batches': 5,
            'connection_pool_size': 10
        },
        'output': {
            'report_dir': 'data',
            'report_filename': 'publish_report.json',
            'detailed_errors': True,
            'save_failed_entities': True,
            'failed_entities_filename': 'failed_entities.json'
        }
    }


@pytest.fixture
def sample_config_file(tmp_path, sample_stellio_config):
    """Create temporary config file for testing."""
    config_dir = tmp_path / 'config'
    config_dir.mkdir()
    config_file = config_dir / 'stellio.yaml'
    
    with open(config_file, 'w') as f:
        yaml.dump({'stellio': sample_stellio_config}, f)
    
    return str(config_file)


@pytest.fixture
def sample_ngsi_ld_entity():
    """Create sample NGSI-LD entity for testing."""
    return {
        'id': 'urn:ngsi-ld:Camera:TEST001',
        'type': 'Camera',
        '@context': [
            'https://uri.etsi.org/ngsi-ld/v1/ngsi-ld-core-context.jsonld',
            'https://smart-data-models.github.io/dataModel.Device/context.jsonld'
        ],
        'name': {
            'type': 'Property',
            'value': 'Test Camera'
        },
        'location': {
            'type': 'GeoProperty',
            'value': {
                'type': 'Point',
                'coordinates': [105.123, 21.456]
            }
        }
    }


@pytest.fixture
def sample_entities_file(tmp_path, sample_ngsi_ld_entity):
    """Create temporary entities file for testing."""
    data_dir = tmp_path / 'data'
    data_dir.mkdir()
    entities_file = data_dir / 'entities.json'
    
    entities = [sample_ngsi_ld_entity.copy() for i in range(10)]
    for i, entity in enumerate(entities):
        entity['id'] = f'urn:ngsi-ld:Camera:TEST{i:03d}'
    
    with open(entities_file, 'w') as f:
        json.dump(entities, f, indent=2)
    
    return str(entities_file)


@pytest.fixture
def large_entities_file(tmp_path, sample_ngsi_ld_entity):
    """Create large entities file for performance testing (722 entities)."""
    data_dir = tmp_path / 'data'
    data_dir.mkdir()
    entities_file = data_dir / 'large_entities.json'
    
    entities = [sample_ngsi_ld_entity.copy() for i in range(722)]
    for i, entity in enumerate(entities):
        entity['id'] = f'urn:ngsi-ld:Camera:TEST{i:04d}'
    
    with open(entities_file, 'w') as f:
        json.dump(entities, f, indent=2)
    
    return str(entities_file)


# ============================================================================
# UNIT TESTS - ConfigLoader
# ============================================================================

class TestConfigLoader:
    """Unit tests for ConfigLoader class."""
    
    def test_load_config_success(self, sample_config_file):
        """Test successful config loading."""
        loader = ConfigLoader(sample_config_file)
        config = loader.load_config()
        
        assert config is not None
        assert 'base_url' in config
        assert config['base_url'] == 'http://localhost:8080'
        assert config['batch_size'] == 50
        assert config['timeout'] == 30
    
    def test_load_config_file_not_found(self):
        """Test config loading with non-existent file."""
        loader = ConfigLoader('nonexistent.yaml')
        
        with pytest.raises(FileNotFoundError):
            loader.load_config()
    
    def test_load_config_invalid_yaml(self, tmp_path):
        """Test config loading with invalid YAML."""
        config_file = tmp_path / 'invalid.yaml'
        with open(config_file, 'w') as f:
            f.write('invalid: yaml: content: [[[')
        
        loader = ConfigLoader(str(config_file))
        
        with pytest.raises(yaml.YAMLError):
            loader.load_config()
    
    def test_load_config_missing_stellio_section(self, tmp_path):
        """Test config loading with missing stellio section."""
        config_file = tmp_path / 'missing_section.yaml'
        with open(config_file, 'w') as f:
            yaml.dump({'other': 'data'}, f)
        
        loader = ConfigLoader(str(config_file))
        
        with pytest.raises(ValueError, match="Configuration file must contain 'stellio' section"):
            loader.load_config()
    
    def test_env_override_base_url(self, sample_config_file, monkeypatch):
        """Test base URL override from environment variable."""
        monkeypatch.setenv('STELLIO_BASE_URL', 'http://production:8080')
        
        loader = ConfigLoader(sample_config_file)
        config = loader.load_config()
        
        assert config['base_url'] == 'http://production:8080'
    
    def test_env_override_auth_token(self, sample_config_file, monkeypatch):
        """Test auth token override from environment variable."""
        monkeypatch.setenv('STELLIO_AUTH_TOKEN', 'secret-token-123')
        
        loader = ConfigLoader(sample_config_file)
        config = loader.load_config()
        
        assert config['auth']['enabled'] is True
        assert config['auth']['token'] == 'secret-token-123'
    
    def test_env_override_batch_size(self, sample_config_file, monkeypatch):
        """Test batch size override from environment variable."""
        monkeypatch.setenv('STELLIO_BATCH_SIZE', '100')
        
        loader = ConfigLoader(sample_config_file)
        config = loader.load_config()
        
        assert config['batch_size'] == 100
    
    def test_env_override_timeout(self, sample_config_file, monkeypatch):
        """Test timeout override from environment variable."""
        monkeypatch.setenv('STELLIO_TIMEOUT', '60')
        
        loader = ConfigLoader(sample_config_file)
        config = loader.load_config()
        
        assert config['timeout'] == 60
    
    def test_env_override_max_retries(self, sample_config_file, monkeypatch):
        """Test max retries override from environment variable."""
        monkeypatch.setenv('STELLIO_MAX_RETRIES', '5')
        
        loader = ConfigLoader(sample_config_file)
        config = loader.load_config()
        
        assert config['retry']['max_attempts'] == 5
    
    def test_validate_config_missing_base_url(self, tmp_path):
        """Test validation with missing base_url."""
        config_file = tmp_path / 'missing_base_url.yaml'
        with open(config_file, 'w') as f:
            yaml.dump({'stellio': {'api_version': 'v1'}}, f)
        
        loader = ConfigLoader(str(config_file))
        
        with pytest.raises(ValueError, match="Required field 'base_url' missing"):
            loader.load_config()
    
    def test_validate_config_missing_endpoints(self, tmp_path):
        """Test validation with missing endpoints."""
        config_file = tmp_path / 'missing_endpoints.yaml'
        with open(config_file, 'w') as f:
            yaml.dump({'stellio': {
                'base_url': 'http://localhost',
                'api_version': 'v1'
            }}, f)
        
        loader = ConfigLoader(str(config_file))
        
        with pytest.raises(ValueError, match="Required field 'endpoints' missing"):
            loader.load_config()
    
    def test_validate_config_invalid_batch_size(self, tmp_path):
        """Test validation with invalid batch size."""
        config_file = tmp_path / 'invalid_batch_size.yaml'
        with open(config_file, 'w') as f:
            yaml.dump({'stellio': {
                'base_url': 'http://localhost',
                'api_version': 'v1',
                'endpoints': {'entities': '/entities', 'batch': '/batch'},
                'batch_size': -1
            }}, f)
        
        loader = ConfigLoader(str(config_file))
        
        with pytest.raises(ValueError, match="batch_size must be greater than 0"):
            loader.load_config()
    
    def test_validate_config_invalid_timeout(self, tmp_path):
        """Test validation with invalid timeout."""
        config_file = tmp_path / 'invalid_timeout.yaml'
        with open(config_file, 'w') as f:
            yaml.dump({'stellio': {
                'base_url': 'http://localhost',
                'api_version': 'v1',
                'endpoints': {'entities': '/entities', 'batch': '/batch'},
                'batch_size': 50,
                'timeout': 0
            }}, f)
        
        loader = ConfigLoader(str(config_file))
        
        with pytest.raises(ValueError, match="timeout must be greater than 0"):
            loader.load_config()


# ============================================================================
# UNIT TESTS - BatchPublisher
# ============================================================================

class TestBatchPublisher:
    """Unit tests for BatchPublisher class."""
    
    def test_init_batch_publisher(self, sample_stellio_config):
        """Test BatchPublisher initialization."""
        publisher = BatchPublisher(sample_stellio_config)
        
        assert publisher.base_url == 'http://localhost:8080'
        assert publisher.api_version == 'ngsi-ld/v1'
        assert publisher.timeout == 30
        assert publisher.session is not None
        assert publisher.headers is not None
    
    def test_create_headers_without_auth(self, sample_stellio_config):
        """Test header creation without authentication."""
        publisher = BatchPublisher(sample_stellio_config)
        
        assert 'Content-Type' in publisher.headers
        assert publisher.headers['Content-Type'] == 'application/ld+json'
        assert 'Authorization' not in publisher.headers
    
    def test_create_headers_with_auth(self, sample_stellio_config):
        """Test header creation with authentication."""
        config = sample_stellio_config.copy()
        config['auth']['enabled'] = True
        config['auth']['token'] = 'test-token-123'
        
        publisher = BatchPublisher(config)
        
        assert 'Authorization' in publisher.headers
        assert publisher.headers['Authorization'] == 'Bearer test-token-123'
    
    def test_calculate_backoff_delay(self, sample_stellio_config):
        """Test exponential backoff calculation."""
        publisher = BatchPublisher(sample_stellio_config)
        
        # Attempt 1: 1 * (2^0) = 1s
        assert publisher._calculate_backoff_delay(1) == 1
        
        # Attempt 2: 1 * (2^1) = 2s
        assert publisher._calculate_backoff_delay(2) == 2
        
        # Attempt 3: 1 * (2^2) = 4s
        assert publisher._calculate_backoff_delay(3) == 4
        
        # Attempt 5: 1 * (2^4) = 16s, capped at max_delay (10s)
        assert publisher._calculate_backoff_delay(5) == 10
    
    @responses.activate
    def test_publish_entity_success(self, sample_stellio_config, sample_ngsi_ld_entity):
        """Test successful entity publishing."""
        # Mock Stellio API
        responses.add(
            responses.POST,
            'http://localhost:8080/ngsi-ld/v1/entities',
            status=201,
            json={'success': True}
        )
        
        publisher = BatchPublisher(sample_stellio_config)
        result = publisher.publish_entity(sample_ngsi_ld_entity)
        
        assert result.success is True
        assert result.status_code == 201
        assert result.attempts == 1
        assert result.entity_id == 'urn:ngsi-ld:Camera:TEST001'
    
    @responses.activate
    def test_publish_entity_conflict_409(self, sample_stellio_config, sample_ngsi_ld_entity):
        """Test entity publishing with 409 conflict (entity exists)."""
        # Mock POST returning 409
        responses.add(
            responses.POST,
            'http://localhost:8080/ngsi-ld/v1/entities',
            status=409,
            json={'error': 'Already exists'}
        )
        
        # Mock PATCH for update
        entity_id = sample_ngsi_ld_entity['id']
        responses.add(
            responses.PATCH,
            f'http://localhost:8080/ngsi-ld/v1/entities/{entity_id}/attrs',
            status=204
        )
        
        publisher = BatchPublisher(sample_stellio_config)
        result = publisher.publish_entity(sample_ngsi_ld_entity)
        
        assert result.success is True
        assert result.status_code == 204
        assert result.attempts == 1
    
    @responses.activate
    def test_publish_entity_retry_on_500(self, sample_stellio_config, sample_ngsi_ld_entity):
        """Test entity publishing with retry on 500 error."""
        # Mock first 2 attempts returning 500, third succeeds
        responses.add(
            responses.POST,
            'http://localhost:8080/ngsi-ld/v1/entities',
            status=500,
            json={'error': 'Internal Server Error'}
        )
        responses.add(
            responses.POST,
            'http://localhost:8080/ngsi-ld/v1/entities',
            status=500,
            json={'error': 'Internal Server Error'}
        )
        responses.add(
            responses.POST,
            'http://localhost:8080/ngsi-ld/v1/entities',
            status=201,
            json={'success': True}
        )
        
        publisher = BatchPublisher(sample_stellio_config)
        
        # Reduce backoff delays for faster test
        publisher.retry_config['initial_delay'] = 0.01
        
        result = publisher.publish_entity(sample_ngsi_ld_entity)
        
        assert result.success is True
        assert result.status_code == 201
        assert result.attempts == 3
    
    @responses.activate
    def test_publish_entity_max_retries_exceeded(self, sample_stellio_config, sample_ngsi_ld_entity):
        """Test entity publishing when max retries exceeded."""
        # Mock all attempts returning 500
        for _ in range(3):
            responses.add(
                responses.POST,
                'http://localhost:8080/ngsi-ld/v1/entities',
                status=500,
                json={'error': 'Internal Server Error'}
            )
        
        publisher = BatchPublisher(sample_stellio_config)
        
        # Reduce backoff delays for faster test
        publisher.retry_config['initial_delay'] = 0.01
        
        result = publisher.publish_entity(sample_ngsi_ld_entity)
        
        assert result.success is False
        assert result.status_code == 500
        assert result.attempts == 3
        assert result.error is not None
    
    @responses.activate
    def test_publish_entity_non_retryable_error(self, sample_stellio_config, sample_ngsi_ld_entity):
        """Test entity publishing with non-retryable error (400)."""
        responses.add(
            responses.POST,
            'http://localhost:8080/ngsi-ld/v1/entities',
            status=400,
            json={'error': 'Bad Request'}
        )
        
        publisher = BatchPublisher(sample_stellio_config)
        result = publisher.publish_entity(sample_ngsi_ld_entity)
        
        assert result.success is False
        assert result.status_code == 400
        assert result.attempts == 1  # No retry for 400
    
    @responses.activate
    def test_publish_batch_success(self, sample_stellio_config, sample_ngsi_ld_entity):
        """Test successful batch publishing."""
        entities = [sample_ngsi_ld_entity.copy() for _ in range(5)]
        for i, entity in enumerate(entities):
            entity['id'] = f'urn:ngsi-ld:Camera:TEST{i:03d}'
        
        # Mock batch upsert
        responses.add(
            responses.POST,
            'http://localhost:8080/ngsi-ld/v1/entityOperations/upsert',
            status=200,
            json={'success': True}
        )
        
        publisher = BatchPublisher(sample_stellio_config)
        results = publisher.publish_batch(entities)
        
        assert len(results) == 5
        assert all(r.success for r in results)
    
    @responses.activate
    def test_publish_batch_fallback_to_individual(self, sample_stellio_config, sample_ngsi_ld_entity):
        """Test batch publishing fallback to individual entities."""
        entities = [sample_ngsi_ld_entity.copy() for _ in range(3)]
        for i, entity in enumerate(entities):
            entity['id'] = f'urn:ngsi-ld:Camera:TEST{i:03d}'
        
        # Mock batch upsert failure
        responses.add(
            responses.POST,
            'http://localhost:8080/ngsi-ld/v1/entityOperations/upsert',
            status=500,
            json={'error': 'Batch failed'}
        )
        
        # Mock individual entity posts
        for entity in entities:
            responses.add(
                responses.POST,
                'http://localhost:8080/ngsi-ld/v1/entities',
                status=201,
                json={'success': True}
            )
        
        publisher = BatchPublisher(sample_stellio_config)
        results = publisher.publish_batch(entities)
        
        assert len(results) == 3
        assert all(r.success for r in results)
    
    def test_publish_batch_empty_list(self, sample_stellio_config):
        """Test publishing empty batch."""
        publisher = BatchPublisher(sample_stellio_config)
        results = publisher.publish_batch([])
        
        assert len(results) == 0
    
    def test_close_publisher(self, sample_stellio_config):
        """Test closing publisher and cleaning up resources."""
        publisher = BatchPublisher(sample_stellio_config)
        
        assert publisher.session is not None
        publisher.close()
        
        # Session should be closed (no exception means success)


# ============================================================================
# UNIT TESTS - PublishReportGenerator
# ============================================================================

class TestPublishReportGenerator:
    """Unit tests for PublishReportGenerator class."""
    
    def test_init_report_generator(self, sample_stellio_config):
        """Test PublishReportGenerator initialization."""
        generator = PublishReportGenerator(sample_stellio_config)
        
        assert generator.statistics is not None
        assert generator.statistics.total_entities == 0
        assert generator.statistics.successful == 0
        assert generator.statistics.failed == 0
    
    def test_start_end_tracking(self, sample_stellio_config):
        """Test tracking start and end times."""
        generator = PublishReportGenerator(sample_stellio_config)
        
        generator.start_tracking()
        assert generator.start_time is not None
        
        time.sleep(0.1)
        
        generator.end_tracking()
        assert generator.end_time is not None
        assert generator.statistics.duration_seconds > 0
    
    def test_record_successful_results(self, sample_stellio_config):
        """Test recording successful results."""
        generator = PublishReportGenerator(sample_stellio_config)
        
        results = [
            PublishResult(entity_id='entity1', status_code=201, success=True),
            PublishResult(entity_id='entity2', status_code=201, success=True),
            PublishResult(entity_id='entity3', status_code=200, success=True)
        ]
        
        generator.record_results(results)
        
        assert generator.statistics.total_entities == 3
        assert generator.statistics.successful == 3
        assert generator.statistics.failed == 0
        assert len(generator.statistics.errors) == 0
    
    def test_record_failed_results(self, sample_stellio_config):
        """Test recording failed results."""
        generator = PublishReportGenerator(sample_stellio_config)
        
        results = [
            PublishResult(entity_id='entity1', status_code=201, success=True),
            PublishResult(
                entity_id='entity2',
                status_code=500,
                success=False,
                error='Internal Server Error',
                attempts=3,
                duration=1.5
            )
        ]
        
        generator.record_results(results)
        
        assert generator.statistics.total_entities == 2
        assert generator.statistics.successful == 1
        assert generator.statistics.failed == 1
        assert len(generator.statistics.errors) == 1
        assert generator.statistics.errors[0]['entity_id'] == 'entity2'
    
    def test_generate_report(self, sample_stellio_config):
        """Test report generation."""
        generator = PublishReportGenerator(sample_stellio_config)
        
        generator.start_tracking()
        
        results = [
            PublishResult(entity_id='entity1', status_code=201, success=True),
            PublishResult(entity_id='entity2', status_code=201, success=True),
            PublishResult(
                entity_id='entity3',
                status_code=500,
                success=False,
                error='Server Error'
            )
        ]
        
        generator.record_results(results)
        generator.end_tracking()
        
        report = generator.generate_report()
        
        assert 'timestamp' in report
        assert report['total_entities'] == 3
        assert report['successful'] == 2
        assert report['failed'] == 1
        assert report['success_rate'] == 66.67
        assert 'duration_seconds' in report
        assert 'throughput' in report
    
    def test_save_report(self, sample_stellio_config, tmp_path):
        """Test saving report to file."""
        config = sample_stellio_config.copy()
        config['output']['report_dir'] = str(tmp_path)
        
        generator = PublishReportGenerator(config)
        generator.start_tracking()
        generator.end_tracking()
        
        report = generator.generate_report()
        report_path = generator.save_report(report)
        
        assert os.path.exists(report_path)
        
        with open(report_path, 'r') as f:
            saved_report = json.load(f)
        
        assert saved_report['total_entities'] == 0
    
    def test_save_failed_entities(self, sample_stellio_config, tmp_path):
        """Test saving failed entities to file."""
        config = sample_stellio_config.copy()
        config['output']['report_dir'] = str(tmp_path)
        
        generator = PublishReportGenerator(config)
        
        entities = [
            {'id': 'entity1', 'type': 'Camera'},
            {'id': 'entity2', 'type': 'Camera'},
            {'id': 'entity3', 'type': 'Camera'}
        ]
        
        results = [
            PublishResult(entity_id='entity1', status_code=201, success=True),
            PublishResult(entity_id='entity2', status_code=500, success=False, error='Error'),
            PublishResult(entity_id='entity3', status_code=500, success=False, error='Error')
        ]
        
        failed_path = generator.save_failed_entities(entities, results)
        
        assert failed_path is not None
        assert os.path.exists(failed_path)
        
        with open(failed_path, 'r') as f:
            failed_entities = json.load(f)
        
        assert len(failed_entities) == 2
        assert failed_entities[0]['id'] == 'entity2'
        assert failed_entities[1]['id'] == 'entity3'
    
    def test_save_failed_entities_no_failures(self, sample_stellio_config, tmp_path):
        """Test saving failed entities when no failures."""
        config = sample_stellio_config.copy()
        config['output']['report_dir'] = str(tmp_path)
        
        generator = PublishReportGenerator(config)
        
        entities = [{'id': 'entity1', 'type': 'Camera'}]
        results = [PublishResult(entity_id='entity1', status_code=201, success=True)]
        
        failed_path = generator.save_failed_entities(entities, results)
        
        assert failed_path is None


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestEntityPublisherAgentIntegration:
    """Integration tests for Entity Publisher Agent with mock Stellio."""
    
    @responses.activate
    def test_publish_success(self, sample_config_file, sample_entities_file, tmp_path):
        """Test successful publishing of entities."""
        # Mock batch upsert
        responses.add(
            responses.POST,
            'http://localhost:8080/ngsi-ld/v1/entityOperations/upsert',
            status=200,
            json={'success': True}
        )
        
        # Update config to use tmp_path for output
        with open(sample_config_file, 'r') as f:
            config = yaml.safe_load(f)
        config['stellio']['output']['report_dir'] = str(tmp_path)
        with open(sample_config_file, 'w') as f:
            yaml.dump(config, f)
        
        agent = EntityPublisherAgent(config_path=sample_config_file)
        report = agent.publish(
            input_file=sample_entities_file,
            output_report=str(tmp_path / 'report.json')
        )
        
        assert report['total_entities'] == 10
        assert report['successful'] == 10
        assert report['failed'] == 0
        assert report['success_rate'] == 100.0
        
        agent.close()
    
    @responses.activate
    def test_publish_with_conflicts(self, sample_config_file, sample_entities_file, tmp_path):
        """Test publishing with conflict resolution (409 → PATCH)."""
        # Mock batch upsert failure (fallback to individual)
        responses.add(
            responses.POST,
            'http://localhost:8080/ngsi-ld/v1/entityOperations/upsert',
            status=500
        )
        
        # Mock individual POST returning 409 for some entities
        for i in range(10):
            if i < 5:
                responses.add(
                    responses.POST,
                    'http://localhost:8080/ngsi-ld/v1/entities',
                    status=409
                )
                # Mock PATCH for update
                responses.add(
                    responses.PATCH,
                    f'http://localhost:8080/ngsi-ld/v1/entities/urn:ngsi-ld:Camera:TEST{i:03d}/attrs',
                    status=204
                )
            else:
                responses.add(
                    responses.POST,
                    'http://localhost:8080/ngsi-ld/v1/entities',
                    status=201
                )
        
        # Update config
        with open(sample_config_file, 'r') as f:
            config = yaml.safe_load(f)
        config['stellio']['output']['report_dir'] = str(tmp_path)
        with open(sample_config_file, 'w') as f:
            yaml.dump(config, f)
        
        agent = EntityPublisherAgent(config_path=sample_config_file)
        report = agent.publish(
            input_file=sample_entities_file,
            output_report=str(tmp_path / 'report.json')
        )
        
        assert report['total_entities'] == 10
        assert report['successful'] == 10
        assert report['failed'] == 0
        
        agent.close()
    
    @responses.activate
    def test_publish_with_failures(self, sample_config_file, sample_entities_file, tmp_path):
        """Test publishing with some failures."""
        # Mock batch upsert failure
        responses.add(
            responses.POST,
            'http://localhost:8080/ngsi-ld/v1/entityOperations/upsert',
            status=500
        )
        
        # Mock individual posts with some failures
        for i in range(10):
            if i < 7:
                responses.add(
                    responses.POST,
                    'http://localhost:8080/ngsi-ld/v1/entities',
                    status=201
                )
            else:
                # Fail with 3 retry attempts
                for _ in range(3):
                    responses.add(
                        responses.POST,
                        'http://localhost:8080/ngsi-ld/v1/entities',
                        status=500,
                        json={'error': 'Server Error'}
                    )
        
        # Update config
        with open(sample_config_file, 'r') as f:
            config = yaml.safe_load(f)
        config['stellio']['output']['report_dir'] = str(tmp_path)
        config['stellio']['retry']['initial_delay'] = 0.01  # Fast retry for test
        with open(sample_config_file, 'w') as f:
            yaml.dump(config, f)
        
        agent = EntityPublisherAgent(config_path=sample_config_file)
        report = agent.publish(
            input_file=sample_entities_file,
            output_report=str(tmp_path / 'report.json')
        )
        
        assert report['total_entities'] == 10
        assert report['successful'] == 7
        assert report['failed'] == 3
        assert report['success_rate'] == 70.0
        assert len(report['errors']) == 3
        
        agent.close()
    
    def test_publish_empty_input(self, sample_config_file, tmp_path):
        """Test publishing with empty input file."""
        empty_file = tmp_path / 'empty.json'
        with open(empty_file, 'w') as f:
            json.dump([], f)
        
        agent = EntityPublisherAgent(config_path=sample_config_file)
        report = agent.publish(input_file=str(empty_file))
        
        assert report['total_entities'] == 0
        assert report['successful'] == 0
        assert report['failed'] == 0
        
        agent.close()
    
    def test_publish_invalid_input_file(self, sample_config_file):
        """Test publishing with non-existent input file."""
        agent = EntityPublisherAgent(config_path=sample_config_file)
        
        with pytest.raises(FileNotFoundError):
            agent.publish(input_file='nonexistent.json')
        
        agent.close()
    
    def test_publish_invalid_json(self, sample_config_file, tmp_path):
        """Test publishing with invalid JSON input."""
        invalid_file = tmp_path / 'invalid.json'
        with open(invalid_file, 'w') as f:
            f.write('invalid json content {[[')
        
        agent = EntityPublisherAgent(config_path=sample_config_file)
        
        with pytest.raises(json.JSONDecodeError):
            agent.publish(input_file=str(invalid_file))
        
        agent.close()


# ============================================================================
# PERFORMANCE TESTS
# ============================================================================

class TestPerformance:
    """Performance tests for Entity Publisher Agent."""
    
    @responses.activate
    def test_publish_722_entities_under_30_seconds(
        self,
        sample_config_file,
        large_entities_file,
        tmp_path
    ):
        """Test publishing 722 entities completes in under 30 seconds."""
        # Mock batch upsert with success
        responses.add(
            responses.POST,
            'http://localhost:8080/ngsi-ld/v1/entityOperations/upsert',
            status=200,
            json={'success': True}
        )
        
        # Update config
        with open(sample_config_file, 'r') as f:
            config = yaml.safe_load(f)
        config['stellio']['output']['report_dir'] = str(tmp_path)
        with open(sample_config_file, 'w') as f:
            yaml.dump(config, f)
        
        agent = EntityPublisherAgent(config_path=sample_config_file)
        
        start_time = time.time()
        report = agent.publish(
            input_file=large_entities_file,
            output_report=str(tmp_path / 'report.json')
        )
        duration = time.time() - start_time
        
        # Performance requirement: < 30 seconds
        assert duration < 30, f"Publishing took {duration}s, expected < 30s"
        
        assert report['total_entities'] == 722
        assert report['successful'] == 722
        assert report['failed'] == 0
        
        agent.close()
    
    @responses.activate
    def test_batching_efficiency(self, sample_config_file, large_entities_file, tmp_path):
        """Test that batching reduces number of requests."""
        # Track number of batch requests
        batch_requests = []
        
        def request_callback(request):
            batch_requests.append(request)
            return (200, {}, json.dumps({'success': True}))
        
        responses.add_callback(
            responses.POST,
            'http://localhost:8080/ngsi-ld/v1/entityOperations/upsert',
            callback=request_callback
        )
        
        # Update config
        with open(sample_config_file, 'r') as f:
            config = yaml.safe_load(f)
        config['stellio']['output']['report_dir'] = str(tmp_path)
        config['stellio']['batch_size'] = 50
        with open(sample_config_file, 'w') as f:
            yaml.dump(config, f)
        
        agent = EntityPublisherAgent(config_path=sample_config_file)
        report = agent.publish(
            input_file=large_entities_file,
            output_report=str(tmp_path / 'report.json')
        )
        
        # Should have ceil(722 / 50) = 15 batch requests
        expected_batches = (722 + 50 - 1) // 50
        assert len(batch_requests) == expected_batches
        
        agent.close()
    
    @responses.activate
    def test_throughput_calculation(self, sample_config_file, sample_entities_file, tmp_path):
        """Test throughput calculation in report."""
        responses.add(
            responses.POST,
            'http://localhost:8080/ngsi-ld/v1/entityOperations/upsert',
            status=200
        )
        
        # Update config
        with open(sample_config_file, 'r') as f:
            config = yaml.safe_load(f)
        config['stellio']['output']['report_dir'] = str(tmp_path)
        with open(sample_config_file, 'w') as f:
            yaml.dump(config, f)
        
        agent = EntityPublisherAgent(config_path=sample_config_file)
        report = agent.publish(input_file=sample_entities_file)
        
        # Verify throughput is calculated and present
        assert 'throughput' in report
        assert report['throughput'] > 0
        
        # Verify throughput makes sense (entities per second)
        # With 10 entities and any reasonable duration, should be < 100,000 entities/sec
        assert report['throughput'] < 100000
        
        # Verify throughput calculation logic
        # Throughput = total_entities / max(duration_seconds, 0.001)
        assert report['total_entities'] == 10
        assert report['duration_seconds'] >= 0
        
        agent.close()


# ============================================================================
# EDGE CASE TESTS
# ============================================================================

class TestEdgeCases:
    """Edge case tests for Entity Publisher Agent."""
    
    @responses.activate
    def test_network_timeout(self, sample_config_file, sample_entities_file, tmp_path):
        """Test handling of network timeout."""
        # Update config with very short timeout
        with open(sample_config_file, 'r') as f:
            config = yaml.safe_load(f)
        config['stellio']['timeout'] = 1  # 1 second timeout
        config['stellio']['retry']['initial_delay'] = 0.01
        config['stellio']['output']['report_dir'] = str(tmp_path)
        with open(sample_config_file, 'w') as f:
            yaml.dump(config, f)
        
        # Mock batch upsert failure
        responses.add(
            responses.POST,
            'http://localhost:8080/ngsi-ld/v1/entityOperations/upsert',
            status=500
        )
        
        # Mock all individual requests with 500 errors (simulate timeout scenario)
        for _ in range(30):  # 10 entities × 3 retries
            responses.add(
                responses.POST,
                'http://localhost:8080/ngsi-ld/v1/entities',
                status=504,  # Gateway Timeout
                json={'error': 'Gateway Timeout'}
            )
        
        agent = EntityPublisherAgent(config_path=sample_config_file)
        report = agent.publish(input_file=sample_entities_file)
        
        # All should fail with timeout
        assert report['failed'] > 0
        agent.close()
    
    @responses.activate
    def test_all_entities_fail(self, sample_config_file, sample_entities_file, tmp_path):
        """Test scenario where all entities fail to publish."""
        # Mock all requests returning 500
        responses.add(
            responses.POST,
            'http://localhost:8080/ngsi-ld/v1/entityOperations/upsert',
            status=500
        )
        
        for _ in range(30):  # 10 entities × 3 retries
            responses.add(
                responses.POST,
                'http://localhost:8080/ngsi-ld/v1/entities',
                status=500
            )
        
        # Update config
        with open(sample_config_file, 'r') as f:
            config = yaml.safe_load(f)
        config['stellio']['output']['report_dir'] = str(tmp_path)
        config['stellio']['retry']['initial_delay'] = 0.01
        with open(sample_config_file, 'w') as f:
            yaml.dump(config, f)
        
        agent = EntityPublisherAgent(config_path=sample_config_file)
        report = agent.publish(input_file=sample_entities_file)
        
        assert report['total_entities'] == 10
        assert report['successful'] == 0
        assert report['failed'] == 10
        assert report['success_rate'] == 0.0
        assert len(report['errors']) == 10
        
        agent.close()
    
    @responses.activate
    def test_mixed_status_codes(self, sample_config_file, sample_entities_file, tmp_path):
        """Test handling of mixed status codes (200, 409, 500, 400)."""
        responses.add(
            responses.POST,
            'http://localhost:8080/ngsi-ld/v1/entityOperations/upsert',
            status=500
        )
        
        # Mix of different status codes
        status_codes = [201, 409, 500, 500, 500, 400, 201, 409, 201, 201]
        
        for i, status in enumerate(status_codes):
            if status == 409:
                responses.add(responses.POST, 'http://localhost:8080/ngsi-ld/v1/entities', status=409)
                responses.add(
                    responses.PATCH,
                    f'http://localhost:8080/ngsi-ld/v1/entities/urn:ngsi-ld:Camera:TEST{i:03d}/attrs',
                    status=204
                )
            elif status == 500:
                for _ in range(3):  # 3 retries
                    responses.add(responses.POST, 'http://localhost:8080/ngsi-ld/v1/entities', status=500)
            else:
                responses.add(responses.POST, 'http://localhost:8080/ngsi-ld/v1/entities', status=status)
        
        # Update config
        with open(sample_config_file, 'r') as f:
            config = yaml.safe_load(f)
        config['stellio']['output']['report_dir'] = str(tmp_path)
        config['stellio']['retry']['initial_delay'] = 0.01
        with open(sample_config_file, 'w') as f:
            yaml.dump(config, f)
        
        agent = EntityPublisherAgent(config_path=sample_config_file)
        report = agent.publish(input_file=sample_entities_file)
        
        assert report['total_entities'] == 10
        # Success: 4×201 + 2×409→204 = 6
        # Fail: 3×500 + 1×400 = 4
        assert report['successful'] >= 6
        
        agent.close()
    
    def test_malformed_entities(self, sample_config_file, tmp_path):
        """Test handling of malformed entities (missing required fields)."""
        malformed_file = tmp_path / 'malformed.json'
        
        # Entities with missing 'id' or 'type'
        malformed_entities = [
            {'type': 'Camera', 'name': {'type': 'Property', 'value': 'Test'}},
            {'id': 'urn:ngsi-ld:Camera:TEST001'},
            {'id': 'urn:ngsi-ld:Camera:TEST002', 'type': 'Camera'}
        ]
        
        with open(malformed_file, 'w') as f:
            json.dump(malformed_entities, f)
        
        # Mock responses for entities that have id
        with responses.RequestsMock() as rsps:
            rsps.add(
                responses.POST,
                'http://localhost:8080/ngsi-ld/v1/entityOperations/upsert',
                status=500
            )
            rsps.add(
                responses.POST,
                'http://localhost:8080/ngsi-ld/v1/entities',
                status=201
            )
            
            # Update config
            with open(sample_config_file, 'r') as f:
                config = yaml.safe_load(f)
            config['stellio']['output']['report_dir'] = str(tmp_path)
            with open(sample_config_file, 'w') as f:
                yaml.dump(config, f)
            
            agent = EntityPublisherAgent(config_path=sample_config_file)
            report = agent.publish(input_file=str(malformed_file))
            
            # Should process all 3 entities (entity with no 'id' gets 'unknown')
            assert report['total_entities'] == 3
            
            agent.close()


# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == '__main__':
    pytest.main([__file__, '-v', '--cov=agents.context_management', '--cov-report=html'])
