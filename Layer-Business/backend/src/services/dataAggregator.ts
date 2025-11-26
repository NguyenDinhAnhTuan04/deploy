import { WebSocketService } from './websocketService';
import { StellioService } from './stellioService';
import { FusekiService } from './fusekiService';
import { Neo4jService } from './neo4jService';
import { PostgresService } from './postgresService';
import { logger } from '../utils/logger';
import { Camera, Weather, AirQuality, Accident, TrafficPattern } from '../types';

interface EntityCache {
  data: any;
  dateModified: string;
}

export class DataAggregator {
  private wsService: WebSocketService;
  private stellioService: StellioService;
  private fusekiService: FusekiService;
  private neo4jService: Neo4jService;
  private postgresService: PostgresService;
  private intervalId: NodeJS.Timeout | null = null;
  private updateInterval: number;

  // Change detection caches
  private cameraCache: Map<string, EntityCache> = new Map();
  private weatherCache: Map<string, EntityCache> = new Map();
  private airQualityCache: Map<string, EntityCache> = new Map();
  private accidentCache: Map<string, EntityCache> = new Map();
  private patternCache: Map<string, EntityCache> = new Map();

  constructor(wsService: WebSocketService) {
    this.wsService = wsService;
    this.stellioService = new StellioService();
    this.fusekiService = new FusekiService();
    this.neo4jService = new Neo4jService();
    this.postgresService = new PostgresService();
    this.updateInterval = parseInt(process.env.DATA_UPDATE_INTERVAL || '30000', 10);

    // Register snapshot provider with WebSocket service
    this.wsService.setSnapshotProvider(() => this.getCurrentSnapshot());
  }

  start(): void {
    logger.info('Starting data aggregation service with change detection...');

    // Send initial snapshot immediately
    this.fetchAndBroadcastAll(true);

    // Poll for changes every 30 seconds
    this.intervalId = setInterval(() => {
      this.fetchAndBroadcastAll(false);
    }, this.updateInterval);

    logger.info(`Data aggregation service started (interval: ${this.updateInterval}ms)`);
  }

  stop(): void {
    if (this.intervalId) {
      clearInterval(this.intervalId);
      this.intervalId = null;
      logger.info('Data aggregation service stopped');
    }
  }

  /**
   * Get current snapshot of all cached data for new WebSocket clients
   */
  getCurrentSnapshot(): { cameras: any[], weather: any[], airQuality: any[], accidents: any[], patterns: any[] } {
    const snapshot = {
      cameras: Array.from(this.cameraCache.values()).map(entry => entry.data),
      weather: Array.from(this.weatherCache.values()).map(entry => entry.data),
      airQuality: Array.from(this.airQualityCache.values()).map(entry => entry.data),
      accidents: Array.from(this.accidentCache.values()).map(entry => entry.data),
      patterns: Array.from(this.patternCache.values()).map(entry => entry.data)
    };

    logger.info(`Prepared snapshot: cameras=${snapshot.cameras.length}, weather=${snapshot.weather.length}, airQuality=${snapshot.airQuality.length}, accidents=${snapshot.accidents.length}, patterns=${snapshot.patterns.length}`);

    return snapshot;
  }

  private async fetchAndBroadcastAll(isInitial: boolean = false): Promise<void> {
    try {
      await Promise.allSettled([
        this.fetchAndBroadcastCameras(isInitial),
        this.fetchAndBroadcastWeather(isInitial),
        this.fetchAndBroadcastAirQuality(isInitial),
        this.fetchAndBroadcastAccidents(isInitial),
        this.fetchAndBroadcastPatterns(isInitial)
      ]);
    } catch (error) {
      logger.error('Error in fetchAndBroadcastAll:', error);
    }
  }

  /**
   * Detect if entity has changed by comparing dateModified
   */
  private hasChanged(entityId: string, dateModified: string, cache: Map<string, EntityCache>): boolean {
    const cached = cache.get(entityId);
    if (!cached) return true; // New entity
    return cached.dateModified !== dateModified;
  }

  /**
   * Update cache with new entity data
   */
  private updateCache(entityId: string, data: any, dateModified: string, cache: Map<string, EntityCache>): void {
    cache.set(entityId, { data, dateModified });
  }

  private async fetchAndBroadcastCameras(isInitial: boolean): Promise<void> {
    try {
      const cameras: Camera[] = await this.stellioService.getCameras();
      const changedCameras: Camera[] = [];

      cameras.forEach(camera => {
        const entityId = camera.id;
        const dateModified = camera.dateModified || new Date().toISOString();

        // Check for changes
        if (isInitial || this.hasChanged(entityId, dateModified, this.cameraCache)) {
          changedCameras.push(camera);
          this.updateCache(entityId, camera, dateModified, this.cameraCache);
        }
      });

      // Broadcast ALL changed cameras in ONE message
      if (changedCameras.length > 0) {
        this.wsService.broadcast({
          type: 'cameras', // plural - batch update
          data: changedCameras,
          timestamp: new Date().toISOString()
        });
        logger.debug(`Broadcasted ${changedCameras.length} camera updates in batch`);
      }
    } catch (error) {
      logger.error('Error fetching and broadcasting cameras:', error);
    }
  }

  private async fetchAndBroadcastWeather(isInitial: boolean): Promise<void> {
    try {
      const weatherData = await this.stellioService.getWeatherData();
      const changedWeather: Weather[] = [];

      const transformedWeather: Weather[] = weatherData.map((data: any) => ({
        id: data.id || data['@id'] || `weather-${Date.now()}`,
        cameraId: data.cameraId || data.refDevice || 'unknown',
        location: {
          lat: data.location?.coordinates?.[1] || data.latitude || 10.8231,
          lng: data.location?.coordinates?.[0] || data.longitude || 106.6297
        },
        temperature: typeof data.temperature === 'number' ? data.temperature : parseFloat(String(data.temperature || '30')),
        humidity: typeof data.humidity === 'number' ? data.humidity : parseFloat(String(data.humidity || '70')),
        precipitation: typeof data.rainfall === 'number' ? data.rainfall : parseFloat(String(data.rainfall || data.precipitation || '0')),
        windSpeed: typeof data.windSpeed === 'number' ? data.windSpeed : parseFloat(String(data.windSpeed || '10')),
        windDirection: data.windDirection || 'N',
        weatherType: data.weatherType || data.condition || 'Clear',
        pressure: data.pressure,
        visibility: data.visibility,
        dateObserved: data.dateObserved || data.timestamp || new Date().toISOString()
      }));

      transformedWeather.forEach(weather => {
        const entityId = weather.id;
        const dateModified = weather.dateObserved;

        // Check for changes
        if (isInitial || this.hasChanged(entityId, dateModified, this.weatherCache)) {
          changedWeather.push(weather);
          this.updateCache(entityId, weather, dateModified, this.weatherCache);
        }
      });

      // Broadcast ALL changed weather in ONE message
      if (changedWeather.length > 0) {
        this.wsService.broadcast({
          type: 'weathers',
          data: changedWeather,
          timestamp: new Date().toISOString()
        });
        logger.debug(`Broadcasted ${changedWeather.length} weather updates in batch`);
      }
    } catch (error) {
      logger.error('Error fetching and broadcasting weather:', error);
    }
  }

  private async fetchAndBroadcastAirQuality(isInitial: boolean): Promise<void> {
    try {
      const airQualityData = await this.stellioService.getAirQualityData();
      const changedAirQuality: AirQuality[] = [];

      const transformedAirQuality: AirQuality[] = airQualityData.map((data: any) => {
        const aqi = typeof data.aqi === 'number' ? data.aqi : parseFloat(String(data.airQualityIndex || data.aqi || '50'));
        return {
          id: data.id || data['@id'] || `aqi-${Date.now()}`,
          cameraId: data.cameraId || data.refDevice || 'unknown',
          location: {
            lat: data.location?.coordinates?.[1] || data.latitude || 10.8231,
            lng: data.location?.coordinates?.[0] || data.longitude || 106.6297
          },
          aqi,
          pm25: typeof data.pm25 === 'number' ? data.pm25 : parseFloat(String(data.pm25 || '25')),
          pm10: typeof data.pm10 === 'number' ? data.pm10 : parseFloat(String(data.pm10 || '50')),
          co: typeof data.co === 'number' ? data.co : parseFloat(String(data.co || '0.5')),
          no2: typeof data.no2 === 'number' ? data.no2 : parseFloat(String(data.no2 || '20')),
          so2: typeof data.so2 === 'number' ? data.so2 : parseFloat(String(data.so2 || '10')),
          o3: typeof data.o3 === 'number' ? data.o3 : parseFloat(String(data.o3 || '30')),
          level: this.getAQILevel(aqi),
          colorCode: this.getAQIColorCode(aqi),
          dateObserved: data.dateObserved || data.timestamp || new Date().toISOString()
        };
      });

      transformedAirQuality.forEach(airQuality => {
        const entityId = airQuality.id;
        const dateModified = airQuality.dateObserved;

        // Check for changes
        if (isInitial || this.hasChanged(entityId, dateModified, this.airQualityCache)) {
          changedAirQuality.push(airQuality);
          this.updateCache(entityId, airQuality, dateModified, this.airQualityCache);

          // Send alert if AQI > 150
          if (airQuality.aqi > 150) {
            this.wsService.sendAlert('aqi_warning', {
              cameraId: airQuality.cameraId,
              aqi: airQuality.aqi,
              level: airQuality.level,
              location: airQuality.location,
              message: `High AQI detected: ${airQuality.aqi}`
            }, 'medium');
          }
        }
      });

      // Broadcast ALL changed air quality in ONE message
      if (changedAirQuality.length > 0) {
        this.wsService.broadcast({
          type: 'air_qualities',
          data: changedAirQuality,
          timestamp: new Date().toISOString()
        });
        logger.debug(`Broadcasted ${changedAirQuality.length} air quality updates in batch`);
      }
    } catch (error) {
      logger.error('Error fetching and broadcasting air quality:', error);
    }
  }

  private async fetchAndBroadcastAccidents(isInitial: boolean): Promise<void> {
    try {
      const accidents: Accident[] = await this.neo4jService.getAccidents();
      const changedAccidents: Accident[] = [];

      accidents.forEach(accident => {
        const entityId = accident.id;
        const dateModified = accident.timestamp || new Date().toISOString();

        // Check for changes (new accidents)
        if (isInitial || this.hasChanged(entityId, dateModified, this.accidentCache)) {
          changedAccidents.push(accident);
          this.updateCache(entityId, accident, dateModified, this.accidentCache);

          // Send alert for severe accidents
          if (accident.severity === 'severe' || accident.severity === 'fatal') {
            this.wsService.sendAlert('accident_alert', {
              accidentId: accident.id,
              severity: accident.severity,
              type: accident.type,
              location: accident.location,
              message: `Severe accident detected: ${accident.type}`
            }, 'high');
          }
        }
      });

      // Broadcast ALL changed accidents in ONE message
      if (changedAccidents.length > 0) {
        this.wsService.broadcast({
          type: 'accidents',
          data: changedAccidents,
          timestamp: new Date().toISOString()
        });
        logger.debug(`Broadcasted ${changedAccidents.length} accident updates in batch`);
      }
    } catch (error) {
      logger.error('Error fetching and broadcasting accidents:', error);
    }
  }

  private async fetchAndBroadcastPatterns(isInitial: boolean): Promise<void> {
    try {
      // Fetch real TrafficFlowPattern entities from Stellio
      const patterns: TrafficPattern[] = await this.stellioService.getTrafficFlowPatterns();

      logger.debug(`Fetched ${patterns.length} traffic patterns from Stellio`);
      let updateCount = 0;

      patterns.forEach(pattern => {
        const entityId = pattern.id;
        const dateModified = pattern.timestamp || new Date().toISOString();

        // Check for changes
        if (isInitial || this.hasChanged(entityId, dateModified, this.patternCache)) {
          this.wsService.broadcast({
            type: 'pattern',
            data: pattern,
            timestamp: new Date().toISOString()
          });

          this.updateCache(entityId, pattern, dateModified, this.patternCache);
          updateCount++;
        }
      });

      if (updateCount > 0 || isInitial) {
        logger.debug(`Broadcasted ${updateCount} pattern updates`);
      }
    } catch (error) {
      logger.error('Error fetching and broadcasting patterns:', error);
    }
  }

  // Old mergePatternData method - no longer used since we fetch directly from Stellio
  // private async mergePatternData(fusekiPatterns: any[], postgresMetrics: any[]): Promise<TrafficPattern[]> { ... }

  private getAQILevel(aqi: number): 'good' | 'moderate' | 'unhealthy' | 'very_unhealthy' | 'hazardous' {
    if (aqi <= 50) return 'good';
    if (aqi <= 100) return 'moderate';
    if (aqi <= 150) return 'unhealthy';
    if (aqi <= 200) return 'very_unhealthy';
    return 'hazardous';
  }

  private getAQIColorCode(aqi: number): string {
    if (aqi <= 50) return '#00e400'; // Green - Good
    if (aqi <= 100) return '#ffff00'; // Yellow - Moderate
    if (aqi <= 150) return '#ff7e00'; // Orange - Unhealthy for Sensitive Groups
    if (aqi <= 200) return '#ff0000'; // Red - Unhealthy
    if (aqi <= 300) return '#8f3f97'; // Purple - Very Unhealthy
    return '#7e0023'; // Maroon - Hazardous
  }

  private getCongestionLevel(speed: number): 'free_flow' | 'light' | 'moderate' | 'heavy' | 'severe' {
    if (speed >= 60) return 'free_flow';
    if (speed >= 40) return 'light';
    if (speed >= 25) return 'moderate';
    if (speed >= 15) return 'heavy';
    return 'severe';
  }
}
