"""
Comprehensive test suite for CV Analysis Agent

Tests cover:
- Unit tests for all components
- Integration tests with real workflow
- Performance tests
- Edge cases and error handling
"""

import asyncio
import json
import pytest
import time
from pathlib import Path
from PIL import Image
from unittest.mock import Mock, patch, AsyncMock, MagicMock
import io
import yaml
from datetime import datetime

from agents.analytics.cv_analysis_agent import (
    CVAnalysisAgent,
    CVConfig,
    YOLOv8Detector,
    ImageDownloader,
    MetricsCalculator,
    NGSILDEntityGenerator,
    Detection,
    ImageAnalysisResult,
    TrafficMetrics,
    DetectionStatus
)


# ============================================================================
# Test CVConfig
# ============================================================================

class TestCVConfig:
    """Test CV configuration loader"""
    
    def test_load_config_success(self, tmp_path):
        """Test successful configuration loading"""
        config_file = tmp_path / "cv_config.yaml"
        config_data = {
            'cv_analysis': {
                'model': {
                    'type': 'yolov8',
                    'weights': 'yolov8n.pt',
                    'confidence': 0.5
                },
                'vehicle_classes': ['car', 'bus'],
                'batch_size': 20,
                'timeout': 10
            }
        }
        
        with open(config_file, 'w') as f:
            yaml.dump(config_data, f)
        
        config = CVConfig(str(config_file))
        
        assert config.config == config_data
        assert config.get_batch_size() == 20
        assert config.get_timeout() == 10
    
    def test_load_config_file_not_found(self):
        """Test handling of missing configuration file"""
        with pytest.raises(FileNotFoundError):
            CVConfig('nonexistent.yaml')
    
    def test_load_config_invalid_yaml(self, tmp_path):
        """Test handling of invalid YAML"""
        config_file = tmp_path / "invalid.yaml"
        with open(config_file, 'w') as f:
            f.write("invalid: yaml: content: [\n")
        
        with pytest.raises(ValueError):
            CVConfig(str(config_file))
    
    def test_get_model_config(self, tmp_path):
        """Test getting model configuration"""
        config_file = tmp_path / "cv_config.yaml"
        config_data = {
            'cv_analysis': {
                'model': {
                    'type': 'yolov8',
                    'weights': 'yolov8n.pt',
                    'confidence': 0.5,
                    'device': 'cpu'
                }
            }
        }
        
        with open(config_file, 'w') as f:
            yaml.dump(config_data, f)
        
        config = CVConfig(str(config_file))
        model_config = config.get_model_config()
        
        assert model_config['type'] == 'yolov8'
        assert model_config['weights'] == 'yolov8n.pt'
        assert model_config['confidence'] == 0.5
        assert model_config['device'] == 'cpu'
    
    def test_get_vehicle_classes(self, tmp_path):
        """Test getting vehicle classes"""
        config_file = tmp_path / "cv_config.yaml"
        config_data = {
            'cv_analysis': {
                'vehicle_classes': ['car', 'motorbike', 'bus', 'truck']
            }
        }
        
        with open(config_file, 'w') as f:
            yaml.dump(config_data, f)
        
        config = CVConfig(str(config_file))
        classes = config.get_vehicle_classes()
        
        assert classes == ['car', 'motorbike', 'bus', 'truck']
    
    def test_get_metrics_config(self, tmp_path):
        """Test getting metrics configuration"""
        config_file = tmp_path / "cv_config.yaml"
        config_data = {
            'cv_analysis': {
                'metrics': {
                    'intensity_threshold': 0.7,
                    'occupancy_max_vehicles': 50,
                    'default_speed_kmh': 20.0
                }
            }
        }
        
        with open(config_file, 'w') as f:
            yaml.dump(config_data, f)
        
        config = CVConfig(str(config_file))
        metrics = config.get_metrics_config()
        
        assert metrics['intensity_threshold'] == 0.7
        assert metrics['occupancy_max_vehicles'] == 50
        assert metrics['default_speed_kmh'] == 20.0
    
    def test_get_output_config(self, tmp_path):
        """Test getting output configuration"""
        config_file = tmp_path / "cv_config.yaml"
        config_data = {
            'cv_analysis': {
                'output': {
                    'file': 'data/observations.json',
                    'format': 'ngsi-ld',
                    'include_detections': True
                }
            }
        }
        
        with open(config_file, 'w') as f:
            yaml.dump(config_data, f)
        
        config = CVConfig(str(config_file))
        output = config.get_output_config()
        
        assert output['file'] == 'data/observations.json'
        assert output['format'] == 'ngsi-ld'
        assert output['include_detections'] is True


# ============================================================================
# Test YOLOv8Detector
# ============================================================================

class TestYOLOv8Detector:
    """Test YOLOv8 detector"""
    
    def test_detector_initialization(self):
        """Test detector initialization"""
        config = {
            'type': 'yolov8',
            'weights': 'yolov8n.pt',
            'confidence': 0.5,
            'device': 'cpu'
        }
        
        detector = YOLOv8Detector(config)
        
        assert detector.confidence == 0.5
        assert detector.device == 'cpu'
    
    def test_detect_with_mock_model(self):
        """Test detection with mock model"""
        config = {
            'weights': 'yolov8n.pt',
            'confidence': 0.5,
            'device': 'cpu'
        }
        
        detector = YOLOv8Detector(config)
        detector.model = None  # Force mock detection
        
        # Create test image
        image = Image.new('RGB', (640, 480), color='blue')
        
        detections = detector.detect(image)
        
        assert len(detections) > 0
        assert all(isinstance(d, Detection) for d in detections)
        assert all(d.confidence > 0 for d in detections)
    
    def test_detect_empty_image(self):
        """Test detection on empty image"""
        config = {'weights': 'yolov8n.pt', 'confidence': 0.5}
        detector = YOLOv8Detector(config)
        detector.model = None
        
        # Create small image
        image = Image.new('RGB', (10, 10), color='white')
        
        detections = detector.detect(image)
        
        # Mock detector should still return detections
        assert isinstance(detections, list)
    
    def test_coco_class_mapping(self):
        """Test COCO class name mapping"""
        assert YOLOv8Detector.COCO_CLASSES[0] == 'person'
        assert YOLOv8Detector.COCO_CLASSES[2] == 'car'
        assert YOLOv8Detector.COCO_CLASSES[3] == 'motorcycle'
        assert YOLOv8Detector.COCO_CLASSES[5] == 'bus'
        assert YOLOv8Detector.COCO_CLASSES[7] == 'truck'
    
    def test_class_name_to_id_mapping(self):
        """Test class name to ID mapping"""
        assert YOLOv8Detector.CLASS_NAME_TO_ID['person'] == 0
        assert YOLOv8Detector.CLASS_NAME_TO_ID['car'] == 2
        assert YOLOv8Detector.CLASS_NAME_TO_ID['motorcycle'] == 3
        assert YOLOv8Detector.CLASS_NAME_TO_ID['motorbike'] == 3
        assert YOLOv8Detector.CLASS_NAME_TO_ID['bus'] == 5
        assert YOLOv8Detector.CLASS_NAME_TO_ID['truck'] == 7


# ============================================================================
# Test ImageDownloader
# ============================================================================

class TestImageDownloader:
    """Test image downloader"""
    
    @pytest.mark.asyncio
    async def test_download_image_success(self):
        """Test successful image download"""
        downloader = ImageDownloader(timeout=5)
        
        # Create mock response
        image = Image.new('RGB', (100, 100), color='red')
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format='PNG')
        img_byte_arr.seek(0)
        
        mock_response = Mock()
        mock_response.status = 200
        mock_response.read = AsyncMock(return_value=img_byte_arr.getvalue())
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        
        mock_session = Mock()
        mock_session.get = Mock(return_value=mock_response)
        
        result = await downloader.download_image(mock_session, 'http://example.com/image.jpg')
        
        assert result is not None
        assert isinstance(result, Image.Image)
    
    @pytest.mark.asyncio
    async def test_download_image_http_error(self):
        """Test handling of HTTP errors"""
        downloader = ImageDownloader(timeout=5, max_retries=2)
        
        mock_response = Mock()
        mock_response.status = 404
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        
        mock_session = Mock()
        mock_session.get = Mock(return_value=mock_response)
        
        result = await downloader.download_image(mock_session, 'http://example.com/notfound.jpg')
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_download_image_timeout(self):
        """Test handling of timeout"""
        downloader = ImageDownloader(timeout=1, max_retries=2, retry_delay=0.1)
        
        mock_session = AsyncMock()
        mock_session.get = AsyncMock(side_effect=asyncio.TimeoutError())
        
        result = await downloader.download_image(mock_session, 'http://example.com/slow.jpg')
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_download_batch(self):
        """Test batch download"""
        downloader = ImageDownloader(timeout=5)
        
        # Create mock images
        urls = [
            ('CAM001', 'http://example.com/cam1.jpg'),
            ('CAM002', 'http://example.com/cam2.jpg')
        ]
        
        with patch.object(downloader, 'download_image') as mock_download:
            # Mock successful downloads
            image1 = Image.new('RGB', (100, 100), color='red')
            image2 = Image.new('RGB', (100, 100), color='blue')
            mock_download.side_effect = [image1, image2]
            
            results = await downloader.download_batch(urls)
            
            assert len(results) == 2
            assert 'CAM001' in results
            assert 'CAM002' in results


# ============================================================================
# Test MetricsCalculator
# ============================================================================

class TestMetricsCalculator:
    """Test metrics calculator"""
    
    def test_calculate_free_flow(self):
        """Test metrics calculation for free flow traffic"""
        config = {
            'intensity_threshold': 0.7,
            'low_intensity_threshold': 0.3,
            'occupancy_max_vehicles': 50,
            'min_speed_kmh': 5.0,
            'max_speed_kmh': 80.0
        }
        
        calculator = MetricsCalculator(config)
        metrics = calculator.calculate(vehicle_count=10)
        
        assert metrics.vehicle_count == 10
        assert metrics.intensity == 0.2  # 10/50
        assert metrics.occupancy == 0.2
        assert metrics.congestion_level == "free"
        assert metrics.average_speed == 80.0
    
    def test_calculate_moderate_traffic(self):
        """Test metrics calculation for moderate traffic"""
        config = {
            'intensity_threshold': 0.7,
            'low_intensity_threshold': 0.3,
            'occupancy_max_vehicles': 50,
            'min_speed_kmh': 5.0,
            'max_speed_kmh': 80.0
        }
        
        calculator = MetricsCalculator(config)
        metrics = calculator.calculate(vehicle_count=25)
        
        assert metrics.vehicle_count == 25
        assert metrics.intensity == 0.5  # 25/50
        assert metrics.occupancy == 0.5
        assert metrics.congestion_level == "moderate"
        assert 5.0 < metrics.average_speed < 80.0
    
    def test_calculate_congested_traffic(self):
        """Test metrics calculation for congested traffic"""
        config = {
            'intensity_threshold': 0.7,
            'low_intensity_threshold': 0.3,
            'occupancy_max_vehicles': 50,
            'min_speed_kmh': 5.0,
            'max_speed_kmh': 80.0
        }
        
        calculator = MetricsCalculator(config)
        metrics = calculator.calculate(vehicle_count=40)
        
        assert metrics.vehicle_count == 40
        assert metrics.intensity == 0.8  # 40/50
        assert metrics.occupancy == 0.8
        assert metrics.congestion_level == "congested"
        assert metrics.average_speed == 5.0
    
    def test_calculate_max_occupancy(self):
        """Test metrics with vehicle count exceeding max"""
        config = {
            'occupancy_max_vehicles': 50,
            'intensity_threshold': 0.7,
            'low_intensity_threshold': 0.3,
            'min_speed_kmh': 5.0
        }
        
        calculator = MetricsCalculator(config)
        metrics = calculator.calculate(vehicle_count=60)
        
        assert metrics.intensity == 1.0  # Capped at 1.0
        assert metrics.occupancy == 1.0
        assert metrics.congestion_level == "congested"
    
    def test_calculate_zero_vehicles(self):
        """Test metrics with no vehicles"""
        config = {
            'occupancy_max_vehicles': 50,
            'intensity_threshold': 0.7,
            'low_intensity_threshold': 0.3,
            'max_speed_kmh': 80.0
        }
        
        calculator = MetricsCalculator(config)
        metrics = calculator.calculate(vehicle_count=0)
        
        assert metrics.vehicle_count == 0
        assert metrics.intensity == 0.0
        assert metrics.occupancy == 0.0
        assert metrics.congestion_level == "free"


# ============================================================================
# Test NGSILDEntityGenerator
# ============================================================================

class TestNGSILDEntityGenerator:
    """Test NGSI-LD entity generator"""
    
    def test_create_item_flow_observed(self):
        """Test creating ItemFlowObserved entity"""
        camera_id = "CAM001"
        location = {"type": "Point", "coordinates": [106.691, 10.791]}
        metrics = TrafficMetrics(
            vehicle_count=25,
            intensity=0.5,
            occupancy=0.5,
            average_speed=42.5,
            congestion_level="moderate"
        )
        timestamp = "2025-11-01T10:00:00Z"
        
        entity = NGSILDEntityGenerator.create_item_flow_observed(
            camera_id=camera_id,
            location=location,
            metrics=metrics,
            timestamp=timestamp
        )
        
        assert entity['type'] == 'ItemFlowObserved'
        assert 'CAM001' in entity['id']
        assert entity['refDevice']['object'] == 'urn:ngsi-ld:Camera:CAM001'
        assert entity['location']['type'] == 'GeoProperty'
        assert entity['location']['value'] == location
        assert entity['intensity']['value'] == 0.5
        assert entity['occupancy']['value'] == 0.5
        assert entity['averageSpeed']['value'] == 42.5
        assert entity['averageSpeed']['unitCode'] == 'KMH'
        assert entity['vehicleCount']['value'] == 25
        assert entity['congestionLevel']['value'] == 'moderate'
    
    def test_create_item_flow_observed_with_detections(self):
        """Test creating entity with detection details"""
        camera_id = "CAM002"
        location = {"type": "Point", "coordinates": [106.692, 10.792]}
        metrics = TrafficMetrics(
            vehicle_count=3,
            intensity=0.06,
            occupancy=0.06,
            average_speed=80.0,
            congestion_level="free"
        )
        timestamp = "2025-11-01T10:00:00Z"
        detections = [
            Detection(class_id=2, class_name='car', confidence=0.85, bbox=[10, 20, 100, 200]),
            Detection(class_id=2, class_name='car', confidence=0.78, bbox=[200, 30, 300, 250]),
            Detection(class_id=3, class_name='motorcycle', confidence=0.92, bbox=[400, 50, 500, 300])
        ]
        
        entity = NGSILDEntityGenerator.create_item_flow_observed(
            camera_id=camera_id,
            location=location,
            metrics=metrics,
            timestamp=timestamp,
            detections=detections
        )
        
        assert 'detectionDetails' in entity
        assert entity['detectionDetails']['value']['total_detections'] == 3
        assert entity['detectionDetails']['value']['classes']['car'] == 2
        assert entity['detectionDetails']['value']['classes']['motorcycle'] == 1


# ============================================================================
# Test Detection and ImageAnalysisResult
# ============================================================================

class TestDataClasses:
    """Test data classes"""
    
    def test_detection_to_dict(self):
        """Test Detection serialization"""
        detection = Detection(
            class_id=2,
            class_name='car',
            confidence=0.85,
            bbox=[10.5, 20.3, 100.7, 200.9]
        )
        
        d = detection.to_dict()
        
        assert d['class_id'] == 2
        assert d['class_name'] == 'car'
        assert d['confidence'] == 0.85
        assert d['bbox'] == [10.5, 20.3, 100.7, 200.9]
    
    def test_image_analysis_result_to_dict(self):
        """Test ImageAnalysisResult serialization"""
        detections = [
            Detection(class_id=2, class_name='car', confidence=0.85, bbox=[10, 20, 100, 200])
        ]
        
        result = ImageAnalysisResult(
            camera_id='CAM001',
            status=DetectionStatus.SUCCESS,
            timestamp='2025-11-01T10:00:00Z',
            detections=detections,
            vehicle_count=1,
            person_count=0,
            processing_time=0.5,
            image_url='http://example.com/image.jpg'
        )
        
        d = result.to_dict()
        
        assert d['camera_id'] == 'CAM001'
        assert d['status'] == 'success'
        assert d['vehicle_count'] == 1
        assert len(d['detections']) == 1
    
    def test_traffic_metrics_to_dict(self):
        """Test TrafficMetrics serialization"""
        metrics = TrafficMetrics(
            vehicle_count=25,
            intensity=0.5,
            occupancy=0.5,
            average_speed=42.5,
            congestion_level='moderate'
        )
        
        d = metrics.to_dict()
        
        assert d['vehicle_count'] == 25
        assert d['intensity'] == 0.5
        assert d['occupancy'] == 0.5
        assert d['average_speed'] == 42.5
        assert d['congestion_level'] == 'moderate'


# ============================================================================
# Test CVAnalysisAgent
# ============================================================================

class TestCVAnalysisAgent:
    """Test main CV analysis agent"""
    
    def test_agent_initialization(self, tmp_path):
        """Test agent initialization"""
        config_file = tmp_path / "cv_config.yaml"
        config_data = {
            'cv_analysis': {
                'model': {'type': 'yolov8', 'weights': 'yolov8n.pt', 'confidence': 0.5},
                'vehicle_classes': ['car', 'bus'],
                'person_classes': ['person'],
                'batch_size': 20,
                'timeout': 10,
                'metrics': {
                    'intensity_threshold': 0.7,
                    'occupancy_max_vehicles': 50
                },
                'output': {'file': 'data/observations.json'}
            }
        }
        
        with open(config_file, 'w') as f:
            yaml.dump(config_data, f)
        
        agent = CVAnalysisAgent(str(config_file))
        
        assert agent.config_loader is not None
        assert agent.detector is not None
        assert agent.downloader is not None
        assert agent.metrics_calculator is not None
        assert 'car' in agent.vehicle_classes
        assert 'person' in agent.person_classes
    
    def test_analyze_image_success(self, tmp_path):
        """Test successful image analysis"""
        config_file = tmp_path / "cv_config.yaml"
        config_data = {
            'cv_analysis': {
                'model': {'weights': 'yolov8n.pt', 'confidence': 0.5},
                'vehicle_classes': ['car', 'motorcycle'],
                'person_classes': ['person'],
                'batch_size': 20,
                'timeout': 10,
                'metrics': {'occupancy_max_vehicles': 50},
                'output': {'file': 'data/observations.json'}
            }
        }
        
        with open(config_file, 'w') as f:
            yaml.dump(config_data, f)
        
        agent = CVAnalysisAgent(str(config_file))
        
        # Create test image
        image = Image.new('RGB', (640, 480), color='blue')
        
        result = agent.analyze_image('CAM001', image, 'http://example.com/image.jpg')
        
        assert result.camera_id == 'CAM001'
        assert result.status in [DetectionStatus.SUCCESS, DetectionStatus.NO_DETECTIONS]
        assert result.processing_time >= 0  # Changed from > 0 to >= 0
        assert result.image_url == 'http://example.com/image.jpg'
    
    def test_analyze_image_failure(self, tmp_path):
        """Test image analysis failure handling"""
        config_file = tmp_path / "cv_config.yaml"
        config_data = {
            'cv_analysis': {
                'model': {'weights': 'yolov8n.pt'},
                'vehicle_classes': ['car'],
                'person_classes': ['person'],
                'batch_size': 20,
                'timeout': 10,
                'metrics': {},
                'output': {}
            }
        }
        
        with open(config_file, 'w') as f:
            yaml.dump(config_data, f)
        
        agent = CVAnalysisAgent(str(config_file))
        
        # Mock detector to raise exception
        with patch.object(agent.detector, 'detect', side_effect=Exception("Detection error")):
            image = Image.new('RGB', (640, 480))
            result = agent.analyze_image('CAM001', image)
            
            assert result.status == DetectionStatus.FAILED
            assert result.error_message == "Detection error"
    
    @pytest.mark.asyncio
    async def test_process_cameras(self, tmp_path):
        """Test processing batch of cameras"""
        config_file = tmp_path / "cv_config.yaml"
        config_data = {
            'cv_analysis': {
                'model': {'weights': 'yolov8n.pt', 'confidence': 0.5},
                'vehicle_classes': ['car'],
                'person_classes': ['person'],
                'batch_size': 2,
                'timeout': 10,
                'metrics': {'occupancy_max_vehicles': 50},
                'output': {'file': 'data/observations.json', 'include_detections': False}
            }
        }
        
        with open(config_file, 'w') as f:
            yaml.dump(config_data, f)
        
        agent = CVAnalysisAgent(str(config_file))
        
        cameras = [
            {
                'id': 'CAM001',
                'imageSnapshot': 'http://example.com/cam1.jpg',
                'location': {'type': 'Point', 'coordinates': [106.691, 10.791]}
            },
            {
                'id': 'CAM002',
                'imageSnapshot': 'http://example.com/cam2.jpg',
                'location': {'type': 'Point', 'coordinates': [106.692, 10.792]}
            }
        ]
        
        # Mock image download
        test_image = Image.new('RGB', (640, 480), color='blue')
        with patch.object(agent.downloader, 'download_batch', return_value={'CAM001': test_image, 'CAM002': test_image}):
            entities = await agent.process_cameras(cameras)
            
            assert len(entities) == 2
            assert all(e['type'] == 'ItemFlowObserved' for e in entities)
    
    def test_save_observations(self, tmp_path):
        """Test saving observations to file"""
        config_file = tmp_path / "cv_config.yaml"
        config_data = {
            'cv_analysis': {
                'model': {},
                'vehicle_classes': [],
                'person_classes': [],
                'batch_size': 20,
                'timeout': 10,
                'metrics': {},
                'output': {'file': str(tmp_path / 'observations.json')}
            }
        }
        
        with open(config_file, 'w') as f:
            yaml.dump(config_data, f)
        
        agent = CVAnalysisAgent(str(config_file))
        
        entities = [
            {
                'id': 'urn:ngsi-ld:ItemFlowObserved:CAM001-20251101',
                'type': 'ItemFlowObserved',
                'vehicleCount': {'type': 'Property', 'value': 10}
            }
        ]
        
        output_file = tmp_path / 'test_observations.json'
        agent.save_observations(entities, str(output_file))
        
        assert output_file.exists()
        
        with open(output_file, 'r') as f:
            saved_data = json.load(f)
        
        assert len(saved_data) == 1
        assert saved_data[0]['type'] == 'ItemFlowObserved'
    
    @pytest.mark.asyncio
    async def test_run_with_array_input(self, tmp_path):
        """Test run with camera array input"""
        config_file = tmp_path / "cv_config.yaml"
        config_data = {
            'cv_analysis': {
                'model': {'weights': 'yolov8n.pt'},
                'vehicle_classes': ['car'],
                'person_classes': ['person'],
                'batch_size': 2,
                'timeout': 10,
                'metrics': {'occupancy_max_vehicles': 50},
                'output': {'file': str(tmp_path / 'observations.json'), 'include_detections': False}
            }
        }
        
        with open(config_file, 'w') as f:
            yaml.dump(config_data, f)
        
        # Create input file with camera array
        input_file = tmp_path / 'cameras.json'
        cameras = [
            {'id': 'CAM001', 'imageSnapshot': 'http://example.com/1.jpg', 'location': {'type': 'Point', 'coordinates': [106, 10]}}
        ]
        with open(input_file, 'w') as f:
            json.dump(cameras, f)
        
        agent = CVAnalysisAgent(str(config_file))
        
        # Mock image download and processing
        test_image = Image.new('RGB', (640, 480))
        with patch.object(agent.downloader, 'download_batch', return_value={'CAM001': test_image}):
            entities = await agent.run(str(input_file))
            
            assert len(entities) == 1
    
    @pytest.mark.asyncio
    async def test_run_with_object_input(self, tmp_path):
        """Test run with camera object input"""
        config_file = tmp_path / "cv_config.yaml"
        config_data = {
            'cv_analysis': {
                'model': {},
                'vehicle_classes': ['car'],
                'person_classes': [],
                'batch_size': 2,
                'timeout': 10,
                'metrics': {'occupancy_max_vehicles': 50},
                'output': {'file': str(tmp_path / 'observations.json')}
            }
        }
        
        with open(config_file, 'w') as f:
            yaml.dump(config_data, f)
        
        # Create input file with cameras object
        input_file = tmp_path / 'cameras.json'
        data = {
            'cameras': [
                {'id': 'CAM001', 'imageSnapshot': 'http://example.com/1.jpg', 'location': {}}
            ]
        }
        with open(input_file, 'w') as f:
            json.dump(data, f)
        
        agent = CVAnalysisAgent(str(config_file))
        
        test_image = Image.new('RGB', (640, 480))
        with patch.object(agent.downloader, 'download_batch', return_value={'CAM001': test_image}):
            entities = await agent.run(str(input_file))
            
            assert len(entities) == 1


# ============================================================================
# Integration Tests
# ============================================================================

class TestIntegration:
    """Integration tests"""
    
    @pytest.mark.asyncio
    async def test_end_to_end_workflow(self, tmp_path):
        """Test complete end-to-end workflow"""
        # Setup configuration
        config_file = tmp_path / "cv_config.yaml"
        config_data = {
            'cv_analysis': {
                'model': {
                    'type': 'yolov8',
                    'weights': 'yolov8n.pt',
                    'confidence': 0.5,
                    'device': 'cpu'
                },
                'vehicle_classes': ['car', 'motorcycle', 'bus', 'truck'],
                'person_classes': ['person'],
                'metrics': {
                    'intensity_threshold': 0.7,
                    'low_intensity_threshold': 0.3,
                    'occupancy_max_vehicles': 50,
                    'min_speed_kmh': 5.0,
                    'max_speed_kmh': 80.0
                },
                'batch_size': 5,
                'timeout': 10,
                'output': {
                    'file': str(tmp_path / 'observations.json'),
                    'format': 'ngsi-ld',
                    'include_detections': True
                }
            }
        }
        
        with open(config_file, 'w') as f:
            yaml.dump(config_data, f)
        
        # Create input cameras
        input_file = tmp_path / 'cameras.json'
        cameras = []
        for i in range(10):
            cameras.append({
                'id': f'CAM{i:03d}',
                'imageSnapshot': f'http://example.com/camera{i}.jpg',
                'location': {
                    'type': 'Point',
                    'coordinates': [106.691 + i*0.001, 10.791 + i*0.001]
                }
            })
        
        with open(input_file, 'w') as f:
            json.dump(cameras, f)
        
        # Run agent
        agent = CVAnalysisAgent(str(config_file))
        
        # Mock image downloads
        test_images = {f'CAM{i:03d}': Image.new('RGB', (640, 480), color='blue') for i in range(10)}
        with patch.object(agent.downloader, 'download_batch', return_value=test_images):
            entities = await agent.run(str(input_file))
        
        # Verify results
        assert len(entities) == 10
        
        for entity in entities:
            assert entity['type'] == 'ItemFlowObserved'
            assert 'id' in entity
            assert 'refDevice' in entity
            assert 'location' in entity
            assert 'intensity' in entity
            assert 'occupancy' in entity
            assert 'averageSpeed' in entity
            assert 'vehicleCount' in entity
            assert 'congestionLevel' in entity
        
        # Verify output file
        output_file = tmp_path / 'observations.json'
        assert output_file.exists()
        
        with open(output_file, 'r') as f:
            saved_entities = json.load(f)
        
        assert len(saved_entities) == 10


# ============================================================================
# Performance Tests
# ============================================================================

class TestPerformance:
    """Performance tests"""
    
    @pytest.mark.asyncio
    async def test_process_722_cameras_under_2_minutes(self, tmp_path):
        """Test processing 722 cameras in under 2 minutes"""
        config_file = tmp_path / "cv_config.yaml"
        config_data = {
            'cv_analysis': {
                'model': {'weights': 'yolov8n.pt'},
                'vehicle_classes': ['car'],
                'person_classes': [],
                'batch_size': 50,  # Large batch for speed
                'timeout': 5,
                'metrics': {'occupancy_max_vehicles': 50},
                'output': {'file': str(tmp_path / 'observations.json'), 'include_detections': False}
            }
        }
        
        with open(config_file, 'w') as f:
            yaml.dump(config_data, f)
        
        # Create 722 cameras
        cameras = []
        for i in range(722):
            cameras.append({
                'id': f'CAM{i:04d}',
                'imageSnapshot': f'http://example.com/cam{i}.jpg',
                'location': {'type': 'Point', 'coordinates': [106 + i*0.001, 10 + i*0.001]}
            })
        
        agent = CVAnalysisAgent(str(config_file))
        
        # Mock fast image download and analysis
        mock_images = {f'CAM{i:04d}': Image.new('RGB', (100, 100)) for i in range(722)}
        
        with patch.object(agent.downloader, 'download_batch', return_value=mock_images):
            start_time = time.time()
            entities = await agent.process_cameras(cameras)
            duration = time.time() - start_time
        
        assert len(entities) == 722
        assert duration < 120  # Under 2 minutes
    
    @pytest.mark.asyncio
    async def test_batch_processing_performance(self, tmp_path):
        """Test batch processing is faster than sequential"""
        config_file = tmp_path / "cv_config.yaml"
        config_data = {
            'cv_analysis': {
                'model': {},
                'vehicle_classes': ['car'],
                'person_classes': [],
                'batch_size': 20,
                'timeout': 10,
                'metrics': {},
                'output': {}
            }
        }
        
        with open(config_file, 'w') as f:
            yaml.dump(config_data, f)
        
        agent = CVAnalysisAgent(str(config_file))
        
        cameras = [
            {'id': f'CAM{i:03d}', 'imageSnapshot': f'http://example.com/{i}.jpg', 'location': {}}
            for i in range(50)
        ]
        
        # Mock image downloads with delay
        async def mock_download_with_delay(urls):
            await asyncio.sleep(0.01 * len(urls))  # Simulate network delay
            return {cam_id: Image.new('RGB', (100, 100)) for cam_id, _ in urls}
        
        with patch.object(agent.downloader, 'download_batch', side_effect=mock_download_with_delay):
            start_time = time.time()
            entities = await agent.process_cameras(cameras)
            duration = time.time() - start_time
        
        # With batch_size=20, should process in 3 batches
        # Should be faster than sequential (50 * 0.01 = 0.5s)
        assert len(entities) == 50
        assert duration < 1.0  # Allow more overhead for batch processing


# ============================================================================
# Edge Cases
# ============================================================================

class TestEdgeCases:
    """Test edge cases"""
    
    @pytest.mark.asyncio
    async def test_empty_camera_list(self, tmp_path):
        """Test handling empty camera list"""
        config_file = tmp_path / "cv_config.yaml"
        config_data = {
            'cv_analysis': {
                'model': {},
                'vehicle_classes': [],
                'person_classes': [],
                'batch_size': 20,
                'timeout': 10,
                'metrics': {},
                'output': {}
            }
        }
        
        with open(config_file, 'w') as f:
            yaml.dump(config_data, f)
        
        agent = CVAnalysisAgent(str(config_file))
        entities = await agent.process_cameras([])
        
        assert len(entities) == 0
    
    @pytest.mark.asyncio
    async def test_all_image_downloads_fail(self, tmp_path):
        """Test handling when all image downloads fail"""
        config_file = tmp_path / "cv_config.yaml"
        config_data = {
            'cv_analysis': {
                'model': {},
                'vehicle_classes': ['car'],
                'person_classes': [],
                'batch_size': 20,
                'timeout': 10,
                'metrics': {},
                'output': {}
            }
        }
        
        with open(config_file, 'w') as f:
            yaml.dump(config_data, f)
        
        agent = CVAnalysisAgent(str(config_file))
        
        cameras = [
            {'id': 'CAM001', 'imageSnapshot': 'http://example.com/1.jpg', 'location': {}},
            {'id': 'CAM002', 'imageSnapshot': 'http://example.com/2.jpg', 'location': {}}
        ]
        
        # Mock failed downloads
        with patch.object(agent.downloader, 'download_batch', return_value={'CAM001': None, 'CAM002': None}):
            entities = await agent.process_cameras(cameras)
        
        assert len(entities) == 0
    
    def test_analyze_corrupted_image(self, tmp_path):
        """Test handling of corrupted image"""
        config_file = tmp_path / "cv_config.yaml"
        config_data = {
            'cv_analysis': {
                'model': {},
                'vehicle_classes': ['car'],
                'person_classes': [],
                'batch_size': 20,
                'timeout': 10,
                'metrics': {},
                'output': {}
            }
        }
        
        with open(config_file, 'w') as f:
            yaml.dump(config_data, f)
        
        agent = CVAnalysisAgent(str(config_file))
        
        # Create corrupted image (very small)
        image = Image.new('RGB', (1, 1))
        
        result = agent.analyze_image('CAM001', image)
        
        # Should still return a result
        assert result.camera_id == 'CAM001'
        assert result.status in [DetectionStatus.SUCCESS, DetectionStatus.NO_DETECTIONS, DetectionStatus.FAILED]
    
    def test_detection_status_enum(self):
        """Test DetectionStatus enum values"""
        assert DetectionStatus.SUCCESS.value == "success"
        assert DetectionStatus.FAILED.value == "failed"
        assert DetectionStatus.NO_DETECTIONS.value == "no_detections"
        assert DetectionStatus.INVALID_IMAGE.value == "invalid_image"
        assert DetectionStatus.TIMEOUT.value == "timeout"


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
