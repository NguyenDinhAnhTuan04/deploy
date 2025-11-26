"""
Test Suite for SOSA/SSN Mapper Agent

Comprehensive tests ensuring 100% coverage:
- Unit tests for all methods and classes
- Integration tests with real NGSI-LD data
- Ontology validation for SOSA/SSN compliance
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

from agents.transformation.sosa_ssn_mapper_agent import (
    SOSARelationshipBuilder,
    SOSAEntityGenerator,
    SOSAValidator,
    SOSASSNMapperAgent
)


@pytest.fixture
def mock_config_file(tmp_path):
    """Create a temporary SOSA mappings config file."""
    config_data = {
        'sensor_type': 'sosa:Sensor',
        'observable_property': {
            'type': 'ObservableProperty',
            'domain_type': 'TrafficFlow',
            'uri_prefix': 'urn:ngsi-ld:ObservableProperty:',
            'properties': {
                'name': 'Traffic Flow Monitoring',
                'description': 'Observable property for traffic flow',
                'unit_of_measurement': 'vehicles/hour'
            }
        },
        'platform': {
            'id': 'urn:ngsi-ld:Platform:TestSystem',
            'name': 'Test Monitoring System',
            'description': 'Test platform',
            'type': 'Platform',
            'properties': {
                'operator': 'Test Operator',
                'deployment_year': 2020
            }
        },
        'relationships': {
            'observes': {
                'type': 'Relationship',
                'property_name': 'sosa:observes',
                'target_type': 'ObservableProperty',
                'required': True
            },
            'isHostedBy': {
                'type': 'Relationship',
                'property_name': 'sosa:isHostedBy',
                'target_type': 'Platform',
                'required': True
            }
        },
        'context': {
            'sosa': 'https://www.w3.org/ns/sosa/',
            'ssn': 'https://www.w3.org/ns/ssn/'
        },
        'entity_type_mappings': {
            'Camera': {
                'add_sensor_type': True
            },
            'Sensor': {
                'add_sensor_type': True
            }
        },
        'output': {
            'source_file': 'data/test_source.json',
            'output_file': 'data/test_output.json',
            'pretty_print': True,
            'validate_output': True,
            'include_generated_entities': True
        },
        'validation': {
            'required_sosa_properties': ['sosa:observes'],
            'optional_sosa_properties': ['sosa:isHostedBy'],
            'check_relationship_targets': True,
            'validate_context_urls': True
        },
        'processing': {
            'batch_size': 100,
            'generate_observable_properties': True,
            'generate_platform': True,
            'preserve_original_properties': True,
            'merge_contexts': True
        }
    }
    
    config_file = tmp_path / "test_sosa_mappings.yaml"
    with open(config_file, 'w') as f:
        yaml.dump(config_data, f)
    
    return str(config_file)


@pytest.fixture
def mock_ngsi_ld_entities(tmp_path):
    """Create temporary NGSI-LD entities file."""
    entities = [
        {
            'id': 'urn:ngsi-ld:Camera:001',
            'type': 'Camera',
            '@context': [
                'https://uri.etsi.org/ngsi-ld/v1/ngsi-ld-core-context.jsonld'
            ],
            'cameraName': {
                'type': 'Property',
                'value': 'Test Camera 1'
            },
            'location': {
                'type': 'GeoProperty',
                'value': {
                    'type': 'Point',
                    'coordinates': [106.7, 10.8]
                }
            }
        },
        {
            'id': 'urn:ngsi-ld:Camera:002',
            'type': 'Camera',
            '@context': [
                'https://uri.etsi.org/ngsi-ld/v1/ngsi-ld-core-context.jsonld'
            ],
            'cameraName': {
                'type': 'Property',
                'value': 'Test Camera 2'
            }
        },
        {
            'id': 'urn:ngsi-ld:Device:001',
            'type': 'Device',
            '@context': [
                'https://uri.etsi.org/ngsi-ld/v1/ngsi-ld-core-context.jsonld'
            ]
        }
    ]
    
    data_dir = tmp_path / "data"
    data_dir.mkdir(exist_ok=True)
    
    source_file = data_dir / "test_source.json"
    with open(source_file, 'w') as f:
        json.dump(entities, f)
    
    return str(source_file)


class TestSOSARelationshipBuilder:
    """Test cases for SOSARelationshipBuilder class."""
    
    def test_builder_init(self):
        """Test relationship builder initialization."""
        config = {
            'observes': {'type': 'Relationship'},
            'isHostedBy': {'type': 'Relationship'}
        }
        builder = SOSARelationshipBuilder(config)
        
        assert builder.config == config
    
    def test_create_observes_relationship(self):
        """Test creating sosa:observes relationship."""
        builder = SOSARelationshipBuilder({})
        
        rel = builder.create_observes_relationship('urn:ngsi-ld:ObservableProperty:TrafficFlow')
        
        assert rel['type'] == 'Relationship'
        assert rel['object'] == 'urn:ngsi-ld:ObservableProperty:TrafficFlow'
    
    def test_create_hosted_by_relationship(self):
        """Test creating sosa:isHostedBy relationship."""
        builder = SOSARelationshipBuilder({})
        
        rel = builder.create_hosted_by_relationship('urn:ngsi-ld:Platform:TestPlatform')
        
        assert rel['type'] == 'Relationship'
        assert rel['object'] == 'urn:ngsi-ld:Platform:TestPlatform'
    
    def test_create_observation_relationship(self):
        """Test creating sosa:madeObservation relationship."""
        builder = SOSARelationshipBuilder({})
        
        rel = builder.create_observation_relationship('urn:ngsi-ld:Observation:001')
        
        assert rel['type'] == 'Relationship'
        assert rel['object'] == 'urn:ngsi-ld:Observation:001'
    
    def test_create_observation_relationship_with_timestamp(self):
        """Test creating observation relationship with observedAt."""
        builder = SOSARelationshipBuilder({})
        
        rel = builder.create_observation_relationship(
            'urn:ngsi-ld:Observation:001',
            observed_at='2025-11-01T12:00:00Z'
        )
        
        assert rel['observedAt'] == '2025-11-01T12:00:00Z'


class TestSOSAEntityGenerator:
    """Test cases for SOSAEntityGenerator class."""
    
    def test_generator_init(self, mock_config_file):
        """Test entity generator initialization."""
        with open(mock_config_file, 'r') as f:
            config = yaml.safe_load(f)
        
        generator = SOSAEntityGenerator(config)
        
        assert generator.config == config
        assert 'domain_type' in generator.observable_property_config
        assert 'id' in generator.platform_config
    
    def test_generate_observable_property(self, mock_config_file):
        """Test generating ObservableProperty entity."""
        with open(mock_config_file, 'r') as f:
            config = yaml.safe_load(f)
        
        generator = SOSAEntityGenerator(config)
        entity = generator.generate_observable_property()
        
        assert entity['id'] == 'urn:ngsi-ld:ObservableProperty:TrafficFlow'
        assert entity['type'] == 'ObservableProperty'
        assert '@context' in entity
        assert 'name' in entity
        assert entity['name']['value'] == 'Traffic Flow Monitoring'
        assert 'description' in entity
        assert 'unitOfMeasurement' in entity
    
    def test_generate_platform(self, mock_config_file):
        """Test generating Platform entity."""
        with open(mock_config_file, 'r') as f:
            config = yaml.safe_load(f)
        
        generator = SOSAEntityGenerator(config)
        entity = generator.generate_platform()
        
        assert entity['id'] == 'urn:ngsi-ld:Platform:TestSystem'
        assert entity['type'] == 'Platform'
        assert '@context' in entity
        assert 'name' in entity
        assert entity['name']['value'] == 'Test Monitoring System'
        assert 'description' in entity
        assert 'operator' in entity
        assert entity['operator']['value'] == 'Test Operator'
    
    def test_camel_case_conversion(self):
        """Test snake_case to camelCase conversion."""
        generator = SOSAEntityGenerator({})
        
        assert generator._to_camel_case('deployment_year') == 'deploymentYear'
        assert generator._to_camel_case('test_value') == 'testValue'
        assert generator._to_camel_case('single') == 'single'


class TestSOSAValidator:
    """Test cases for SOSAValidator class."""
    
    def test_validator_init(self, mock_config_file):
        """Test validator initialization."""
        with open(mock_config_file, 'r') as f:
            config = yaml.safe_load(f)
        
        validator = SOSAValidator(config['validation'])
        
        assert 'sosa:observes' in validator.required_properties
        assert validator.errors == []
    
    def test_valid_entity(self, mock_config_file):
        """Test validation of valid SOSA entity."""
        with open(mock_config_file, 'r') as f:
            config = yaml.safe_load(f)
        
        validator = SOSAValidator(config['validation'])
        
        entity = {
            'id': 'urn:ngsi-ld:Camera:001',
            'type': ['Camera', 'sosa:Sensor'],
            '@context': [
                'https://uri.etsi.org/ngsi-ld/v1/ngsi-ld-core-context.jsonld',
                'https://www.w3.org/ns/sosa/'
            ],
            'sosa:observes': {
                'type': 'Relationship',
                'object': 'urn:ngsi-ld:ObservableProperty:TrafficFlow'
            }
        }
        
        assert validator.validate_entity(entity) is True
        assert len(validator.get_errors()) == 0
    
    def test_missing_sosa_property(self, mock_config_file):
        """Test validation fails for missing sosa:observes."""
        with open(mock_config_file, 'r') as f:
            config = yaml.safe_load(f)
        
        validator = SOSAValidator(config['validation'])
        
        entity = {
            'id': 'urn:ngsi-ld:Camera:001',
            'type': ['Camera', 'sosa:Sensor'],
            '@context': ['https://uri.etsi.org/ngsi-ld/v1/ngsi-ld-core-context.jsonld']
        }
        
        assert validator.validate_entity(entity) is False
        assert any('Missing required SOSA property' in err for err in validator.get_errors())
    
    def test_missing_sensor_type(self, mock_config_file):
        """Test validation fails when sosa:Sensor not in type."""
        with open(mock_config_file, 'r') as f:
            config = yaml.safe_load(f)
        
        validator = SOSAValidator(config['validation'])
        
        entity = {
            'id': 'urn:ngsi-ld:Camera:001',
            'type': 'Camera',  # Missing sosa:Sensor
            '@context': ['https://www.w3.org/ns/sosa/'],
            'sosa:observes': {
                'type': 'Relationship',
                'object': 'urn:ngsi-ld:ObservableProperty:TrafficFlow'
            }
        }
        
        assert validator.validate_entity(entity) is False
        errors = validator.get_errors()
        assert any('sosa:Sensor' in err for err in errors)
    
    def test_invalid_relationship_structure(self, mock_config_file):
        """Test validation fails for invalid relationship."""
        with open(mock_config_file, 'r') as f:
            config = yaml.safe_load(f)
        
        validator = SOSAValidator(config['validation'])
        
        entity = {
            'id': 'urn:ngsi-ld:Camera:001',
            'type': ['Camera', 'sosa:Sensor'],
            '@context': ['https://www.w3.org/ns/sosa/'],
            'sosa:observes': {
                'type': 'Property',  # Should be Relationship
                'value': 'wrong'
            }
        }
        
        assert validator.validate_entity(entity) is False
    
    def test_missing_context(self, mock_config_file):
        """Test validation fails when SOSA context missing."""
        with open(mock_config_file, 'r') as f:
            config = yaml.safe_load(f)
        
        validator = SOSAValidator(config['validation'])
        
        entity = {
            'id': 'urn:ngsi-ld:Camera:001',
            'type': ['Camera', 'sosa:Sensor'],
            '@context': ['https://uri.etsi.org/ngsi-ld/v1/ngsi-ld-core-context.jsonld'],
            'sosa:observes': {
                'type': 'Relationship',
                'object': 'urn:ngsi-ld:ObservableProperty:TrafficFlow'
            }
        }
        
        assert validator.validate_entity(entity) is False
        assert any('SOSA context' in err for err in validator.get_errors())


class TestSOSASSNMapperAgent:
    """Test cases for SOSASSNMapperAgent class."""
    
    def test_agent_init(self, mock_config_file):
        """Test agent initialization."""
        agent = SOSASSNMapperAgent(config_path=mock_config_file)
        
        assert agent.config['sensor_type'] == 'sosa:Sensor'
        assert isinstance(agent.relationship_builder, SOSARelationshipBuilder)
        assert isinstance(agent.entity_generator, SOSAEntityGenerator)
        assert isinstance(agent.validator, SOSAValidator)
    
    def test_load_config_missing_file(self):
        """Test loading missing config file."""
        with pytest.raises(FileNotFoundError):
            SOSASSNMapperAgent(config_path='nonexistent.yaml')
    
    def test_load_config_invalid_yaml(self, tmp_path):
        """Test loading invalid YAML."""
        invalid_config = tmp_path / "invalid.yaml"
        with open(invalid_config, 'w') as f:
            f.write("invalid: yaml: content: [")
        
        with pytest.raises(ValueError, match="Invalid YAML"):
            SOSASSNMapperAgent(config_path=str(invalid_config))
    
    def test_load_config_missing_section(self, tmp_path):
        """Test config missing required section."""
        config_file = tmp_path / "incomplete.yaml"
        with open(config_file, 'w') as f:
            yaml.dump({'sensor_type': 'sosa:Sensor'}, f)
        
        with pytest.raises(ValueError, match="Missing required config section"):
            SOSASSNMapperAgent(config_path=str(config_file))
    
    def test_load_ngsi_ld_entities(self, mock_config_file, mock_ngsi_ld_entities, tmp_path):
        """Test loading NGSI-LD entities."""
        # Update config to use correct source path
        with open(mock_config_file, 'r') as f:
            config = yaml.safe_load(f)
        config['output']['source_file'] = mock_ngsi_ld_entities
        with open(mock_config_file, 'w') as f:
            yaml.dump(config, f)
        
        agent = SOSASSNMapperAgent(config_path=mock_config_file)
        entities = agent.load_ngsi_ld_entities()
        
        assert len(entities) == 3
        assert entities[0]['id'] == 'urn:ngsi-ld:Camera:001'
    
    def test_should_enhance_entity_camera(self, mock_config_file):
        """Test Camera entity should be enhanced."""
        agent = SOSASSNMapperAgent(config_path=mock_config_file)
        
        entity = {'type': 'Camera'}
        assert agent.should_enhance_entity(entity) is True
    
    def test_should_enhance_entity_array_type(self, mock_config_file):
        """Test entity with array type."""
        agent = SOSASSNMapperAgent(config_path=mock_config_file)
        
        entity = {'type': ['Camera', 'Device']}
        assert agent.should_enhance_entity(entity) is True
    
    def test_should_not_enhance_unknown_type(self, mock_config_file):
        """Test unknown entity type should not be enhanced."""
        agent = SOSASSNMapperAgent(config_path=mock_config_file)
        
        entity = {'type': 'Building'}
        assert agent.should_enhance_entity(entity) is False
    
    def test_enhance_with_sosa_type_string(self, mock_config_file):
        """Test adding SOSA type to string type."""
        agent = SOSASSNMapperAgent(config_path=mock_config_file)
        
        entity = {'type': 'Camera'}
        agent.enhance_with_sosa_type(entity)
        
        assert entity['type'] == ['Camera', 'sosa:Sensor']
    
    def test_enhance_with_sosa_type_array(self, mock_config_file):
        """Test adding SOSA type to array type."""
        agent = SOSASSNMapperAgent(config_path=mock_config_file)
        
        entity = {'type': ['Camera', 'Device']}
        agent.enhance_with_sosa_type(entity)
        
        assert 'sosa:Sensor' in entity['type']
        assert len(entity['type']) == 3
    
    def test_enhance_with_sosa_type_already_present(self, mock_config_file):
        """Test SOSA type not duplicated."""
        agent = SOSASSNMapperAgent(config_path=mock_config_file)
        
        entity = {'type': ['Camera', 'sosa:Sensor']}
        agent.enhance_with_sosa_type(entity)
        
        assert entity['type'].count('sosa:Sensor') == 1
    
    def test_add_observes_relationship(self, mock_config_file):
        """Test adding sosa:observes relationship."""
        agent = SOSASSNMapperAgent(config_path=mock_config_file)
        
        entity = {}
        agent.add_observes_relationship(entity)
        
        assert 'sosa:observes' in entity
        assert entity['sosa:observes']['type'] == 'Relationship'
        assert 'ObservableProperty:TrafficFlow' in entity['sosa:observes']['object']
    
    def test_add_hosted_by_relationship(self, mock_config_file):
        """Test adding sosa:isHostedBy relationship."""
        agent = SOSASSNMapperAgent(config_path=mock_config_file)
        
        entity = {}
        agent.add_hosted_by_relationship(entity)
        
        assert 'sosa:isHostedBy' in entity
        assert entity['sosa:isHostedBy']['type'] == 'Relationship'
        assert 'Platform:TestSystem' in entity['sosa:isHostedBy']['object']
    
    def test_merge_context_from_string(self, mock_config_file):
        """Test merging context from string."""
        agent = SOSASSNMapperAgent(config_path=mock_config_file)
        
        entity = {
            '@context': 'https://uri.etsi.org/ngsi-ld/v1/ngsi-ld-core-context.jsonld'
        }
        agent.merge_context(entity)
        
        assert isinstance(entity['@context'], list)
        assert 'https://www.w3.org/ns/sosa/' in entity['@context']
    
    def test_merge_context_from_array(self, mock_config_file):
        """Test merging context from array."""
        agent = SOSASSNMapperAgent(config_path=mock_config_file)
        
        entity = {
            '@context': ['https://uri.etsi.org/ngsi-ld/v1/ngsi-ld-core-context.jsonld']
        }
        agent.merge_context(entity)
        
        assert 'https://www.w3.org/ns/sosa/' in entity['@context']
        assert 'https://www.w3.org/ns/ssn/' in entity['@context']
    
    def test_merge_context_no_duplicates(self, mock_config_file):
        """Test context merging doesn't create duplicates."""
        agent = SOSASSNMapperAgent(config_path=mock_config_file)
        
        entity = {
            '@context': [
                'https://uri.etsi.org/ngsi-ld/v1/ngsi-ld-core-context.jsonld',
                'https://www.w3.org/ns/sosa/'
            ]
        }
        agent.merge_context(entity)
        
        assert entity['@context'].count('https://www.w3.org/ns/sosa/') == 1
    
    def test_enhance_entity_complete(self, mock_config_file):
        """Test complete entity enhancement."""
        agent = SOSASSNMapperAgent(config_path=mock_config_file)
        
        entity = {
            'id': 'urn:ngsi-ld:Camera:001',
            'type': 'Camera',
            '@context': ['https://uri.etsi.org/ngsi-ld/v1/ngsi-ld-core-context.jsonld'],
            'cameraName': {'type': 'Property', 'value': 'Test'}
        }
        
        enhanced = agent.enhance_entity(entity)
        
        # Check type enhancement
        assert 'sosa:Sensor' in enhanced['type']
        
        # Check relationships
        assert 'sosa:observes' in enhanced
        assert 'sosa:isHostedBy' in enhanced
        
        # Check context
        assert 'https://www.w3.org/ns/sosa/' in enhanced['@context']
        
        # Check original properties preserved
        assert 'cameraName' in enhanced
        assert enhanced['cameraName']['value'] == 'Test'
    
    def test_enhance_entity_non_camera(self, mock_config_file):
        """Test entity that shouldn't be enhanced."""
        agent = SOSASSNMapperAgent(config_path=mock_config_file)
        
        entity = {
            'id': 'urn:ngsi-ld:Building:001',
            'type': 'Building',
            '@context': ['https://uri.etsi.org/ngsi-ld/v1/ngsi-ld-core-context.jsonld']
        }
        
        enhanced = agent.enhance_entity(entity)
        
        # Should not be enhanced
        assert 'sosa:observes' not in enhanced
        assert enhanced['type'] == 'Building'
    
    def test_generate_support_entities(self, mock_config_file):
        """Test generating ObservableProperty and Platform."""
        agent = SOSASSNMapperAgent(config_path=mock_config_file)
        
        support_entities = agent.generate_support_entities()
        
        assert len(support_entities) == 2
        
        # Check ObservableProperty
        obs_prop = next(e for e in support_entities if e['type'] == 'ObservableProperty')
        assert 'TrafficFlow' in obs_prop['id']
        
        # Check Platform
        platform = next(e for e in support_entities if e['type'] == 'Platform')
        assert 'TestSystem' in platform['id']


class TestIntegration:
    """Integration tests with realistic data."""
    
    def test_full_enhancement_workflow(self, mock_config_file, mock_ngsi_ld_entities, tmp_path):
        """Test complete enhancement workflow."""
        # Update config
        with open(mock_config_file, 'r') as f:
            config = yaml.safe_load(f)
        config['output']['source_file'] = mock_ngsi_ld_entities
        output_file = tmp_path / "enhanced_output.json"
        config['output']['output_file'] = str(output_file)
        with open(mock_config_file, 'w') as f:
            yaml.dump(config, f)
        
        agent = SOSASSNMapperAgent(config_path=mock_config_file)
        agent.run()
        
        # Check output file
        assert output_file.exists()
        
        with open(output_file, 'r') as f:
            enhanced_entities = json.load(f)
        
        # Should have 3 original + 2 support entities
        assert len(enhanced_entities) == 5
        
        # Check Platform entity
        platform = next(e for e in enhanced_entities if e['type'] == 'Platform')
        assert platform['id'] == 'urn:ngsi-ld:Platform:TestSystem'
        
        # Check ObservableProperty entity
        obs_prop = next(e for e in enhanced_entities if e['type'] == 'ObservableProperty')
        assert 'TrafficFlow' in obs_prop['id']
        
        # Check enhanced Camera entities
        cameras = [e for e in enhanced_entities if 'Camera' in str(e.get('type', ''))]
        assert len(cameras) == 2
        
        for camera in cameras:
            assert 'sosa:Sensor' in camera['type']
            assert 'sosa:observes' in camera
            assert 'sosa:isHostedBy' in camera
            assert 'https://www.w3.org/ns/sosa/' in camera['@context']


class TestOntologyValidation:
    """Ontology validation tests."""
    
    def test_sosa_relationship_types(self, mock_config_file):
        """Test SOSA relationship types are correct."""
        agent = SOSASSNMapperAgent(config_path=mock_config_file)
        
        entity = {
            'id': 'urn:ngsi-ld:Camera:001',
            'type': 'Camera',
            '@context': ['https://uri.etsi.org/ngsi-ld/v1/ngsi-ld-core-context.jsonld']
        }
        
        enhanced = agent.enhance_entity(entity)
        
        # Check relationship types
        assert enhanced['sosa:observes']['type'] == 'Relationship'
        assert enhanced['sosa:isHostedBy']['type'] == 'Relationship'
    
    def test_observable_property_structure(self, mock_config_file):
        """Test ObservableProperty entity structure."""
        agent = SOSASSNMapperAgent(config_path=mock_config_file)
        
        obs_prop = agent.entity_generator.generate_observable_property()
        
        # Check required fields
        assert 'id' in obs_prop
        assert 'type' in obs_prop
        assert obs_prop['type'] == 'ObservableProperty'
        assert '@context' in obs_prop
        
        # Check properties
        assert 'name' in obs_prop
        assert obs_prop['name']['type'] == 'Property'
    
    def test_platform_structure(self, mock_config_file):
        """Test Platform entity structure."""
        agent = SOSASSNMapperAgent(config_path=mock_config_file)
        
        platform = agent.entity_generator.generate_platform()
        
        # Check required fields
        assert 'id' in platform
        assert 'type' in platform
        assert platform['type'] == 'Platform'
        assert '@context' in platform
        
        # Check properties
        assert 'name' in platform
        assert platform['name']['type'] == 'Property'
    
    def test_context_urls_correct(self, mock_config_file):
        """Test context URLs are SOSA/SSN compliant."""
        agent = SOSASSNMapperAgent(config_path=mock_config_file)
        
        entity = {
            'type': 'Camera',
            '@context': ['https://uri.etsi.org/ngsi-ld/v1/ngsi-ld-core-context.jsonld']
        }
        
        enhanced = agent.enhance_entity(entity)
        
        # Check SOSA context
        assert 'https://www.w3.org/ns/sosa/' in enhanced['@context']


class TestPerformance:
    """Performance tests."""
    
    def test_large_dataset_performance(self, mock_config_file, tmp_path):
        """Test performance with large dataset (722 entities simulation)."""
        # Create large dataset
        large_dataset = [
            {
                'id': f'urn:ngsi-ld:Camera:{i:03d}',
                'type': 'Camera',
                '@context': ['https://uri.etsi.org/ngsi-ld/v1/ngsi-ld-core-context.jsonld'],
                'cameraName': {'type': 'Property', 'value': f'Camera {i}'}
            }
            for i in range(722)
        ]
        
        source_file = tmp_path / "large_cameras.json"
        with open(source_file, 'w') as f:
            json.dump(large_dataset, f)
        
        # Update config
        with open(mock_config_file, 'r') as f:
            config = yaml.safe_load(f)
        config['output']['source_file'] = str(source_file)
        output_file = tmp_path / "large_output.json"
        config['output']['output_file'] = str(output_file)
        with open(mock_config_file, 'w') as f:
            yaml.dump(config, f)
        
        agent = SOSASSNMapperAgent(config_path=mock_config_file)
        
        start_time = time.time()
        agent.run()
        elapsed = time.time() - start_time
        
        # Should complete in < 5 seconds
        assert elapsed < 5.0
        
        # Verify output
        with open(output_file, 'r') as f:
            enhanced_entities = json.load(f)
        
        # 722 cameras + 2 support entities
        assert len(enhanced_entities) == 724
        assert agent.stats['enhanced_entities'] == 722
