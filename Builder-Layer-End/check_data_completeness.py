"""
Data Completeness Verification Script
Checks data in Stellio, Fuseki, Neo4j, and local files
"""

import requests
from requests.auth import HTTPBasicAuth
import json
from pathlib import Path

def check_stellio():
    """Check NGSI-LD entities in Stellio"""
    print("\n" + "="*60)
    print("1. STELLIO (NGSI-LD Context Broker)")
    print("="*60)
    
    base_url = "http://localhost:8080/ngsi-ld/v1/entities"
    
    try:
        # Get Cameras
        cameras = requests.get(f"{base_url}?type=Camera&limit=100").json()
        camera_count = len(cameras) if isinstance(cameras, list) else 0
        print(f"✅ Cameras: {camera_count}")
        
        # Get Weather
        weather = requests.get(f"{base_url}?type=WeatherObserved&limit=100").json()
        weather_count = len(weather) if isinstance(weather, list) else 0
        print(f"✅ WeatherObserved: {weather_count}")
        
        # Get AirQuality  
        airquality = requests.get(f"{base_url}?type=AirQualityObserved&limit=100").json()
        airquality_count = len(airquality) if isinstance(airquality, list) else 0
        print(f"✅ AirQualityObserved: {airquality_count}")
        
        total = camera_count + weather_count + airquality_count
        print(f"\n📊 TOTAL: {total} entities")
        
        return total
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return 0


def check_fuseki():
    """Check RDF triples in Fuseki"""
    print("\n" + "="*60)
    print("2. FUSEKI (RDF Triplestore)")
    print("="*60)
    
    auth = HTTPBasicAuth('admin', 'test_admin')
    
    try:
        # Count triples in ALL graphs (including default and named)
        sparql_count = """
        SELECT (COUNT(*) as ?count) WHERE {
            { ?s ?p ?o }
            UNION
            { GRAPH ?g { ?s ?p ?o } }
        }
        """
        
        response = requests.post(
            "http://localhost:3030/lod-dataset/sparql",
            data={'query': sparql_count},
            headers={'Accept': 'application/sparql-results+json'},
            auth=auth
        )
        
        result = response.json()
        triples = int(result['results']['bindings'][0]['count']['value'])
        print(f"✅ Total Triples: {triples:,}")
        
        # Count named graphs
        sparql_graphs = """
        SELECT (COUNT(DISTINCT ?g) as ?count) WHERE {
            GRAPH ?g { ?s ?p ?o }
        }
        """
        
        response2 = requests.post(
            "http://localhost:3030/lod-dataset/sparql",
            data={'query': sparql_graphs},
            headers={'Accept': 'application/sparql-results+json'},
            auth=auth
        )
        
        result2 = response2.json()
        graphs = int(result2['results']['bindings'][0]['count']['value'])
        print(f"✅ Named Graphs: {graphs}")
        
        return triples
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return 0


def check_neo4j():
    """Check nodes in Neo4j"""
    print("\n" + "="*60)
    print("3. NEO4J (Property Graph)")
    print("="*60)
    
    # Use correct password from neo4j_sync.yaml
    auth = HTTPBasicAuth('neo4j', 'test12345')
    headers = {'Content-Type': 'application/json'}
    
    try:
        # Count all nodes
        query = {
            "statements": [
                {"statement": "MATCH (n) RETURN count(n) as total"}
            ]
        }
        
        response = requests.post(
            "http://localhost:7474/db/neo4j/tx/commit",
            json=query,
            headers=headers,
            auth=auth
        )
        
        result = response.json()
        
        # Check for errors
        if 'errors' in result and result['errors']:
            error_msg = result['errors'][0].get('message', 'Unknown error')
            print(f"❌ Neo4j ERROR: {error_msg}")
            return 0
        
        total = result['results'][0]['data'][0]['row'][0]
        print(f"✅ Total Nodes: {total}")
        
        # Count by type
        query2 = {
            "statements": [
                {"statement": "MATCH (n:Camera) RETURN count(n) as count"},
                {"statement": "MATCH (n:WeatherObserved) RETURN count(n) as count"},
                {"statement": "MATCH (n:AirQualityObserved) RETURN count(n) as count"}
            ]
        }
        
        response2 = requests.post(
            "http://localhost:7474/db/neo4j/tx/commit",
            json=query2,
            headers=headers,
            auth=auth
        )
        
        result2 = response2.json()
        cameras = result2['results'][0]['data'][0]['row'][0]
        weather = result2['results'][1]['data'][0]['row'][0]
        airquality = result2['results'][2]['data'][0]['row'][0]
        
        print(f"   - Camera: {cameras}")
        print(f"   - WeatherObserved: {weather}")
        print(f"   - AirQualityObserved: {airquality}")
        
        return total
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return 0


def check_local_files():
    """Check local RDF and JSON files"""
    print("\n" + "="*60)
    print("4. LOCAL FILES")
    print("="*60)
    
    # Check RDF files
    rdf_dir = Path("data/rdf")
    if rdf_dir.exists():
        ttl_files = list(rdf_dir.glob("*.ttl"))
        camera_files = [f for f in ttl_files if f.name.startswith("Camera_")]
        property_files = [f for f in ttl_files if f.name.startswith("ObservableProperty_")]
        
        print(f"✅ Total RDF Files: {len(ttl_files)}")
        print(f"   - Camera_*.ttl: {len(camera_files)}")
        print(f"   - ObservableProperty_*.ttl: {len(property_files)}")
    else:
        print("❌ RDF directory not found")
    
    # Check JSON files
    json_files = {
        "cameras_updated.json": "Updated Cameras",
        "cameras_enriched.json": "Enriched Cameras (with weather/AQ)",
        "ngsi_ld_entities.json": "NGSI-LD Entities",
        "observations.json": "CV Observations"
    }
    
    print("\n📁 JSON Files:")
    for filename, description in json_files.items():
        filepath = Path(f"data/{filename}")
        if filepath.exists():
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    count = len(data) if isinstance(data, list) else 1
                    print(f"✅ {description}: {count} entities")
            except Exception as e:
                print(f"⚠️  {description}: Error reading ({e})")
        else:
            print(f"❌ {description}: NOT FOUND")


def main():
    print("\n" + "="*60)
    print("DATA COMPLETENESS VERIFICATION")
    print("="*60)
    
    # Run all checks
    stellio_count = check_stellio()
    fuseki_count = check_fuseki()
    neo4j_count = check_neo4j()
    check_local_files()
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"Stellio Entities: {stellio_count}")
    print(f"Fuseki Triples: {fuseki_count:,}")
    print(f"Neo4j Nodes: {neo4j_count}")
    print("\n✅ Data completeness verification complete!")
    print("="*60)


if __name__ == "__main__":
    main()
