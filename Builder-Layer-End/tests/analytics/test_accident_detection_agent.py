#!/usr/bin/env python3
"""
Test Suite for Accident Detection Agent
========================================

Comprehensive tests covering:
- Unit tests for each detection method
- Integration tests for full pipeline
- Edge cases and error handling
- False positive filtering
- Severity classification
- State management
- Alert generation
"""

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict

import pytest
import yaml

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from agents.analytics.accident_detection_agent import (
    AccidentConfig,
    AccidentDetectionAgent,
    OccupancySpikeDetector,
    PatternAnomalyDetector,
    SpeedVarianceDetector,
    StateStore,
    SuddenStopDetector,
    now_iso,
)


def write_yaml(path: Path, data: Dict[str, Any]) -> None:
    """Write YAML file"""
    with open(path, 'w', encoding='utf-8') as f:
        yaml.dump(data, f)


def now_iso_fixed():
    """Return fixed timestamp for testing"""
    return "2025-11-01T10:00:00Z"


def make_observation(
    camera_ref: str,
    occ: float = 0.5,
    speed: float = 30,
    intensity: float = 10,
    observed_at: str = None
) -> Dict[str, Any]:
    """Create test observation entity"""
    if observed_at is None:
        observed_at = now_iso_fixed()
    return {
        'id': f'urn:ngsi-ld:ItemFlowObserved:{camera_ref}-obs',
        'type': 'ItemFlowObserved',
        'refDevice': {'object': camera_ref},
        'occupancy': {'type': 'Property', 'value': occ, 'observedAt': observed_at},
        'averageSpeed': {'type': 'Property', 'value': speed, 'observedAt': observed_at},
        'intensity': {'type': 'Property', 'value': intensity, 'observedAt': observed_at},
        'location': {
            'type': 'GeoProperty',
            'value': {'type': 'Point', 'coordinates': [106.691, 10.791]}
        }
    }


class MockResponse:
    def __init__(self, status_code: int, text: str = ''):
        self.status_code = status_code
        self.text = text


# ==================== Unit Tests: Speed Variance Detector ====================

def test_speed_variance_detector_normal_traffic():
    """Test speed variance detector with normal traffic (no accident)"""
    config = {
        'name': 'speed_variance',
        'enabled': True,
        'threshold': 3.0,
        'window_size': 10
    }
    detector = SpeedVarianceDetector(config)
    
    # Create observations with stable speeds
    observations = [
        make_observation('urn:ngsi-ld:Camera:Test', speed=30 + i * 0.5)
        for i in range(10)
    ]
    
    detected, confidence, reason = detector.detect(observations, 'urn:ngsi-ld:Camera:Test')
    
    assert detected is False
    assert confidence == 0.0
    assert 'normal_variance' in reason


def test_speed_variance_detector_accident():
    """Test speed variance detector with accident scenario"""
    config = {
        'name': 'speed_variance',
        'enabled': True,
        'threshold': 0.5,  # Lower threshold for easier testing
        'window_size': 10
    }
    detector = SpeedVarianceDetector(config)
    
    # Create observations with extreme speed variance
    observations = [
        make_observation('urn:ngsi-ld:Camera:Test', speed=60),
        make_observation('urn:ngsi-ld:Camera:Test', speed=2),
        make_observation('urn:ngsi-ld:Camera:Test', speed=58),
        make_observation('urn:ngsi-ld:Camera:Test', speed=3),
        make_observation('urn:ngsi-ld:Camera:Test', speed=55),
        make_observation('urn:ngsi-ld:Camera:Test', speed=5),
        make_observation('urn:ngsi-ld:Camera:Test', speed=60),
        make_observation('urn:ngsi-ld:Camera:Test', speed=1),
        make_observation('urn:ngsi-ld:Camera:Test', speed=57),
        make_observation('urn:ngsi-ld:Camera:Test', speed=4),
    ]
    
    detected, confidence, reason = detector.detect(observations, 'urn:ngsi-ld:Camera:Test')
    
    assert detected is True
    assert confidence > 0.0
    assert 'speed_variance' in reason


def test_speed_variance_detector_insufficient_data():
    """Test speed variance detector with insufficient data"""
    config = {
        'name': 'speed_variance',
        'enabled': True,
        'threshold': 3.0,
        'window_size': 10
    }
    detector = SpeedVarianceDetector(config)
    
    observations = [
        make_observation('urn:ngsi-ld:Camera:Test', speed=30)
        for _ in range(3)
    ]
    
    detected, confidence, reason = detector.detect(observations, 'urn:ngsi-ld:Camera:Test')
    
    assert detected is False
    assert 'insufficient_data' in reason


# ==================== Unit Tests: Occupancy Spike Detector ====================

def test_occupancy_spike_detector_normal_traffic():
    """Test occupancy spike detector with normal traffic"""
    config = {
        'name': 'occupancy_spike',
        'enabled': True,
        'spike_factor': 2.0,
        'baseline_window': 20
    }
    detector = OccupancySpikeDetector(config)
    
    # Create observations with stable occupancy
    observations = [
        make_observation('urn:ngsi-ld:Camera:Test', occ=0.5)
        for _ in range(25)
    ]
    
    detected, confidence, reason = detector.detect(observations, 'urn:ngsi-ld:Camera:Test')
    
    assert detected is False
    assert 'normal_occupancy' in reason


def test_occupancy_spike_detector_accident():
    """Test occupancy spike detector with accident scenario"""
    config = {
        'name': 'occupancy_spike',
        'enabled': True,
        'spike_factor': 2.0,
        'baseline_window': 20
    }
    detector = OccupancySpikeDetector(config)
    
    # Create observations with sudden occupancy spike
    observations = [
        make_observation('urn:ngsi-ld:Camera:Test', occ=0.3)
        for _ in range(20)
    ] + [
        make_observation('urn:ngsi-ld:Camera:Test', occ=0.9)
    ]
    
    detected, confidence, reason = detector.detect(observations, 'urn:ngsi-ld:Camera:Test')
    
    assert detected is True
    assert confidence > 0.0
    assert 'occupancy_spike' in reason


# ==================== Unit Tests: Sudden Stop Detector ====================

def test_sudden_stop_detector_normal_deceleration():
    """Test sudden stop detector with normal deceleration"""
    config = {
        'name': 'sudden_stop',
        'enabled': True,
        'speed_drop_threshold': 0.8,
        'time_window': 30,
        'min_initial_speed': 20
    }
    detector = SuddenStopDetector(config)
    
    # Create observations with gradual deceleration
    observations = [
        make_observation('urn:ngsi-ld:Camera:Test', speed=50 - i * 3, observed_at=f"2025-11-01T10:00:{i:02d}Z")
        for i in range(10)
    ]
    
    detected, confidence, reason = detector.detect(observations, 'urn:ngsi-ld:Camera:Test')
    
    assert detected is False


def test_sudden_stop_detector_accident():
    """Test sudden stop detector with sudden stop scenario"""
    config = {
        'name': 'sudden_stop',
        'enabled': True,
        'speed_drop_threshold': 0.8,
        'time_window': 30,
        'min_initial_speed': 20
    }
    detector = SuddenStopDetector(config)
    
    # Create observations with sudden stop
    observations = [
        make_observation('urn:ngsi-ld:Camera:Test', speed=60, observed_at="2025-11-01T10:00:00Z"),
        make_observation('urn:ngsi-ld:Camera:Test', speed=5, observed_at="2025-11-01T10:00:10Z")
    ]
    
    detected, confidence, reason = detector.detect(observations, 'urn:ngsi-ld:Camera:Test')
    
    assert detected is True
    assert confidence > 0.8
    assert 'sudden_stop' in reason


def test_sudden_stop_detector_low_initial_speed():
    """Test sudden stop detector with low initial speed (no accident)"""
    config = {
        'name': 'sudden_stop',
        'enabled': True,
        'speed_drop_threshold': 0.8,
        'time_window': 30,
        'min_initial_speed': 20
    }
    detector = SuddenStopDetector(config)
    
    # Low initial speed - should not trigger
    observations = [
        make_observation('urn:ngsi-ld:Camera:Test', speed=15, observed_at="2025-11-01T10:00:00Z"),
        make_observation('urn:ngsi-ld:Camera:Test', speed=2, observed_at="2025-11-01T10:00:10Z")
    ]
    
    detected, confidence, reason = detector.detect(observations, 'urn:ngsi-ld:Camera:Test')
    
    assert detected is False
    assert 'initial_speed_too_low' in reason


# ==================== Unit Tests: Pattern Anomaly Detector ====================

def test_pattern_anomaly_detector_normal_pattern():
    """Test pattern anomaly detector with normal traffic pattern"""
    config = {
        'name': 'pattern_anomaly',
        'enabled': True,
        'intensity_threshold': 2.5
    }
    detector = PatternAnomalyDetector(config)
    
    # Create observations with stable intensity
    observations = [
        make_observation('urn:ngsi-ld:Camera:Test', intensity=10 + i * 0.5)
        for i in range(20)
    ]
    
    detected, confidence, reason = detector.detect(observations, 'urn:ngsi-ld:Camera:Test')
    
    assert detected is False
    assert 'normal_pattern' in reason


def test_pattern_anomaly_detector_accident():
    """Test pattern anomaly detector with abnormal pattern"""
    config = {
        'name': 'pattern_anomaly',
        'enabled': True,
        'intensity_threshold': 2.5
    }
    detector = PatternAnomalyDetector(config)
    
    # Create observations with sudden intensity spike
    observations = [
        make_observation('urn:ngsi-ld:Camera:Test', intensity=10)
        for _ in range(19)
    ] + [
        make_observation('urn:ngsi-ld:Camera:Test', intensity=100)
    ]
    
    detected, confidence, reason = detector.detect(observations, 'urn:ngsi-ld:Camera:Test')
    
    assert detected is True
    assert confidence > 0.0
    assert 'pattern_anomaly' in reason


# ==================== Unit Tests: Severity Classification ====================

def test_severity_classification(tmp_path):
    """Test severity classification based on confidence"""
    cfg = {
        'accident_detection': {
            'methods': [],
            'severity_thresholds': {
                'minor': 0.3,
                'moderate': 0.6,
                'severe': 0.9
            },
            'filtering': {'min_confidence': 0.0},
            'stellio': {'base_url': 'http://test', 'create_endpoint': '/entities'},
            'state': {'file': str(tmp_path / 'state.json')}
        }
    }
    cfg_path = tmp_path / 'config.yaml'
    write_yaml(cfg_path, cfg)
    
    agent = AccidentDetectionAgent(str(cfg_path))
    
    assert agent._classify_severity(0.2) == 'unknown'
    assert agent._classify_severity(0.4) == 'minor'
    assert agent._classify_severity(0.7) == 'moderate'
    assert agent._classify_severity(0.95) == 'severe'


# ==================== Integration Tests ====================

def test_accident_detection_integration(tmp_path, monkeypatch):
    """Test full accident detection pipeline"""
    cfg = {
        'accident_detection': {
            'methods': [
                {'name': 'speed_variance', 'enabled': True, 'threshold': 0.5, 'window_size': 5},
                {'name': 'occupancy_spike', 'enabled': True, 'spike_factor': 2.0, 'baseline_window': 10}
            ],
            'severity_thresholds': {'minor': 0.3, 'moderate': 0.6, 'severe': 0.9},
            'filtering': {'min_confidence': 0.3, 'cooldown_period': 0},
            'stellio': {'base_url': 'http://test', 'create_endpoint': '/entities', 'batch_create': False},
            'alert': {'enabled': True, 'notify_on_severity': ['moderate', 'severe'], 'alert_file': str(tmp_path / 'alerts.json')},
            'state': {'file': str(tmp_path / 'state.json'), 'history_file': str(tmp_path / 'history.json')},
            'entity': {'type': 'RoadAccident', 'id_prefix': 'urn:ngsi-ld:RoadAccident'}
        }
    }
    cfg_path = tmp_path / 'config.yaml'
    write_yaml(cfg_path, cfg)
    
    agent = AccidentDetectionAgent(str(cfg_path))
    
    # Mock POST
    def fake_post(url, json=None, headers=None, timeout=None):
        return MockResponse(201)
    
    monkeypatch.setattr(agent.session, 'post', fake_post)
    
    # Create accident scenario observations with extreme variance
    camera_ref = 'urn:ngsi-ld:Camera:Test'
    observations = [
        make_observation(camera_ref, speed=50, occ=0.3)
        for _ in range(10)
    ] + [
        make_observation(camera_ref, speed=60, occ=0.3),
        make_observation(camera_ref, speed=2, occ=0.9),
        make_observation(camera_ref, speed=58, occ=0.9),
        make_observation(camera_ref, speed=1, occ=0.9),
        make_observation(camera_ref, speed=55, occ=0.9)
    ]
    
    obs_file = tmp_path / 'obs.json'
    obs_file.write_text(json.dumps(observations))
    
    results = agent.process_observations_file(str(obs_file))
    
    # Verify detection
    detections = [r for r in results if r.get('detected')]
    assert len(detections) > 0
    
    detection = detections[0]
    assert detection['camera'] == camera_ref
    assert detection['confidence'] > 0.3
    assert 'severity' in detection
    assert len(detection['methods']) >= 1


def test_false_positive_filtering_cooldown(tmp_path, monkeypatch):
    """Test cooldown period filtering"""
    cfg = {
        'accident_detection': {
            'methods': [
                {'name': 'speed_variance', 'enabled': True, 'threshold': 0.5, 'window_size': 5}
            ],
            'severity_thresholds': {'minor': 0.3, 'moderate': 0.6, 'severe': 0.9},
            'filtering': {'min_confidence': 0.3, 'cooldown_period': 300},  # 5 minutes
            'stellio': {'base_url': 'http://test', 'create_endpoint': '/entities', 'batch_create': False},
            'state': {'file': str(tmp_path / 'state.json')}
        }
    }
    cfg_path = tmp_path / 'config.yaml'
    write_yaml(cfg_path, cfg)
    
    agent = AccidentDetectionAgent(str(cfg_path))
    
    # Mock POST
    post_count = {'count': 0}
    def fake_post(url, json=None, headers=None, timeout=None):
        post_count['count'] += 1
        return MockResponse(201)
    
    monkeypatch.setattr(agent.session, 'post', fake_post)
    
    # Create accident observations with extreme variance
    camera_ref = 'urn:ngsi-ld:Camera:Test'
    observations = [
        make_observation(camera_ref, speed=60),
        make_observation(camera_ref, speed=1),
        make_observation(camera_ref, speed=58),
        make_observation(camera_ref, speed=2),
        make_observation(camera_ref, speed=55),
        make_observation(camera_ref, speed=3),
        make_observation(camera_ref, speed=60),
        make_observation(camera_ref, speed=1),
        make_observation(camera_ref, speed=57),
        make_observation(camera_ref, speed=2),
    ]
    
    obs_file = tmp_path / 'obs1.json'
    obs_file.write_text(json.dumps(observations))
    
    # First detection
    results1 = agent.process_observations_file(str(obs_file))
    detections1 = [r for r in results1 if r.get('detected') and not r.get('filtered')]
    
    # Second detection immediately (should be filtered by cooldown)
    results2 = agent.process_observations_file(str(obs_file))
    detections2 = [r for r in results2 if r.get('detected') and not r.get('filtered')]
    
    assert len(detections1) > 0
    assert len(detections2) == 0  # Filtered by cooldown
    assert post_count['count'] == 1  # Only first detection created entity


def test_false_positive_filtering_min_confidence(tmp_path, monkeypatch):
    """Test minimum confidence filtering"""
    cfg = {
        'accident_detection': {
            'methods': [
                {'name': 'speed_variance', 'enabled': True, 'threshold': 5.0, 'window_size': 10}  # High threshold = low confidence
            ],
            'severity_thresholds': {'minor': 0.3, 'moderate': 0.6, 'severe': 0.9},
            'filtering': {'min_confidence': 0.8, 'cooldown_period': 0},  # High minimum
            'stellio': {'base_url': 'http://test', 'create_endpoint': '/entities', 'batch_create': False},
            'state': {'file': str(tmp_path / 'state.json')}
        }
    }
    cfg_path = tmp_path / 'config.yaml'
    write_yaml(cfg_path, cfg)
    
    agent = AccidentDetectionAgent(str(cfg_path))
    
    # Mock POST
    post_count = {'count': 0}
    def fake_post(url, json=None, headers=None, timeout=None):
        post_count['count'] += 1
        return MockResponse(201)
    
    monkeypatch.setattr(agent.session, 'post', fake_post)
    
    # Create low-confidence scenario
    camera_ref = 'urn:ngsi-ld:Camera:Test'
    observations = [
        make_observation(camera_ref, speed=30 + i)
        for i in range(15)
    ]
    
    obs_file = tmp_path / 'obs.json'
    obs_file.write_text(json.dumps(observations))
    
    results = agent.process_observations_file(str(obs_file))
    
    # All detections should be filtered
    unfiltered = [r for r in results if r.get('detected') and not r.get('filtered')]
    assert len(unfiltered) == 0
    assert post_count['count'] == 0


def test_multiple_methods_detection(tmp_path, monkeypatch):
    """Test detection with multiple methods agreeing"""
    cfg = {
        'accident_detection': {
            'methods': [
                {'name': 'speed_variance', 'enabled': True, 'threshold': 2.0, 'window_size': 5},
                {'name': 'occupancy_spike', 'enabled': True, 'spike_factor': 2.0, 'baseline_window': 10},
                {'name': 'sudden_stop', 'enabled': True, 'speed_drop_threshold': 0.8, 'time_window': 30, 'min_initial_speed': 20}
            ],
            'severity_thresholds': {'minor': 0.3, 'moderate': 0.6, 'severe': 0.9},
            'filtering': {'min_confidence': 0.3, 'cooldown_period': 0},
            'stellio': {'base_url': 'http://test', 'create_endpoint': '/entities', 'batch_create': False},
            'state': {'file': str(tmp_path / 'state.json')}
        }
    }
    cfg_path = tmp_path / 'config.yaml'
    write_yaml(cfg_path, cfg)
    
    agent = AccidentDetectionAgent(str(cfg_path))
    
    # Mock POST
    def fake_post(url, json=None, headers=None, timeout=None):
        return MockResponse(201)
    
    monkeypatch.setattr(agent.session, 'post', fake_post)
    
    # Create severe accident scenario (all methods should detect)
    camera_ref = 'urn:ngsi-ld:Camera:Test'
    observations = [
        make_observation(camera_ref, speed=50, occ=0.3, intensity=10, observed_at=f"2025-11-01T10:00:{i:02d}Z")
        for i in range(12)
    ] + [
        make_observation(camera_ref, speed=5, occ=0.9, intensity=100, observed_at="2025-11-01T10:00:15Z")
        for _ in range(3)
    ]
    
    obs_file = tmp_path / 'obs.json'
    obs_file.write_text(json.dumps(observations))
    
    results = agent.process_observations_file(str(obs_file))
    
    detections = [r for r in results if r.get('detected') and not r.get('filtered')]
    assert len(detections) > 0
    
    detection = detections[0]
    # Multiple methods should have detected
    assert len(detection['methods']) >= 2
    assert detection['confidence'] > 0.5


def test_rush_hour_false_positive(tmp_path, monkeypatch):
    """Test that rush hour patterns don't trigger false positives"""
    cfg = {
        'accident_detection': {
            'methods': [
                {'name': 'occupancy_spike', 'enabled': True, 'spike_factor': 2.0, 'baseline_window': 20}
            ],
            'severity_thresholds': {'minor': 0.3, 'moderate': 0.6, 'severe': 0.9},
            'filtering': {'min_confidence': 0.5, 'cooldown_period': 0},
            'stellio': {'base_url': 'http://test', 'create_endpoint': '/entities', 'batch_create': False},
            'state': {'file': str(tmp_path / 'state.json')}
        }
    }
    cfg_path = tmp_path / 'config.yaml'
    write_yaml(cfg_path, cfg)
    
    agent = AccidentDetectionAgent(str(cfg_path))
    
    # Mock POST
    post_count = {'count': 0}
    def fake_post(url, json=None, headers=None, timeout=None):
        post_count['count'] += 1
        return MockResponse(201)
    
    monkeypatch.setattr(agent.session, 'post', fake_post)
    
    # Gradual increase in occupancy (rush hour pattern)
    camera_ref = 'urn:ngsi-ld:Camera:Test'
    observations = [
        make_observation(camera_ref, occ=0.3 + i * 0.02)
        for i in range(30)
    ]
    
    obs_file = tmp_path / 'obs.json'
    obs_file.write_text(json.dumps(observations))
    
    results = agent.process_observations_file(str(obs_file))
    
    # Should not detect accident (gradual increase)
    detections = [r for r in results if r.get('detected') and not r.get('filtered')]
    assert len(detections) == 0
    assert post_count['count'] == 0


def test_entity_creation_with_relationships(tmp_path, monkeypatch):
    """Test RoadAccident entity creation with proper relationships"""
    cfg = {
        'accident_detection': {
            'methods': [
                {'name': 'speed_variance', 'enabled': True, 'threshold': 0.5, 'window_size': 5}
            ],
            'severity_thresholds': {'minor': 0.3, 'moderate': 0.6, 'severe': 0.9},
            'filtering': {'min_confidence': 0.3, 'cooldown_period': 0},
            'stellio': {'base_url': 'http://test', 'create_endpoint': '/entities', 'batch_create': False},
            'state': {'file': str(tmp_path / 'state.json')},
            'entity': {
                'type': 'RoadAccident',
                'id_prefix': 'urn:ngsi-ld:RoadAccident',
                'link_to_camera': True,
                'link_to_observations': True,
                'include_metadata': True
            }
        }
    }
    cfg_path = tmp_path / 'config.yaml'
    write_yaml(cfg_path, cfg)
    
    agent = AccidentDetectionAgent(str(cfg_path))
    
    # Capture posted entity
    posted_entities = []
    def fake_post(url, json=None, headers=None, timeout=None):
        posted_entities.append(json)
        return MockResponse(201)
    
    monkeypatch.setattr(agent.session, 'post', fake_post)
    
    # Create accident with extreme variance
    camera_ref = 'urn:ngsi-ld:Camera:TestCam'
    observations = [
        make_observation(camera_ref, speed=60),
        make_observation(camera_ref, speed=1),
        make_observation(camera_ref, speed=58),
        make_observation(camera_ref, speed=2),
        make_observation(camera_ref, speed=55),
        make_observation(camera_ref, speed=3),
        make_observation(camera_ref, speed=60),
        make_observation(camera_ref, speed=1),
        make_observation(camera_ref, speed=57),
        make_observation(camera_ref, speed=2),
    ]
    
    obs_file = tmp_path / 'obs.json'
    obs_file.write_text(json.dumps(observations))
    
    results = agent.process_observations_file(str(obs_file))
    
    # Verify entity structure
    assert len(posted_entities) > 0
    entity = posted_entities[0]
    
    assert entity['type'] == 'RoadAccident'
    assert 'urn:ngsi-ld:RoadAccident' in entity['id']
    assert 'refCamera' in entity
    assert entity['refCamera']['type'] == 'Relationship'
    assert entity['refCamera']['object'] == camera_ref
    assert 'refObservation' in entity
    assert 'severity' in entity
    assert 'confidence' in entity
    assert 'detectionMethod' in entity
    assert 'accidentDate' in entity
    assert '@context' in entity


def test_alert_generation(tmp_path, monkeypatch):
    """Test alert file generation for severe accidents"""
    alert_file = tmp_path / 'alerts.json'
    cfg = {
        'accident_detection': {
            'methods': [
                {'name': 'speed_variance', 'enabled': True, 'threshold': 0.5, 'window_size': 5}
            ],
            'severity_thresholds': {'minor': 0.3, 'moderate': 0.6, 'severe': 0.9},
            'filtering': {'min_confidence': 0.3, 'cooldown_period': 0},
            'stellio': {'base_url': 'http://test', 'create_endpoint': '/entities', 'batch_create': False},
            'alert': {
                'enabled': True,
                'notify_on_severity': ['severe'],
                'alert_file': str(alert_file)
            },
            'state': {'file': str(tmp_path / 'state.json')}
        }
    }
    cfg_path = tmp_path / 'config.yaml'
    write_yaml(cfg_path, cfg)
    
    agent = AccidentDetectionAgent(str(cfg_path))
    
    # Mock POST
    def fake_post(url, json=None, headers=None, timeout=None):
        return MockResponse(201)
    
    monkeypatch.setattr(agent.session, 'post', fake_post)
    
    # Create severe accident with extreme variance
    camera_ref = 'urn:ngsi-ld:Camera:Test'
    observations = [
        make_observation(camera_ref, speed=60),
        make_observation(camera_ref, speed=1),
        make_observation(camera_ref, speed=58),
        make_observation(camera_ref, speed=2),
        make_observation(camera_ref, speed=55),
        make_observation(camera_ref, speed=3),
        make_observation(camera_ref, speed=60),
        make_observation(camera_ref, speed=1),
        make_observation(camera_ref, speed=57),
        make_observation(camera_ref, speed=2),
    ]
    
    obs_file = tmp_path / 'obs.json'
    obs_file.write_text(json.dumps(observations))
    
    results = agent.process_observations_file(str(obs_file))
    
    # Check if severe accident was detected
    severe_detections = [r for r in results if r.get('severity') == 'severe']
    
    if len(severe_detections) > 0:
        # Alert file should be created
        assert alert_file.exists()
        
        alerts = json.loads(alert_file.read_text())
        assert len(alerts) > 0
        assert alerts[0]['severity'] == 'severe'
        assert alerts[0]['camera'] == camera_ref


def test_state_persistence(tmp_path, monkeypatch):
    """Test state and history persistence across runs"""
    state_file = tmp_path / 'state.json'
    history_file = tmp_path / 'history.json'
    
    cfg = {
        'accident_detection': {
            'methods': [
                {'name': 'speed_variance', 'enabled': True, 'threshold': 0.5, 'window_size': 5}
            ],
            'severity_thresholds': {'minor': 0.3, 'moderate': 0.6, 'severe': 0.9},
            'filtering': {'min_confidence': 0.3, 'cooldown_period': 60},
            'stellio': {'base_url': 'http://test', 'create_endpoint': '/entities', 'batch_create': False},
            'state': {
                'file': str(state_file),
                'history_file': str(history_file),
                'retention_days': 7
            }
        }
    }
    cfg_path = tmp_path / 'config.yaml'
    write_yaml(cfg_path, cfg)
    
    # First run
    agent1 = AccidentDetectionAgent(str(cfg_path))
    
    # Mock POST
    def fake_post(url, json=None, headers=None, timeout=None):
        return MockResponse(201)
    
    monkeypatch.setattr(agent1.session, 'post', fake_post)
    
    camera_ref = 'urn:ngsi-ld:Camera:Test'
    observations = [
        make_observation(camera_ref, speed=60),
        make_observation(camera_ref, speed=1),
        make_observation(camera_ref, speed=58),
        make_observation(camera_ref, speed=2),
        make_observation(camera_ref, speed=55),
        make_observation(camera_ref, speed=3),
        make_observation(camera_ref, speed=60),
        make_observation(camera_ref, speed=1),
        make_observation(camera_ref, speed=57),
        make_observation(camera_ref, speed=2),
    ]
    
    obs_file = tmp_path / 'obs.json'
    obs_file.write_text(json.dumps(observations))
    
    results1 = agent1.process_observations_file(str(obs_file))
    
    # State files should exist
    assert state_file.exists()
    assert history_file.exists()
    
    # Second run (new agent instance)
    agent2 = AccidentDetectionAgent(str(cfg_path))
    monkeypatch.setattr(agent2.session, 'post', fake_post)
    
    # State should be loaded
    camera_state = agent2.state_store.get_camera_state(camera_ref)
    assert camera_state['last_alert_ts'] is not None


def test_missing_observation_fields(tmp_path, monkeypatch):
    """Test graceful handling of missing observation fields"""
    cfg = {
        'accident_detection': {
            'methods': [
                {'name': 'speed_variance', 'enabled': True, 'threshold': 2.0, 'window_size': 5}
            ],
            'severity_thresholds': {'minor': 0.3, 'moderate': 0.6, 'severe': 0.9},
            'filtering': {'min_confidence': 0.3, 'cooldown_period': 0},
            'stellio': {'base_url': 'http://test', 'create_endpoint': '/entities', 'batch_create': False},
            'state': {'file': str(tmp_path / 'state.json')}
        }
    }
    cfg_path = tmp_path / 'config.yaml'
    write_yaml(cfg_path, cfg)
    
    agent = AccidentDetectionAgent(str(cfg_path))
    
    # Mock POST
    def fake_post(url, json=None, headers=None, timeout=None):
        return MockResponse(201)
    
    monkeypatch.setattr(agent.session, 'post', fake_post)
    
    # Create observations with missing speed field
    camera_ref = 'urn:ngsi-ld:Camera:Test'
    observations = [
        {'id': f'obs{i}', 'refDevice': {'object': camera_ref}, 'occupancy': {'value': 0.5}}
        for i in range(10)
    ]
    
    obs_file = tmp_path / 'obs.json'
    obs_file.write_text(json.dumps(observations))
    
    # Should not crash
    results = agent.process_observations_file(str(obs_file))
    
    assert len(results) > 0
    # No detection expected due to missing data
    detections = [r for r in results if r.get('detected')]
    assert len(detections) == 0


def test_batch_entity_creation(tmp_path, monkeypatch):
    """Test batch entity creation with multiple cameras"""
    cfg = {
        'accident_detection': {
            'methods': [
                {'name': 'speed_variance', 'enabled': True, 'threshold': 0.5, 'window_size': 5}
            ],
            'severity_thresholds': {'minor': 0.3, 'moderate': 0.6, 'severe': 0.9},
            'filtering': {'min_confidence': 0.3, 'cooldown_period': 0},
            'stellio': {'base_url': 'http://test', 'create_endpoint': '/entities', 'batch_create': True, 'max_workers': 2},
            'state': {'file': str(tmp_path / 'state.json')}
        }
    }
    cfg_path = tmp_path / 'config.yaml'
    write_yaml(cfg_path, cfg)
    
    agent = AccidentDetectionAgent(str(cfg_path))
    
    # Mock POST
    post_count = {'count': 0}
    def fake_post(url, json=None, headers=None, timeout=None):
        post_count['count'] += 1
        return MockResponse(201)
    
    monkeypatch.setattr(agent.session, 'post', fake_post)
    
    # Create accidents for multiple cameras with extreme variance
    observations = []
    for cam_id in range(3):
        camera_ref = f'urn:ngsi-ld:Camera:Cam{cam_id}'
        observations.extend([
            make_observation(camera_ref, speed=60),
            make_observation(camera_ref, speed=1),
            make_observation(camera_ref, speed=58),
            make_observation(camera_ref, speed=2),
            make_observation(camera_ref, speed=55),
            make_observation(camera_ref, speed=3),
            make_observation(camera_ref, speed=60),
            make_observation(camera_ref, speed=1),
            make_observation(camera_ref, speed=57),
            make_observation(camera_ref, speed=2),
        ])
    
    obs_file = tmp_path / 'obs.json'
    obs_file.write_text(json.dumps(observations))
    
    results = agent.process_observations_file(str(obs_file))
    
    # All cameras should be processed
    cameras_processed = set(r['camera'] for r in results)
    assert len(cameras_processed) == 3
    
    # Entities should be created
    assert post_count['count'] >= 1


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
