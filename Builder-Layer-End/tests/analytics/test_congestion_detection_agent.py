import json
from types import SimpleNamespace
from pathlib import Path
import pytest
from agents.analytics.congestion_detection_agent import CongestionDetectionAgent, CongestionConfig, StateStore, now_iso


class MockResponse:
    def __init__(self, status_code=204):
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception(f"HTTP {self.status_code}")


def write_yaml(path, data):
    import yaml
    with open(path, 'w', encoding='utf-8') as f:
        yaml.safe_dump(data, f)


def make_entity(camera_ref, occ=None, speed=None, intensity=None, observed_at=None):
    if observed_at is None:
        observed_at = now_iso()
    ent = {'id': f'urn:ngsi-ld:ItemFlowObserved:{camera_ref}', 'refDevice': {'object': camera_ref}}
    if occ is not None:
        ent['occupancy'] = {'type': 'Property', 'value': occ, 'observedAt': observed_at}
    if speed is not None:
        ent['averageSpeed'] = {'type': 'Property', 'value': speed, 'observedAt': observed_at}
    if intensity is not None:
        ent['intensity'] = {'type': 'Property', 'value': intensity, 'observedAt': observed_at}
    return ent


def test_simple_congestion_patch(tmp_path, monkeypatch):
    # Config with min_duration 0 -> immediate patch
    cfg = {
        'congestion_detection': {
            'thresholds': {'occupancy': 0.5, 'average_speed': 15, 'intensity': 10},
            'rules': {'logic': 'AND', 'min_duration': 0},
            'stellio': {'base_url': 'http://localhost:1234', 'update_endpoint': '/entities/{id}/attrs', 'batch_updates': True},
            'alert': {'enabled': False}
        }
    }
    cfg_path = tmp_path / 'cong.yaml'
    write_yaml(cfg_path, cfg)
    state_file = tmp_path / 'state.json'

    agent = CongestionDetectionAgent(str(cfg_path))
    # Override state's path to our tmp state
    agent.state_store = StateStore(str(state_file))

    # Prepare observation that breaches all thresholds
    ent = make_entity('urn:ngsi-ld:Camera:Cam1', occ=0.7, speed=10, intensity=12)
    obs_file = tmp_path / 'obs.json'
    obs_file.write_text(json.dumps([ent]))

    # Mock patch
    def fake_patch(url, json=None, headers=None, timeout=None):
        return MockResponse(204)

    monkeypatch.setattr(agent.session, 'patch', fake_patch)

    results = agent.process_observations_file(str(obs_file))
    # Expect one update result with success True
    updates = [r for r in results if r.get('updated')]
    assert len(updates) == 1
    assert updates[0]['success'] is True
    # State file should reflect congested True
    agent.state_store.save()
    data = json.loads(state_file.read_text())
    assert 'urn:ngsi-ld:Camera:Cam1' in data
    assert data['urn:ngsi-ld:Camera:Cam1']['congested'] is True


def test_min_duration_starts_timer(tmp_path, monkeypatch):
    # Config with min_duration 60 -> no immediate patch
    cfg = {
        'congestion_detection': {
            'thresholds': {'occupancy': 0.5, 'average_speed': 15, 'intensity': 10},
            'rules': {'logic': 'AND', 'min_duration': 60},
            'stellio': {'base_url': 'http://localhost:1234', 'update_endpoint': '/entities/{id}/attrs', 'batch_updates': False},
            'alert': {'enabled': False}
        }
    }
    cfg_path = tmp_path / 'cong2.yaml'
    write_yaml(cfg_path, cfg)
    state_file = tmp_path / 'state2.json'

    agent = CongestionDetectionAgent(str(cfg_path))
    agent.state_store = StateStore(str(state_file))
    agent.detector.state_store = agent.state_store  # Update detector's reference

    ent = make_entity('urn:ngsi-ld:Camera:Cam2', occ=0.8, speed=5, intensity=20)
    obs_file = tmp_path / 'obs2.json'
    obs_file.write_text(json.dumps([ent]))

    # Mock patch should not be called, but patch if called returns 204
    called = {'v': False}

    def fake_patch(url, json=None, headers=None, timeout=None):
        called['v'] = True
        return MockResponse(204)

    monkeypatch.setattr(agent.session, 'patch', fake_patch)

    results = agent.process_observations_file(str(obs_file))
    # No update should be performed yet
    updates = [r for r in results if r.get('updated')]
    assert len(updates) == 0
    assert called['v'] is False
    # State should have first_breach_ts set
    data = json.loads(state_file.read_text()) if state_file.exists() and state_file.read_text() else None
    # The agent saved state via in-memory StateStore; ensure it's present
    st = agent.state_store.get('urn:ngsi-ld:Camera:Cam2')
    assert st is not None
    assert st.get('first_breach_ts') is not None
    assert st.get('congested') is False


def test_clear_congestion_triggers_patch(tmp_path, monkeypatch):
    # Start with existing congested state True
    cfg = {
        'congestion_detection': {
            'thresholds': {'occupancy': 0.5, 'average_speed': 15, 'intensity': 10},
            'rules': {'logic': 'AND', 'min_duration': 0},
            'stellio': {'base_url': 'http://localhost:1234', 'update_endpoint': '/entities/{id}/attrs', 'batch_updates': False},
            'alert': {'enabled': False}
        }
    }
    cfg_path = tmp_path / 'cong3.yaml'
    write_yaml(cfg_path, cfg)
    state_file = tmp_path / 'state3.json'

    agent = CongestionDetectionAgent(str(cfg_path))
    agent.state_store = StateStore(str(state_file))
    agent.detector.state_store = agent.state_store  # Update detector's reference
    # Seed state as congested
    agent.state_store.update('urn:ngsi-ld:Camera:Cam3', True, None, now_iso())
    agent.state_store.save()

    # Observation that clears congestion
    ent = make_entity('urn:ngsi-ld:Camera:Cam3', occ=0.1, speed=25, intensity=1)
    obs_file = tmp_path / 'obs3.json'
    obs_file.write_text(json.dumps([ent]))

    called = {'v': False}

    def fake_patch(url, json=None, headers=None, timeout=None):
        called['v'] = True
        return MockResponse(204)

    monkeypatch.setattr(agent.session, 'patch', fake_patch)
    results = agent.process_observations_file(str(obs_file))
    updates = [r for r in results if r.get('updated')]
    assert len(updates) == 1
    assert updates[0]['success'] is True
    # State should be updated to congested False
    st = agent.state_store.get('urn:ngsi-ld:Camera:Cam3')
    assert st['congested'] is False


def test_missing_fields_no_crash(tmp_path, monkeypatch):
    cfg = {
        'congestion_detection': {
            'thresholds': {'occupancy': 0.5, 'average_speed': 15, 'intensity': 10},
            'rules': {'logic': 'AND', 'min_duration': 0},
            'stellio': {'base_url': 'http://localhost:1234', 'update_endpoint': '/entities/{id}/attrs', 'batch_updates': True},
            'alert': {'enabled': False}
        }
    }
    cfg_path = tmp_path / 'cong4.yaml'
    write_yaml(cfg_path, cfg)
    agent = CongestionDetectionAgent(str(cfg_path))

    # Observation missing numeric fields
    ent = {'id': 'urn:ngsi-ld:ItemFlowObserved:CamX', 'refDevice': {'object': 'urn:ngsi-ld:Camera:CamX'}}
    obs_file = tmp_path / 'obs4.json'
    obs_file.write_text(json.dumps([ent]))

    # Monkeypatch patch to ensure not called
    def fake_patch(url, json=None, headers=None, timeout=None):
        raise AssertionError('patch should not be called for missing fields')

    monkeypatch.setattr(agent.session, 'patch', fake_patch)
    results = agent.process_observations_file(str(obs_file))
    # No updates and no crash
    updates = [r for r in results if r.get('updated')]
    assert len(updates) == 0


def test_alert_on_new_congestion(tmp_path, monkeypatch):
    cfg = {
        'congestion_detection': {
            'thresholds': {'occupancy': 0.5, 'average_speed': 15, 'intensity': 10},
            'rules': {'logic': 'AND', 'min_duration': 0},
            'stellio': {'base_url': 'http://localhost:1234', 'update_endpoint': '/entities/{id}/attrs', 'batch_updates': True},
            'alert': {'enabled': True, 'notify_on_change': True},
            'state': {'file': str(tmp_path / 'state5.json')}  # Use temp state file
        }
    }
    cfg_path = tmp_path / 'cong5.yaml'
    write_yaml(cfg_path, cfg)
    alerts_file = Path('data/alerts.json')
    if alerts_file.exists():
        alerts_file.unlink()

    agent = CongestionDetectionAgent(str(cfg_path))
    # Mock patch
    def fake_patch(url, json=None, headers=None, timeout=None):
        return MockResponse(204)

    monkeypatch.setattr(agent.session, 'patch', fake_patch)

    ent = make_entity('urn:ngsi-ld:Camera:CamAlert', occ=0.9, speed=5, intensity=20)
    obs_file = tmp_path / 'obs5.json'
    obs_file.write_text(json.dumps([ent]))

    results = agent.process_observations_file(str(obs_file))
    # Alert file should be created
    assert alerts_file.exists()
    alerts = json.loads(alerts_file.read_text())
    assert any(a['camera'] == 'urn:ngsi-ld:Camera:CamAlert' for a in alerts)
    # Clean up
    alerts_file.unlink()
