"""
Comprehensive Test Suite for Pattern Recognition Agent

Tests cover:
- Unit Tests: Time windows, pattern detection, forecasting algorithms
- Integration Tests: Neo4j mock, full pipeline, entity creation
- Statistical Tests: Rush hour accuracy, anomaly detection, weekly patterns

Target: 100% pass rate, >=80% coverage
"""

import pytest
import json
import yaml
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch
import statistics

# Import agent components
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from agents.analytics.pattern_recognition_agent import (
    PatternConfig,
    Neo4jConnector,
    TimeSeriesAnalyzer,
    PatternDetector,
    ForecastEngine,
    PatternRecognitionAgent
)


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def temp_config(tmp_path):
    """Create temporary configuration file."""
    config = {
        'pattern_recognition': {
            'neo4j': {
                'uri': 'bolt://localhost:7687',
                'auth': {'username': 'neo4j', 'password': 'testpass'},
                'database': 'neo4j'
            },
            'analysis': {
                'time_windows': ['1_hour', '1_day', '7_days'],
                'metrics': ['intensity', 'occupancy'],
                'min_data_points': {'hourly': 10, 'daily': 7, 'weekly': 28}
            },
            'patterns': {
                'rush_hours': {
                    'morning': {'start': 7, 'end': 9},
                    'evening': {'start': 17, 'end': 19},
                    'intensity_threshold': 0.7,
                    'occupancy_threshold': 0.6
                },
                'anomaly_detection': {
                    'enabled': True,
                    'method': 'zscore',
                    'threshold': 2.5,
                    'min_samples': 30
                },
                'weekly_patterns': {
                    'enabled': True,
                    'compare_weekdays': True,
                    'weekend_days': [5, 6]
                }
            },
            'forecasting': {
                'enabled': True,
                'method': 'moving_average',
                'window': 7,
                'alpha': 0.3,
                'confidence_level': 0.75,
                'horizon': {'next_hour': True}
            },
            'entity': {
                'type': 'TrafficPattern',
                'id_prefix': 'urn:ngsi-ld:TrafficPattern:',
                'relationships': {'link_to_camera': True},
                'pattern_types': ['hourly', 'daily', 'weekly']
            },
            'stellio': {
                'base_url': 'http://test:8080',
                'create_endpoint': '/ngsi-ld/v1/entities',
                'batch_create': False
            },
            'output': {
                'patterns_file': str(tmp_path / 'patterns.json')
            },
            'state': {
                'file': str(tmp_path / 'state.json')
            }
        }
    }
    
    config_file = tmp_path / 'config.yaml'
    with open(config_file, 'w') as f:
        yaml.dump(config, f)
    
    return str(config_file)


@pytest.fixture
def sample_temporal_data():
    """Generate sample temporal observation data."""
    base_time = datetime(2025, 11, 1, 0, 0, 0)
    data = []
    
    for i in range(168):  # 7 days, hourly data
        timestamp = base_time + timedelta(hours=i)
        hour = timestamp.hour
        weekday = timestamp.weekday()
        
        # Simulate rush hour patterns
        if 7 <= hour < 9 or 17 <= hour < 19:
            intensity = 0.8 + (i % 10) * 0.02
            occupancy = 0.7 + (i % 10) * 0.02
        else:
            intensity = 0.4 + (i % 10) * 0.01
            occupancy = 0.3 + (i % 10) * 0.01
        
        # Weekend reduction
        if weekday >= 5:
            intensity *= 0.7
            occupancy *= 0.7
        
        data.append({
            'timestamp': timestamp.isoformat(),
            'intensity': intensity,
            'occupancy': occupancy,
            'speed': 50.0 - intensity * 20.0,
            'congested_count': int(intensity * 10)
        })
    
    return data


@pytest.fixture
def sample_anomaly_data():
    """Generate data with anomalies for testing anomaly detection."""
    base_time = datetime(2025, 11, 1, 0, 0, 0)
    data = []
    
    for i in range(100):
        timestamp = base_time + timedelta(hours=i)
        
        # Normal values around 0.5
        if i in [25, 50, 75]:  # Anomalies
            intensity = 0.95
            occupancy = 0.98
        else:
            intensity = 0.5 + (i % 5) * 0.02
            occupancy = 0.4 + (i % 5) * 0.02
        
        data.append({
            'timestamp': timestamp.isoformat(),
            'intensity': intensity,
            'occupancy': occupancy
        })
    
    return data


# ============================================================================
# Unit Tests - Configuration
# ============================================================================

def test_pattern_config_load(temp_config):
    """Test configuration loading."""
    config = PatternConfig(temp_config)
    
    assert config.config is not None
    assert 'pattern_recognition' in config.config


def test_pattern_config_neo4j(temp_config):
    """Test Neo4j configuration extraction."""
    config = PatternConfig(temp_config)
    neo4j_config = config.get_neo4j_config()
    
    assert neo4j_config['uri'] == 'bolt://localhost:7687'
    assert neo4j_config['auth']['username'] == 'neo4j'


def test_pattern_config_analysis(temp_config):
    """Test analysis configuration extraction."""
    config = PatternConfig(temp_config)
    analysis_config = config.get_analysis_config()
    
    assert '7_days' in analysis_config['time_windows']
    assert 'intensity' in analysis_config['metrics']


def test_pattern_config_invalid_file():
    """Test handling of invalid configuration file."""
    with pytest.raises(FileNotFoundError):
        PatternConfig('/nonexistent/config.yaml')


# ============================================================================
# Unit Tests - Time-Series Analyzer
# ============================================================================

def test_time_series_analyzer_init(sample_temporal_data):
    """Test TimeSeriesAnalyzer initialization."""
    analyzer = TimeSeriesAnalyzer(sample_temporal_data, ['intensity', 'occupancy'])
    
    assert analyzer.data == sample_temporal_data
    assert analyzer.metrics == ['intensity', 'occupancy']


def test_hourly_aggregates(sample_temporal_data):
    """Test hourly aggregation calculation."""
    analyzer = TimeSeriesAnalyzer(sample_temporal_data, ['intensity'])
    hourly_stats = analyzer.get_hourly_aggregates('intensity')
    
    # Should have stats for 24 hours
    assert len(hourly_stats) <= 24
    
    # Rush hour (8am) should have higher mean than off-peak (2am)
    if 8 in hourly_stats and 2 in hourly_stats:
        assert hourly_stats[8]['mean'] > hourly_stats[2]['mean']


def test_daily_aggregates(sample_temporal_data):
    """Test daily aggregation calculation."""
    analyzer = TimeSeriesAnalyzer(sample_temporal_data, ['intensity'])
    daily_stats = analyzer.get_daily_aggregates('intensity')
    
    # Should have stats for 7 days
    assert len(daily_stats) == 7
    
    # Each day should have mean, std, count
    for date, stats in daily_stats.items():
        assert 'mean' in stats
        assert 'std' in stats
        assert 'count' in stats


def test_weekday_aggregates(sample_temporal_data):
    """Test weekday aggregation calculation."""
    analyzer = TimeSeriesAnalyzer(sample_temporal_data, ['intensity'])
    weekday_stats = analyzer.get_weekday_aggregates('intensity')
    
    # Should have stats for some weekdays
    assert len(weekday_stats) > 0
    
    # Weekdays (0-4) should have higher values than weekends (5-6)
    weekday_means = [stats['mean'] for day, stats in weekday_stats.items() if day < 5]
    weekend_means = [stats['mean'] for day, stats in weekday_stats.items() if day >= 5]
    
    if weekday_means and weekend_means:
        assert statistics.mean(weekday_means) > statistics.mean(weekend_means)


def test_zscore_calculation(sample_anomaly_data):
    """Test z-score calculation for anomaly detection."""
    analyzer = TimeSeriesAnalyzer(sample_anomaly_data, ['intensity'])
    z_scores = analyzer.calculate_zscore('intensity')
    
    assert len(z_scores) > 0
    
    # Anomalies (intensity=0.95) should have high z-scores
    high_z_scores = [z for ts, val, z in z_scores if abs(z) > 2.0]
    assert len(high_z_scores) >= 3  # We injected 3 anomalies


def test_zscore_empty_data():
    """Test z-score calculation with empty data."""
    analyzer = TimeSeriesAnalyzer([], ['intensity'])
    z_scores = analyzer.calculate_zscore('intensity')
    
    assert z_scores == []


# ============================================================================
# Unit Tests - Pattern Detector
# ============================================================================

def test_rush_hour_detection(temp_config, sample_temporal_data):
    """Test rush hour detection."""
    config = PatternConfig(temp_config)
    patterns_config = config.get_patterns_config()
    
    analyzer = TimeSeriesAnalyzer(sample_temporal_data, ['intensity'])
    detector = PatternDetector(patterns_config, analyzer)
    
    rush_hours = detector.detect_rush_hours('intensity')
    
    # Should detect morning (7-9) and evening (17-19) rush hours
    rush_hour_hours = [rh['hour'] for rh in rush_hours]
    assert any(7 <= h < 9 for h in rush_hour_hours)  # Morning
    assert any(17 <= h < 19 for h in rush_hour_hours)  # Evening


def test_rush_hour_no_detection_low_intensity(temp_config):
    """Test that low intensity traffic doesn't trigger rush hour detection."""
    config = PatternConfig(temp_config)
    patterns_config = config.get_patterns_config()
    
    # Create data with consistently low intensity
    data = []
    base_time = datetime(2025, 11, 1, 0, 0, 0)
    for i in range(24):
        data.append({
            'timestamp': (base_time + timedelta(hours=i)).isoformat(),
            'intensity': 0.3  # Below threshold
        })
    
    analyzer = TimeSeriesAnalyzer(data, ['intensity'])
    detector = PatternDetector(patterns_config, analyzer)
    
    rush_hours = detector.detect_rush_hours('intensity')
    assert len(rush_hours) == 0


def test_anomaly_detection(temp_config, sample_anomaly_data):
    """Test anomaly detection with z-score method."""
    config = PatternConfig(temp_config)
    patterns_config = config.get_patterns_config()
    
    analyzer = TimeSeriesAnalyzer(sample_anomaly_data, ['intensity'])
    detector = PatternDetector(patterns_config, analyzer)
    
    anomalies = detector.detect_anomalies('intensity', threshold=2.5, min_samples=30)
    
    # Should detect the 3 injected anomalies
    assert len(anomalies) >= 3


def test_anomaly_detection_insufficient_data(temp_config):
    """Test anomaly detection with insufficient data."""
    config = PatternConfig(temp_config)
    patterns_config = config.get_patterns_config()
    
    # Only 10 data points (below min_samples=30)
    data = []
    base_time = datetime(2025, 11, 1, 0, 0, 0)
    for i in range(10):
        data.append({
            'timestamp': (base_time + timedelta(hours=i)).isoformat(),
            'intensity': 0.5
        })
    
    analyzer = TimeSeriesAnalyzer(data, ['intensity'])
    detector = PatternDetector(patterns_config, analyzer)
    
    anomalies = detector.detect_anomalies('intensity', threshold=2.5, min_samples=30)
    assert anomalies == []


def test_weekly_patterns_detection(temp_config, sample_temporal_data):
    """Test weekly pattern detection."""
    config = PatternConfig(temp_config)
    patterns_config = config.get_patterns_config()
    
    analyzer = TimeSeriesAnalyzer(sample_temporal_data, ['intensity'])
    detector = PatternDetector(patterns_config, analyzer)
    
    weekly = detector.detect_weekly_patterns('intensity')
    
    assert 'weekday_stats' in weekly
    assert 'weekend_stats' in weekly
    assert 'comparison' in weekly
    
    # Weekdays should have higher average than weekends
    comparison = weekly['comparison']
    assert comparison['weekday_avg'] > comparison['weekend_avg']
    assert comparison['pattern'] == 'weekday_higher'


# ============================================================================
# Unit Tests - Forecast Engine
# ============================================================================

def test_moving_average_forecast(temp_config, sample_temporal_data):
    """Test moving average forecasting."""
    config = PatternConfig(temp_config)
    forecasting_config = config.get_forecasting_config()
    forecasting_config['method'] = 'moving_average'
    forecasting_config['window'] = 7
    
    analyzer = TimeSeriesAnalyzer(sample_temporal_data, ['intensity'])
    forecast_engine = ForecastEngine(forecasting_config, analyzer)
    
    forecast = forecast_engine.forecast_next_hour('intensity')
    
    assert 'forecast' in forecast
    assert 'confidence' in forecast
    assert 'method' in forecast
    assert forecast['method'] == 'moving_average'
    assert 0.0 <= forecast['forecast'] <= 1.0


def test_exponential_smoothing_forecast(temp_config, sample_temporal_data):
    """Test exponential smoothing forecasting."""
    config = PatternConfig(temp_config)
    forecasting_config = config.get_forecasting_config()
    forecasting_config['method'] = 'exponential_smoothing'
    forecasting_config['alpha'] = 0.3
    
    analyzer = TimeSeriesAnalyzer(sample_temporal_data, ['intensity'])
    forecast_engine = ForecastEngine(forecasting_config, analyzer)
    
    forecast = forecast_engine.forecast_next_hour('intensity')
    
    assert forecast['method'] == 'exponential_smoothing'
    assert 'alpha' in forecast
    assert forecast['alpha'] == 0.3


def test_forecast_empty_data(temp_config):
    """Test forecasting with empty data."""
    config = PatternConfig(temp_config)
    forecasting_config = config.get_forecasting_config()
    
    analyzer = TimeSeriesAnalyzer([], ['intensity'])
    forecast_engine = ForecastEngine(forecasting_config, analyzer)
    
    forecast = forecast_engine.forecast_next_hour('intensity')
    
    assert forecast['forecast'] == 0.0
    assert forecast['confidence'] == 0.0


def test_forecast_invalid_method(temp_config, sample_temporal_data):
    """Test forecasting with invalid method."""
    config = PatternConfig(temp_config)
    forecasting_config = config.get_forecasting_config()
    forecasting_config['method'] = 'invalid_method'
    
    analyzer = TimeSeriesAnalyzer(sample_temporal_data, ['intensity'])
    forecast_engine = ForecastEngine(forecasting_config, analyzer)
    
    with pytest.raises(ValueError, match="Unknown forecasting method"):
        forecast_engine.forecast_next_hour('intensity')


# ============================================================================
# Integration Tests - Mock Neo4j
# ============================================================================

class MockNeo4jDriver:
    """Mock Neo4j driver for testing."""
    
    def __init__(self, temporal_data):
        self.temporal_data = temporal_data
    
    def verify_connectivity(self):
        pass
    
    def session(self, database=None):
        return MockNeo4jSession(self.temporal_data)
    
    def close(self):
        pass


class MockNeo4jSession:
    """Mock Neo4j session."""
    
    def __init__(self, temporal_data):
        self.temporal_data = temporal_data
    
    def __enter__(self):
        return self
    
    def __exit__(self, *args):
        pass
    
    def run(self, query, **params):
        # Return mock data
        return MockNeo4jResult(self.temporal_data)


class MockNeo4jResult:
    """Mock Neo4j query result."""
    
    def __init__(self, data):
        self.data = data
    
    def __iter__(self):
        for obs in self.data:
            yield MockNeo4jRecord(obs)


class MockNeo4jRecord:
    """Mock Neo4j record."""
    
    def __init__(self, data):
        self.data = data
    
    def __getitem__(self, key):
        return self.data.get(key)
    
    def get(self, key, default=None):
        return self.data.get(key, default)


@pytest.fixture
def mock_neo4j_connector(sample_temporal_data, monkeypatch):
    """Create mocked Neo4j connector."""
    # Mock Neo4j availability
    monkeypatch.setattr('agents.analytics.pattern_recognition_agent.NEO4J_AVAILABLE', True)
    
    # Create mock GraphDatabase class
    class MockGraphDatabase:
        @staticmethod
        def driver(*args, **kwargs):
            return MockNeo4jDriver(sample_temporal_data)
    
    # Mock the GraphDatabase import
    import agents.analytics.pattern_recognition_agent as pr_agent
    pr_agent.GraphDatabase = MockGraphDatabase
    
    return {
        'uri': 'bolt://localhost:7687',
        'auth': {'username': 'neo4j', 'password': 'test'},
        'database': 'neo4j'
    }


def test_neo4j_query_temporal_data(mock_neo4j_connector, sample_temporal_data):
    """Test querying temporal data from Neo4j."""
    connector = Neo4jConnector(mock_neo4j_connector)
    
    start_time = datetime(2025, 11, 1, 0, 0, 0)
    end_time = datetime(2025, 11, 8, 0, 0, 0)
    
    data = connector.query_temporal_data(
        'urn:ngsi-ld:Camera:Test',
        start_time,
        end_time,
        ['intensity', 'occupancy']
    )
    
    assert len(data) > 0
    assert 'timestamp' in data[0]
    
    connector.close()


# ============================================================================
# Integration Tests - Pattern Recognition Agent
# ============================================================================

@pytest.fixture
def mock_http_response():
    """Mock HTTP response."""
    class MockResponse:
        def __init__(self, status_code=201):
            self.status_code = status_code
            self.text = 'OK'
    
    return MockResponse


def test_pattern_entity_creation(temp_config, monkeypatch):
    """Test TrafficPattern entity creation."""
    # Mock Neo4j availability
    monkeypatch.setattr('agents.analytics.pattern_recognition_agent.NEO4J_AVAILABLE', True)
    
    # Mock Neo4jConnector __init__ to avoid actual connection
    def mock_neo4j_init(self, config):
        self.config = config
        self.driver = None
    
    monkeypatch.setattr('agents.analytics.pattern_recognition_agent.Neo4jConnector.__init__',
                       mock_neo4j_init)
    
    agent = PatternRecognitionAgent(temp_config)
    
    camera_id = 'urn:ngsi-ld:Camera:Test'
    analysis_results = {
        'start_time': '2025-11-01T00:00:00',
        'end_time': '2025-11-08T00:00:00',
        'data_points': 168,
        'rush_hours': [
            {'hour': 8, 'period': 'morning', 'intensity': 0.85, 'confidence': 0.9},
            {'hour': 18, 'period': 'evening', 'intensity': 0.82, 'confidence': 0.88}
        ],
        'forecast': {
            'forecast': 0.65,
            'confidence': 0.75,
            'method': 'moving_average'
        },
        'anomalies': [],
        'weekly_patterns': {
            'comparison': {
                'weekday_avg': 0.7,
                'weekend_avg': 0.5,
                'pattern': 'weekday_higher'
            }
        }
    }
    
    entity = agent.create_pattern_entity(camera_id, 'weekly', analysis_results)
    
    assert entity['type'] == 'TrafficPattern'
    assert 'urn:ngsi-ld:TrafficPattern:' in entity['id']
    assert entity['patternType']['value'] == 'weekly'
    assert 'refCamera' in entity
    assert entity['refCamera']['object'] == camera_id
    assert 'rushHours' in entity
    assert 'forecast' in entity
    
    agent.close()


def test_pattern_entity_post(temp_config, monkeypatch, mock_http_response):
    """Test posting TrafficPattern entity to Stellio."""
    # Mock Neo4j availability
    monkeypatch.setattr('agents.analytics.pattern_recognition_agent.NEO4J_AVAILABLE', True)
    
    # Mock Neo4jConnector __init__
    def mock_neo4j_init(self, config):
        self.config = config
        self.driver = None
    
    monkeypatch.setattr('agents.analytics.pattern_recognition_agent.Neo4jConnector.__init__',
                       mock_neo4j_init)
    
    agent = PatternRecognitionAgent(temp_config)
    
    # Mock HTTP POST
    def mock_post(*args, **kwargs):
        return mock_http_response()
    
    monkeypatch.setattr(agent.session, 'post', mock_post)
    
    entity = {
        'id': 'urn:ngsi-ld:TrafficPattern:Test',
        'type': 'TrafficPattern',
        'patternType': {'type': 'Property', 'value': 'weekly'}
    }
    
    success = agent.post_entity(entity)
    assert success is True
    
    agent.close()


def test_analyze_camera_patterns_integration(temp_config, mock_neo4j_connector, sample_temporal_data):
    """Test full camera pattern analysis pipeline."""
    agent = PatternRecognitionAgent(temp_config)
    
    # Replace Neo4j connector with mock
    agent.neo4j = Neo4jConnector(mock_neo4j_connector)
    
    results = agent.analyze_camera_patterns('urn:ngsi-ld:Camera:Test', '7_days')
    
    assert results is not None
    assert 'camera_id' in results
    assert 'rush_hours' in results
    assert 'forecast' in results
    assert len(results['rush_hours']) > 0
    
    agent.close()


def test_analyze_camera_no_data(temp_config, monkeypatch):
    """Test analysis with no data available."""
    # Mock Neo4j availability
    monkeypatch.setattr('agents.analytics.pattern_recognition_agent.NEO4J_AVAILABLE', True)
    
    # Mock Neo4jConnector __init__
    def mock_neo4j_init(self, config):
        self.config = config
        self.driver = None
    
    monkeypatch.setattr('agents.analytics.pattern_recognition_agent.Neo4jConnector.__init__',
                       mock_neo4j_init)
    
    # Mock Neo4j to return empty data
    def mock_query_temporal_data(*args, **kwargs):
        return []
    
    agent = PatternRecognitionAgent(temp_config)
    monkeypatch.setattr(agent.neo4j, 'query_temporal_data', mock_query_temporal_data)
    
    results = agent.analyze_camera_patterns('urn:ngsi-ld:Camera:Empty', '7_days')
    
    assert results == {}
    
    agent.close()


# ============================================================================
# Statistical Tests
# ============================================================================

def test_rush_hour_accuracy(temp_config):
    """Test accuracy of rush hour detection."""
    # Create synthetic data with known rush hours
    data = []
    base_time = datetime(2025, 11, 1, 0, 0, 0)
    
    for hour in range(24):
        for day in range(7):
            timestamp = base_time + timedelta(days=day, hours=hour)
            
            # Rush hours: 7-9am (0.9 intensity), 5-7pm (0.85 intensity)
            # Off-peak: 0.3 intensity
            if 7 <= hour < 9:
                intensity = 0.9
            elif 17 <= hour < 19:
                intensity = 0.85
            else:
                intensity = 0.3
            
            data.append({
                'timestamp': timestamp.isoformat(),
                'intensity': intensity
            })
    
    config = PatternConfig(temp_config)
    patterns_config = config.get_patterns_config()
    patterns_config['rush_hours']['intensity_threshold'] = 0.7
    
    analyzer = TimeSeriesAnalyzer(data, ['intensity'])
    detector = PatternDetector(patterns_config, analyzer)
    
    rush_hours = detector.detect_rush_hours('intensity')
    
    # Should detect exactly hours 7, 8, 17, 18
    detected_hours = set(rh['hour'] for rh in rush_hours)
    expected_hours = {7, 8, 17, 18}
    
    # Allow some tolerance
    assert len(detected_hours & expected_hours) >= 3  # At least 3 of 4


def test_anomaly_detection_accuracy(temp_config):
    """Test accuracy of anomaly detection."""
    # Create data with exactly 5 anomalies
    data = []
    base_time = datetime(2025, 11, 1, 0, 0, 0)
    anomaly_indices = [20, 40, 60, 80, 100]
    
    for i in range(120):
        timestamp = base_time + timedelta(hours=i)
        
        if i in anomaly_indices:
            intensity = 0.99  # Clear anomaly
        else:
            intensity = 0.5 + (i % 3) * 0.01  # Normal variation
        
        data.append({
            'timestamp': timestamp.isoformat(),
            'intensity': intensity
        })
    
    config = PatternConfig(temp_config)
    patterns_config = config.get_patterns_config()
    
    analyzer = TimeSeriesAnalyzer(data, ['intensity'])
    detector = PatternDetector(patterns_config, analyzer)
    
    anomalies = detector.detect_anomalies('intensity', threshold=2.5, min_samples=30)
    
    # Should detect all 5 anomalies
    assert len(anomalies) == 5


def test_forecast_stability(temp_config):
    """Test forecast stability with consistent data."""
    # Create very stable data
    data = []
    base_time = datetime(2025, 11, 1, 0, 0, 0)
    
    for i in range(100):
        data.append({
            'timestamp': (base_time + timedelta(hours=i)).isoformat(),
            'intensity': 0.6  # Constant value
        })
    
    config = PatternConfig(temp_config)
    forecasting_config = config.get_forecasting_config()
    forecasting_config['method'] = 'moving_average'
    forecasting_config['window'] = 7
    
    analyzer = TimeSeriesAnalyzer(data, ['intensity'])
    forecast_engine = ForecastEngine(forecasting_config, analyzer)
    
    forecast = forecast_engine.forecast_next_hour('intensity')
    
    # Forecast should be very close to 0.6
    assert abs(forecast['forecast'] - 0.6) < 0.1


# ============================================================================
# Edge Case Tests
# ============================================================================

def test_time_window_calculation(temp_config, monkeypatch):
    """Test time window calculations."""
    # Mock Neo4j availability
    monkeypatch.setattr('agents.analytics.pattern_recognition_agent.NEO4J_AVAILABLE', True)
    
    # Mock Neo4jConnector __init__
    def mock_neo4j_init(self, config):
        self.config = config
        self.driver = None
        self.query_temporal_data = lambda *args, **kwargs: []
    
    monkeypatch.setattr('agents.analytics.pattern_recognition_agent.Neo4jConnector.__init__',
                       mock_neo4j_init)
    
    agent = PatternRecognitionAgent(temp_config)
    
    # Test all time windows
    for window in ['1_hour', '1_day', '7_days', '30_days']:
        # Should not raise exception
        try:
            results = agent.analyze_camera_patterns('urn:ngsi-ld:Camera:Test', window)
            assert results == {}  # Empty due to no data
        except ValueError:
            pytest.fail(f"Time window '{window}' should be valid")
    
    agent.close()


def test_invalid_time_window(temp_config, monkeypatch):
    """Test invalid time window handling."""
    # Mock Neo4j availability
    monkeypatch.setattr('agents.analytics.pattern_recognition_agent.NEO4J_AVAILABLE', True)
    
    # Mock Neo4jConnector __init__
    def mock_neo4j_init(self, config):
        self.config = config
        self.driver = None
    
    monkeypatch.setattr('agents.analytics.pattern_recognition_agent.Neo4jConnector.__init__',
                       mock_neo4j_init)
    
    agent = PatternRecognitionAgent(temp_config)
    
    with pytest.raises(ValueError, match="Invalid time window"):
        agent.analyze_camera_patterns('urn:ngsi-ld:Camera:Test', 'invalid_window')
    
    agent.close()


def test_missing_metric_in_data(temp_config):
    """Test handling of missing metrics in observation data."""
    # Data with some missing metrics
    data = [
        {'timestamp': '2025-11-01T00:00:00', 'intensity': 0.5},
        {'timestamp': '2025-11-01T01:00:00'},  # Missing intensity
        {'timestamp': '2025-11-01T02:00:00', 'intensity': 0.6}
    ]
    
    analyzer = TimeSeriesAnalyzer(data, ['intensity'])
    hourly_stats = analyzer.get_hourly_aggregates('intensity')
    
    # Should handle missing data gracefully
    assert len(hourly_stats) > 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
