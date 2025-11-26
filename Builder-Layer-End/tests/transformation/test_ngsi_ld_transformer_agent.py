"""
Test Suite for NGSI-LD Transformer Agent

Comprehensive tests ensuring 100% coverage:
- Unit tests for all methods and classes
- Integration tests with real camera data
- Validation tests for NGSI-LD compliance
- Performance tests with 722 entities

Author: Builder Layer LOD System
Version: 1.0.0
"""

import json
import pytest
import time
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import yaml

from agents.transformation.ngsi_ld_transformer_agent import (
    TransformationEngine,
    NGSILDValidator,
    NGSILDTransformerAgent,
)


@pytest.fixture
def mock_config_file(tmp_path):
    """Create a temporary config file for testing."""
    config_data = {
        "entity_type": "Camera",
        "uri_prefix": "urn:ngsi-ld:Camera:",
        "id_field": "code",
        "property_mappings": {
            "name": {"target": "cameraName", "type": "Property"},
            "code": {"target": "cameraNum", "type": "Property"},
            "ptz": {
                "target": "cameraType",
                "type": "Property",
                "transform": "boolean_to_ptz",
            },
            "cam_type": {
                "target": "cameraUsage",
                "type": "Property",
                "transform": "uppercase",
            },
        },
        "geo_property": {
            "source": ["latitude", "longitude"],
            "target": "location",
            "format": "Point",
            "type": "GeoProperty",
        },
        "relationships": [],
        "context_urls": [
            "https://uri.etsi.org/ngsi-ld/v1/ngsi-ld-core-context.jsonld",
            "https://raw.githubusercontent.com/smart-data-models/dataModel.Device/master/context.jsonld",
        ],
        "transforms": {
            "boolean_to_ptz": {
                "type": "boolean_map",
                "true_value": "PTZ",
                "false_value": "Fixed",
            },
            "uppercase": {"type": "string_uppercase"},
            "iso_datetime": {"type": "datetime_format", "output_format": "iso8601"},
        },
        "validation": {
            "required_fields": ["id", "type", "@context"],
            "required_properties": ["location"],
            "geo_constraints": {
                "latitude_range": [-90, 90],
                "longitude_range": [-180, 180],
            },
        },
        "processing": {
            "batch_size": 100,
            "source_file": "data/test_cameras.json",
            "output_file": "data/test_output.json",
            "validate_output": True,
            "pretty_print": True,
        },
    }

    config_file = tmp_path / "test_mappings.yaml"
    with open(config_file, "w") as f:
        yaml.dump(config_data, f)

    return str(config_file)


@pytest.fixture
def mock_source_data(tmp_path):
    """Create temporary source data file."""
    source_data = [
        {
            "code": "001",
            "name": "Test Camera 1",
            "ptz": True,
            "cam_type": "tth",
            "latitude": 10.7755,
            "longitude": 106.7019,
            "url": "http://example.com/cam1",
        },
        {
            "code": "002",
            "name": "Test Camera 2",
            "ptz": False,
            "cam_type": "traffic",
            "latitude": 21.0285,
            "longitude": 105.8542,
            "url": "http://example.com/cam2",
        },
        {
            "code": "003",
            "name": "Invalid Camera",
            "ptz": True,
            "cam_type": "test",
            "latitude": "invalid",
            "longitude": "invalid",
        },
    ]

    data_dir = tmp_path / "data"
    data_dir.mkdir(exist_ok=True)

    source_file = data_dir / "test_cameras.json"
    with open(source_file, "w") as f:
        json.dump(source_data, f)

    return str(source_file)


class TestTransformationEngine:
    """Test cases for TransformationEngine class."""

    def test_engine_init(self, mock_config_file):
        """Test transformation engine initialization."""
        with open(mock_config_file, "r") as f:
            config = yaml.safe_load(f)

        engine = TransformationEngine(config["transforms"])

        assert "boolean_to_ptz" in engine._transform_functions
        assert "uppercase" in engine._transform_functions
        assert "iso_datetime" in engine._transform_functions

    def test_boolean_to_ptz_transform(self, mock_config_file):
        """Test boolean to PTZ type transformation."""
        with open(mock_config_file, "r") as f:
            config = yaml.safe_load(f)

        engine = TransformationEngine(config["transforms"])

        assert engine.apply_transform("boolean_to_ptz", True) == "PTZ"
        assert engine.apply_transform("boolean_to_ptz", False) == "Fixed"
        assert engine.apply_transform("boolean_to_ptz", "true") == "PTZ"
        assert engine.apply_transform("boolean_to_ptz", "false") == "Fixed"

    def test_uppercase_transform(self, mock_config_file):
        """Test uppercase transformation."""
        with open(mock_config_file, "r") as f:
            config = yaml.safe_load(f)

        engine = TransformationEngine(config["transforms"])

        assert engine.apply_transform("uppercase", "tth") == "TTH"
        assert engine.apply_transform("uppercase", "traffic") == "TRAFFIC"
        assert engine.apply_transform("uppercase", "Test") == "TEST"

    def test_datetime_transform(self, mock_config_file):
        """Test datetime formatting transformation."""
        with open(mock_config_file, "r") as f:
            config = yaml.safe_load(f)

        engine = TransformationEngine(config["transforms"])

        # Test ISO format passthrough
        result = engine.apply_transform("iso_datetime", "2025-11-01T12:00:00Z")
        assert "Z" in result

        # Test string passthrough for invalid dates
        result = engine.apply_transform("iso_datetime", "invalid")
        assert result == "invalid"

    def test_unknown_transform(self, mock_config_file):
        """Test unknown transformation returns identity."""
        with open(mock_config_file, "r") as f:
            config = yaml.safe_load(f)

        engine = TransformationEngine(config["transforms"])

        result = engine.apply_transform("unknown_transform", "test")
        assert result == "test"


class TestNGSILDValidator:
    """Test cases for NGSILDValidator class."""

    def test_validator_init(self, mock_config_file):
        """Test validator initialization."""
        with open(mock_config_file, "r") as f:
            config = yaml.safe_load(f)

        validator = NGSILDValidator(config["validation"])

        assert validator.config == config["validation"]
        assert validator.errors == []

    def test_valid_entity(self, mock_config_file):
        """Test validation of valid entity."""
        with open(mock_config_file, "r") as f:
            config = yaml.safe_load(f)

        validator = NGSILDValidator(config["validation"])

        entity = {
            "id": "urn:ngsi-ld:Camera:001",
            "type": "Camera",
            "@context": ["https://uri.etsi.org/ngsi-ld/v1/ngsi-ld-core-context.jsonld"],
            "location": {
                "type": "GeoProperty",
                "value": {"type": "Point", "coordinates": [106.7, 10.8]},
            },
        }

        assert validator.validate_entity(entity) is True
        assert len(validator.get_errors()) == 0

    def test_missing_required_field(self, mock_config_file):
        """Test validation fails for missing required field."""
        with open(mock_config_file, "r") as f:
            config = yaml.safe_load(f)

        validator = NGSILDValidator(config["validation"])

        entity = {
            "id": "urn:ngsi-ld:Camera:001",
            "type": "Camera",
            # Missing @context
        }

        assert validator.validate_entity(entity) is False
        assert any("Missing required field" in err for err in validator.get_errors())

    def test_missing_required_property(self, mock_config_file):
        """Test validation fails for missing required property."""
        with open(mock_config_file, "r") as f:
            config = yaml.safe_load(f)

        validator = NGSILDValidator(config["validation"])

        entity = {
            "id": "urn:ngsi-ld:Camera:001",
            "type": "Camera",
            "@context": ["https://uri.etsi.org/ngsi-ld/v1/ngsi-ld-core-context.jsonld"],
            # Missing location
        }

        assert validator.validate_entity(entity) is False
        assert any("Missing required property" in err for err in validator.get_errors())

    def test_invalid_coordinates(self, mock_config_file):
        """Test validation fails for invalid coordinates."""
        with open(mock_config_file, "r") as f:
            config = yaml.safe_load(f)

        validator = NGSILDValidator(config["validation"])

        entity = {
            "id": "urn:ngsi-ld:Camera:001",
            "type": "Camera",
            "@context": ["https://uri.etsi.org/ngsi-ld/v1/ngsi-ld-core-context.jsonld"],
            "location": {
                "type": "GeoProperty",
                "value": {
                    "type": "Point",
                    "coordinates": [200, 100],  # Invalid lat/lng
                },
            },
        }

        assert validator.validate_entity(entity) is False
        errors = validator.get_errors()
        assert any("out of range" in err for err in errors)


class TestNGSILDTransformerAgent:
    """Test cases for NGSILDTransformerAgent class."""

    def test_agent_init(self, mock_config_file):
        """Test agent initialization."""
        agent = NGSILDTransformerAgent(config_path=mock_config_file)

        assert agent.config["entity_type"] == "Camera"
        assert agent.config["uri_prefix"] == "urn:ngsi-ld:Camera:"
        assert isinstance(agent.transform_engine, TransformationEngine)
        assert isinstance(agent.validator, NGSILDValidator)

    def test_load_config_missing_file(self):
        """Test loading missing config file."""
        with pytest.raises(FileNotFoundError):
            NGSILDTransformerAgent(config_path="nonexistent.yaml")

    def test_load_config_invalid_yaml(self, tmp_path):
        """Test loading invalid YAML."""
        invalid_config = tmp_path / "invalid.yaml"
        with open(invalid_config, "w") as f:
            f.write("invalid: yaml: content: [")

        with pytest.raises(ValueError, match="Invalid YAML"):
            NGSILDTransformerAgent(config_path=str(invalid_config))

    def test_load_config_missing_section(self, tmp_path):
        """Test config missing required section."""
        config_file = tmp_path / "incomplete.yaml"
        with open(config_file, "w") as f:
            yaml.dump({"entity_type": "Test"}, f)

        with pytest.raises(ValueError, match="Missing required config section"):
            NGSILDTransformerAgent(config_path=str(config_file))

    def test_load_source_data(self, mock_config_file, mock_source_data, tmp_path):
        """Test loading source data."""
        # Update config to use correct source path
        with open(mock_config_file, "r") as f:
            config = yaml.safe_load(f)
        config["processing"]["source_file"] = mock_source_data
        with open(mock_config_file, "w") as f:
            yaml.dump(config, f)

        agent = NGSILDTransformerAgent(config_path=mock_config_file)
        entities = agent.load_source_data()

        assert len(entities) == 3
        assert entities[0]["code"] == "001"

    def test_load_source_data_missing_file(self, mock_config_file):
        """Test loading missing source file."""
        agent = NGSILDTransformerAgent(config_path=mock_config_file)

        with pytest.raises(FileNotFoundError):
            agent.load_source_data("nonexistent.json")

    def test_generate_uri(self, mock_config_file):
        """Test URI generation."""
        agent = NGSILDTransformerAgent(config_path=mock_config_file)

        entity = {"code": "001", "name": "Test"}
        uri = agent.generate_uri(entity)

        assert uri == "urn:ngsi-ld:Camera:001"

    def test_create_property(self, mock_config_file):
        """Test Property creation."""
        agent = NGSILDTransformerAgent(config_path=mock_config_file)

        prop = agent.create_property("test value")

        assert prop["type"] == "Property"
        assert prop["value"] == "test value"

    def test_create_property_with_observed_at(self, mock_config_file):
        """Test Property with observedAt."""
        agent = NGSILDTransformerAgent(config_path=mock_config_file)

        prop = agent.create_property("test", observed_at="2025-11-01T12:00:00Z")

        assert prop["type"] == "Property"
        assert prop["observedAt"] == "2025-11-01T12:00:00Z"

    def test_create_geo_property(self, mock_config_file):
        """Test GeoProperty creation."""
        agent = NGSILDTransformerAgent(config_path=mock_config_file)

        geo = agent.create_geo_property(10.7755, 106.7019)

        assert geo["type"] == "GeoProperty"
        assert geo["value"]["type"] == "Point"
        assert geo["value"]["coordinates"] == [106.7019, 10.7755]  # lng, lat

    def test_create_relationship(self, mock_config_file):
        """Test Relationship creation."""
        agent = NGSILDTransformerAgent(config_path=mock_config_file)

        rel = agent.create_relationship("urn:ngsi-ld:Camera:002")

        assert rel["type"] == "Relationship"
        assert rel["object"] == "urn:ngsi-ld:Camera:002"

    def test_apply_property_mapping_simple(self, mock_config_file):
        """Test simple property mapping."""
        agent = NGSILDTransformerAgent(config_path=mock_config_file)

        entity = {"name": "Test Camera"}
        prop = agent.apply_property_mapping(entity, "name", "cameraName")

        assert prop["type"] == "Property"
        assert prop["value"] == "Test Camera"

    def test_apply_property_mapping_with_transform(self, mock_config_file):
        """Test property mapping with transformation."""
        agent = NGSILDTransformerAgent(config_path=mock_config_file)

        entity = {"ptz": True}
        mapping_config = {
            "target": "cameraType",
            "type": "Property",
            "transform": "boolean_to_ptz",
        }

        prop = agent.apply_property_mapping(entity, "ptz", mapping_config)

        assert prop["type"] == "Property"
        assert prop["value"] == "PTZ"

    def test_apply_property_mapping_missing_field(self, mock_config_file):
        """Test property mapping with missing source field."""
        agent = NGSILDTransformerAgent(config_path=mock_config_file)

        entity = {}
        prop = agent.apply_property_mapping(entity, "missing_field", "target")

        assert prop is None

    def test_transform_entity_complete(self, mock_config_file):
        """Test complete entity transformation."""
        agent = NGSILDTransformerAgent(config_path=mock_config_file)

        entity = {
            "code": "001",
            "name": "Test Camera",
            "ptz": True,
            "cam_type": "tth",
            "latitude": 10.7755,
            "longitude": 106.7019,
        }

        ngsi_entity = agent.transform_entity(entity)

        assert ngsi_entity is not None
        assert ngsi_entity["id"] == "urn:ngsi-ld:Camera:001"
        assert ngsi_entity["type"] == "Camera"
        assert "@context" in ngsi_entity
        assert "cameraName" in ngsi_entity
        assert ngsi_entity["cameraName"]["value"] == "Test Camera"
        assert ngsi_entity["cameraType"]["value"] == "PTZ"
        assert ngsi_entity["cameraUsage"]["value"] == "TTH"
        assert "location" in ngsi_entity
        assert ngsi_entity["location"]["type"] == "GeoProperty"

    def test_transform_entity_invalid_coordinates(self, mock_config_file):
        """Test entity transformation with invalid coordinates."""
        agent = NGSILDTransformerAgent(config_path=mock_config_file)

        entity = {
            "code": "003",
            "name": "Invalid Camera",
            "ptz": False,
            "cam_type": "test",
            "latitude": "invalid",
            "longitude": "invalid",
        }

        ngsi_entity = agent.transform_entity(entity)

        assert ngsi_entity is not None
        assert "location" not in ngsi_entity  # Should skip invalid coords

    def test_process_batch(self, mock_config_file, mock_source_data, tmp_path):
        """Test batch processing."""
        # Update config
        with open(mock_config_file, "r") as f:
            config = yaml.safe_load(f)
        config["processing"]["source_file"] = mock_source_data
        with open(mock_config_file, "w") as f:
            yaml.dump(config, f)

        agent = NGSILDTransformerAgent(config_path=mock_config_file)
        entities = agent.load_source_data()

        ngsi_entities = agent.process_batch(entities)

        # Should have 2 valid entities (entity 3 has invalid coords, fails validation)
        assert len(ngsi_entities) == 2
        assert all("id" in e for e in ngsi_entities)
        assert all("type" in e for e in ngsi_entities)

    def test_save_output(self, mock_config_file, tmp_path):
        """Test saving output to file."""
        agent = NGSILDTransformerAgent(config_path=mock_config_file)

        ngsi_entities = [
            {
                "id": "urn:ngsi-ld:Camera:001",
                "type": "Camera",
                "@context": [
                    "https://uri.etsi.org/ngsi-ld/v1/ngsi-ld-core-context.jsonld"
                ],
            }
        ]

        output_file = tmp_path / "output.json"
        agent.save_output(ngsi_entities, str(output_file))

        assert output_file.exists()

        with open(output_file, "r") as f:
            saved_data = json.load(f)

        assert len(saved_data) == 1
        assert saved_data[0]["id"] == "urn:ngsi-ld:Camera:001"


class TestIntegration:
    """Integration tests with realistic data."""

    def test_full_transformation_workflow(
        self, mock_config_file, mock_source_data, tmp_path
    ):
        """Test complete transformation workflow."""
        # Update config
        with open(mock_config_file, "r") as f:
            config = yaml.safe_load(f)
        config["processing"]["source_file"] = mock_source_data
        output_file = tmp_path / "output.json"
        config["processing"]["output_file"] = str(output_file)
        with open(mock_config_file, "w") as f:
            yaml.dump(config, f)

        agent = NGSILDTransformerAgent(config_path=mock_config_file)
        agent.run()

        # Check output file
        assert output_file.exists()

        with open(output_file, "r") as f:
            ngsi_entities = json.load(f)

        assert len(ngsi_entities) == 2  # 2 valid entities

        # Verify structure of first entity
        entity = ngsi_entities[0]
        assert entity["id"].startswith("urn:ngsi-ld:Camera:")
        assert entity["type"] == "Camera"
        assert "@context" in entity
        assert len(entity["@context"]) == 2

        # Verify properties
        assert "cameraName" in entity
        assert entity["cameraName"]["type"] == "Property"

        # Verify geo property
        assert "location" in entity
        assert entity["location"]["type"] == "GeoProperty"
        assert entity["location"]["value"]["type"] == "Point"
        assert len(entity["location"]["value"]["coordinates"]) == 2


class TestPerformance:
    """Performance tests."""

    def test_large_dataset_performance(self, mock_config_file, tmp_path):
        """Test performance with large dataset (722 cameras simulation)."""
        # Create large dataset
        large_dataset = [
            {
                "code": f"{i:03d}",
                "name": f"Camera {i}",
                "ptz": i % 2 == 0,
                "cam_type": "tth",
                "latitude": 10.7 + (i * 0.001),
                "longitude": 106.7 + (i * 0.001),
            }
            for i in range(722)
        ]

        source_file = tmp_path / "large_cameras.json"
        with open(source_file, "w") as f:
            json.dump(large_dataset, f)

        # Update config
        with open(mock_config_file, "r") as f:
            config = yaml.safe_load(f)
        config["processing"]["source_file"] = str(source_file)
        output_file = tmp_path / "large_output.json"
        config["processing"]["output_file"] = str(output_file)
        with open(mock_config_file, "w") as f:
            yaml.dump(config, f)

        agent = NGSILDTransformerAgent(config_path=mock_config_file)

        start_time = time.time()
        agent.run()
        elapsed = time.time() - start_time

        # Should complete in < 10 seconds
        assert elapsed < 10.0

        # Verify output
        with open(output_file, "r") as f:
            ngsi_entities = json.load(f)

        assert len(ngsi_entities) == 722
        assert agent.stats["successful_transforms"] == 722
        assert agent.stats["failed_transforms"] == 0


class TestValidation:
    """Validation and schema compliance tests."""

    def test_ngsi_ld_structure_compliance(
        self, mock_config_file, mock_source_data, tmp_path
    ):
        """Test NGSI-LD structure compliance."""
        # Update config
        with open(mock_config_file, "r") as f:
            config = yaml.safe_load(f)
        config["processing"]["source_file"] = mock_source_data
        with open(mock_config_file, "w") as f:
            yaml.dump(config, f)

        agent = NGSILDTransformerAgent(config_path=mock_config_file)
        ngsi_entities = agent.transform_all()

        for entity in ngsi_entities:
            # Check required NGSI-LD fields
            assert "id" in entity
            assert "type" in entity
            assert "@context" in entity

            # Check id format
            assert entity["id"].startswith("urn:ngsi-ld:")

            # Check context is array
            assert isinstance(entity["@context"], list)

            # Check properties have correct structure
            for key, value in entity.items():
                if key in ["id", "type", "@context"]:
                    continue

                # Each property should have 'type' field
                assert "type" in value
                assert value["type"] in ["Property", "GeoProperty", "Relationship"]

                # Properties and GeoProperties should have 'value'
                if value["type"] in ["Property", "GeoProperty"]:
                    assert "value" in value

                # Relationships should have 'object'
                if value["type"] == "Relationship":
                    assert "object" in value

    def test_geojson_point_format(self, mock_config_file, mock_source_data, tmp_path):
        """Test GeoJSON Point format compliance."""
        # Update config
        with open(mock_config_file, "r") as f:
            config = yaml.safe_load(f)
        config["processing"]["source_file"] = mock_source_data
        with open(mock_config_file, "w") as f:
            yaml.dump(config, f)

        agent = NGSILDTransformerAgent(config_path=mock_config_file)
        ngsi_entities = agent.transform_all()

        for entity in ngsi_entities:
            if "location" in entity:
                loc = entity["location"]

                # Check GeoProperty structure
                assert loc["type"] == "GeoProperty"
                assert "value" in loc

                # Check GeoJSON Point format
                geo_value = loc["value"]
                assert geo_value["type"] == "Point"
                assert "coordinates" in geo_value
                assert isinstance(geo_value["coordinates"], list)
                assert len(geo_value["coordinates"]) == 2

                # Check coordinate order: [longitude, latitude]
                lng, lat = geo_value["coordinates"]
                assert -180 <= lng <= 180
                assert -90 <= lat <= 90
