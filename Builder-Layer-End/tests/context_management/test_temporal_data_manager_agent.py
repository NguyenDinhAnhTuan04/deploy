"""
Comprehensive Test Suite for Temporal Data Manager Agent

Tests cover:
- Configuration loading and validation
- Retention logic (should_aggregate, should_archive, should_delete)
- Aggregation calculations (mean, max, mode)
- Archive path generation
- Stellio temporal API (mocked)
- Cleanup simulation
- Data integrity (no loss, accuracy, retrieval)
- Edge cases

Author: Builder Layer Agent
Version: 1.0.0
"""

import gzip
import json
import pytest
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List
from unittest.mock import Mock, patch

# Import agent modules
from agents.context_management.temporal_data_manager_agent import (
    TemporalConfig,
    TemporalDataStore,
    AggregationEngine,
    RetentionManager,
    ArchiveManager,
    TemporalDataManagerAgent,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def temp_config():
    """Create temporary configuration file."""
    config_content = """
temporal_data_manager:
  stellio:
    base_url: "http://localhost:8080"
    timeout: 10
    max_retries: 3
    temporal_endpoint: "/ngsi-ld/v1/temporal/entities/{entity_id}/attrs"
    batch:
      enabled: true
      max_batch_size: 100
    headers:
      Content-Type: "application/ld+json"
  
  retention:
    detailed:
      enabled: true
      period: 30
      resolution: "full"
    
    aggregated:
      enabled: true
      period: 60
      resolution: "hourly"
      start_after: 30
    
    archived:
      enabled: true
      period: 365
      storage: "filesystem"
      start_after: 90
      filesystem:
        base_path: "/tmp/test_archive"
        compression: "gzip"
    
    deletion:
      enabled: true
      start_after: 455
  
  aggregation:
    enabled: true
    resolutions:
      hourly:
        window: 3600
      daily:
        window: 86400
    
    metrics:
      - name: "intensity"
        method: "mean"
        precision: 2
        fill_missing: true
        fill_value: 0.0
      
      - name: "occupancy"
        method: "max"
        precision: 2
      
      - name: "congested"
        method: "mode"
        fill_missing: true
        fill_value: false
"""

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(config_content)
        temp_path = f.name

    yield temp_path

    # Cleanup
    Path(temp_path).unlink()


@pytest.fixture
def sample_observations():
    """Create sample temporal observations."""
    now = datetime.utcnow()

    observations = []
    for i in range(10):
        obs = {
            "observedAt": (now - timedelta(minutes=i)).isoformat() + "Z",
            "intensity": 0.5 + (i * 0.05),
            "occupancy": 0.6 + (i * 0.02),
            "congested": i % 2 == 0,
        }
        observations.append(obs)

    return observations


@pytest.fixture
def old_observations():
    """Create old observations for retention testing."""
    now = datetime.utcnow()

    # Create observations at different ages
    observations = []

    # 5 days old (detailed)
    for i in range(5):
        observations.append(
            {
                "observedAt": (now - timedelta(days=5, minutes=i)).isoformat() + "Z",
                "intensity": 0.5,
            }
        )

    # 35 days old (should aggregate)
    for i in range(5):
        observations.append(
            {
                "observedAt": (now - timedelta(days=35, minutes=i)).isoformat() + "Z",
                "intensity": 0.6,
            }
        )

    # 100 days old (should archive)
    for i in range(5):
        observations.append(
            {
                "observedAt": (now - timedelta(days=100, minutes=i)).isoformat() + "Z",
                "intensity": 0.7,
            }
        )

    # 500 days old (should delete)
    for i in range(5):
        observations.append(
            {
                "observedAt": (now - timedelta(days=500, minutes=i)).isoformat() + "Z",
                "intensity": 0.8,
            }
        )

    return observations


# ============================================================================
# Unit Tests - Configuration
# ============================================================================


def test_config_load(temp_config):
    """Test configuration loading."""
    config = TemporalConfig(temp_config)

    assert config is not None
    assert config.temporal_manager is not None


def test_config_stellio(temp_config):
    """Test Stellio configuration."""
    config = TemporalConfig(temp_config)
    stellio = config.get_stellio_config()

    assert stellio["base_url"] == "http://localhost:8080"
    assert stellio["timeout"] == 10


def test_config_retention(temp_config):
    """Test retention configuration."""
    config = TemporalConfig(temp_config)
    retention = config.get_retention_config()

    assert retention["detailed"]["period"] == 30
    assert retention["aggregated"]["start_after"] == 30
    assert retention["archived"]["start_after"] == 90


def test_config_aggregation(temp_config):
    """Test aggregation configuration."""
    config = TemporalConfig(temp_config)
    aggregation = config.get_aggregation_config()

    assert aggregation["enabled"] is True
    assert len(aggregation["metrics"]) == 3


def test_config_invalid_file():
    """Test configuration with invalid file."""
    with pytest.raises(FileNotFoundError):
        TemporalConfig("nonexistent.yaml")


# ============================================================================
# Unit Tests - RetentionManager
# ============================================================================


def test_retention_manager_init(temp_config):
    """Test RetentionManager initialization."""
    config = TemporalConfig(temp_config)
    manager = RetentionManager(config)

    assert manager.detailed_days == 30
    assert manager.aggregated_start == 30
    assert manager.archived_start == 90


def test_should_aggregate_recent(temp_config):
    """Test should_aggregate with recent data."""
    config = TemporalConfig(temp_config)
    manager = RetentionManager(config)

    # 10 days old - should NOT aggregate
    timestamp = datetime.utcnow() - timedelta(days=10)
    assert manager.should_aggregate(timestamp) is False


def test_should_aggregate_old(temp_config):
    """Test should_aggregate with old data."""
    config = TemporalConfig(temp_config)
    manager = RetentionManager(config)

    # 35 days old - should aggregate
    timestamp = datetime.utcnow() - timedelta(days=35)
    assert manager.should_aggregate(timestamp) is True


def test_should_archive(temp_config):
    """Test should_archive."""
    config = TemporalConfig(temp_config)
    manager = RetentionManager(config)

    # 100 days old - should archive
    timestamp = datetime.utcnow() - timedelta(days=100)
    assert manager.should_archive(timestamp) is True

    # 50 days old - should NOT archive
    timestamp = datetime.utcnow() - timedelta(days=50)
    assert manager.should_archive(timestamp) is False


def test_should_delete(temp_config):
    """Test should_delete."""
    config = TemporalConfig(temp_config)
    manager = RetentionManager(config)

    # 500 days old - should delete
    timestamp = datetime.utcnow() - timedelta(days=500)
    assert manager.should_delete(timestamp) is True

    # 100 days old - should NOT delete
    timestamp = datetime.utcnow() - timedelta(days=100)
    assert manager.should_delete(timestamp) is False


def test_get_cutoff_dates(temp_config):
    """Test get_cutoff_dates."""
    config = TemporalConfig(temp_config)
    manager = RetentionManager(config)

    cutoffs = manager.get_cutoff_dates()

    assert "detailed" in cutoffs
    assert "aggregated" in cutoffs
    assert "archived" in cutoffs
    assert "deletion" in cutoffs


# ============================================================================
# Unit Tests - AggregationEngine
# ============================================================================


def test_aggregation_engine_init(temp_config):
    """Test AggregationEngine initialization."""
    config = TemporalConfig(temp_config)
    engine = AggregationEngine(config)

    assert len(engine.metrics) == 3


def test_aggregate_observations_mean(temp_config):
    """Test aggregation with mean method."""
    config = TemporalConfig(temp_config)
    engine = AggregationEngine(config)

    # Create observations in same hour
    now = datetime.utcnow()
    observations = []

    for i in range(5):
        observations.append(
            {
                "observedAt": (now - timedelta(minutes=i)).isoformat() + "Z",
                "intensity": 0.5 + (i * 0.1),
                "occupancy": 0.6,
                "congested": True,
            }
        )

    # Aggregate to hourly
    aggregated = engine.aggregate_observations(observations, "hourly")

    assert len(aggregated) == 1
    assert "intensity" in aggregated[0]
    assert "observation_count" in aggregated[0]
    assert aggregated[0]["observation_count"] == 5

    # Check mean calculation
    expected_mean = (0.5 + 0.6 + 0.7 + 0.8 + 0.9) / 5
    assert abs(aggregated[0]["intensity"] - expected_mean) < 0.01


def test_aggregate_observations_max(temp_config):
    """Test aggregation with max method."""
    config = TemporalConfig(temp_config)
    engine = AggregationEngine(config)

    now = datetime.utcnow()
    observations = []

    for i in range(5):
        observations.append(
            {
                "observedAt": (now - timedelta(minutes=i)).isoformat() + "Z",
                "occupancy": 0.5 + (i * 0.1),
            }
        )

    aggregated = engine.aggregate_observations(observations, "hourly")

    assert aggregated[0]["occupancy"] == 0.9  # Max value


def test_aggregate_observations_mode(temp_config):
    """Test aggregation with mode method."""
    config = TemporalConfig(temp_config)
    engine = AggregationEngine(config)

    now = datetime.utcnow()
    observations = []

    # 3 True, 2 False
    for i in range(5):
        observations.append(
            {
                "observedAt": (now - timedelta(minutes=i)).isoformat() + "Z",
                "congested": i < 3,
            }
        )

    aggregated = engine.aggregate_observations(observations, "hourly")

    assert aggregated[0]["congested"] is True  # Most common


def test_aggregate_empty_observations(temp_config):
    """Test aggregation with empty list."""
    config = TemporalConfig(temp_config)
    engine = AggregationEngine(config)

    aggregated = engine.aggregate_observations([], "hourly")

    assert len(aggregated) == 0


def test_aggregate_multiple_windows(temp_config):
    """Test aggregation across multiple time windows."""
    config = TemporalConfig(temp_config)
    engine = AggregationEngine(config)

    now = datetime.utcnow()
    observations = []

    # 2 hours of data
    for hour in range(2):
        for minute in range(5):
            observations.append(
                {
                    "observedAt": (
                        now - timedelta(hours=hour, minutes=minute)
                    ).isoformat()
                    + "Z",
                    "intensity": 0.5,
                }
            )

    aggregated = engine.aggregate_observations(observations, "hourly")

    assert len(aggregated) == 2  # 2 hourly windows


# ============================================================================
# Unit Tests - ArchiveManager
# ============================================================================


def test_archive_manager_init(temp_config):
    """Test ArchiveManager initialization."""
    config = TemporalConfig(temp_config)
    manager = ArchiveManager(config)

    assert manager.storage == "filesystem"


def test_generate_archive_path(temp_config):
    """Test archive path generation."""
    config = TemporalConfig(temp_config)
    manager = ArchiveManager(config)

    entity_id = "urn:ngsi-ld:Camera:TTH406"
    date = datetime(2025, 11, 1)

    path = manager.generate_archive_path(entity_id, date)

    assert "Camera" in str(path)
    assert "TTH406" in str(path)
    assert "2025" in str(path)
    assert "11" in str(path)
    assert "01.json.gz" in str(path)


def test_archive_and_retrieve_data(temp_config, sample_observations, tmp_path):
    """Test archiving and retrieving data."""
    config = TemporalConfig(temp_config)
    manager = ArchiveManager(config)

    # Override base path to temp directory
    manager.base_path = tmp_path

    entity_id = "urn:ngsi-ld:Camera:TTH406"
    date = datetime(2025, 11, 1)

    # Archive
    success = manager.archive_data(entity_id, date, sample_observations)
    assert success is True

    # Retrieve
    retrieved = manager.retrieve_archived_data(entity_id, date)
    assert retrieved is not None
    assert len(retrieved) == len(sample_observations)


def test_retrieve_nonexistent_archive(temp_config, tmp_path):
    """Test retrieving nonexistent archive."""
    config = TemporalConfig(temp_config)
    manager = ArchiveManager(config)
    manager.base_path = tmp_path

    entity_id = "urn:ngsi-ld:Camera:TTH999"
    date = datetime(2020, 1, 1)

    retrieved = manager.retrieve_archived_data(entity_id, date)
    assert retrieved is None


# ============================================================================
# Unit Tests - TemporalDataStore
# ============================================================================


def test_temporal_data_store_init(temp_config):
    """Test TemporalDataStore initialization."""
    config = TemporalConfig(temp_config)
    store = TemporalDataStore(config)

    assert store.base_url == "http://localhost:8080"
    assert store.timeout == 10


def test_build_temporal_url(temp_config):
    """Test temporal URL building."""
    config = TemporalConfig(temp_config)
    store = TemporalDataStore(config)

    entity_id = "urn:ngsi-ld:Camera:TTH406"
    url = store.build_temporal_url(entity_id)

    assert "TTH406" in url
    assert "temporal" in url
    assert "/attrs" in url


@patch("requests.Session.post")
def test_post_temporal_instances_success(mock_post, temp_config):
    """Test successful POST of temporal instances."""
    config = TemporalConfig(temp_config)
    store = TemporalDataStore(config)

    # Mock successful response
    mock_response = Mock()
    mock_response.status_code = 204
    mock_post.return_value = mock_response

    entity_id = "urn:ngsi-ld:Camera:TTH406"
    instances = {
        "intensity": [
            {"type": "Property", "value": 0.75, "observedAt": "2025-11-01T10:00:00Z"}
        ]
    }

    success = store.post_temporal_instances(entity_id, instances)

    assert success is True
    assert mock_post.called


@patch("requests.Session.post")
def test_post_temporal_instances_failure(mock_post, temp_config):
    """Test failed POST of temporal instances."""
    config = TemporalConfig(temp_config)
    store = TemporalDataStore(config)

    # Mock error response
    mock_response = Mock()
    mock_response.status_code = 500
    mock_response.text = "Internal Server Error"
    mock_post.return_value = mock_response

    entity_id = "urn:ngsi-ld:Camera:TTH406"
    instances = {"intensity": []}

    success = store.post_temporal_instances(entity_id, instances)

    assert success is False


# ============================================================================
# Integration Tests
# ============================================================================


@patch("requests.Session.post")
def test_agent_store_observations(mock_post, temp_config, sample_observations):
    """Test agent storing observations."""
    config = TemporalConfig(temp_config)
    agent = TemporalDataManagerAgent(temp_config)

    mock_response = Mock()
    mock_response.status_code = 204
    mock_post.return_value = mock_response

    entity_id = "urn:ngsi-ld:Camera:TTH406"
    success = agent.store_temporal_observations(entity_id, sample_observations)

    assert success is True
    assert agent.stats["observations_stored"] == len(sample_observations)


def test_agent_run_cleanup(temp_config, old_observations, tmp_path):
    """Test agent cleanup process."""
    config = TemporalConfig(temp_config)
    agent = TemporalDataManagerAgent(temp_config)

    # Override archive path
    agent.archive_manager.base_path = tmp_path

    entity_id = "urn:ngsi-ld:Camera:TTH406"
    results = agent.run_cleanup(entity_id, old_observations)

    # Check results
    assert results["aggregated"] > 0
    assert results["archived"] > 0
    assert results["deleted"] > 0


def test_agent_statistics(temp_config):
    """Test agent statistics."""
    agent = TemporalDataManagerAgent(temp_config)

    stats = agent.get_statistics()

    assert "observations_stored" in stats
    assert "observations_aggregated" in stats
    assert "observations_archived" in stats


# ============================================================================
# Data Integrity Tests
# ============================================================================


def test_aggregation_no_data_loss(temp_config):
    """Test that aggregation doesn't lose data."""
    config = TemporalConfig(temp_config)
    engine = AggregationEngine(config)

    # Create 100 observations
    now = datetime.utcnow()
    observations = []

    for i in range(100):
        observations.append(
            {
                "observedAt": (now - timedelta(minutes=i)).isoformat() + "Z",
                "intensity": 0.5,
            }
        )

    aggregated = engine.aggregate_observations(observations, "hourly")

    # Count total observations
    total_count = sum(agg["observation_count"] for agg in aggregated)
    assert total_count == 100  # No observations lost


def test_aggregation_accuracy(temp_config):
    """Test aggregation calculation accuracy."""
    config = TemporalConfig(temp_config)
    engine = AggregationEngine(config)

    now = datetime.utcnow()
    values = [0.1, 0.2, 0.3, 0.4, 0.5]
    observations = []

    for value in values:
        observations.append({"observedAt": now.isoformat() + "Z", "intensity": value})

    aggregated = engine.aggregate_observations(observations, "hourly")

    # Check mean
    expected_mean = sum(values) / len(values)
    assert abs(aggregated[0]["intensity"] - expected_mean) < 0.001


def test_archive_retrieval_integrity(temp_config, sample_observations, tmp_path):
    """Test archived data can be retrieved accurately."""
    config = TemporalConfig(temp_config)
    manager = ArchiveManager(config)
    manager.base_path = tmp_path

    entity_id = "urn:ngsi-ld:Camera:TTH406"
    date = datetime(2025, 11, 1)

    # Archive
    manager.archive_data(entity_id, date, sample_observations)

    # Retrieve
    retrieved = manager.retrieve_archived_data(entity_id, date)

    # Verify integrity
    assert len(retrieved) == len(sample_observations)

    for original, retrieved_obs in zip(sample_observations, retrieved):
        assert original["observedAt"] == retrieved_obs["observedAt"]
        assert original["intensity"] == retrieved_obs["intensity"]


# ============================================================================
# Edge Case Tests
# ============================================================================


def test_empty_observations_storage(temp_config):
    """Test storing empty observations list."""
    agent = TemporalDataManagerAgent(temp_config)

    entity_id = "urn:ngsi-ld:Camera:TTH406"
    success = agent.store_temporal_observations(entity_id, [])

    assert success is True


def test_missing_observed_at(temp_config):
    """Test observations without observedAt."""
    config = TemporalConfig(temp_config)
    engine = AggregationEngine(config)

    observations = [{"intensity": 0.5}, {"intensity": 0.6}]  # Missing observedAt

    aggregated = engine.aggregate_observations(observations, "hourly")

    # Should handle gracefully
    assert isinstance(aggregated, list)


def test_malformed_entity_id(temp_config):
    """Test archive path generation with malformed entity ID."""
    config = TemporalConfig(temp_config)
    manager = ArchiveManager(config)

    # Malformed ID
    entity_id = "invalid-id-format"
    date = datetime(2025, 11, 1)

    path = manager.generate_archive_path(entity_id, date)

    # Should still generate a path
    assert path is not None


def test_cleanup_empty_observations(temp_config):
    """Test cleanup with empty observations."""
    agent = TemporalDataManagerAgent(temp_config)

    entity_id = "urn:ngsi-ld:Camera:TTH406"
    results = agent.run_cleanup(entity_id, [])

    assert results["aggregated"] == 0
    assert results["archived"] == 0
    assert results["deleted"] == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
