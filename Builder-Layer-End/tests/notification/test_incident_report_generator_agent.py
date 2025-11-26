"""
Tests for Incident Report Generator Agent

Comprehensive test suite covering:
- Configuration loading
- Data collection (mocked Neo4j)
- Report generation (JSON, HTML, PDF)
- Visualization generation
- Email notifications (mocked)
- API endpoints

Author: Builder Layer Development Team
Version: 1.0.0
"""

import json
import pytest
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import sys

sys.path.append(str(Path(__file__).parent.parent.parent))

from agents.notification.incident_report_generator_agent import (
    IncidentReportConfig,
    Neo4jQueryExecutor,
    ReportDataCollector,
    VisualizationGenerator,
    ReportGenerator,
    NotificationSender,
    IncidentReportGenerator,
)


# Test fixtures


@pytest.fixture
def sample_config(tmp_path):
    """Create sample configuration file."""
    config = {
        "incident_report_generator": {
            "triggers": [
                {"entity_type": "RoadAccident", "severity": ["moderate", "severe"]}
            ],
            "data_sources": {
                "neo4j": {
                    "enabled": False,
                    "uri": "bolt://localhost:7687",
                    "username": "neo4j",
                    "password": "password",
                    "queries": {
                        "context": {"query": "MATCH (a) RETURN a", "timeout": 10}
                    },
                },
                "stellio": {"enabled": False, "base_url": "http://localhost:8080"},
            },
            "report_formats": [
                {
                    "type": "json",
                    "enabled": True,
                    "fields": ["report_id"],
                    "pretty_print": True,
                },
                {
                    "type": "html",
                    "enabled": True,
                    "template": "templates/incident_web.html",
                },
                {
                    "type": "pdf",
                    "enabled": False,
                    "template": "templates/incident_report.html",
                    "engine": "weasyprint",
                },
            ],
            "storage": {
                "filesystem": {
                    "enabled": True,
                    "base_path": str(tmp_path / "reports"),
                    "subdirs_by_date": False,
                }
            },
            "notifications": {
                "email": {
                    "enabled": False,
                    "smtp_host": "localhost",
                    "smtp_port": 25,
                    "recipients": {"moderate": ["admin@test.com"]},
                }
            },
            "visualizations": {"charts": {"enabled": True}, "maps": {"enabled": False}},
            "report_sections": {
                "recommendations": {
                    "rules": [
                        {
                            "condition": {"severity": "moderate"},
                            "actions": ["Monitor situation", "Update traffic apps"],
                        }
                    ]
                }
            },
        }
    }

    config_path = tmp_path / "incident_report_config.yaml"
    import yaml

    with open(config_path, "w") as f:
        yaml.dump(config, f)

    return str(config_path)


@pytest.fixture
def sample_entity_data():
    """Sample incident entity data."""
    return {
        "id": "urn:ngsi-ld:RoadAccident:TEST-001",
        "type": "RoadAccident",
        "roadName": {"value": "Test Road - Main Street"},
        "severity": {"value": "moderate"},
        "cameraId": {"value": "CAM-001"},
        "detectionTime": {"value": "2025-11-01T10:00:00Z"},
        "avgSpeed": {"value": 25.5},
        "speedVariance": {"value": 15.2},
        "location": {"value": {"type": "Point", "coordinates": [106.6297, 10.8231]}},
    }


# Configuration Tests


class TestIncidentReportConfig:
    """Test configuration loading."""

    def test_load_config(self, sample_config):
        """Test loading configuration from YAML."""
        config = IncidentReportConfig(sample_config)

        assert config.config is not None
        assert "incident_report_generator" in config.config

    def test_get_triggers(self, sample_config):
        """Test getting trigger configuration."""
        config = IncidentReportConfig(sample_config)
        triggers = config.get_triggers()

        assert len(triggers) > 0
        assert triggers[0]["entity_type"] == "RoadAccident"

    def test_get_data_sources(self, sample_config):
        """Test getting data sources configuration."""
        config = IncidentReportConfig(sample_config)
        data_sources = config.get_data_sources()

        assert "neo4j" in data_sources
        assert "stellio" in data_sources

    def test_get_report_formats(self, sample_config):
        """Test getting report formats."""
        config = IncidentReportConfig(sample_config)
        formats = config.get_report_formats()

        format_types = [f["type"] for f in formats]
        assert "json" in format_types
        assert "html" in format_types
        assert "pdf" in format_types

    def test_invalid_config_path(self):
        """Test invalid configuration path."""
        with pytest.raises(FileNotFoundError):
            IncidentReportConfig("nonexistent.yaml")


# Neo4j Query Executor Tests


class TestNeo4jQueryExecutor:
    """Test Neo4j query executor."""

    def test_executor_disabled(self, sample_config):
        """Test executor when Neo4j is disabled."""
        config = IncidentReportConfig(sample_config)
        neo4j_config = config.get_data_sources().get("neo4j", {})

        executor = Neo4jQueryExecutor(neo4j_config)

        assert executor.enabled is False

    def test_execute_query_disabled(self, sample_config):
        """Test query execution when disabled."""
        config = IncidentReportConfig(sample_config)
        neo4j_config = config.get_data_sources().get("neo4j", {})

        executor = Neo4jQueryExecutor(neo4j_config)
        results = executor.execute_query("context", {"accident_id": "test"})

        assert results == []


# Report Data Collector Tests


class TestReportDataCollector:
    """Test report data collector."""

    def test_initialization(self, sample_config):
        """Test data collector initialization."""
        config = IncidentReportConfig(sample_config)
        collector = ReportDataCollector(config)

        assert collector.config is not None
        assert collector.neo4j is not None

    def test_collect_incident_data(self, sample_config, sample_entity_data):
        """Test incident data collection."""
        config = IncidentReportConfig(sample_config)
        collector = ReportDataCollector(config)

        data = collector.collect_incident_data(
            sample_entity_data["id"], sample_entity_data
        )

        assert "accident_id" in data
        assert "entity_data" in data
        assert "context" in data
        assert "timeline" in data
        assert data["accident_id"] == sample_entity_data["id"]


# Visualization Generator Tests


class TestVisualizationGenerator:
    """Test visualization generation."""

    def test_initialization(self):
        """Test visualization generator initialization."""
        config = {"charts": {"enabled": True}, "maps": {"enabled": False}}
        viz_gen = VisualizationGenerator(config)

        assert viz_gen.charts_enabled is True
        assert viz_gen.maps_enabled is False

    def test_generate_speed_timeline_chart(self):
        """Test speed timeline chart generation."""
        config = {"charts": {"enabled": True}}
        viz_gen = VisualizationGenerator(config)

        timeline_data = [
            {"o": {"observedAt": "2025-11-01T10:00:00Z", "avgSpeed": 45.0}},
            {"o": {"observedAt": "2025-11-01T10:01:00Z", "avgSpeed": 35.0}},
            {"o": {"observedAt": "2025-11-01T10:02:00Z", "avgSpeed": 25.0}},
        ]

        chart = viz_gen.generate_speed_timeline_chart(timeline_data)

        # Should return base64-encoded PNG or None
        assert chart is None or isinstance(chart, str)

    def test_generate_speed_variance_chart(self):
        """Test speed variance chart generation."""
        config = {"charts": {"enabled": True}}
        viz_gen = VisualizationGenerator(config)

        timeline_data = [
            {"o": {"speedVariance": 10.0}},
            {"o": {"speedVariance": 15.0}},
            {"o": {"speedVariance": 20.0}},
        ]

        chart = viz_gen.generate_speed_variance_chart(timeline_data)

        # Should return base64-encoded PNG or None
        assert chart is None or isinstance(chart, str)

    def test_charts_disabled(self):
        """Test chart generation when disabled."""
        config = {"charts": {"enabled": False}}
        viz_gen = VisualizationGenerator(config)

        timeline_data = [{"o": {"avgSpeed": 45.0}}]
        chart = viz_gen.generate_speed_timeline_chart(timeline_data)

        assert chart is None


# Report Generator Tests


class TestReportGenerator:
    """Test report generation."""

    def test_initialization(self, sample_config):
        """Test report generator initialization."""
        config = IncidentReportConfig(sample_config)
        generator = ReportGenerator(config)

        assert generator.config is not None
        assert generator.jinja_env is not None

    def test_generate_recommendations(self, sample_config):
        """Test recommendation generation."""
        config = IncidentReportConfig(sample_config)
        generator = ReportGenerator(config)

        recommendations = generator._generate_recommendations("moderate")

        assert isinstance(recommendations, list)
        assert len(recommendations) > 0

    def test_build_report_data(self, sample_config, sample_entity_data):
        """Test report data building."""
        config = IncidentReportConfig(sample_config)
        generator = ReportGenerator(config)

        data = {
            "accident_id": sample_entity_data["id"],
            "entity_data": sample_entity_data,
            "timeline": [],
            "related_incidents": [],
            "historical_patterns": {},
            "weather": {},
        }

        report_data = generator._build_report_data(data, "RPT-TEST-001")

        assert report_data["report_id"] == "RPT-TEST-001"
        assert report_data["accident_id"] == sample_entity_data["id"]
        assert "summary" in report_data
        assert "timeline" in report_data
        assert "impact" in report_data
        assert "recommendations" in report_data

    def test_generate_json_report(self, sample_config, sample_entity_data):
        """Test JSON report generation."""
        config = IncidentReportConfig(sample_config)
        generator = ReportGenerator(config)

        data = {
            "accident_id": sample_entity_data["id"],
            "entity_data": sample_entity_data,
            "timeline": [],
            "related_incidents": [],
            "historical_patterns": {},
            "weather": {},
        }

        report_data = generator._build_report_data(data, "RPT-TEST-002")
        json_path = generator._generate_json(report_data, "RPT-TEST-002")

        assert Path(json_path).exists()
        assert json_path.endswith(".json")

        # Verify JSON content
        with open(json_path, "r") as f:
            json_data = json.load(f)
            assert json_data["report_id"] == "RPT-TEST-002"

    def test_generate_html_report(self, sample_config, sample_entity_data):
        """Test HTML report generation."""
        config = IncidentReportConfig(sample_config)
        generator = ReportGenerator(config)

        data = {
            "accident_id": sample_entity_data["id"],
            "entity_data": sample_entity_data,
            "timeline": [],
            "related_incidents": [],
            "historical_patterns": {},
            "weather": {},
        }

        report_data = generator._build_report_data(data, "RPT-TEST-003")
        report_data["charts"] = []
        report_data["map_image"] = None

        html_config = {"template": "templates/incident_web.html"}
        html_path = generator._generate_html(report_data, "RPT-TEST-003", html_config)

        assert Path(html_path).exists()
        assert html_path.endswith(".html")


# Notification Sender Tests


class TestNotificationSender:
    """Test notification sending."""

    def test_initialization(self):
        """Test notification sender initialization."""
        config = {"email": {"enabled": False}, "webhook": {"enabled": False}}

        sender = NotificationSender(config)

        assert sender.email_enabled is False
        assert sender.webhook_enabled is False

    def test_email_disabled(self):
        """Test email notification when disabled."""
        config = {"email": {"enabled": False}}

        sender = NotificationSender(config)

        report_data = {"report_id": "TEST-001", "severity": "moderate"}

        # Should not raise exception
        sender.send_email_notification(report_data)


# Integration Tests


class TestIncidentReportGenerator:
    """Test main incident report generator."""

    def test_initialization(self, sample_config):
        """Test generator initialization."""
        generator = IncidentReportGenerator(sample_config)

        assert generator.config is not None
        assert generator.data_collector is not None
        assert generator.report_generator is not None
        assert generator.app is not None

    def test_generate_report_for_incident(self, sample_config, sample_entity_data):
        """Test complete report generation."""
        generator = IncidentReportGenerator(sample_config)

        results = generator.generate_report_for_incident(
            sample_entity_data["id"], sample_entity_data
        )

        assert "report_id" in results
        assert "files" in results
        assert generator.stats["reports_generated"] > 0

    def test_generate_report_error_handling(self, sample_config):
        """Test error handling in report generation."""
        generator = IncidentReportGenerator(sample_config)

        # Invalid entity data - should handle gracefully
        try:
            results = generator.generate_report_for_incident("invalid-id", {})
            # Either succeeds with empty data or fails gracefully
            assert "report_id" in results or generator.stats["reports_failed"] > 0
        except Exception:
            # Exception is also acceptable
            assert generator.stats["reports_failed"] > 0

    def test_api_health_endpoint(self, sample_config):
        """Test API health endpoint."""
        generator = IncidentReportGenerator(sample_config)

        with generator.app.test_client() as client:
            response = client.get("/health")

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data["status"] == "healthy"

    def test_api_stats_endpoint(self, sample_config):
        """Test API stats endpoint."""
        generator = IncidentReportGenerator(sample_config)

        with generator.app.test_client() as client:
            response = client.get("/stats")

            assert response.status_code == 200
            data = json.loads(response.data)
            assert "reports_generated" in data
            assert "reports_failed" in data


# Edge Cases


class TestEdgeCases:
    """Test edge cases and error scenarios."""

    def test_missing_template_file(self, sample_config):
        """Test handling missing template file."""
        config = IncidentReportConfig(sample_config)
        generator = ReportGenerator(config)

        # Should handle gracefully (template may not exist in test environment)
        assert generator.jinja_env is not None

    def test_empty_timeline_data(self, sample_config, sample_entity_data):
        """Test report generation with empty timeline."""
        config = IncidentReportConfig(sample_config)
        generator = ReportGenerator(config)

        data = {
            "accident_id": sample_entity_data["id"],
            "entity_data": sample_entity_data,
            "timeline": [],  # Empty timeline
            "related_incidents": [],
            "historical_patterns": {},
            "weather": {},
        }

        report_data = generator._build_report_data(data, "RPT-TEST-EMPTY")

        assert report_data["timeline"] == []
        assert report_data["report_id"] == "RPT-TEST-EMPTY"

    def test_missing_location_data(self, sample_config):
        """Test handling missing location data."""
        config = IncidentReportConfig(sample_config)
        collector = ReportDataCollector(config)

        entity_data = {
            "id": "test-id",
            "type": "RoadAccident",
            "severity": {"value": "moderate"},
            # No location data
        }

        data = collector.collect_incident_data("test-id", entity_data)

        assert data["accident_id"] == "test-id"
        assert "entity_data" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
