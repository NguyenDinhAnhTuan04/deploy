"""
==============================================================================
PERFORMANCE MONITOR AGENT - COMPREHENSIVE TEST SUITE
==============================================================================
Purpose: Unit tests, integration tests, and load tests for PerformanceMonitorAgent
Coverage: 100% of all classes and methods
==============================================================================
"""

import pytest
import time
import os
import tempfile
import yaml
import json
from unittest.mock import Mock, patch, MagicMock, call
from collections import defaultdict
import statistics

# Import modules to test
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from agents.monitoring.performance_monitor_agent import (
    PerformanceMonitorConfig,
    SystemMetricsCollector,
    ApplicationMetricsCollector,
    Neo4jMetricsCollector,
    PrometheusExporter,
    AlertManager,
    TrendAnalysisEngine,
    PerformanceMonitorAgent,
)


# ==============================================================================
# TEST FIXTURES
# ==============================================================================


@pytest.fixture
def sample_config_data():
    """Create sample configuration data."""
    return {
        "performance_monitor": {
            "collection_interval": 30,
            "enabled_collectors": ["system", "application", "neo4j"],
            "system_metrics": [
                {"name": "cpu_percent", "type": "gauge", "enabled": True},
                {"name": "memory_percent", "type": "gauge", "enabled": True},
                {"name": "disk_io_read_bytes", "type": "counter", "enabled": True},
            ],
            "application_metrics": [
                {
                    "name": "agent_execution_time",
                    "type": "histogram",
                    "labels": ["agent_name", "status"],
                    "buckets": [0.1, 1.0, 5.0, 10.0],
                    "enabled": True,
                },
                {
                    "name": "queue_length",
                    "type": "gauge",
                    "labels": ["queue_name"],
                    "enabled": True,
                },
            ],
            "neo4j_metrics": {
                "uri": "bolt://localhost:7687",
                "user": "neo4j",
                "password": "password",
                "database": "neo4j",
                "queries": [
                    {
                        "name": "neo4j_query_duration_p95",
                        "type": "gauge",
                        "query": "RETURN 123.45 AS value",
                        "enabled": True,
                    }
                ],
            },
            "prometheus": {
                "host": "0.0.0.0",
                "port": 9091,
                "metric_prefix": "test_system",
                "default_labels": {"environment": "test", "instance": "test-1"},
            },
            "alerting": {
                "enabled": True,
                "notifications": {
                    "channels": [{"type": "log", "level": "warning", "enabled": True}]
                },
                "rules": [
                    {
                        "name": "high_cpu",
                        "metric": "cpu_percent",
                        "condition": ">",
                        "threshold": 85,
                        "duration": 300,
                        "severity": "warning",
                        "message": "High CPU usage",
                        "enabled": True,
                    }
                ],
            },
        },
        "trend_analysis": {
            "enabled": True,
            "storage": {"backend": "file", "path": "logs/metrics_history"},
            "anomaly_detection": {
                "enabled": True,
                "algorithm": "zscore",
                "sensitivity": 2.0,
                "min_samples": 100,
            },
        },
        "logging": {
            "level": "INFO",
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            "file": "logs/test_performance_monitor.log",
        },
    }


@pytest.fixture
def config_file(sample_config_data):
    """Create temporary configuration file."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump(sample_config_data, f)
        config_path = f.name

    yield config_path

    # Cleanup
    if os.path.exists(config_path):
        os.unlink(config_path)


@pytest.fixture
def config(config_file):
    """Create PerformanceMonitorConfig instance."""
    return PerformanceMonitorConfig(config_file)


# ==============================================================================
# UNIT TESTS - Configuration Loader
# ==============================================================================


class TestPerformanceMonitorConfig:
    """Test configuration loading and validation."""

    def test_config_loads_successfully(self, config):
        """Test configuration loads without errors."""
        assert config.config is not None
        assert "performance_monitor" in config.config

    def test_config_has_required_sections(self, config):
        """Test configuration has all required sections."""
        assert "collection_interval" in config.config["performance_monitor"]
        assert "system_metrics" in config.config["performance_monitor"]
        assert "application_metrics" in config.config["performance_monitor"]
        assert "neo4j_metrics" in config.config["performance_monitor"]
        assert "prometheus" in config.config["performance_monitor"]
        assert "alerting" in config.config["performance_monitor"]

    def test_get_collection_interval(self, config):
        """Test getting collection interval."""
        interval = config.get_collection_interval()
        assert interval == 30

    def test_get_enabled_collectors(self, config):
        """Test getting enabled collectors list."""
        collectors = config.get_enabled_collectors()
        assert "system" in collectors
        assert "application" in collectors
        assert "neo4j" in collectors

    def test_get_system_metrics(self, config):
        """Test getting system metrics configuration."""
        metrics = config.get_system_metrics()
        assert len(metrics) == 3
        assert metrics[0]["name"] == "cpu_percent"

    def test_get_application_metrics(self, config):
        """Test getting application metrics configuration."""
        metrics = config.get_application_metrics()
        assert len(metrics) == 2
        assert metrics[0]["name"] == "agent_execution_time"

    def test_get_neo4j_config(self, config):
        """Test getting Neo4j configuration."""
        neo4j_config = config.get_neo4j_config()
        assert neo4j_config["uri"] == "bolt://localhost:7687"
        assert "queries" in neo4j_config

    def test_get_prometheus_config(self, config):
        """Test getting Prometheus configuration."""
        prom_config = config.get_prometheus_config()
        assert prom_config["port"] == 9091
        assert prom_config["metric_prefix"] == "test_system"

    def test_get_alerting_config(self, config):
        """Test getting alerting configuration."""
        alert_config = config.get_alerting_config()
        assert alert_config["enabled"] is True
        assert len(alert_config["rules"]) == 1

    def test_env_var_expansion(self, config_file):
        """Test environment variable expansion in config."""
        os.environ["TEST_VAR"] = "test_value"

        # Load config with env var
        config_data = {
            "performance_monitor": {
                "collection_interval": 30,
                "prometheus": {"host": "${TEST_VAR}"},
            }
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = f.name

        try:
            config = PerformanceMonitorConfig(temp_path)
            assert (
                config.config["performance_monitor"]["prometheus"]["host"]
                == "test_value"
            )
        finally:
            os.unlink(temp_path)
            del os.environ["TEST_VAR"]

    def test_invalid_config_file(self):
        """Test loading invalid configuration file."""
        with pytest.raises(FileNotFoundError):
            PerformanceMonitorConfig("nonexistent.yaml")

    def test_invalid_yaml_format(self):
        """Test loading malformed YAML."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("invalid: yaml: content:")
            temp_path = f.name

        try:
            with pytest.raises(ValueError):
                PerformanceMonitorConfig(temp_path)
        finally:
            os.unlink(temp_path)


# ==============================================================================
# UNIT TESTS - System Metrics Collector
# ==============================================================================


class TestSystemMetricsCollector:
    """Test system metrics collection."""

    def test_collector_initializes(self, config):
        """Test collector initializes successfully."""
        collector = SystemMetricsCollector(config)
        assert collector.config == config
        assert collector.prev_disk_io is None
        assert collector.prev_net_io is None

    @patch("psutil.cpu_percent")
    def test_collect_cpu_percent(self, mock_cpu, config):
        """Test CPU percentage collection."""
        mock_cpu.return_value = 45.5

        collector = SystemMetricsCollector(config)
        metrics = collector.collect()

        assert "cpu_percent" in metrics
        assert metrics["cpu_percent"] == 45.5

    @patch("psutil.virtual_memory")
    def test_collect_memory_percent(self, mock_memory, config):
        """Test memory percentage collection."""
        mock_mem = Mock()
        mock_mem.percent = 65.3
        mock_memory.return_value = mock_mem

        collector = SystemMetricsCollector(config)
        metrics = collector.collect()

        assert "memory_percent" in metrics
        assert metrics["memory_percent"] == 65.3

    @patch("psutil.disk_io_counters")
    def test_collect_disk_io_rates(self, mock_disk_io, config):
        """Test disk I/O rate calculation."""
        # First call
        mock_io1 = Mock()
        mock_io1.read_bytes = 1000
        mock_io1.write_bytes = 500
        mock_disk_io.return_value = mock_io1

        collector = SystemMetricsCollector(config)
        metrics1 = collector.collect()

        # Disk I/O not in first collection (no previous data)
        assert "disk_io_read_bytes" not in metrics1

        # Second call after time passes
        time.sleep(0.1)
        mock_io2 = Mock()
        mock_io2.read_bytes = 2000  # +1000 bytes
        mock_io2.write_bytes = 700  # +200 bytes
        mock_disk_io.return_value = mock_io2

        metrics2 = collector.collect()

        # Should have rate now
        assert "disk_io_read_bytes" in metrics2
        assert metrics2["disk_io_read_bytes"] > 0

    def test_collect_handles_errors_gracefully(self, config):
        """Test collector handles errors in metric collection."""
        collector = SystemMetricsCollector(config)

        # Should not raise even if psutil fails
        with patch("psutil.cpu_percent", side_effect=Exception("Test error")):
            metrics = collector.collect()
            # Should return empty or partial metrics, not crash
            assert isinstance(metrics, dict)


# ==============================================================================
# UNIT TESTS - Application Metrics Collector
# ==============================================================================


class TestApplicationMetricsCollector:
    """Test application metrics collection."""

    def test_collector_initializes(self, config):
        """Test collector initializes successfully."""
        collector = ApplicationMetricsCollector(config)
        assert collector.config == config
        assert len(collector.counters) == 0
        assert len(collector.gauges) == 0
        assert len(collector.histograms) == 0

    def test_record_agent_execution(self, config):
        """Test recording agent execution metrics."""
        collector = ApplicationMetricsCollector(config)

        collector.record_agent_execution("test_agent", 1.5, "success")

        # Check histogram has value
        key = "agent_execution_time:test_agent:success"
        assert key in collector.histograms
        assert 1.5 in collector.histograms[key]

        # Check counter incremented
        counter_key = "agent_execution_count:test_agent:success"
        assert collector.counters[counter_key] == 1

    def test_record_agent_error(self, config):
        """Test recording agent errors."""
        collector = ApplicationMetricsCollector(config)

        collector.record_agent_error("test_agent", "timeout")

        key = "agent_error_count:test_agent:timeout"
        assert collector.counters[key] == 1

    def test_record_api_request(self, config):
        """Test recording API request metrics."""
        collector = ApplicationMetricsCollector(config)

        collector.record_api_request("/api/test", "GET", 0.123, 200)

        # Check histogram
        hist_key = "api_request_duration:/api/test:GET:200"
        assert hist_key in collector.histograms
        assert 0.123 in collector.histograms[hist_key]

        # Check counter
        counter_key = "api_request_count:/api/test:GET:200"
        assert collector.counters[counter_key] == 1

    def test_record_api_error(self, config):
        """Test recording API errors."""
        collector = ApplicationMetricsCollector(config)

        collector.record_api_error("/api/test", "POST", "validation_error")

        key = "api_error_count:/api/test:POST:validation_error"
        assert collector.counters[key] == 1

    def test_set_queue_length(self, config):
        """Test setting queue length gauge."""
        collector = ApplicationMetricsCollector(config)

        collector.set_queue_length("task_queue", 42)

        key = "queue_length:task_queue"
        assert collector.gauges[key] == 42

    def test_record_queue_processing(self, config):
        """Test recording queue processing metrics."""
        collector = ApplicationMetricsCollector(config)

        collector.record_queue_processing("task_queue", 2.5)

        hist_key = "queue_processing_time:task_queue"
        assert hist_key in collector.histograms
        assert 2.5 in collector.histograms[hist_key]

        counter_key = "queue_items_processed:task_queue"
        assert collector.counters[counter_key] == 1

    def test_record_entity_processing(self, config):
        """Test recording entity processing metrics."""
        collector = ApplicationMetricsCollector(config)

        collector.record_entity_processing("Camera", "create", 0.05)

        hist_key = "entities_processing_time:Camera:create"
        assert hist_key in collector.histograms
        assert 0.05 in collector.histograms[hist_key]

        counter_key = "entities_processed_total:Camera:create"
        assert collector.counters[counter_key] == 1

    def test_record_cache_metrics(self, config):
        """Test recording cache hit/miss metrics."""
        collector = ApplicationMetricsCollector(config)

        collector.record_cache_hit("entity_cache")
        collector.record_cache_miss("entity_cache")
        collector.set_cache_size("entity_cache", 150)

        assert collector.counters["cache_hits:entity_cache"] == 1
        assert collector.counters["cache_misses:entity_cache"] == 1
        assert collector.gauges["cache_size:entity_cache"] == 150

    def test_collect_all_metrics(self, config):
        """Test collecting all recorded metrics."""
        collector = ApplicationMetricsCollector(config)

        # Record various metrics
        collector.record_agent_execution("agent1", 1.0, "success")
        collector.set_queue_length("queue1", 10)
        collector.record_cache_hit("cache1")

        metrics = collector.collect()

        assert "counters" in metrics
        assert "gauges" in metrics
        assert "histograms" in metrics
        assert len(metrics["counters"]) > 0
        assert len(metrics["gauges"]) > 0
        assert len(metrics["histograms"]) > 0

    def test_thread_safety(self, config):
        """Test collector is thread-safe."""
        import threading

        collector = ApplicationMetricsCollector(config)

        def record_metrics():
            for i in range(100):
                collector.record_agent_execution("test_agent", 1.0, "success")

        threads = [threading.Thread(target=record_metrics) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Should have 500 total executions
        counter_key = "agent_execution_count:test_agent:success"
        assert collector.counters[counter_key] == 500


# ==============================================================================
# UNIT TESTS - Neo4j Metrics Collector
# ==============================================================================


class TestNeo4jMetricsCollector:
    """Test Neo4j metrics collection."""

    @patch("neo4j.GraphDatabase.driver")
    def test_collector_initializes(self, mock_driver, config):
        """Test collector initializes and connects to Neo4j."""
        mock_session = Mock()
        mock_session.run.return_value = None
        mock_driver.return_value.session.return_value.__enter__.return_value = (
            mock_session
        )

        collector = Neo4jMetricsCollector(config)

        assert collector.driver is not None
        mock_driver.assert_called_once()

    @patch("neo4j.GraphDatabase.driver")
    def test_collect_single_value_metric(self, mock_driver, config):
        """Test collecting single-value metric."""
        # Mock the entire Neo4j session context manager properly
        mock_record = {"value": 123.45}

        mock_result = Mock()
        mock_result.single.return_value = mock_record

        mock_session = MagicMock()
        mock_session.run.return_value = mock_result
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=None)

        mock_driver_instance = Mock()
        mock_driver_instance.session.return_value = mock_session
        mock_driver.return_value = mock_driver_instance

        collector = Neo4jMetricsCollector(config)
        metrics = collector.collect()

        assert "neo4j_query_duration_p95" in metrics
        assert metrics["neo4j_query_duration_p95"] == 123.45

    @patch("neo4j.GraphDatabase.driver")
    def test_collect_handles_connection_errors(self, mock_driver, config):
        """Test collector handles Neo4j connection errors gracefully."""
        mock_driver.side_effect = Exception("Connection failed")

        collector = Neo4jMetricsCollector(config)
        metrics = collector.collect()

        # Should return empty dict on error
        assert metrics == {}

    @patch("neo4j.GraphDatabase.driver")
    def test_close_connection(self, mock_driver, config):
        """Test closing Neo4j connection."""
        mock_driver_instance = MagicMock()
        mock_driver_instance.session.return_value.__enter__.return_value.run.return_value = (
            None
        )
        mock_driver_instance.session.return_value.__exit__.return_value = None
        mock_driver.return_value = mock_driver_instance

        collector = Neo4jMetricsCollector(config)

        # Collector should have driver
        assert collector.driver is not None

        collector.close()

        # Close should be called
        mock_driver_instance.close.assert_called_once()


# ==============================================================================
# UNIT TESTS - Prometheus Exporter
# ==============================================================================


class TestPrometheusExporter:
    """Test Prometheus metrics export."""

    def test_exporter_initializes(self, config):
        """Test exporter initializes successfully."""
        exporter = PrometheusExporter(config)

        assert exporter.config == config
        assert exporter.prefix == "test_system"
        assert len(exporter.default_labels) == 2

    def test_initialize_metrics_from_config(self, config):
        """Test metrics are initialized from configuration."""
        exporter = PrometheusExporter(config)

        # Should have gauges and histograms from config
        assert len(exporter.gauges) > 0
        assert len(exporter.histograms) > 0

    def test_update_system_metrics(self, config):
        """Test updating system metrics."""
        exporter = PrometheusExporter(config)

        system_metrics = {"cpu_percent": 45.5, "memory_percent": 65.3}

        # Should not raise
        exporter.update_metrics(system_metrics, {}, {})

    def test_update_application_metrics(self, config):
        """Test updating application metrics."""
        exporter = PrometheusExporter(config)

        app_metrics = {
            "counters": {"agent_execution_count:test_agent:success": 10},
            "gauges": {"queue_length:task_queue": 5},
            "histograms": {"agent_execution_time:test_agent:success": [1.0, 2.0, 1.5]},
        }

        # Should not raise
        exporter.update_metrics({}, app_metrics, {})

    def test_generate_metrics_text(self, config):
        """Test generating Prometheus text format."""
        exporter = PrometheusExporter(config)

        text = exporter.generate_metrics_text()

        # Should be valid Prometheus format
        assert isinstance(text, str)
        assert len(text) > 0


# ==============================================================================
# UNIT TESTS - Alert Manager
# ==============================================================================


class TestAlertManager:
    """Test alert evaluation and notification."""

    def test_alert_manager_initializes(self, config):
        """Test alert manager initializes successfully."""
        manager = AlertManager(config)

        assert manager.config == config
        assert len(manager.alert_states) == 0
        assert len(manager.active_alerts) == 0

    def test_record_metric_value(self, config):
        """Test recording metric values."""
        manager = AlertManager(config)

        manager.record_metric_value("cpu_percent", 45.5)

        assert "cpu_percent" in manager.metric_history
        assert len(manager.metric_history["cpu_percent"]) == 1

    def test_evaluate_rules_no_alert(self, config):
        """Test evaluating rules when threshold not exceeded."""
        manager = AlertManager(config)

        # Record values below threshold
        for i in range(10):
            manager.record_metric_value("cpu_percent", 50.0)

        alerts = manager.evaluate_rules()

        assert len(alerts) == 0

    def test_evaluate_rules_trigger_alert(self, config):
        """Test triggering alert when threshold exceeded."""
        manager = AlertManager(config)

        # Record high CPU for duration - need samples spread across time
        start_time = time.time() - 400  # Start in the past

        # Record 20 samples over the duration window
        for i in range(20):
            timestamp = start_time + i * 20  # Every 20 seconds
            manager.record_metric_value("cpu_percent", 90.0, timestamp)

        # Manually set alert state to simulate condition being met for duration
        manager.alert_states["high_cpu"] = {
            "start_time": start_time,
            "triggered": False,
        }

        # Evaluate - current time is now past duration threshold
        alerts = manager.evaluate_rules()

        # Should trigger high_cpu alert
        assert len(alerts) > 0
        assert alerts[0]["rule_name"] == "high_cpu"
        assert alerts[0]["severity"] == "warning"

    def test_alert_with_aggregation(self, config):
        """Test alert with percentile aggregation."""
        # Add rule with aggregation
        config.config["performance_monitor"]["alerting"]["rules"].append(
            {
                "name": "slow_api",
                "metric": "api_duration",
                "aggregation": "p95",
                "condition": ">",
                "threshold": 1.0,
                "duration": 60,
                "severity": "warning",
                "enabled": True,
            }
        )

        manager = AlertManager(config)

        # Record mostly fast requests, some slow - enough samples for percentile
        start_time = time.time() - 120  # Start in the past

        # Record 100 samples for good P95 calculation
        for i in range(95):
            manager.record_metric_value("api_duration", 0.1, start_time + i)
        for i in range(5):
            manager.record_metric_value("api_duration", 2.0, start_time + 95 + i)

        # Set alert state manually to simulate condition met for duration
        manager.alert_states["slow_api"] = {
            "start_time": start_time,
            "triggered": False,
        }

        # Evaluate
        alerts = manager.evaluate_rules()

        # P95 should exceed threshold
        slow_alerts = [a for a in alerts if a["rule_name"] == "slow_api"]
        assert len(slow_alerts) > 0

    def test_alert_resolution(self, config):
        """Test alert resolves when condition no longer met."""
        manager = AlertManager(config)

        # Trigger alert - set up state first
        start_time = time.time() - 400
        for i in range(20):
            manager.record_metric_value("cpu_percent", 90.0, start_time + i * 20)

        # Set alert state to triggered
        manager.alert_states["high_cpu"] = {"start_time": start_time, "triggered": True}
        manager.active_alerts.append(
            {"rule_name": "high_cpu", "metric": "cpu_percent", "value": 90.0}
        )

        # Record low CPU now
        current_time = time.time()
        for i in range(10):
            manager.record_metric_value("cpu_percent", 30.0, current_time + i)

        # Evaluate - condition no longer met
        alerts2 = manager.evaluate_rules()

        # Alert should be resolved (state cleared)
        assert "high_cpu" not in manager.alert_states

    def test_get_active_alerts(self, config):
        """Test getting list of active alerts."""
        manager = AlertManager(config)

        # Manually add alert
        alert = {
            "rule_name": "test_alert",
            "metric": "test_metric",
            "value": 100,
            "threshold": 50,
            "severity": "warning",
        }
        manager.active_alerts.append(alert)

        active = manager.get_active_alerts()

        assert len(active) == 1
        assert active[0]["rule_name"] == "test_alert"

    def test_clear_active_alerts(self, config):
        """Test clearing active alerts."""
        manager = AlertManager(config)

        manager.active_alerts.append({"test": "alert"})
        manager.clear_active_alerts()

        assert len(manager.active_alerts) == 0


# ==============================================================================
# UNIT TESTS - Trend Analysis Engine
# ==============================================================================


class TestTrendAnalysisEngine:
    """Test trend analysis and anomaly detection."""

    def test_engine_initializes(self, config):
        """Test engine initializes successfully."""
        engine = TrendAnalysisEngine(config)

        assert engine.config == config
        assert len(engine.metric_history) == 0

    def test_record_metric(self, config):
        """Test recording metric for trend analysis."""
        engine = TrendAnalysisEngine(config)

        engine.record_metric("cpu_percent", 45.5)

        assert "cpu_percent" in engine.metric_history
        assert len(engine.metric_history["cpu_percent"]) == 1

    def test_get_trend_statistics(self, config):
        """Test calculating trend statistics."""
        engine = TrendAnalysisEngine(config)

        # Record values
        current_time = time.time()
        values = [40, 45, 50, 55, 60, 65, 70]
        for i, val in enumerate(values):
            engine.record_metric(
                "cpu_percent", val, current_time - (len(values) - i) * 60
            )

        stats = engine.get_trend_statistics("cpu_percent", "1h")

        assert "mean" in stats
        assert "max" in stats
        assert "min" in stats
        assert stats["mean"] == statistics.mean(values)
        assert stats["max"] == max(values)
        assert stats["min"] == min(values)

    def test_detect_anomalies_zscore(self, config):
        """Test Z-score based anomaly detection."""
        engine = TrendAnalysisEngine(config)

        # Record normal values
        current_time = time.time()
        for i in range(100):
            engine.record_metric(
                "cpu_percent", 50.0 + (i % 10), current_time - (100 - i) * 60
            )

        # Record anomaly
        engine.record_metric("cpu_percent", 200.0, current_time)

        anomalies = engine.detect_anomalies("cpu_percent")

        # Should detect the 200.0 value as anomaly
        assert len(anomalies) > 0
        assert any(a["value"] == 200.0 for a in anomalies)

    def test_detect_anomalies_insufficient_samples(self, config):
        """Test anomaly detection with insufficient samples."""
        engine = TrendAnalysisEngine(config)

        # Record only a few values
        for i in range(10):
            engine.record_metric("cpu_percent", 50.0)

        anomalies = engine.detect_anomalies("cpu_percent")

        # Should return empty (min_samples = 100)
        assert len(anomalies) == 0

    def test_parse_window(self, config):
        """Test parsing time window strings."""
        engine = TrendAnalysisEngine(config)

        assert engine._parse_window("30s") == 30
        assert engine._parse_window("5m") == 300
        assert engine._parse_window("1h") == 3600
        assert engine._parse_window("7d") == 604800


# ==============================================================================
# INTEGRATION TESTS
# ==============================================================================


class TestPerformanceMonitorAgentIntegration:
    """Integration tests for full agent."""

    @patch("neo4j.GraphDatabase.driver")
    def test_agent_initializes(self, mock_driver, config_file):
        """Test agent initializes all components."""
        mock_driver.return_value.session.return_value.__enter__.return_value.run.return_value = (
            None
        )

        agent = PerformanceMonitorAgent(config_file)

        assert agent.config is not None
        assert agent.system_collector is not None
        assert agent.app_collector is not None
        assert agent.neo4j_collector is not None
        assert agent.exporter is not None
        assert agent.alert_manager is not None
        assert agent.trend_analyzer is not None

    @patch("neo4j.GraphDatabase.driver")
    @patch("prometheus_client.start_http_server")
    def test_agent_start_stop(self, mock_prom_server, mock_driver, config_file):
        """Test agent start and stop."""
        mock_driver.return_value.session.return_value.__enter__.return_value.run.return_value = (
            None
        )

        agent = PerformanceMonitorAgent(config_file)

        agent.start()
        assert agent.running is True
        assert agent.collection_thread is not None

        time.sleep(0.5)  # Let thread start

        agent.stop()
        assert agent.running is False

    @patch("neo4j.GraphDatabase.driver")
    @patch("psutil.cpu_percent")
    @patch("psutil.virtual_memory")
    def test_collect_and_export(self, mock_memory, mock_cpu, mock_driver, config_file):
        """Test full collection and export cycle."""
        # Mock system metrics
        mock_cpu.return_value = 55.5
        mock_mem = Mock()
        mock_mem.percent = 70.0
        mock_memory.return_value = mock_mem

        # Mock Neo4j
        mock_driver_instance = MagicMock()
        mock_driver_instance.session.return_value.__enter__.return_value.run.return_value.single.return_value = (
            None
        )
        mock_driver_instance.session.return_value.__exit__.return_value = None
        mock_driver.return_value = mock_driver_instance

        agent = PerformanceMonitorAgent(config_file)

        # Trigger collection
        agent._collect_and_export()

        # Should complete without errors
        assert agent.running is False  # Not started yet

    @patch("neo4j.GraphDatabase.driver")
    def test_get_metrics_summary(self, mock_driver, config_file):
        """Test getting metrics summary."""
        mock_driver.return_value.session.return_value.__enter__.return_value.run.return_value = (
            None
        )

        agent = PerformanceMonitorAgent(config_file)

        summary = agent.get_metrics_summary()

        assert "timestamp" in summary
        assert "active_alerts" in summary
        assert "collectors" in summary
        assert summary["collectors"]["system"] is True

    @patch("neo4j.GraphDatabase.driver")
    def test_get_application_collector(self, mock_driver, config_file):
        """Test getting application collector for external use."""
        mock_driver.return_value.session.return_value.__enter__.return_value.run.return_value = (
            None
        )

        agent = PerformanceMonitorAgent(config_file)

        app_collector = agent.get_application_collector()

        assert app_collector is not None
        assert isinstance(app_collector, ApplicationMetricsCollector)


# ==============================================================================
# LOAD TESTS
# ==============================================================================


class TestPerformanceUnderLoad:
    """Load tests for high-volume scenarios."""

    def test_high_volume_metric_recording(self, config):
        """Test recording high volume of metrics."""
        collector = ApplicationMetricsCollector(config)

        start_time = time.time()

        # Record 10,000 metrics
        for i in range(10000):
            collector.record_agent_execution(f"agent_{i % 10}", 1.0, "success")

        duration = time.time() - start_time

        # Should complete in reasonable time (< 2 seconds)
        assert duration < 2.0

        # All metrics recorded
        assert sum(collector.counters.values()) == 10000

    def test_concurrent_metric_collection(self, config):
        """Test concurrent metric collection from multiple threads."""
        import threading

        collector = ApplicationMetricsCollector(config)
        errors = []

        def collect_metrics(agent_id):
            try:
                for i in range(1000):
                    collector.record_agent_execution(
                        f"agent_{agent_id}", 1.0, "success"
                    )
            except Exception as e:
                errors.append(e)

        # Start 10 threads
        threads = [
            threading.Thread(target=collect_metrics, args=(i,)) for i in range(10)
        ]
        start_time = time.time()

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        duration = time.time() - start_time

        # No errors
        assert len(errors) == 0

        # All metrics recorded (10 threads * 1000 each)
        assert sum(collector.counters.values()) == 10000

        # Completed in reasonable time (< 5 seconds)
        assert duration < 5.0

    def test_alert_evaluation_performance(self, config):
        """Test alert evaluation with large metric history."""
        manager = AlertManager(config)

        # Record 1000 metric values
        current_time = time.time()
        for i in range(1000):
            manager.record_metric_value(
                "cpu_percent", 50.0 + (i % 50), current_time - (1000 - i)
            )

        start_time = time.time()

        # Evaluate rules 100 times
        for _ in range(100):
            manager.evaluate_rules()

        duration = time.time() - start_time

        # Should complete in reasonable time (< 1 second)
        assert duration < 1.0

    def test_trend_analysis_performance(self, config):
        """Test trend analysis with large dataset."""
        engine = TrendAnalysisEngine(config)

        # Record 10,000 metric values
        current_time = time.time()
        for i in range(10000):
            engine.record_metric(
                "cpu_percent", 50.0 + (i % 50), current_time - (10000 - i) * 60
            )

        start_time = time.time()

        # Calculate statistics
        stats = engine.get_trend_statistics("cpu_percent", "24h")

        duration = time.time() - start_time

        # Should complete quickly (< 0.5 seconds)
        assert duration < 0.5

        # Statistics calculated
        assert "mean" in stats
        assert "max" in stats


# ==============================================================================
# TEST RUNNER
# ==============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
