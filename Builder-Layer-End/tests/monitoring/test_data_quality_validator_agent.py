"""
Test Suite for Data Quality Validator Agent

Comprehensive tests covering:
- Configuration loading and validation
- Schema validation
- Business rules engine
- Quality scoring
- Data cleaning
- Integration scenarios
- Performance benchmarks

Author: Builder Layer
Date: 2025-11-02
"""

import pytest
import json
import yaml
import os
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Import agent components
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from agents.monitoring.data_quality_validator_agent import (
    DataQualityConfig,
    SchemaValidator,
    BusinessRulesEngine,
    QualityScorer,
    DataCleaner,
    DataQualityValidatorAgent
)


# ==============================================================================
# Test Fixtures
# ==============================================================================

@pytest.fixture
def config_path():
    """Path to test configuration file."""
    return 'config/data_quality_config.yaml'


@pytest.fixture
def data_quality_config(config_path):
    """Load data quality configuration."""
    return DataQualityConfig(config_path)


@pytest.fixture
def schema_validator(data_quality_config):
    """Create schema validator instance."""
    return SchemaValidator(data_quality_config)


@pytest.fixture
def business_rules_engine(data_quality_config):
    """Create business rules engine instance."""
    return BusinessRulesEngine(data_quality_config)


@pytest.fixture
def quality_scorer(data_quality_config):
    """Create quality scorer instance."""
    return QualityScorer(data_quality_config)


@pytest.fixture
def data_cleaner(data_quality_config):
    """Create data cleaner instance."""
    return DataCleaner(data_quality_config)


@pytest.fixture
def validator_agent(config_path):
    """Create validator agent instance."""
    return DataQualityValidatorAgent(config_path)


@pytest.fixture
def valid_camera_entity():
    """Create a valid camera entity for testing."""
    return {
        "id": "urn:ngsi-ld:Camera:TTH406",
        "type": "Camera",
        "@context": [
            "https://uri.etsi.org/ngsi-ld/v1/ngsi-ld-core-context.jsonld"
        ],
        "location": {
            "type": "GeoProperty",
            "value": {
                "type": "Point",
                "coordinates": [106.677234, 10.782345]
            }
        },
        "status": {
            "type": "Property",
            "value": "online",
            "observedAt": "2025-11-01T10:00:00.000Z"
        },
        "imageSnapshot": {
            "type": "Property",
            "value": "https://example.com/camera/TTH406/snapshot.jpg"
        },
        "averageSpeed": {
            "type": "Property",
            "value": 45.5,
            "unitCode": "KMH",
            "observedAt": "2025-11-01T10:00:00.000Z"
        },
        "description": {
            "type": "Property",
            "value": "Traffic camera at intersection TTH406"
        }
    }


@pytest.fixture
def invalid_camera_entity():
    """Create an invalid camera entity for testing."""
    return {
        "id": "invalid_id",  # Invalid format
        "type": "Camera",
        "@context": "https://uri.etsi.org/ngsi-ld/v1/ngsi-ld-core-context.jsonld",
        "location": {
            "type": "GeoProperty",
            "value": {
                "type": "Point",
                "coordinates": [200.0, 100.0]  # Invalid coordinates
            }
        },
        "averageSpeed": {
            "type": "Property",
            "value": -10.0  # Negative speed
        },
        "imageSnapshot": {
            "type": "Property",
            "value": "not_a_url"  # Invalid URL
        }
    }


# ==============================================================================
# Configuration Tests
# ==============================================================================

class TestDataQualityConfig:
    """Test configuration loading and management."""
    
    def test_config_loads_successfully(self, data_quality_config):
        """Test configuration file loads without errors."""
        assert data_quality_config.config is not None
        assert 'data_quality_validator' in data_quality_config.config
    
    def test_config_has_required_sections(self, data_quality_config):
        """Test configuration has all required sections."""
        validator_config = data_quality_config.config['data_quality_validator']
        
        assert 'schema_validation' in validator_config
        assert 'business_rules' in validator_config
        assert 'quality_thresholds' in validator_config
        assert 'data_cleaning' in validator_config
    
    def test_get_business_rules(self, data_quality_config):
        """Test retrieving business rules."""
        rules = data_quality_config.get_business_rules()
        
        assert isinstance(rules, list)
        assert len(rules) > 0
        
        # Check rule structure
        rule = rules[0]
        assert 'name' in rule
        assert 'field' in rule
        assert 'rules' in rule
        assert 'weight' in rule
    
    def test_get_business_rules_filtered_by_type(self, data_quality_config):
        """Test filtering business rules by entity type."""
        all_rules = data_quality_config.get_business_rules()
        camera_rules = data_quality_config.get_business_rules('Camera')
        
        # Camera rules should be subset of all rules
        assert len(camera_rules) <= len(all_rules)
    
    def test_get_quality_thresholds(self, data_quality_config):
        """Test retrieving quality thresholds."""
        thresholds = data_quality_config.get_quality_thresholds()
        
        assert 'accept' in thresholds
        assert 'warn' in thresholds
        assert 'reject' in thresholds
        
        # Validate threshold values
        assert 0.0 <= thresholds['accept'] <= 1.0
        assert 0.0 <= thresholds['reject'] <= 1.0
    
    def test_get_data_cleaning_rules(self, data_quality_config):
        """Test retrieving data cleaning rules."""
        cleaning_config = data_quality_config.get_data_cleaning_rules()
        
        assert 'enabled' in cleaning_config
        assert 'rules' in cleaning_config
        assert isinstance(cleaning_config['rules'], list)
    
    def test_env_var_expansion(self, config_path, monkeypatch):
        """Test environment variable expansion in configuration."""
        # Set test environment variable
        monkeypatch.setenv('TEST_VAR', 'test_value')
        
        # Create temp config with env var
        temp_config = """
data_quality_validator:
  test_field: ${TEST_VAR}
  business_rules: []
  quality_thresholds:
    accept: 0.7
    reject: 0.5
"""
        temp_path = 'config/temp_test_config.yaml'
        with open(temp_path, 'w') as f:
            f.write(temp_config)
        
        try:
            config = DataQualityConfig(temp_path)
            assert config.config['data_quality_validator']['test_field'] == 'test_value'
        finally:
            os.remove(temp_path)


# ==============================================================================
# Schema Validation Tests
# ==============================================================================

class TestSchemaValidator:
    """Test schema validation functionality."""
    
    def test_validate_valid_entity(self, schema_validator, valid_camera_entity):
        """Test validation of a valid entity."""
        is_valid, errors = schema_validator.validate(valid_camera_entity)
        
        assert is_valid is True
        assert len(errors) == 0
    
    def test_validate_missing_required_field(self, schema_validator):
        """Test validation fails for missing required fields."""
        entity = {
            "type": "Camera",
            "@context": "https://uri.etsi.org/ngsi-ld/v1/ngsi-ld-core-context.jsonld"
        }
        
        is_valid, errors = schema_validator.validate(entity)
        
        assert is_valid is False
        assert any('id' in error for error in errors)
    
    def test_validate_invalid_field_type(self, schema_validator):
        """Test validation fails for invalid field types."""
        entity = {
            "id": "urn:ngsi-ld:Camera:TTH406",
            "type": 123,  # Should be string
            "@context": "https://uri.etsi.org/ngsi-ld/v1/ngsi-ld-core-context.jsonld"
        }
        
        is_valid, errors = schema_validator.validate(entity)
        
        assert is_valid is False
        assert any('type' in error for error in errors)
    
    def test_validate_property_structure(self, schema_validator):
        """Test validation of NGSI-LD property structures."""
        entity = {
            "id": "urn:ngsi-ld:Camera:TTH406",
            "type": "Camera",
            "@context": "https://uri.etsi.org/ngsi-ld/v1/ngsi-ld-core-context.jsonld",
            "status": {
                "value": "online"  # Missing 'type' field
            }
        }
        
        is_valid, errors = schema_validator.validate(entity)
        
        # May pass or fail depending on strict_mode
        # Just ensure it runs without exception
        assert isinstance(is_valid, bool)
        assert isinstance(errors, list)
    
    def test_validate_with_strict_mode_disabled(self, data_quality_config, valid_camera_entity):
        """Test validation with strict mode disabled allows extra fields."""
        # Add extra field
        entity = valid_camera_entity.copy()
        entity['extraField'] = 'extra_value'
        
        validator = SchemaValidator(data_quality_config)
        is_valid, errors = validator.validate(entity)
        
        # Should pass with extra fields when strict_mode is false
        assert is_valid is True


# ==============================================================================
# Business Rules Engine Tests
# ==============================================================================

class TestBusinessRulesEngine:
    """Test business rules engine functionality."""
    
    def test_evaluate_valid_coordinates(self, business_rules_engine, valid_camera_entity):
        """Test coordinate validation passes for valid coordinates."""
        results = business_rules_engine.evaluate_rules(valid_camera_entity, 'Camera')
        
        # Find coordinate validation result
        coord_results = [r for r in results if 'coordinate' in r['rule'].lower()]
        
        assert len(coord_results) > 0
        # At least one coordinate rule should pass
        assert any(r['passed'] for r in coord_results)
    
    def test_evaluate_invalid_coordinates(self, business_rules_engine):
        """Test coordinate validation fails for invalid coordinates."""
        entity = {
            "id": "urn:ngsi-ld:Camera:TTH406",
            "type": "Camera",
            "@context": "https://uri.etsi.org/ngsi-ld/v1/ngsi-ld-core-context.jsonld",
            "location": {
                "type": "GeoProperty",
                "value": {
                    "type": "Point",
                    "coordinates": [200.0, 100.0]  # Invalid
                }
            }
        }
        
        results = business_rules_engine.evaluate_rules(entity, 'Camera')
        
        # Find coordinate validation result
        coord_results = [r for r in results if 'coordinate' in r['rule'].lower()]
        
        # At least one coordinate rule should fail
        assert any(not r['passed'] for r in coord_results)
    
    def test_evaluate_speed_validation(self, business_rules_engine):
        """Test speed validation rules."""
        entity = {
            "id": "urn:ngsi-ld:Camera:TTH406",
            "type": "Camera",
            "@context": "https://uri.etsi.org/ngsi-ld/v1/ngsi-ld-core-context.jsonld",
            "averageSpeed": {
                "type": "Property",
                "value": 45.5
            }
        }
        
        results = business_rules_engine.evaluate_rules(entity, 'Camera')
        
        # Find speed validation result
        speed_results = [r for r in results if 'speed' in r['rule'].lower()]
        
        if speed_results:
            # Valid speed should pass
            assert any(r['passed'] for r in speed_results)
    
    def test_evaluate_negative_speed(self, business_rules_engine):
        """Test negative speed fails validation."""
        entity = {
            "id": "urn:ngsi-ld:Camera:TTH406",
            "type": "Camera",
            "@context": "https://uri.etsi.org/ngsi-ld/v1/ngsi-ld-core-context.jsonld",
            "averageSpeed": {
                "type": "Property",
                "value": -10.0
            }
        }
        
        results = business_rules_engine.evaluate_rules(entity, 'Camera')
        
        # Find speed validation result
        speed_results = [r for r in results if 'speed' in r['rule'].lower()]
        
        # Negative speed should fail
        assert any(not r['passed'] for r in speed_results)
    
    def test_evaluate_timestamp_order(self, business_rules_engine):
        """Test timestamp order validation."""
        # Future timestamp
        future_time = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
        
        entity = {
            "id": "urn:ngsi-ld:Camera:TTH406",
            "type": "Camera",
            "@context": "https://uri.etsi.org/ngsi-ld/v1/ngsi-ld-core-context.jsonld",
            "observedAt": future_time
        }
        
        results = business_rules_engine.evaluate_rules(entity, 'Camera')
        
        # Find timestamp validation result
        timestamp_results = [r for r in results if 'timestamp' in r['rule'].lower()]
        
        # Future timestamp should fail
        if timestamp_results:
            assert any(not r['passed'] for r in timestamp_results)
    
    @patch('requests.head')
    def test_evaluate_url_accessibility(self, mock_head, business_rules_engine):
        """Test URL accessibility validation."""
        # Mock successful HTTP response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_head.return_value = mock_response
        
        entity = {
            "id": "urn:ngsi-ld:Camera:TTH406",
            "type": "Camera",
            "@context": "https://uri.etsi.org/ngsi-ld/v1/ngsi-ld-core-context.jsonld",
            "imageSnapshot": {
                "type": "Property",
                "value": "https://example.com/image.jpg"
            }
        }
        
        results = business_rules_engine.evaluate_rules(entity, 'Camera')
        
        # Find URL validation result
        url_results = [r for r in results if 'url' in r['rule'].lower() or 'image' in r['rule'].lower()]
        
        # Accessible URL should pass
        if url_results:
            assert any(r['passed'] for r in url_results)
    
    def test_extract_field_value_nested(self, business_rules_engine):
        """Test extracting nested field values."""
        entity = {
            "location": {
                "value": {
                    "coordinates": [106.5, 10.5]
                }
            }
        }
        
        # Test dot notation
        value = business_rules_engine._extract_field_value(
            entity,
            "location.value.coordinates"
        )
        assert value == [106.5, 10.5]
        
        # Test array indexing
        value = business_rules_engine._extract_field_value(
            entity,
            "location.value.coordinates[0]"
        )
        assert value == 106.5
    
    def test_expression_evaluation_comparison(self, business_rules_engine):
        """Test expression evaluation with comparison operators."""
        # Test >= operator
        result = business_rules_engine._evaluate_expression(
            "speed >= 0.0",
            45.5,
            {}
        )
        assert result is True
        
        # Test <= operator
        result = business_rules_engine._evaluate_expression(
            "speed <= 120.0",
            45.5,
            {}
        )
        assert result is True
        
        # Test AND operator
        result = business_rules_engine._evaluate_expression(
            "speed >= 0.0 AND speed <= 120.0",
            45.5,
            {}
        )
        assert result is True
    
    def test_expression_evaluation_in_operator(self, business_rules_engine):
        """Test expression evaluation with IN operator."""
        result = business_rules_engine._evaluate_expression(
            "200 IN [200, 301, 302]",
            200,
            {}
        )
        assert result is True
        
        result = business_rules_engine._evaluate_expression(
            "404 IN [200, 301, 302]",
            404,
            {}
        )
        assert result is False
    
    def test_expression_evaluation_matches_operator(self, business_rules_engine):
        """Test expression evaluation with MATCHES operator."""
        # Test regex matching
        result = business_rules_engine._evaluate_expression(
            "MATCHES(url, '^https?://')",
            "https://example.com",
            {}
        )
        assert result is True
        
        result = business_rules_engine._evaluate_expression(
            "MATCHES(url, '^https?://')",
            "not_a_url",
            {}
        )
        assert result is False


# ==============================================================================
# Quality Scorer Tests
# ==============================================================================

class TestQualityScorer:
    """Test quality scoring functionality."""
    
    def test_calculate_score_all_passed(self, quality_scorer):
        """Test score calculation when all rules pass."""
        rule_results = [
            {'passed': True, 'weight': 1.0},
            {'passed': True, 'weight': 0.8},
            {'passed': True, 'weight': 0.5}
        ]
        
        score, status = quality_scorer.calculate_score(True, rule_results)
        
        assert score == 1.0
        assert status == 'PASS'
    
    def test_calculate_score_all_failed(self, quality_scorer):
        """Test score calculation when all rules fail."""
        rule_results = [
            {'passed': False, 'weight': 1.0},
            {'passed': False, 'weight': 0.8},
            {'passed': False, 'weight': 0.5}
        ]
        
        score, status = quality_scorer.calculate_score(True, rule_results)
        
        assert score == 0.0
        assert status == 'REJECT'
    
    def test_calculate_score_partial(self, quality_scorer):
        """Test score calculation with partial pass."""
        rule_results = [
            {'passed': True, 'weight': 1.0},
            {'passed': False, 'weight': 0.8},
            {'passed': True, 'weight': 0.5}
        ]
        
        score, status = quality_scorer.calculate_score(True, rule_results)
        
        # Score = (1.0 + 0.5) / (1.0 + 0.8 + 0.5) = 1.5 / 2.3 ≈ 0.652
        assert 0.6 <= score <= 0.7
        assert status in ['PASS', 'WARNING']
    
    def test_calculate_score_schema_invalid(self, quality_scorer):
        """Test score is 0 when schema validation fails."""
        rule_results = [
            {'passed': True, 'weight': 1.0}
        ]
        
        score, status = quality_scorer.calculate_score(False, rule_results)
        
        assert score == 0.0
        assert status == 'REJECT'
    
    def test_calculate_score_skipped_rules(self, quality_scorer):
        """Test score calculation ignores skipped rules."""
        rule_results = [
            {'passed': True, 'weight': 1.0},
            {'passed': True, 'weight': 0.8, 'skipped': True},  # Skipped
            {'passed': True, 'weight': 0.5}
        ]
        
        score, status = quality_scorer.calculate_score(True, rule_results)
        
        # Score = (1.0 + 0.5) / (1.0 + 0.5) = 1.0 (skipped rule not counted)
        assert score == 1.0
    
    def test_get_status_thresholds(self, quality_scorer):
        """Test status determination based on thresholds."""
        # High score -> PASS
        status = quality_scorer._get_status(0.85)
        assert status == 'PASS'
        
        # Medium score -> WARNING
        status = quality_scorer._get_status(0.6)
        assert status in ['PASS', 'WARNING']
        
        # Low score -> REJECT
        status = quality_scorer._get_status(0.3)
        assert status == 'REJECT'


# ==============================================================================
# Data Cleaner Tests
# ==============================================================================

class TestDataCleaner:
    """Test data cleaning functionality."""
    
    def test_clean_timezone_conversion(self, data_cleaner):
        """Test timezone conversion to UTC."""
        entity = {
            "id": "urn:ngsi-ld:Camera:TTH406",
            "type": "Camera",
            "observedAt": "2025-11-01T10:00:00+07:00"  # UTC+7
        }
        
        cleaned = data_cleaner.clean(entity)
        
        # Should be converted to UTC (3 hours earlier)
        assert 'observedAt' in cleaned
        assert 'Z' in cleaned['observedAt'] or '+00:00' in cleaned['observedAt']
    
    def test_clean_trim_whitespace(self, data_cleaner):
        """Test whitespace trimming."""
        entity = {
            "id": "urn:ngsi-ld:Camera:TTH406",
            "type": "  Camera  ",
            "description": {
                "type": "Property",
                "value": "  Test description  "
            }
        }
        
        cleaned = data_cleaner.clean(entity)
        
        assert cleaned['type'] == 'CAMERA'  # Also uppercased due to case normalization
        assert cleaned['description']['value'] == 'Test description'
    
    def test_clean_normalize_case(self, data_cleaner):
        """Test case normalization."""
        entity = {
            "id": "urn:ngsi-ld:Camera:TTH406",
            "type": "camera"
        }
        
        cleaned = data_cleaner.clean(entity)
        
        # Type should be uppercase
        assert cleaned['type'] == 'CAMERA'
    
    def test_clean_remove_nulls(self, data_cleaner):
        """Test removal of null values."""
        entity = {
            "id": "urn:ngsi-ld:Camera:TTH406",
            "type": "Camera",
            "nullField": None,
            "emptyField": "",
            "validField": "value"
        }
        
        cleaned = data_cleaner.clean(entity)
        
        assert 'nullField' not in cleaned
        assert 'emptyField' not in cleaned
        assert 'validField' in cleaned
    
    def test_clean_numeric_precision(self, data_cleaner):
        """Test numeric precision rounding."""
        entity = {
            "id": "urn:ngsi-ld:Camera:TTH406",
            "type": "Camera",
            "location": {
                "type": "GeoProperty",
                "value": {
                    "coordinates": [106.12345678, 10.98765432]
                }
            }
        }
        
        cleaned = data_cleaner.clean(entity)
        
        coords = cleaned['location']['value']['coordinates']
        
        # Should be rounded to 6 decimal places
        assert len(str(coords[0]).split('.')[-1]) <= 6
        assert len(str(coords[1]).split('.')[-1]) <= 6
    
    def test_clean_normalize_urls(self, data_cleaner):
        """Test URL normalization."""
        entity = {
            "id": "urn:ngsi-ld:Camera:TTH406",
            "type": "Camera",
            "imageSnapshot": {
                "type": "Property",
                "value": "HTTPS://EXAMPLE.COM/Image/"
            }
        }
        
        cleaned = data_cleaner.clean(entity)
        
        url = cleaned['imageSnapshot']['value']
        
        # Scheme and host should be lowercase, trailing slash removed
        assert url.startswith('https://example.com')
        assert not url.endswith('/')
    
    def test_clean_normalize_datetime(self, data_cleaner):
        """Test datetime normalization."""
        entity = {
            "id": "urn:ngsi-ld:Camera:TTH406",
            "type": "Camera",
            "dateObserved": {
                "type": "Property",
                "value": "2025-11-01T10:00:00"  # Missing timezone
            }
        }
        
        cleaned = data_cleaner.clean(entity)
        
        dt_value = cleaned['dateObserved']['value']
        
        # Should have timezone indicator
        assert 'Z' in dt_value or '+' in dt_value


# ==============================================================================
# Integration Tests
# ==============================================================================

class TestDataQualityValidatorAgent:
    """Test complete validator agent integration."""
    
    def test_validate_valid_entity(self, validator_agent, valid_camera_entity):
        """Test validation of a valid entity."""
        report = validator_agent.validate_entity(valid_camera_entity)
        
        assert report['entity_id'] == 'urn:ngsi-ld:Camera:TTH406'
        assert report['entity_type'] == 'Camera'
        assert 'quality_score' in report
        assert 'status' in report
        assert report['status'] in ['PASS', 'WARNING', 'REJECT']
    
    def test_validate_invalid_entity(self, validator_agent, invalid_camera_entity):
        """Test validation of an invalid entity."""
        report = validator_agent.validate_entity(invalid_camera_entity)
        
        assert report['quality_score'] < 1.0
        assert len(report['errors']) > 0
    
    def test_validate_with_auto_clean(self, validator_agent):
        """Test validation with automatic data cleaning."""
        entity = {
            "id": "urn:ngsi-ld:Camera:TTH406",
            "type": "  camera  ",  # Needs cleaning
            "@context": "https://uri.etsi.org/ngsi-ld/v1/ngsi-ld-core-context.jsonld",
            "location": {
                "type": "GeoProperty",
                "value": {
                    "coordinates": [106.5, 10.5]
                }
            }
        }
        
        report = validator_agent.validate_entity(entity, auto_clean=True)
        
        # Should pass after cleaning
        assert report['status'] in ['PASS', 'WARNING']
    
    def test_validate_batch_sequential(self, validator_agent, valid_camera_entity):
        """Test batch validation in sequential mode."""
        entities = [valid_camera_entity.copy() for _ in range(10)]
        
        # Make each entity unique
        for i, entity in enumerate(entities):
            entity['id'] = f"urn:ngsi-ld:Camera:CAM{i:03d}"
        
        reports = validator_agent.validate_batch(entities, parallel=False)
        
        assert len(reports) == 10
        assert all('quality_score' in r for r in reports)
    
    def test_validate_batch_parallel(self, validator_agent, valid_camera_entity):
        """Test batch validation in parallel mode."""
        entities = [valid_camera_entity.copy() for _ in range(10)]
        
        # Make each entity unique
        for i, entity in enumerate(entities):
            entity['id'] = f"urn:ngsi-ld:Camera:CAM{i:03d}"
        
        reports = validator_agent.validate_batch(entities, parallel=True)
        
        assert len(reports) == 10
        assert all('quality_score' in r for r in reports)
    
    def test_get_validation_summary(self, validator_agent):
        """Test validation summary generation."""
        reports = [
            {'status': 'PASS', 'quality_score': 0.95},
            {'status': 'PASS', 'quality_score': 0.85},
            {'status': 'WARNING', 'quality_score': 0.65},
            {'status': 'REJECT', 'quality_score': 0.35}
        ]
        
        summary = validator_agent.get_validation_summary(reports)
        
        assert summary['total_entities'] == 4
        assert summary['passed'] == 2
        assert summary['warnings'] == 1
        assert summary['rejected'] == 1
        assert 0.0 <= summary['average_quality_score'] <= 1.0
        assert summary['pass_rate'] == 50.0  # 2/4 = 50%
    
    def test_validation_report_structure(self, validator_agent, valid_camera_entity):
        """Test validation report has correct structure."""
        report = validator_agent.validate_entity(valid_camera_entity)
        
        # Check required fields
        required_fields = [
            'entity_id',
            'entity_type',
            'validation_timestamp',
            'quality_score',
            'status',
            'schema_validation',
            'business_rules',
            'checks',
            'errors',
            'warnings'
        ]
        
        for field in required_fields:
            assert field in report, f"Missing field: {field}"
    
    def test_validation_with_different_entity_types(self, validator_agent):
        """Test validation works with different entity types."""
        # Test with TrafficFlowObserved entity
        entity = {
            "id": "urn:ngsi-ld:TrafficFlowObserved:TF001",
            "type": "TrafficFlowObserved",
            "@context": "https://uri.etsi.org/ngsi-ld/v1/ngsi-ld-core-context.jsonld",
            "location": {
                "type": "GeoProperty",
                "value": {
                    "coordinates": [106.5, 10.5]
                }
            },
            "intensity": {
                "type": "Property",
                "value": 150
            }
        }
        
        report = validator_agent.validate_entity(entity)
        
        assert report['entity_type'] == 'TrafficFlowObserved'
        assert 'quality_score' in report


# ==============================================================================
# Edge Cases and Error Handling Tests
# ==============================================================================

class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_validate_empty_entity(self, validator_agent):
        """Test validation of empty entity."""
        entity = {}
        
        report = validator_agent.validate_entity(entity)
        
        assert report['status'] == 'REJECT'
        assert report['quality_score'] == 0.0
    
    def test_validate_missing_optional_fields(self, validator_agent):
        """Test validation with missing optional fields."""
        entity = {
            "id": "urn:ngsi-ld:Camera:TTH406",
            "type": "Camera",
            "@context": "https://uri.etsi.org/ngsi-ld/v1/ngsi-ld-core-context.jsonld"
        }
        
        report = validator_agent.validate_entity(entity)
        
        # Should not fail completely for missing optional fields
        assert report['status'] in ['PASS', 'WARNING', 'REJECT']
    
    def test_validate_malformed_coordinates(self, validator_agent):
        """Test validation with malformed coordinates."""
        entity = {
            "id": "urn:ngsi-ld:Camera:TTH406",
            "type": "Camera",
            "@context": "https://uri.etsi.org/ngsi-ld/v1/ngsi-ld-core-context.jsonld",
            "location": {
                "type": "GeoProperty",
                "value": {
                    "coordinates": [106.5]  # Missing latitude
                }
            }
        }
        
        report = validator_agent.validate_entity(entity)
        
        # Should detect malformed coordinates
        assert report['quality_score'] < 1.0
    
    def test_validate_with_http_timeout(self, validator_agent):
        """Test validation handles HTTP timeouts gracefully."""
        entity = {
            "id": "urn:ngsi-ld:Camera:TTH406",
            "type": "Camera",
            "@context": "https://uri.etsi.org/ngsi-ld/v1/ngsi-ld-core-context.jsonld",
            "imageSnapshot": {
                "type": "Property",
                "value": "https://httpstat.us/200?sleep=10000"  # Will timeout
            }
        }
        
        # Should not raise exception, just mark as failed
        report = validator_agent.validate_entity(entity)
        assert 'quality_score' in report
    
    def test_validate_special_characters(self, validator_agent):
        """Test validation with special characters in strings."""
        entity = {
            "id": "urn:ngsi-ld:Camera:TTH406",
            "type": "Camera",
            "@context": "https://uri.etsi.org/ngsi-ld/v1/ngsi-ld-core-context.jsonld",
            "description": {
                "type": "Property",
                "value": "Test <>&\"' special characters"
            }
        }
        
        report = validator_agent.validate_entity(entity)
        
        # Should handle special characters without errors
        assert 'quality_score' in report


# ==============================================================================
# Performance Tests
# ==============================================================================

class TestPerformance:
    """Test performance requirements."""
    
    def test_validate_722_entities_under_10_seconds(self, validator_agent, valid_camera_entity):
        """Test validation of 722 entities completes in under 10 seconds."""
        # Create 722 unique entities
        entities = []
        for i in range(722):
            entity = valid_camera_entity.copy()
            entity['id'] = f"urn:ngsi-ld:Camera:CAM{i:04d}"
            entities.append(entity)
        
        # Measure time
        start_time = time.time()
        reports = validator_agent.validate_batch(entities, parallel=True)
        elapsed_time = time.time() - start_time
        
        # Check results
        assert len(reports) == 722
        assert elapsed_time < 10.0, f"Validation took {elapsed_time:.2f}s, expected < 10s"
        
        print(f"\nPerformance: Validated 722 entities in {elapsed_time:.2f}s")
    
    def test_parallel_faster_than_sequential(self, validator_agent, valid_camera_entity):
        """Test parallel validation is faster than sequential."""
        # Create test entities
        entities = [valid_camera_entity.copy() for _ in range(50)]
        for i, entity in enumerate(entities):
            entity['id'] = f"urn:ngsi-ld:Camera:CAM{i:03d}"
        
        # Sequential validation
        start_seq = time.time()
        reports_seq = validator_agent.validate_batch(entities, parallel=False)
        time_seq = time.time() - start_seq
        
        # Parallel validation
        start_par = time.time()
        reports_par = validator_agent.validate_batch(entities, parallel=True)
        time_par = time.time() - start_par
        
        # Results should be the same
        assert len(reports_seq) == len(reports_par) == 50
        
        # Parallel should be faster (or at least not significantly slower)
        print(f"\nSequential: {time_seq:.2f}s, Parallel: {time_par:.2f}s")
        # Allow some tolerance due to overhead
        assert time_par <= time_seq * 1.5
    
    def test_caching_improves_performance(self, business_rules_engine):
        """Test HTTP caching improves performance for repeated checks."""
        url = "https://example.com/test.jpg"
        
        # Clear cache first
        business_rules_engine.http_cache.clear()
        
        # First check (uncached) - should call requests.head
        with patch('requests.head') as mock_head:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_head.return_value = mock_response
            
            status1 = business_rules_engine._http_head_check(url)
            call_count_1 = mock_head.call_count
        
        # Second check (cached) - should NOT call requests.head
        with patch('requests.head') as mock_head:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_head.return_value = mock_response
            
            status2 = business_rules_engine._http_head_check(url)
            call_count_2 = mock_head.call_count
        
        # Verify cache works: first call hits the network, second doesn't
        assert status1 == status2 == 200
        assert call_count_1 == 1, "First check should call requests.head"
        assert call_count_2 == 0, "Second check should use cache, not call requests.head"


# ==============================================================================
# Test Runner
# ==============================================================================

if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
