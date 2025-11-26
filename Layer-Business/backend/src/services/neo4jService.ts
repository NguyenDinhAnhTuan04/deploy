import neo4j, { Driver, Session } from 'neo4j-driver';
import { logger } from '../utils/logger';
import { Accident } from '../types';

export class Neo4jService {
  private driver: Driver;

  constructor() {
    const uri = process.env.NEO4J_URL || 'bolt://localhost:7687';
    const user = process.env.NEO4J_USER || 'neo4j';
    const password = process.env.NEO4J_PASSWORD || 'test12345';

    this.driver = neo4j.driver(uri, neo4j.auth.basic(user, password), {
      connectionTimeout: 10000,
      maxConnectionLifetime: 3600000
    });
    
    logger.info(`Neo4jService initialized with URI: ${uri}`);
  }

  async getAccidents(): Promise<Accident[]> {
    const session: Session = this.driver.session();
    try {
      const result = await session.run(`
        MATCH (a:Accident)
        RETURN a
        ORDER BY a.timestamp DESC
        LIMIT 100
      `);

      const accidents = result.records.map(record => {
        const accident = record.get('a').properties;
        return {
          id: accident.id,
          location: {
            latitude: parseFloat(accident.latitude),
            longitude: parseFloat(accident.longitude),
            address: accident.address || 'Unknown location'
          },
          type: accident.type || 'other',
          severity: accident.severity || 'minor',
          description: accident.description || '',
          timestamp: accident.timestamp,
          resolved: accident.resolved === true || accident.resolved === 'true',
          casualties: accident.casualties ? parseInt(accident.casualties, 10) : undefined
        };
      });
      
      logger.debug(`Fetched ${accidents.length} accidents from Neo4j`);
      return accidents;
    } catch (error) {
      logger.error('Error fetching accidents from Neo4j:', error);
      throw new Error('Failed to fetch accidents from Neo4j');
    } finally {
      await session.close();
    }
  }

  async getAccidentById(id: string): Promise<Accident | null> {
    const session: Session = this.driver.session();
    try {
      const result = await session.run(
        'MATCH (a:Accident {id: $id}) RETURN a',
        { id }
      );

      if (result.records.length === 0) {
        return null;
      }

      const accident = result.records[0].get('a').properties;
      return {
        id: accident.id,
        location: {
          latitude: parseFloat(accident.latitude),
          longitude: parseFloat(accident.longitude),
          address: accident.address || 'Unknown location'
        },
        type: accident.type || 'other',
        severity: accident.severity || 'minor',
        description: accident.description || '',
        timestamp: accident.timestamp,
        resolved: accident.resolved === true || accident.resolved === 'true',
        casualties: accident.casualties ? parseInt(accident.casualties, 10) : undefined
      };
    } catch (error) {
      logger.error(`Error fetching accident ${id} from Neo4j:`, error);
      return null;
    } finally {
      await session.close();
    }
  }

  async getAccidentsByArea(latitude: number, longitude: number, radiusKm: number = 5): Promise<Accident[]> {
    const session: Session = this.driver.session();
    try {
      const result = await session.run(`
        MATCH (a:Accident)
        WITH a, point({latitude: toFloat(a.latitude), longitude: toFloat(a.longitude)}) AS accidentPoint,
             point({latitude: $latitude, longitude: $longitude}) AS centerPoint
        WHERE distance(accidentPoint, centerPoint) <= $radiusMeters
        RETURN a
        ORDER BY a.timestamp DESC
      `, {
        latitude,
        longitude,
        radiusMeters: radiusKm * 1000
      });

      return result.records.map(record => {
        const accident = record.get('a').properties;
        return {
          id: accident.id,
          location: {
            latitude: parseFloat(accident.latitude),
            longitude: parseFloat(accident.longitude),
            address: accident.address || 'Unknown location'
          },
          type: accident.type || 'other',
          severity: accident.severity || 'minor',
          description: accident.description || '',
          timestamp: accident.timestamp,
          resolved: accident.resolved === true || accident.resolved === 'true',
          casualties: accident.casualties ? parseInt(accident.casualties, 10) : undefined
        };
      });
    } catch (error) {
      logger.error('Error fetching accidents by area from Neo4j:', error);
      throw new Error('Failed to fetch accidents by area from Neo4j');
    } finally {
      await session.close();
    }
  }

  async getAccidentRelationships(accidentId: string): Promise<any> {
    const session: Session = this.driver.session();
    try {
      const result = await session.run(`
        MATCH (a:Accident {id: $id})-[r]-(related)
        RETURN type(r) AS relationship, labels(related) AS relatedType, related
      `, { id: accidentId });

      return result.records.map(record => ({
        relationship: record.get('relationship'),
        relatedType: record.get('relatedType')[0],
        related: record.get('related').properties
      }));
    } catch (error) {
      logger.error('Error fetching accident relationships from Neo4j:', error);
      return [];
    } finally {
      await session.close();
    }
  }

  async close(): Promise<void> {
    await this.driver.close();
  }
}
