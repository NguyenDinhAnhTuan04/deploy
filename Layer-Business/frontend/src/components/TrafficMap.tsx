import React, { useState, useRef, useImperativeHandle, forwardRef, useEffect } from 'react';
import {
  MapContainer,
  TileLayer,
  Marker,
  Popup,
  Polyline,
  LayersControl,
  ScaleControl,
  ZoomControl,
  Tooltip,
  useMap
} from 'react-leaflet';
import { Icon, LatLngExpression, Map as LeafletMap } from 'leaflet';
import { useTrafficStore } from '../store/trafficStore';
import { Camera, Accident, Weather, AirQuality, TrafficPattern } from '../types';
import { format, subHours, parseISO } from 'date-fns';
import AQIHeatmap from './AQIHeatmap';
import WeatherOverlay from './WeatherOverlay';
import AccidentMarkers from './AccidentMarkers';
import PatternZones from './PatternZones';
// Advanced components disabled - require API endpoints not available
// import PollutantCircles from './PollutantCircles';
// import HumidityVisibilityLayer from './HumidityVisibilityLayer';
// import VehicleHeatmap from './VehicleHeatmap';
// import SpeedZones from './SpeedZones';
// import CorrelationLines from './CorrelationLines';
// import AccidentFrequencyChart from './AccidentFrequencyChart';
import CameraDetailModal from './CameraDetailModal';
import ConnectionStatus from './ConnectionStatus';
import TimeMachine from './TimeMachine';
import HistoricalViewBanner from './HistoricalViewBanner';
import useWebSocket from '../hooks/useWebSocket';
import 'leaflet/dist/leaflet.css';

const { BaseLayer } = LayersControl;

const createCameraIcon = (status: string = 'active'): Icon => {
  // Note: Future versions may include type-specific icons (PTZ/Static/Dome)
  const color = status === 'active' || status === 'online' ? 'blue' : 'red';
  return new Icon({
    iconUrl: `https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-${color}.png`,
    shadowUrl: `https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png`,
    iconSize: [35, 57],  // Tăng từ [25, 41] lên 40% để dễ nhìn hơn
    iconAnchor: [17, 57],  // Điều chỉnh anchor point
    popupAnchor: [1, -50],  // Điều chỉnh popup position
    shadowSize: [57, 57],  // Tăng shadow size
  });
};

const accidentIconBySeverity = (severity: string): Icon => {
  const colorMap: Record<string, string> = {
    'fatal': 'black',
    'severe': 'red',
    'moderate': 'orange',
    'minor': 'yellow',
  };
  const color = colorMap[severity] || 'red';
  return new Icon({
    iconUrl: `https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-${color}.png`,
    shadowUrl: `https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png`,
    iconSize: [35, 57],
    iconAnchor: [17, 57],
    popupAnchor: [1, -50],
    shadowSize: [57, 57],
  });
};

const weatherIcon = new Icon({
  iconUrl: `https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-blue.png`,
  shadowUrl: `https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png`,
  iconSize: [35, 57],
  iconAnchor: [17, 57],
  popupAnchor: [1, -50],
  shadowSize: [57, 57],
});

const airQualityIconByLevel = (level: string): Icon => {
  const colorMap: Record<string, string> = {
    'good': 'green',
    'moderate': 'yellow',
    'unhealthy': 'orange',
    'very_unhealthy': 'red',
    'hazardous': 'violet',
  };
  const color = colorMap[level] || 'grey';
  return new Icon({
    iconUrl: `https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-${color}.png`,
    shadowUrl: `https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png`,
    iconSize: [35, 57],
    iconAnchor: [17, 57],
    popupAnchor: [1, -50],
    shadowSize: [57, 57],
  });
};

const TrafficMap = forwardRef<any, {}>((_props, ref) => {
  const {
    cameras,
    accidents,
    weather,
    airQuality,
    patterns,
    filters,
    setSelectedCamera,
    setSelectedAccident,
    setSelectedPattern,
  } = useTrafficStore();

  // Debug: Log data counts
  useEffect(() => {
    console.log('📊 TrafficMap Data:', {
      cameras: cameras.length,
      accidents: accidents.length,
      weather: weather.length,
      airQuality: airQuality.length,
      patterns: patterns.length
    });
  }, [cameras, accidents, weather, airQuality, patterns]);

  // WebSocket connection
  const { connected, connecting, error, reconnectCount } = useWebSocket({
    url: import.meta.env.VITE_WS_URL || 'ws://localhost:5001',
    heartbeatInterval: 10000,
    reconnectInterval: 3000
  });

  // Camera detail modal state
  const [selectedCameraForModal, setSelectedCameraForModal] = useState<Camera | null>(null);
  const mapRef = useRef<LeafletMap | null>(null);

  // Historical mode state
  const [showTimeMachine, setShowTimeMachine] = useState(false);
  const [historicalData, setHistoricalData] = useState<{
    timestamp: Date;
    weather: Weather[];
    airQuality: AirQuality[];
    patterns: TrafficPattern[];
    accidents: Accident[];
  } | null>(null);

  // Display mode for PatternZones
  const [displayMode] = useState<'congestion' | 'aqi' | 'dual'>('dual');

  // Handle camera click for modal
  const handleCameraClick = (camera: Camera) => {
    setSelectedCamera(camera);
    setSelectedCameraForModal(camera);
  };

  // Handle view on map from modal
  const handleViewOnMap = (camera: Camera) => {
    if (mapRef.current) {
      mapRef.current.setView([camera.location.latitude, camera.location.longitude], 16, {
        animate: true,
        duration: 1
      });
    }
  };

  // Handle zoom to camera from FilterPanel
  const handleZoomToCamera = (camera: Camera) => {
    if (mapRef.current) {
      mapRef.current.setView([camera.location.latitude, camera.location.longitude], 16, {
        animate: true,
        duration: 1
      });
    }
  };

  // Handle zoom to district from FilterPanel
  const handleZoomToDistrict = (
    bounds: { minLat: number; maxLat: number; minLng: number; maxLng: number },
    _center: { lat: number; lng: number }
  ) => {
    if (mapRef.current) {
      // Zoom to fit district bounds
      mapRef.current.fitBounds(
        [[bounds.minLat, bounds.minLng], [bounds.maxLat, bounds.maxLng]],
        {
          padding: [50, 50],
          animate: true,
          duration: 1
        }
      );
    }
  };

  // Handle historical data update from TimeMachine
  const handleHistoricalDataUpdate = (data: {
    timestamp: Date;
    weather: Weather[];
    airQuality: AirQuality[];
    patterns: TrafficPattern[];
    accidents: Accident[];
  }) => {
    setHistoricalData(data);
  };

  // Handle close Historical View Banner - only closes the banner, not TimeMachine
  const handleCloseHistoricalBanner = () => {
    setHistoricalData(null);
  };

  // Handle close TimeMachine - closes both TimeMachine and banner
  const handleCloseTimeMachine = () => {
    setShowTimeMachine(false);
    setHistoricalData(null);
  };

  // Expose methods to parent component
  useImperativeHandle(ref, () => ({
    handleCameraClick,
    handleZoomToCamera,
    handleZoomToDistrict,
  }));

  const center: LatLngExpression = [10.8231, 106.6297];

  // Component to capture map ref
  const MapRefCapture: React.FC = () => {
    const map = useMap();
    mapRef.current = map;
    return null;
  };

  const getCongestionColor = (level: string): string => {
    const levelNormalized = level.toLowerCase();
    switch (levelNormalized) {
      case 'free_flow':
      case 'low':
        return '#00FF00';
      case 'light':
        return '#90EE90';
      case 'moderate':
      case 'medium':
        return '#FFFF00';
      case 'heavy':
      case 'high':
        return '#FFA500';
      case 'severe':
        return '#FF0000';
      default:
        return '#808080';
    }
  };

  const getAQIColor = (level: string): string => {
    switch (level) {
      case 'good':
        return '#00E400';
      case 'moderate':
        return '#FFFF00';
      case 'unhealthy':
        return '#FF7E00';
      case 'very_unhealthy':
        return '#FF0000';
      case 'hazardous':
        return '#8F3F97';
      default:
        return '#808080';
    }
  };

  const getRecentAccidentsCount = (cameraLat: number, cameraLng: number, radius: number = 0.01): number => {
    const twentyFourHoursAgo = subHours(new Date(), 24);
    return accidents.filter(accident => {
      const accidentTime = parseISO(accident.timestamp || accident.dateDetected || new Date().toISOString());
      const isRecent = accidentTime >= twentyFourHoursAgo;
      const distance = Math.sqrt(
        Math.pow(accident.location.latitude - cameraLat, 2) +
        Math.pow(accident.location.longitude - cameraLng, 2)
      );
      return isRecent && distance <= radius;
    }).length;
  };

  const getWeatherAtLocation = (lat: number, lng: number): Weather | null => {
    if (weather.length === 0) return null;

    let closest: Weather | null = null;
    let minDistance = Infinity;

    weather.forEach(w => {
      const distance = Math.sqrt(
        Math.pow(w.location.latitude - lat, 2) +
        Math.pow(w.location.longitude - lng, 2)
      );
      if (distance < minDistance) {
        minDistance = distance;
        closest = w;
      }
    });

    return closest;
  };

  const getAQIAtLocation = (lat: number, lng: number): AirQuality | null => {
    if (airQuality.length === 0) return null;

    let closest: AirQuality | null = null;
    let minDistance = Infinity;

    airQuality.forEach(aq => {
      const distance = Math.sqrt(
        Math.pow(aq.location.latitude - lat, 2) +
        Math.pow(aq.location.longitude - lng, 2)
      );
      if (distance < minDistance) {
        minDistance = distance;
        closest = aq;
      }
    });

    return closest;
  };

  return (
    <>
      {/* Connection Status Indicator */}
      <ConnectionStatus
        connected={connected}
        connecting={connecting}
        error={error}
        reconnectCount={reconnectCount}
      />

      {/* Camera Detail Modal */}
      {selectedCameraForModal && (
        <CameraDetailModal
          camera={selectedCameraForModal}
          onClose={() => setSelectedCameraForModal(null)}
          onViewOnMap={handleViewOnMap}
        />
      )}

      <MapContainer
        center={center}
        zoom={13}
        minZoom={11}
        maxZoom={18}
        style={{ height: '100%', width: '100%' }}
        className="z-0"
        zoomControl={false}
      >
        <ZoomControl position="topright" />
        <ScaleControl position="bottomleft" />

        <LayersControl position="topright">
          <BaseLayer checked name="OpenStreetMap">
            <TileLayer
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            />
          </BaseLayer>
          <BaseLayer name="Satellite">
            <TileLayer
              url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
              attribution='Tiles &copy; Esri'
            />
          </BaseLayer>
        </LayersControl>

        {/* Cameras - Controlled by Sidebar filters */}
        {filters.showCameras && (
          <>
            {(() => {
              const filteredCameras = cameras.filter((camera: Camera) => {
                const lat = camera?.location?.latitude || (camera?.location as any)?.lat;
                const lng = camera?.location?.longitude || (camera?.location as any)?.lng;
                return lat != null && lng != null && !isNaN(lat) && !isNaN(lng);
              });

              console.log('🎥 Camera Rendering:', {
                total: cameras.length,
                filtered: filteredCameras.length,
                showCameras: filters.showCameras,
                sample: cameras[0]
              });

              return filteredCameras.map((camera: Camera) => {
                const lat = camera.location.latitude || (camera.location as any).lat;
                const lng = camera.location.longitude || (camera.location as any).lng;
                const nearbyWeather = getWeatherAtLocation(lat, lng);
                const nearbyAQI = getAQIAtLocation(lat, lng);
                const recentAccidents = getRecentAccidentsCount(lat, lng);

                return (
                  <Marker
                    key={camera.id}
                    position={[lat, lng]}
                    icon={createCameraIcon(camera.status)}
                    eventHandlers={{
                      click: () => handleCameraClick(camera),
                    }}
                  >
                    <Tooltip direction="top" offset={[0, -40]} opacity={0.9}>
                      <strong>{camera.name}</strong>
                    </Tooltip>
                    <Popup>
                      <div className="p-3 min-w-[280px]">
                        <h3 className="font-bold text-lg mb-2">{camera.name}</h3>
                        <p className="text-sm text-gray-600 mb-2">{camera.location.address}</p>

                        <div className="space-y-1 mb-3">
                          <p className="text-sm">
                            <span className="font-semibold">Type:</span> {camera.type || 'Static'}
                          </p>
                          <p className="text-sm">
                            <span className="font-semibold">Status:</span>{' '}
                            <span
                              className={`font-semibold ${camera.status === 'active' || camera.status === 'online'
                                ? 'text-green-600'
                                : camera.status === 'inactive' || camera.status === 'offline'
                                  ? 'text-red-600'
                                  : 'text-yellow-600'
                                }`}
                            >
                              {camera.status}
                            </span>
                          </p>
                        </div>

                        {nearbyWeather && (
                          <div className="border-t pt-2 mb-2">
                            <p className="text-xs font-semibold text-gray-700 mb-1">Current Weather:</p>
                            <p className="text-sm">{nearbyWeather.temperature}°C, {nearbyWeather.condition}</p>
                            <p className="text-xs text-gray-600">Humidity: {nearbyWeather.humidity}%</p>
                          </div>
                        )}

                        {nearbyAQI && (
                          <div className="border-t pt-2 mb-2">
                            <p className="text-xs font-semibold text-gray-700 mb-1">Air Quality:</p>
                            <p className="text-sm">
                              AQI: <span style={{ color: getAQIColor(nearbyAQI.level), fontWeight: 'bold' }}>
                                {nearbyAQI.aqi}
                              </span> ({nearbyAQI.level})
                            </p>
                          </div>
                        )}

                        <div className="border-t pt-2">
                          <p className="text-sm">
                            <span className="font-semibold">Recent Accidents (24h):</span>{' '}
                            <span className={recentAccidents > 0 ? 'text-red-600 font-bold' : 'text-green-600'}>
                              {recentAccidents}
                            </span>
                          </p>
                        </div>

                        {camera.streamUrl && (
                          <a
                            href={camera.streamUrl}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="block mt-3 text-center bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 text-sm"
                          >
                            View Stream
                          </a>
                        )}

                        <button
                          onClick={() => handleCameraClick(camera)}
                          className="block w-full mt-2 text-center bg-gray-600 text-white px-4 py-2 rounded hover:bg-gray-700 text-sm"
                        >
                          View Details
                        </button>
                      </div>
                    </Popup>
                  </Marker>
                );
              });
            })()}
          </>
        )}

        {/* Accidents - Controlled by Sidebar filters */}
        {filters.showAccidents && (
          <>
            {(() => {
              const filteredAccidents = accidents.filter((accident: Accident) => {
                const lat = accident?.location?.latitude || (accident?.location as any)?.lat;
                const lng = accident?.location?.longitude || (accident?.location as any)?.lng;
                // Show all accidents regardless of resolved status
                return lat != null && lng != null && !isNaN(lat) && !isNaN(lng);
              });

              console.log('🚨 Accident Rendering:', {
                total: accidents.length,
                filtered: filteredAccidents.length,
                showAccidents: filters.showAccidents,
                sample: accidents[0],
                sampleLocation: accidents[0]?.location,
                allAccidentLocations: accidents.slice(0, 3).map(a => a.location)
              });

              return filteredAccidents.map((accident: Accident) => {
                const lat = accident.location.latitude || (accident.location as any).lat;
                const lng = accident.location.longitude || (accident.location as any).lng;
                return (
                  <Marker
                    key={accident.id}
                    position={[lat, lng]}
                    icon={accidentIconBySeverity(accident.severity)}
                    eventHandlers={{
                      click: () => setSelectedAccident(accident),
                    }}
                  >
                    <Tooltip direction="top" offset={[0, -40]} opacity={0.9}>
                      {accident.severity.toUpperCase()} - {accident.type}
                    </Tooltip>
                    <Popup>
                      <div className="p-3 min-w-[260px]">
                        <h3 className="font-bold text-lg mb-2 text-red-600">Accident</h3>
                        <p className="text-sm text-gray-600 mb-2">{accident.location.address}</p>

                        <div className="space-y-1 mb-2">
                          <p className="text-sm">
                            <span className="font-semibold">Type:</span> {accident.type}
                          </p>
                          <p className="text-sm">
                            <span className="font-semibold">Severity:</span>{' '}
                            <span
                              className={`font-semibold ${accident.severity === 'fatal'
                                ? 'text-black'
                                : accident.severity === 'severe'
                                  ? 'text-red-600'
                                  : accident.severity === 'moderate'
                                    ? 'text-orange-600'
                                    : 'text-yellow-600'
                                }`}
                            >
                              {accident.severity.toUpperCase()}
                            </span>
                          </p>
                          {accident.vehicles !== undefined && (
                            <p className="text-sm">
                              <span className="font-semibold">Vehicles:</span> {accident.vehicles}
                            </p>
                          )}
                          {accident.casualties !== undefined && accident.casualties > 0 && (
                            <p className="text-sm font-semibold text-red-600">
                              Casualties: {accident.casualties}
                            </p>
                          )}
                          <p className="text-xs text-gray-500">
                            {format(parseISO(accident.timestamp || accident.dateDetected || new Date().toISOString()), 'PPpp')}
                          </p>
                        </div>

                        {accident.description && (
                          <p className="text-sm mt-2 p-2 bg-gray-100 rounded">{accident.description}</p>
                        )}
                      </div>
                    </Popup>
                  </Marker>
                );
              });
            })()}
          </>
        )}

        {/* Weather - Controlled by Sidebar filters */}
        {filters.showWeather && (
          <>
            {(() => {
              // First filter valid coordinates
              const validWeather = weather.filter((w: Weather) => {
                const lat = w?.location?.latitude || (w?.location as any)?.lat;
                const lng = w?.location?.longitude || (w?.location as any)?.lng;
                return lat != null && lng != null && !isNaN(lat) && !isNaN(lng);
              });

              // Group by cameraId (station) and keep only latest observation
              const weatherByStation = new Map<string, Weather>();
              validWeather.forEach((w: Weather) => {
                const stationKey = w.cameraId || `${(w.location.latitude || (w.location as any).lat).toFixed(6)},${(w.location.longitude || (w.location as any).lng).toFixed(6)}`;
                const existing = weatherByStation.get(stationKey);
                const currentTime = new Date(w.timestamp || w.dateObserved || w.dateModified || 0).getTime();
                const existingTime = existing ? new Date(existing.timestamp || existing.dateObserved || existing.dateModified || 0).getTime() : 0;
                if (!existing || currentTime > existingTime) {
                  weatherByStation.set(stationKey, w);
                }
              });

              const filteredWeather = Array.from(weatherByStation.values());

              console.log('🌤️ Weather Rendering:', {
                total: weather.length,
                validCoords: validWeather.length,
                uniqueStations: filteredWeather.length,
                showWeather: filters.showWeather,
                sample: filteredWeather[0],
                allStationKeys: Array.from(weatherByStation.keys()).slice(0, 10),
                sampleCameraIds: validWeather.slice(0, 5).map(w => ({ id: w.id, cameraId: w.cameraId, lat: w.location?.lat, lng: w.location?.lng }))
              });

              return filteredWeather.map((w: Weather) => {
                const lat = w.location.latitude || (w.location as any).lat;
                const lng = w.location.longitude || (w.location as any).lng;
                return (
                  <Marker
                    key={w.id}
                    position={[lat, lng]}
                    icon={weatherIcon}
                  >
                    <Tooltip direction="top" offset={[0, -40]} opacity={0.9}>
                      {w.temperature}°C - {w.condition}
                    </Tooltip>
                    <Popup>
                      <div className="p-3 min-w-[240px]">
                        <h3 className="font-bold text-lg mb-2">Weather</h3>
                        <p className="text-sm text-gray-600 mb-2">{w.location.district}</p>

                        <div className="space-y-1">
                          <p className="text-sm">
                            <span className="font-semibold">Temperature:</span> {w.temperature}°C
                          </p>
                          <p className="text-sm">
                            <span className="font-semibold">Humidity:</span> {w.humidity}%
                          </p>
                          <p className="text-sm">
                            <span className="font-semibold">Rainfall:</span> {w.rainfall}mm
                          </p>
                          <p className="text-sm">
                            <span className="font-semibold">Wind:</span> {w.windSpeed}km/h {w.windDirection}
                          </p>
                          <p className="text-sm">
                            <span className="font-semibold">Condition:</span> {w.condition}
                          </p>
                        </div>
                      </div>
                    </Popup>
                  </Marker>
                );
              });
            })()}
          </>
        )}

        {/* Air Quality - Controlled by Sidebar filters */}
        {filters.showAirQuality && (
          <>
            {(() => {
              // First filter valid coordinates
              const validAQ = airQuality.filter((aq: AirQuality) => {
                const lat = aq?.location?.latitude || (aq?.location as any)?.lat;
                const lng = aq?.location?.longitude || (aq?.location as any)?.lng;
                return lat != null && lng != null && !isNaN(lat) && !isNaN(lng);
              });

              // Group by cameraId (station) and keep only latest observation
              const aqByStation = new Map<string, AirQuality>();
              validAQ.forEach((aq: AirQuality) => {
                const stationKey = aq.cameraId || `${(aq.location.latitude || (aq.location as any).lat).toFixed(6)},${(aq.location.longitude || (aq.location as any).lng).toFixed(6)}`;
                const existing = aqByStation.get(stationKey);
                const currentTime = new Date(aq.timestamp || aq.dateObserved || aq.dateModified || 0).getTime();
                const existingTime = existing ? new Date(existing.timestamp || existing.dateObserved || existing.dateModified || 0).getTime() : 0;
                if (!existing || currentTime > existingTime) {
                  aqByStation.set(stationKey, aq);
                }
              });

              const filteredAQ = Array.from(aqByStation.values());

              console.log('💨 Air Quality Rendering:', {
                total: airQuality.length,
                validCoords: validAQ.length,
                uniqueStations: filteredAQ.length,
                showAirQuality: filters.showAirQuality,
                sample: filteredAQ[0],
                allStationKeys: Array.from(aqByStation.keys()).slice(0, 10),
                sampleCameraIds: validAQ.slice(0, 5).map(aq => ({ id: aq.id, cameraId: aq.cameraId, lat: aq.location?.lat, lng: aq.location?.lng }))
              });

              return filteredAQ.map((aq: AirQuality) => {
                const lat = aq.location.latitude || (aq.location as any).lat;
                const lng = aq.location.longitude || (aq.location as any).lng;
                // Add small offset to avoid exact overlap with weather marker at same location
                const offsetLat = lat + 0.0003; // ~33 meters north
                return (
                  <Marker
                    key={aq.id}
                    position={[offsetLat, lng]}
                    icon={airQualityIconByLevel(aq.level)}
                  >
                    <Tooltip direction="top" offset={[0, -40]} opacity={0.9}>
                      AQI: {aq.aqi} ({aq.level})
                    </Tooltip>
                    <Popup>
                      <div className="p-3 min-w-[240px]">
                        <h3 className="font-bold text-lg mb-2">Air Quality</h3>
                        <p className="text-sm text-gray-600 mb-2">{aq.location.station}</p>

                        <div className="space-y-1">
                          <p className="text-sm">
                            <span className="font-semibold">AQI:</span>{' '}
                            <span
                              className="font-semibold text-lg"
                              style={{ color: getAQIColor(aq.level) }}
                            >
                              {aq.aqi}
                            </span>
                            {' '}({aq.level})
                          </p>
                          <p className="text-sm">
                            <span className="font-semibold">PM2.5:</span> {aq.pm25} µg/m³
                          </p>
                          <p className="text-sm">
                            <span className="font-semibold">PM10:</span> {aq.pm10} µg/m³
                          </p>
                          <p className="text-sm">
                            <span className="font-semibold">CO:</span> {aq.co} ppm
                          </p>
                          <p className="text-sm">
                            <span className="font-semibold">NO2:</span> {aq.no2} ppb
                          </p>
                        </div>
                      </div>
                    </Popup>
                  </Marker>
                );
              });
            })()}
          </>
        )}

        {/* Traffic Patterns - Controlled by Sidebar filters */}
        {filters.showPatterns && (
          <>
            {(() => {
              const filteredPatterns = patterns.filter((pattern: TrafficPattern) => {
                if (!pattern.location || !pattern.location.startPoint || !pattern.location.endPoint) return false;
                const startLat = pattern.location.startPoint.latitude || (pattern.location.startPoint as any).lat;
                const startLng = pattern.location.startPoint.longitude || (pattern.location.startPoint as any).lng;
                const endLat = pattern.location.endPoint.latitude || (pattern.location.endPoint as any).lat;
                const endLng = pattern.location.endPoint.longitude || (pattern.location.endPoint as any).lng;
                return startLat != null && startLng != null && endLat != null && endLng != null &&
                  !isNaN(startLat) && !isNaN(startLng) && !isNaN(endLat) && !isNaN(endLng);
              });

              console.log('🚦 Traffic Patterns Rendering:', {
                total: patterns.length,
                filtered: filteredPatterns.length,
                showPatterns: filters.showPatterns,
                sample: patterns[0]
              });

              return filteredPatterns.map((pattern: TrafficPattern) => {
                const startLat = pattern.location!.startPoint.latitude || (pattern.location!.startPoint as any).lat;
                const startLng = pattern.location!.startPoint.longitude || (pattern.location!.startPoint as any).lng;
                const endLat = pattern.location!.endPoint.latitude || (pattern.location!.endPoint as any).lat;
                const endLng = pattern.location!.endPoint.longitude || (pattern.location!.endPoint as any).lng;
                const positions: LatLngExpression[] = [
                  [startLat, startLng],
                  [endLat, endLng],
                ];
                return (
                  <Polyline
                    key={pattern.id}
                    positions={positions}
                    color={getCongestionColor(pattern.congestionLevel)}
                    weight={5}
                    opacity={0.7}
                    eventHandlers={{
                      click: () => setSelectedPattern(pattern),
                    }}
                  >
                    <Popup>
                      <div className="p-3 min-w-[240px]">
                        <h3 className="font-bold text-lg mb-2">Traffic Pattern</h3>
                        {pattern.roadSegment && (
                          <p className="text-sm text-gray-600 mb-2">{pattern.roadSegment}</p>
                        )}

                        <div className="space-y-1">
                          <p className="text-sm">
                            <span className="font-semibold">Type:</span> {pattern.patternType}
                          </p>
                          <p className="text-sm">
                            <span className="font-semibold">Congestion:</span>{' '}
                            <span
                              className="font-semibold"
                              style={{ color: getCongestionColor(pattern.congestionLevel) }}
                            >
                              {pattern.congestionLevel}
                            </span>
                          </p>
                          {pattern.timeRange && (
                            <p className="text-sm">
                              <span className="font-semibold">Time:</span> {pattern.timeRange}
                            </p>
                          )}
                          {pattern.averageSpeed !== undefined && (
                            <p className="text-sm">
                              <span className="font-semibold">Avg Speed:</span> {pattern.averageSpeed} km/h
                            </p>
                          )}
                          {pattern.vehicleCount !== undefined && (
                            <p className="text-sm">
                              <span className="font-semibold">Vehicles:</span> {pattern.vehicleCount}
                            </p>
                          )}
                          {pattern.predictions && (
                            <p className="text-sm mt-2 p-2 bg-blue-50 rounded">
                              <span className="font-semibold">Prediction:</span> {pattern.predictions.nextHour} km/h
                              <br />
                              <span className="text-xs">({(pattern.predictions.confidence * 100).toFixed(1)}% confidence)</span>
                            </p>
                          )}
                        </div>
                      </div>
                    </Popup>
                  </Polyline>
                );
              });
            })()}
          </>
        )}

        <AQIHeatmap visible={filters.showAQIHeatmap} />
        <WeatherOverlay visible={filters.showWeatherOverlay} />
        <AccidentMarkers visible={filters.showAccidentMarkers} />
        <PatternZones visible={filters.showPatternZones} displayMode={displayMode} />

        {/* Advanced Components - Disabled: Require API endpoints not available */}
        {/* FilterPanel, MapLegend, and SimpleLegend are now integrated into Sidebar */}
        {/* <PollutantCircles visible={filters.showPollutantCircles} /> */}
        {/* <HumidityVisibilityLayer visible={filters.showHumidityLayer} /> */}
        {/* <VehicleHeatmap visible={filters.showVehicleHeatmap} /> */}
        {/* <SpeedZones visible={filters.showSpeedZones} /> */}
        {/* <CorrelationLines visible={filters.showCorrelationLines} /> */}
        {/* <AccidentFrequencyChart visible={filters.showAccidentFrequency} /> */}

        {/* Map Ref Capture */}
        <MapRefCapture />
      </MapContainer>

      {/* Time Machine Toggle Button */}
      <button
        onClick={() => setShowTimeMachine(!showTimeMachine)}
        className="fixed bottom-8 right-8 z-[9998] bg-purple-600 hover:bg-purple-700 text-white px-6 py-3 rounded-lg shadow-2xl flex items-center gap-2 transition-all duration-300 hover:scale-105"
        title="Time Machine"
      >
        <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <span className="font-semibold">
          {showTimeMachine ? 'Hide' : 'Show'} Time Machine
        </span>
      </button>

      {/* Historical View Banner */}
      {historicalData && (
        <HistoricalViewBanner
          timestamp={historicalData.timestamp}
          dataCount={{
            weather: historicalData.weather.length,
            airQuality: historicalData.airQuality.length,
            patterns: historicalData.patterns.length,
            accidents: historicalData.accidents.length
          }}
          onClose={handleCloseHistoricalBanner}
        />
      )}

      {/* Time Machine Component */}
      {showTimeMachine && (
        <TimeMachine
          visible={showTimeMachine}
          onDataUpdate={handleHistoricalDataUpdate}
          onClose={handleCloseTimeMachine}
        />
      )}
    </>
  );
});

TrafficMap.displayName = 'TrafficMap';

export default TrafficMap;
