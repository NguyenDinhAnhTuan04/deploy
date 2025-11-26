"""
Neo4j & Fuseki Data Access Examples

This script demonstrates how to query and use data from:
- Neo4j Graph Database (Camera nodes, relationships)
- Apache Jena Fuseki Triplestore (RDF triples, SPARQL)

Requirements:
    pip install neo4j SPARQLWrapper requests

Usage:
    python examples/data_access_examples.py
"""

from neo4j import GraphDatabase
from SPARQLWrapper import SPARQLWrapper, JSON
import json
from typing import List, Dict, Any


# ============================================================================
# NEO4J CONNECTION
# ============================================================================

class Neo4jConnector:
    """Connect to Neo4j and execute Cypher queries."""
    
    def __init__(self, uri: str = "bolt://localhost:7687", 
                 user: str = "neo4j", password: str = "test12345"):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        print(f"✅ Connected to Neo4j: {uri}")
    
    def run_query(self, query: str, parameters: Dict = None) -> List[Dict]:
        """Execute Cypher query and return results."""
        with self.driver.session() as session:
            result = session.run(query, parameters or {})
            return [record.data() for record in result]
    
    def close(self):
        """Close Neo4j driver."""
        self.driver.close()
        print("✅ Neo4j connection closed")


# ============================================================================
# FUSEKI CONNECTION
# ============================================================================

class FusekiConnector:
    """Connect to Fuseki and execute SPARQL queries."""
    
    def __init__(self, endpoint: str = "http://localhost:3030/lod-dataset/sparql",
                 user: str = "admin", password: str = "test_admin"):
        self.sparql = SPARQLWrapper(endpoint)
        self.sparql.setCredentials(user, password)
        self.sparql.setReturnFormat(JSON)
        print(f"✅ Connected to Fuseki: {endpoint}")
    
    def run_query(self, query: str) -> List[Dict]:
        """Execute SPARQL query and return results."""
        self.sparql.setQuery(query)
        results = self.sparql.query().convert()
        return results['results']['bindings']


# ============================================================================
# NEO4J EXAMPLES
# ============================================================================

def example_neo4j_count_nodes(neo4j: Neo4jConnector):
    """Example 1: Count total nodes in Neo4j."""
    print("\n" + "="*60)
    print("EXAMPLE 1: Count Total Nodes in Neo4j")
    print("="*60)
    
    query = """
    MATCH (n)
    RETURN count(n) as totalNodes
    """
    
    results = neo4j.run_query(query)
    total = results[0]['totalNodes']
    print(f"📊 Total nodes: {total}")


def example_neo4j_list_labels(neo4j: Neo4jConnector):
    """Example 2: List all node labels."""
    print("\n" + "="*60)
    print("EXAMPLE 2: List All Node Labels")
    print("="*60)
    
    query = """
    CALL db.labels()
    YIELD label
    RETURN label
    """
    
    results = neo4j.run_query(query)
    print("📋 Node labels:")
    for result in results:
        print(f"  - {result['label']}")


def example_neo4j_get_cameras(neo4j: Neo4jConnector):
    """Example 3: Get all Camera nodes."""
    print("\n" + "="*60)
    print("EXAMPLE 3: Get All Camera Nodes")
    print("="*60)
    
    query = """
    MATCH (c)
    WHERE c.type CONTAINS 'Camera'
    RETURN c.id as cameraId, properties(c) as props
    LIMIT 5
    """
    
    results = neo4j.run_query(query)
    print(f"📷 Found {len(results)} cameras:")
    for i, result in enumerate(results, 1):
        print(f"\n  Camera {i}:")
        print(f"    ID: {result['cameraId']}")
        print(f"    Properties: {json.dumps(result['props'], indent=6)}")


def example_neo4j_find_camera_by_id(neo4j: Neo4jConnector, camera_id: str):
    """Example 4: Find specific Camera by ID."""
    print("\n" + "="*60)
    print("EXAMPLE 4: Find Camera by ID")
    print("="*60)
    
    query = """
    MATCH (c)
    WHERE c.id = $camera_id
    RETURN c
    """
    
    results = neo4j.run_query(query, {'camera_id': camera_id})
    if results:
        camera = results[0]['c']
        print(f"📷 Camera found:")
        print(f"  ID: {camera.get('id')}")
        print(f"  Type: {camera.get('type')}")
        print(f"  All properties: {json.dumps(dict(camera), indent=4)}")
    else:
        print(f"❌ Camera not found: {camera_id}")


def example_neo4j_get_platform(neo4j: Neo4jConnector):
    """Example 5: Get Platform node."""
    print("\n" + "="*60)
    print("EXAMPLE 5: Get Platform Node")
    print("="*60)
    
    query = """
    MATCH (p)
    WHERE p.type CONTAINS 'Platform'
    RETURN p.id as platformId, properties(p) as props
    """
    
    results = neo4j.run_query(query)
    if results:
        print(f"🏢 Platform found:")
        for result in results:
            print(f"  ID: {result['platformId']}")
            print(f"  Properties: {json.dumps(result['props'], indent=4)}")
    else:
        print("❌ No Platform found")


def example_neo4j_get_relationships(neo4j: Neo4jConnector):
    """Example 6: Get all relationships."""
    print("\n" + "="*60)
    print("EXAMPLE 6: Get All Relationships")
    print("="*60)
    
    query = """
    MATCH (a)-[r]->(b)
    RETURN type(r) as relType, 
           a.id as fromNode, 
           b.id as toNode
    LIMIT 10
    """
    
    results = neo4j.run_query(query)
    if results:
        print(f"🔗 Found {len(results)} relationships:")
        for i, result in enumerate(results, 1):
            print(f"  {i}. {result['fromNode']} -[{result['relType']}]-> {result['toNode']}")
    else:
        print("ℹ️  No relationships found (relationships may not be created yet)")


# ============================================================================
# FUSEKI EXAMPLES
# ============================================================================

def example_fuseki_count_triples(fuseki: FusekiConnector):
    """Example 7: Count total triples in Fuseki."""
    print("\n" + "="*60)
    print("EXAMPLE 7: Count Total Triples in Fuseki")
    print("="*60)
    
    query = """
    SELECT (COUNT(*) as ?count)
    WHERE {
      GRAPH ?g {
        ?s ?p ?o
      }
    }
    """
    
    results = fuseki.run_query(query)
    count = results[0]['count']['value']
    print(f"📊 Total triples: {count}")


def example_fuseki_list_graphs(fuseki: FusekiConnector):
    """Example 8: List all named graphs."""
    print("\n" + "="*60)
    print("EXAMPLE 8: List All Named Graphs")
    print("="*60)
    
    query = """
    SELECT DISTINCT ?graph
    WHERE {
      GRAPH ?graph { ?s ?p ?o }
    }
    ORDER BY ?graph
    LIMIT 10
    """
    
    results = fuseki.run_query(query)
    print(f"📋 Named graphs ({len(results)} shown):")
    for result in results:
        print(f"  - {result['graph']['value']}")


def example_fuseki_get_cameras(fuseki: FusekiConnector):
    """Example 9: Get all Camera entities from RDF."""
    print("\n" + "="*60)
    print("EXAMPLE 9: Get All Camera Entities from RDF")
    print("="*60)
    
    query = """
    PREFIX ngsi-ld: <https://uri.etsi.org/ngsi-ld/>
    
    SELECT DISTINCT ?camera ?type
    WHERE {
      GRAPH ?g {
        ?camera a ?type .
        FILTER(CONTAINS(STR(?type), "Camera"))
      }
    }
    LIMIT 5
    """
    
    results = fuseki.run_query(query)
    print(f"📷 Found {len(results)} cameras:")
    for i, result in enumerate(results, 1):
        print(f"  {i}. {result['camera']['value']}")
        print(f"     Type: {result['type']['value']}")


def example_fuseki_get_camera_properties(fuseki: FusekiConnector, camera_uri: str):
    """Example 10: Get all properties of a specific Camera."""
    print("\n" + "="*60)
    print("EXAMPLE 10: Get Camera Properties from RDF")
    print("="*60)
    
    query = f"""
    SELECT ?property ?value
    WHERE {{
      GRAPH ?g {{
        <{camera_uri}> ?property ?value .
      }}
    }}
    LIMIT 20
    """
    
    results = fuseki.run_query(query)
    if results:
        print(f"📷 Camera: {camera_uri}")
        print(f"📋 Properties:")
        for result in results:
            prop = result['property']['value'].split('/')[-1].split('#')[-1]
            val = result['value']['value']
            print(f"  - {prop}: {val[:100]}...")  # Truncate long values
    else:
        print(f"❌ No properties found for camera: {camera_uri}")


def example_fuseki_find_platform(fuseki: FusekiConnector):
    """Example 11: Find Platform from RDF."""
    print("\n" + "="*60)
    print("EXAMPLE 11: Find Platform from RDF")
    print("="*60)
    
    query = """
    PREFIX ngsi-ld: <https://uri.etsi.org/ngsi-ld/>
    
    SELECT DISTINCT ?platform ?type
    WHERE {
      GRAPH ?g {
        ?platform a ?type .
        FILTER(CONTAINS(STR(?type), "Platform"))
      }
    }
    """
    
    results = fuseki.run_query(query)
    if results:
        print(f"🏢 Platform found:")
        for result in results:
            print(f"  - {result['platform']['value']}")
            print(f"    Type: {result['type']['value']}")
    else:
        print("❌ No Platform found")


# ============================================================================
# COMBINED NEO4J + FUSEKI EXAMPLES
# ============================================================================

def example_combined_get_camera(neo4j: Neo4jConnector, fuseki: FusekiConnector, 
                                camera_id: str):
    """Example 12: Get Camera from both Neo4j and Fuseki."""
    print("\n" + "="*60)
    print("EXAMPLE 12: Combined Query - Camera from Neo4j + Fuseki")
    print("="*60)
    
    # Get from Neo4j
    neo4j_query = """
    MATCH (c)
    WHERE c.id = $camera_id
    RETURN c
    """
    neo4j_results = neo4j.run_query(neo4j_query, {'camera_id': camera_id})
    
    # Get from Fuseki
    fuseki_query = f"""
    SELECT ?property ?value
    WHERE {{
      GRAPH ?g {{
        <{camera_id}> ?property ?value .
      }}
    }}
    LIMIT 10
    """
    fuseki_results = fuseki.run_query(fuseki_query)
    
    print(f"📷 Camera: {camera_id}\n")
    
    print("📊 Neo4j Data:")
    if neo4j_results:
        neo4j_data = neo4j_results[0]['c']
        print(f"  {json.dumps(dict(neo4j_data), indent=4)}")
    else:
        print("  ❌ Not found in Neo4j")
    
    print("\n📊 Fuseki RDF Data:")
    if fuseki_results:
        for result in fuseki_results[:5]:  # Show first 5 properties
            prop = result['property']['value'].split('/')[-1]
            val = result['value']['value']
            print(f"  - {prop}: {val[:80]}...")
    else:
        print("  ❌ Not found in Fuseki")


def example_combined_statistics(neo4j: Neo4jConnector, fuseki: FusekiConnector):
    """Example 13: Compare statistics from both databases."""
    print("\n" + "="*60)
    print("EXAMPLE 13: Database Statistics Comparison")
    print("="*60)
    
    # Neo4j stats
    neo4j_query = """
    MATCH (c)
    WHERE c.type CONTAINS 'Camera'
    RETURN count(c) as cameraCount
    """
    neo4j_cameras = neo4j.run_query(neo4j_query)[0]['cameraCount']
    
    # Fuseki stats
    fuseki_query = """
    SELECT (COUNT(DISTINCT ?camera) as ?count)
    WHERE {
      GRAPH ?g {
        ?camera a ?type .
        FILTER(CONTAINS(STR(?type), "Camera"))
      }
    }
    """
    fuseki_results = fuseki.run_query(fuseki_query)
    fuseki_cameras = int(fuseki_results[0]['count']['value'])
    
    print("📊 Statistics:")
    print(f"  Neo4j Cameras: {neo4j_cameras}")
    print(f"  Fuseki Cameras: {fuseki_cameras}")
    print(f"  Match: {'✅' if neo4j_cameras == fuseki_cameras else '❌'}")


# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    """Run all examples."""
    print("\n" + "="*60)
    print("NEO4J & FUSEKI DATA ACCESS EXAMPLES")
    print("="*60)
    
    # Initialize connections
    neo4j = Neo4jConnector()
    fuseki = FusekiConnector()
    
    try:
        # Neo4j Examples
        example_neo4j_count_nodes(neo4j)
        example_neo4j_list_labels(neo4j)
        example_neo4j_get_cameras(neo4j)
        
        # Find a camera ID to use in further examples
        camera_query = """
        MATCH (c)
        WHERE c.type CONTAINS 'Camera'
        RETURN c.id as id
        LIMIT 1
        """
        camera_results = neo4j.run_query(camera_query)
        if camera_results:
            camera_id = camera_results[0]['id']
            example_neo4j_find_camera_by_id(neo4j, camera_id)
        
        example_neo4j_get_platform(neo4j)
        example_neo4j_get_relationships(neo4j)
        
        # Fuseki Examples
        example_fuseki_count_triples(fuseki)
        example_fuseki_list_graphs(fuseki)
        example_fuseki_get_cameras(fuseki)
        example_fuseki_find_platform(fuseki)
        
        if camera_results:
            example_fuseki_get_camera_properties(fuseki, camera_id)
        
        # Combined Examples
        if camera_results:
            example_combined_get_camera(neo4j, fuseki, camera_id)
        
        example_combined_statistics(neo4j, fuseki)
        
        print("\n" + "="*60)
        print("✅ ALL EXAMPLES COMPLETED SUCCESSFULLY")
        print("="*60)
    
    except Exception as e:
        print(f"\n❌ Error occurred: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Close connections
        neo4j.close()
        print("✅ All connections closed")


if __name__ == '__main__':
    main()
