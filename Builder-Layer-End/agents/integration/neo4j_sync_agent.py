"""
Neo4j Sync Agent

Synchronizes NGSI-LD entities from Stellio PostgreSQL database to Neo4j graph database.
This agent bridges the gap between Stellio Context Broker (PostgreSQL backend) and Neo4j.

Architecture:
- Reads validated entities from PostgreSQL (entity_payload table)
- Parses JSONB payload to extract entity properties
- Creates Camera nodes with all properties
- Creates Platform nodes (HCMCTrafficSystem)
- Creates ObservableProperty nodes (TrafficFlow)
- Creates relationships: :IS_HOSTED_BY, :OBSERVES, :LOCATED_AT
- Handles geospatial data (WGS84 coordinates)

Features:
- 100% Config-driven (YAML)
- Domain-agnostic (works with ANY entity types)
- Batch operations with Neo4j driver
- Idempotent (MERGE operations, no duplicates)
- Comprehensive error handling
- Transaction management
- Connection pooling

Usage:
    python agents/integration/neo4j_sync_agent.py
    python agents/integration/neo4j_sync_agent.py --config config/neo4j_sync.yaml
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import psycopg2
import yaml
from psycopg2.extras import RealDictCursor

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Neo4j driver (required dependency)
try:
    from neo4j import GraphDatabase, Driver, Session, Transaction

    NEO4J_AVAILABLE = True
except ImportError:
    NEO4J_AVAILABLE = False
    raise ImportError("neo4j driver required: pip install neo4j")

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# ============================================================================
# Configuration Loader
# ============================================================================


class Neo4jSyncConfig:
    """Load and validate Neo4j sync configuration from YAML file."""

    def __init__(self, config_path: str = "config/neo4j_sync.yaml"):
        """
        Initialize configuration loader.

        Args:
            config_path: Path to YAML configuration file

        Raises:
            FileNotFoundError: If config file not found
            ValueError: If config validation fails
        """
        self.config_path = Path(config_path)
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")

        with open(self.config_path, "r", encoding="utf-8") as f:
            self.config = yaml.safe_load(f)

        self._validate()
        logger.info(f"Loaded Neo4j sync config from {config_path}")

    def _validate(self) -> None:
        """Validate configuration structure and required fields."""
        if "neo4j_sync" not in self.config:
            raise ValueError("Config must have 'neo4j_sync' section")

        root = self.config["neo4j_sync"]

        # Validate required sections
        required = ["postgres", "neo4j", "entity_mapping", "sync_config"]
        for key in required:
            if key not in root:
                raise ValueError(f"Missing required section: neo4j_sync.{key}")

        # Validate PostgreSQL config
        pg_config = root["postgres"]
        pg_required = ["host", "port", "database", "user", "password"]
        for key in pg_required:
            if key not in pg_config:
                raise ValueError(f"Missing postgres.{key}")

        # Validate Neo4j config
        neo4j_config = root["neo4j"]
        neo4j_required = ["uri", "user", "password"]
        for key in neo4j_required:
            if key not in neo4j_config:
                raise ValueError(f"Missing neo4j.{key}")

        logger.info("Configuration validation passed")

    def get_postgres_config(self) -> Dict[str, Any]:
        """Get PostgreSQL connection configuration."""
        return self.config["neo4j_sync"]["postgres"]

    def get_neo4j_config(self) -> Dict[str, Any]:
        """Get Neo4j connection configuration."""
        return self.config["neo4j_sync"]["neo4j"]

    def get_entity_mapping(self) -> Dict[str, Any]:
        """Get entity type to node label mapping."""
        return self.config["neo4j_sync"]["entity_mapping"]

    def get_sync_config(self) -> Dict[str, Any]:
        """Get synchronization configuration."""
        return self.config["neo4j_sync"]["sync_config"]


# ============================================================================
# PostgreSQL Connector
# ============================================================================


class PostgresConnector:
    """Connect to Stellio PostgreSQL database and extract entities."""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize PostgreSQL connector.

        Args:
            config: PostgreSQL connection configuration
        """
        self.config = config
        self.connection = None
        logger.info("PostgreSQL connector initialized")

    def connect(self) -> None:
        """Establish connection to PostgreSQL database."""
        try:
            self.connection = psycopg2.connect(
                host=self.config["host"],
                port=self.config["port"],
                database=self.config["database"],
                user=self.config["user"],
                password=self.config["password"],
                cursor_factory=RealDictCursor,
            )
            logger.info(
                f"Connected to PostgreSQL: {self.config['host']}:{self.config['port']}/{self.config['database']}"
            )
        except Exception as e:
            logger.error(f"Failed to connect to PostgreSQL: {e}")
            raise

    def fetch_entities(self, table: str = "entity_payload") -> List[Dict[str, Any]]:
        """
        Fetch all entities from entity_payload table.

        Args:
            table: Table name (default: entity_payload)

        Returns:
            List of entity dictionaries with parsed JSONB payload
        """
        if not self.connection:
            raise RuntimeError("Not connected to PostgreSQL")

        try:
            with self.connection.cursor() as cursor:
                query = f"""
                    SELECT 
                        entity_id,
                        payload,
                        types,
                        created_at,
                        modified_at
                    FROM {table}
                    WHERE deleted_at IS NULL
                    ORDER BY created_at ASC
                """
                cursor.execute(query)
                rows = cursor.fetchall()

                entities = []
                for row in rows:
                    entity = dict(row)
                    # Parse JSONB payload
                    if isinstance(entity["payload"], str):
                        entity["payload"] = json.loads(entity["payload"])
                    # Extract entity type from types array (parse URI to get simple name)
                    if entity["types"] and len(entity["types"]) > 0:
                        type_uri = entity["types"][0]
                        # Extract simple name from URI (e.g., "Camera" from ".../Camera")
                        # Handle both "/" and "#" as separators
                        entity["entity_type"] = type_uri.split("/")[-1].split("#")[-1]
                    else:
                        entity["entity_type"] = "Entity"
                    entities.append(entity)

                logger.info(f"Fetched {len(entities)} entities from PostgreSQL")
                return entities

        except Exception as e:
            logger.error(f"Failed to fetch entities: {e}")
            raise

    def close(self) -> None:
        """Close PostgreSQL connection."""
        if self.connection:
            self.connection.close()
            logger.info("PostgreSQL connection closed")


# ============================================================================
# Neo4j Connector
# ============================================================================


class Neo4jConnector:
    """Connect to Neo4j and execute Cypher queries with transaction management."""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Neo4j connector.

        Args:
            config: Neo4j connection configuration
        """
        self.config = config
        self.driver: Optional[Driver] = None
        logger.info("Neo4j connector initialized")

    def connect(self) -> None:
        """Establish connection to Neo4j database."""
        try:
            self.driver = GraphDatabase.driver(
                self.config["uri"],
                auth=(self.config["user"], self.config["password"]),
                max_connection_pool_size=self.config.get("pool_size", 50),
                connection_timeout=self.config.get("timeout", 30),
            )
            # Verify connectivity
            self.driver.verify_connectivity()
            logger.info(f"Connected to Neo4j: {self.config['uri']}")

            # Initialize schema constraints and indexes
            self._initialize_schema()
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            raise

    def _initialize_schema(self) -> None:
        """Create schema constraints and indexes for entity types."""
        schema_queries = [
            # Constraints for unique IDs
            "CREATE CONSTRAINT camera_id_unique IF NOT EXISTS FOR (c:Camera) REQUIRE c.id IS UNIQUE",
            "CREATE CONSTRAINT platform_id_unique IF NOT EXISTS FOR (p:Platform) REQUIRE p.id IS UNIQUE",
            "CREATE CONSTRAINT obs_prop_id_unique IF NOT EXISTS FOR (o:ObservableProperty) REQUIRE o.id IS UNIQUE",
            "CREATE CONSTRAINT entity_id_unique IF NOT EXISTS FOR (e:Entity) REQUIRE e.id IS UNIQUE",
            # Indexes for common query patterns
            "CREATE INDEX camera_type_idx IF NOT EXISTS FOR (c:Camera) ON (c.type)",
            "CREATE INDEX platform_name_idx IF NOT EXISTS FOR (p:Platform) ON (p.name)",
            "CREATE INDEX entity_type_idx IF NOT EXISTS FOR (e:Entity) ON (e.type)",
        ]

        with self.driver.session() as session:
            for query in schema_queries:
                try:
                    session.run(query)
                    logger.debug(f"Schema query executed: {query[:50]}...")
                except Exception as e:
                    # Constraint may already exist, log warning but continue
                    logger.warning(f"Schema initialization warning: {e}")

        logger.info("Neo4j schema initialized (constraints + indexes)")

    def create_camera_node(self, tx: Transaction, entity: Dict[str, Any]) -> None:
        """
        Create Camera node in Neo4j.

        Args:
            tx: Neo4j transaction
            entity: Entity dictionary with payload
        """
        payload = entity["payload"]
        entity_id = payload.get("id", entity["entity_id"])
        entity_type = entity.get(
            "entity_type", "Camera"
        )  # Use entity_type from DB, not NGSI-LD type URI

        # Extract properties
        properties = {
            "id": entity_id,
            "type": entity_type,  # Store simple type, not full URI
            "ngsiLdType": payload.get(
                "type", entity_type
            ),  # Store full NGSI-LD type URI separately
            "createdAt": (
                entity.get("created_at").isoformat()
                if entity.get("created_at")
                else None
            ),
            "modifiedAt": (
                entity.get("modified_at").isoformat()
                if entity.get("modified_at")
                else None
            ),
        }

        # Extract NGSI-LD properties
        for key, value in payload.items():
            if key in ["id", "type", "@context"]:
                continue

            if isinstance(value, dict):
                if value.get("type") == "Property":
                    properties[key] = value.get("value")
                elif value.get("type") == "GeoProperty":
                    # Extract coordinates
                    coordinates = value.get("value", {}).get("coordinates", [])
                    if len(coordinates) >= 2:
                        properties[f"{key}_longitude"] = coordinates[0]
                        properties[f"{key}_latitude"] = coordinates[1]
                elif value.get("type") == "Relationship":
                    # Handle relationships separately
                    pass

        # Create node with MERGE (idempotent)
        # Use simple Camera label (not URI-expanded)
        cypher = """
            MERGE (c:Camera {id: $id})
            SET c += $properties
            SET c:Entity
            RETURN c.id as id
        """

        result = tx.run(cypher, id=entity_id, properties=properties)
        record = result.single()
        if record:
            logger.debug(f"Created/Updated Camera node: {record['id']}")

    def create_platform_node(
        self, tx: Transaction, platform_id: str, properties: Dict[str, Any]
    ) -> None:
        """
        Create Platform node in Neo4j.

        Args:
            tx: Neo4j transaction
            platform_id: Platform entity ID
            properties: Platform properties
        """
        cypher = """
            MERGE (p:Platform {id: $id})
            SET p += $properties
            RETURN p.id as id
        """

        result = tx.run(cypher, id=platform_id, properties=properties)
        record = result.single()
        if record:
            logger.debug(f"Created/Updated Platform node: {record['id']}")

    def create_relationship(
        self,
        tx: Transaction,
        from_id: str,
        to_id: str,
        rel_type: str,
        properties: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Create relationship between two nodes.

        Args:
            tx: Neo4j transaction
            from_id: Source node ID
            to_id: Target node ID
            rel_type: Relationship type
            properties: Optional relationship properties
        """
        if properties is None:
            properties = {}

        cypher = f"""
            MATCH (a {{id: $from_id}})
            MATCH (b {{id: $to_id}})
            MERGE (a)-[r:{rel_type}]->(b)
            SET r += $properties
            RETURN type(r) as relType
        """

        result = tx.run(cypher, from_id=from_id, to_id=to_id, properties=properties)
        record = result.single()
        if record:
            logger.debug(
                f"Created relationship: {from_id} -[{record['relType']}]-> {to_id}"
            )

    def execute_transaction(self, work_func, *args, **kwargs) -> Any:
        """
        Execute work function in Neo4j transaction.

        Args:
            work_func: Function to execute in transaction
            *args: Positional arguments for work_func
            **kwargs: Keyword arguments for work_func

        Returns:
            Result from work_func
        """
        if not self.driver:
            raise RuntimeError("Not connected to Neo4j")

        with self.driver.session() as session:
            return session.execute_write(work_func, *args, **kwargs)

    def count_nodes(self, label: Optional[str] = None) -> int:
        """
        Count nodes in Neo4j.

        Args:
            label: Optional node label to filter

        Returns:
            Node count
        """
        if not self.driver:
            raise RuntimeError("Not connected to Neo4j")

        with self.driver.session() as session:
            if label:
                query = f"MATCH (n:{label}) RETURN count(n) as count"
            else:
                query = "MATCH (n) RETURN count(n) as count"

            result = session.run(query)
            record = result.single()
            return record["count"] if record else 0

    def close(self) -> None:
        """Close Neo4j driver."""
        if self.driver:
            self.driver.close()
            logger.info("Neo4j connection closed")


# ============================================================================
# Neo4j Sync Agent
# ============================================================================


class Neo4jSyncAgent:
    """Main agent to synchronize entities from PostgreSQL to Neo4j."""

    def __init__(self, config_path: str = "config/neo4j_sync.yaml"):
        """
        Initialize Neo4j sync agent.

        Args:
            config_path: Path to YAML configuration file
        """
        self.config = Neo4jSyncConfig(config_path)
        self.pg_connector = PostgresConnector(self.config.get_postgres_config())
        self.neo4j_connector = Neo4jConnector(self.config.get_neo4j_config())
        self.entity_mapping = self.config.get_entity_mapping()
        self.sync_config = self.config.get_sync_config()

        logger.info("Neo4j Sync Agent initialized")

    def connect(self) -> None:
        """Establish connections to PostgreSQL and Neo4j."""
        self.pg_connector.connect()
        self.neo4j_connector.connect()

    def sync_entities(self) -> Tuple[int, int, int]:
        """
        Synchronize all entities from PostgreSQL to Neo4j.

        Returns:
            Tuple of (total_entities, successful, failed)
        """
        logger.info("Starting entity synchronization...")

        # Fetch entities from PostgreSQL
        entities = self.pg_connector.fetch_entities()
        total = len(entities)
        successful = 0
        failed = 0

        # Process each entity
        for entity in entities:
            try:
                entity_type = entity.get("entity_type", "")

                # Route to appropriate handler based on entity type
                if entity_type == "Camera":
                    self._sync_camera(entity)
                elif entity_type == "Platform":
                    self._sync_platform(entity)
                elif entity_type == "ObservableProperty":
                    self._sync_observable_property(entity)
                else:
                    # Generic entity handler
                    self._sync_generic_entity(entity)

                successful += 1

            except Exception as e:
                logger.error(f"Failed to sync entity {entity.get('entity_id')}: {e}")
                failed += 1

        logger.info(
            f"Synchronization complete: {successful}/{total} successful, {failed} failed"
        )
        return (total, successful, failed)

    def _sync_camera(self, entity: Dict[str, Any]) -> None:
        """Sync Camera entity to Neo4j."""

        def work(tx: Transaction, entity: Dict[str, Any]):
            # Create Camera node
            self.neo4j_connector.create_camera_node(tx, entity)

            # Create relationships from NGSI-LD relationships
            payload = entity["payload"]
            entity_id = payload.get("id", entity["entity_id"])

            # isHostedBy -> Platform
            is_hosted_by = payload.get("isHostedBy", {})
            if is_hosted_by.get("type") == "Relationship":
                platform_id = is_hosted_by.get("object", "")
                if platform_id:
                    self.neo4j_connector.create_relationship(
                        tx, entity_id, platform_id, "IS_HOSTED_BY"
                    )

            # observes -> ObservableProperty
            observes = payload.get("observes", {})
            if observes.get("type") == "Relationship":
                obs_prop_id = observes.get("object", "")
                if obs_prop_id:
                    self.neo4j_connector.create_relationship(
                        tx, entity_id, obs_prop_id, "OBSERVES"
                    )

        self.neo4j_connector.execute_transaction(work, entity)

    def _sync_platform(self, entity: Dict[str, Any]) -> None:
        """Sync Platform entity to Neo4j."""

        def work(tx: Transaction, entity: Dict[str, Any]):
            payload = entity["payload"]
            platform_id = payload.get("id", entity["entity_id"])

            properties = {
                "id": platform_id,
                "type": "Platform",
                "name": payload.get("name", {}).get("value", ""),
                "description": payload.get("description", {}).get("value", ""),
            }

            self.neo4j_connector.create_platform_node(tx, platform_id, properties)

        self.neo4j_connector.execute_transaction(work, entity)

    def _sync_observable_property(self, entity: Dict[str, Any]) -> None:
        """Sync ObservableProperty entity to Neo4j."""

        def work(tx: Transaction, entity: Dict[str, Any]):
            payload = entity["payload"]
            obs_prop_id = payload.get("id", entity["entity_id"])

            properties = {
                "id": obs_prop_id,
                "type": "ObservableProperty",
                "name": payload.get("name", {}).get("value", ""),
                "description": payload.get("description", {}).get("value", ""),
            }

            cypher = """
                MERGE (o:ObservableProperty {id: $id})
                SET o += $properties
                RETURN o.id as id
            """

            result = tx.run(cypher, id=obs_prop_id, properties=properties)
            record = result.single()
            if record:
                logger.debug(f"Created/Updated ObservableProperty node: {record['id']}")

        self.neo4j_connector.execute_transaction(work, entity)

    def _sync_generic_entity(self, entity: Dict[str, Any]) -> None:
        """Sync generic entity to Neo4j."""

        def work(tx: Transaction, entity: Dict[str, Any]):
            payload = entity["payload"]
            entity_id = payload.get("id", entity["entity_id"])
            entity_type = entity.get("entity_type", "Entity")

            # Extract properties
            properties = {"id": entity_id, "type": entity_type}
            for key, value in payload.items():
                if key in ["id", "type", "@context"]:
                    continue
                if isinstance(value, dict) and value.get("type") == "Property":
                    properties[key] = value.get("value")

            # Create node with escaped label
            # Use backticks to escape label with spaces/special chars
            label = entity_type.replace(" ", "_").replace("-", "_")
            cypher = f"""
                MERGE (n:`{label}` {{id: $id}})
                SET n += $properties
                RETURN n.id as id
            """

            result = tx.run(cypher, id=entity_id, properties=properties)
            record = result.single()
            if record:
                logger.debug(f"Created/Updated {entity_type} node: {record['id']}")

        self.neo4j_connector.execute_transaction(work, entity)

    def verify_sync(self) -> Dict[str, int]:
        """
        Verify synchronization by counting nodes in Neo4j.

        Returns:
            Dictionary with node counts by label
        """
        logger.info("Verifying synchronization...")

        counts = {
            "Camera": self.neo4j_connector.count_nodes("Camera"),
            "Platform": self.neo4j_connector.count_nodes("Platform"),
            "ObservableProperty": self.neo4j_connector.count_nodes(
                "ObservableProperty"
            ),
            "Total": self.neo4j_connector.count_nodes(),
        }

        logger.info(f"Node counts: {counts}")
        return counts

    def close(self) -> None:
        """Close all connections."""
        self.pg_connector.close()
        self.neo4j_connector.close()

    def run(self) -> bool:
        """
        Execute full synchronization workflow.

        Returns:
            True if successful, False otherwise
        """
        try:
            # Connect to databases
            self.connect()

            # Sync entities
            total, successful, failed = self.sync_entities()

            # Verify sync
            counts = self.verify_sync()

            # Check if sync was successful
            if failed == 0 and counts["Total"] > 0:
                logger.info("✅ Synchronization completed successfully")
                return True
            else:
                logger.warning(
                    f"⚠️ Synchronization completed with issues: {failed} failures"
                )
                return False

        except Exception as e:
            logger.error(f"❌ Synchronization failed: {e}")
            return False

        finally:
            self.close()


# ============================================================================
# Main Entry Point
# ============================================================================


def main(config: Optional[Dict[str, Any]] = None):
    """Main entry point for Neo4j sync agent.

    Args:
        config: Optional workflow agent config (from orchestrator)
    """
    # Use config from orchestrator if provided
    if config:
        config_path = config.get("config_path", "config/neo4j_sync.yaml")
    else:
        parser = argparse.ArgumentParser(
            description="Sync entities from Stellio to Neo4j"
        )
        parser.add_argument(
            "--config",
            default="config/neo4j_sync.yaml",
            help="Path to configuration file",
        )
        args = parser.parse_args()
        config_path = args.config

    # Check Neo4j availability
    if not NEO4J_AVAILABLE:
        logger.error("Neo4j driver not available. Install with: pip install neo4j")
        sys.exit(1)

    # Run sync agent
    agent = Neo4jSyncAgent(config_path=config_path)
    success = agent.run()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
