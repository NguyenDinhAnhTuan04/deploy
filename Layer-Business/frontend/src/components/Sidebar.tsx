import React, { useState, useEffect } from 'react';
import { useTrafficStore } from '../store/trafficStore';
import {
  Camera,
  AlertTriangle,
  Cloud,
  Wind,
  Activity,
  MapPin,
  Eye,
  ChevronLeft,
  ChevronRight,
  ChevronDown,
  ChevronUp,
  BarChart3,
  Layers,
  Search,
  X,
} from 'lucide-react';

interface SidebarProps {
  onCameraSelect?: (camera: any) => void;
  onZoomToCamera?: (camera: any) => void;
  onZoomToDistrict?: (bounds: any, center: any) => void;
}

const Sidebar: React.FC<SidebarProps> = ({ onCameraSelect, onZoomToCamera, onZoomToDistrict }) => {
  const {
    cameras,
    accidents,
    weather,
    airQuality,
    patterns,
    filters,
    toggleFilter,
    isConnected,
  } = useTrafficStore();

  const [isCollapsed, setIsCollapsed] = useState(false);
  const [expandedSections, setExpandedSections] = useState({
    basic: true,
    advanced: true,
    stats: true,
    search: true,
    legend: false,
    weather: false,
    accidents: false,
  });
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedDistrict, setSelectedDistrict] = useState('all');
  const [showAutocomplete, setShowAutocomplete] = useState(false);
  const [districtsData, setDistrictsData] = useState<any[]>([]);

  const activeAccidents = accidents.filter((a) => !a.resolved);

  // Fetch districts data
  useEffect(() => {
    const fetchDistricts = async () => {
      try {
        const response = await fetch('http://localhost:3001/api/cameras/districts-ui');
        if (response.ok) {
          const result = await response.json();
          if (result.success && result.data.districts) {
            setDistrictsData(result.data.districts);
          }
        }
      } catch (error) {
        console.error('Error fetching districts:', error);
      }
    };
    fetchDistricts();
  }, []);

  const toggleSection = (section: keyof typeof expandedSections) => {
    setExpandedSections((prev) => ({ ...prev, [section]: !prev[section] }));
  };

  // Search autocomplete
  const autocompleteResults = searchQuery.trim() !== ''
    ? cameras
      .filter(cam => {
        const name = cam.name || cam.cameraName || '';
        const district = cam.district || '';
        const query = searchQuery.toLowerCase();
        return name.toLowerCase().includes(query) || district.toLowerCase().includes(query);
      })
      .slice(0, 5)
    : [];

  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setSearchQuery(value);
    setShowAutocomplete(value.trim() !== '');
  };

  const handleAutocompleteSelect = (camera: any) => {
    setSearchQuery(camera.name || camera.cameraName || '');
    setShowAutocomplete(false);
    if (onZoomToCamera) {
      onZoomToCamera(camera);
    }
    if (onCameraSelect) {
      onCameraSelect(camera);
    }
  };

  const handleDistrictChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const districtId = e.target.value;
    setSelectedDistrict(districtId);
    if (districtId !== 'all') {
      const district = districtsData.find(d => d.id === districtId);
      if (district && onZoomToDistrict) {
        onZoomToDistrict(district.bounds, district.center);
      }
    }
  };

  const clearDistrictFilter = () => {
    setSelectedDistrict('all');
  };

  const basicLayers = [
    { key: 'showCameras' as const, label: 'Cameras', icon: Camera, count: cameras.length, color: 'text-blue-400' },
    { key: 'showAccidents' as const, label: 'Accidents', icon: AlertTriangle, count: activeAccidents.length, color: 'text-red-400' },
    { key: 'showWeather' as const, label: 'Weather', icon: Cloud, count: weather.length, color: 'text-sky-400' },
    { key: 'showAirQuality' as const, label: 'Air Quality', icon: Wind, count: airQuality.length, color: 'text-amber-400' },
    { key: 'showPatterns' as const, label: 'Traffic Patterns', icon: Activity, count: patterns.length, color: 'text-purple-400' },
  ];

  const advancedLayers = [
    { key: 'showAQIHeatmap' as const, label: 'AQI Heatmap', icon: Layers, color: 'text-orange-400' },
    { key: 'showWeatherOverlay' as const, label: 'Weather Overlay', icon: Cloud, color: 'text-cyan-400' },
    { key: 'showAccidentMarkers' as const, label: 'Accident Markers', icon: MapPin, color: 'text-rose-400' },
    { key: 'showPatternZones' as const, label: 'Pattern Zones', icon: BarChart3, color: 'text-indigo-400' },
    { key: 'showPollutantCircles' as const, label: 'Pollutant Circles', icon: Layers, color: 'text-gray-400' },
    { key: 'showHumidityLayer' as const, label: 'Humidity Zones', icon: Cloud, color: 'text-blue-300' },
    { key: 'showVehicleHeatmap' as const, label: 'Vehicle Heatmap', icon: Activity, color: 'text-red-300' },
    { key: 'showSpeedZones' as const, label: 'Speed Zones', icon: Activity, color: 'text-yellow-400' },
    { key: 'showCorrelationLines' as const, label: 'Correlations', icon: Activity, color: 'text-green-400' },
    { key: 'showAccidentFrequency' as const, label: 'Accident Chart', icon: BarChart3, color: 'text-pink-400' },
  ];

  if (isCollapsed) {
    return (
      <div className="w-16 bg-gradient-to-b from-gray-900 via-gray-800 to-gray-900 text-white h-full flex flex-col items-center border-r border-gray-700 shadow-2xl">
        <div className="p-4 border-b border-gray-700 w-full flex justify-center">
          <Activity className="w-6 h-6 text-blue-400" />
        </div>
        <button
          onClick={() => setIsCollapsed(false)}
          className="mt-4 p-2 hover:bg-gray-700 rounded-lg transition-colors"
          title="Expand sidebar"
        >
          <ChevronRight className="w-5 h-5" />
        </button>
        <div className="mt-4">
          <div
            className={`w-3 h-3 rounded-full ${isConnected ? 'bg-green-500 animate-pulse' : 'bg-red-500'
              }`}
          />
        </div>
      </div>
    );
  }

  return (
    <div className="w-80 bg-gradient-to-b from-gray-900 via-gray-800 to-gray-900 text-white h-full overflow-y-auto scrollbar-thin flex flex-col border-r border-gray-700 shadow-2xl">
      {/* Header */}
      <div className="p-4 border-b border-gray-700 bg-gray-800/50 backdrop-blur-sm sticky top-0 z-10">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center space-x-2">
            <Activity className="w-6 h-6 text-blue-400" />
            <h1 className="text-xl font-bold bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent">
              HCMC Traffic
            </h1>
          </div>
          <button
            onClick={() => setIsCollapsed(true)}
            className="p-1.5 hover:bg-gray-700 rounded-lg transition-colors"
            title="Collapse sidebar"
          >
            <ChevronLeft className="w-5 h-5" />
          </button>
        </div>
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <div
              className={`w-2.5 h-2.5 rounded-full ${isConnected ? 'bg-green-500 animate-pulse' : 'bg-red-500'
                }`}
            />
            <span className="text-sm font-medium">
              {isConnected ? 'Connected' : 'Disconnected'}
            </span>
          </div>
          <span className="text-xs text-gray-400">
            {new Date().toLocaleTimeString()}
          </span>
        </div>
      </div>

      {/* Search & Filters Section */}
      <div className="border-b border-gray-700">
        <button
          onClick={() => toggleSection('search')}
          className="w-full p-4 flex items-center justify-between hover:bg-gray-800/50 transition-colors"
        >
          <div className="flex items-center space-x-2">
            <Search className="w-5 h-5 text-blue-400" />
            <h2 className="text-lg font-semibold">Search & Filters</h2>
          </div>
          {expandedSections.search ? (
            <ChevronUp className="w-5 h-5" />
          ) : (
            <ChevronDown className="w-5 h-5" />
          )}
        </button>
        {expandedSections.search && (
          <div className="px-4 pb-4 space-y-3">
            {/* Search Input */}
            <div className="relative">
              <label className="block text-xs font-bold text-gray-300 mb-2 uppercase tracking-wide">
                Search Cameras
              </label>
              <div className="relative">
                <input
                  type="text"
                  value={searchQuery}
                  onChange={handleSearchChange}
                  onFocus={() => setShowAutocomplete(searchQuery.trim() !== '')}
                  onBlur={() => setTimeout(() => setShowAutocomplete(false), 200)}
                  placeholder="Search by name or address..."
                  className="w-full pl-9 pr-4 py-2 bg-gray-800 border border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-white placeholder-gray-500 text-sm"
                />
                <Search className="absolute left-2.5 top-2.5 w-4 h-4 text-gray-500" />
              </div>

              {/* Autocomplete dropdown */}
              {showAutocomplete && autocompleteResults.length > 0 && (
                <div className="absolute z-10 w-full mt-1 bg-gray-800 border border-gray-600 rounded-lg shadow-2xl max-h-48 overflow-y-auto">
                  {autocompleteResults.map((camera) => (
                    <button
                      key={camera.id}
                      onClick={() => handleAutocompleteSelect(camera)}
                      className="w-full text-left px-3 py-2.5 hover:bg-gray-700 border-b border-gray-700 last:border-b-0 transition-colors"
                    >
                      <div className="font-medium text-xs text-white">{camera.name}</div>
                      <div className="text-[10px] text-gray-400 truncate mt-0.5">{camera.location.address}</div>
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* District Filter */}
            <div>
              <label className="block text-xs font-bold text-gray-300 mb-2 uppercase tracking-wide">
                <MapPin className="w-3 h-3 inline mr-1" />
                District Filter
              </label>
              <div className="relative">
                <select
                  value={selectedDistrict}
                  onChange={handleDistrictChange}
                  className="w-full px-3 py-2 bg-gray-800 border border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 appearance-none text-white text-sm pr-8"
                >
                  <option value="all">All Districts</option>
                  {districtsData.map((district) => (
                    <option key={district.id} value={district.id}>
                      {district.name} ({district.cameraCount})
                    </option>
                  ))}
                </select>
                {selectedDistrict !== 'all' && (
                  <button
                    onClick={clearDistrictFilter}
                    className="absolute right-2 top-1/2 -translate-y-1/2 p-1 hover:bg-gray-700 rounded-full transition-colors"
                    title="Clear district filter"
                  >
                    <X className="w-3.5 h-3.5 text-gray-400" />
                  </button>
                )}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Basic Layers */}
      <div className="border-b border-gray-700">
        <button
          onClick={() => toggleSection('basic')}
          className="w-full p-4 flex items-center justify-between hover:bg-gray-800/50 transition-colors"
        >
          <div className="flex items-center space-x-2">
            <Layers className="w-5 h-5 text-blue-400" />
            <h2 className="text-lg font-semibold">Layer Visibility</h2>
          </div>
          {expandedSections.basic ? (
            <ChevronUp className="w-5 h-5" />
          ) : (
            <ChevronDown className="w-5 h-5" />
          )}
        </button>
        {expandedSections.basic && (
          <div className="px-4 pb-4 space-y-1">
            {basicLayers.map(({ key, label, icon: Icon, count, color }) => (
              <label
                key={key}
                className="flex items-center justify-between p-2.5 rounded-lg hover:bg-gray-700/50 cursor-pointer transition-all group"
              >
                <div className="flex items-center space-x-3">
                  <div className="relative">
                    <input
                      type="checkbox"
                      checked={filters[key]}
                      onChange={() => toggleFilter(key)}
                      className="w-4 h-4 rounded border-gray-600 text-blue-500 focus:ring-blue-500 focus:ring-offset-gray-800"
                    />
                  </div>
                  <Icon className={`w-4 h-4 ${color}`} />
                  <span className="text-sm font-medium group-hover:text-white transition-colors">
                    {label}
                  </span>
                </div>
                <span className={`text-xs font-bold px-2 py-0.5 rounded-full bg-gray-700 ${color}`}>
                  {count}
                </span>
              </label>
            ))}
          </div>
        )}
      </div>

      {/* Advanced Layers */}
      <div className="border-b border-gray-700">
        <button
          onClick={() => toggleSection('advanced')}
          className="w-full p-4 flex items-center justify-between hover:bg-gray-800/50 transition-colors"
        >
          <div className="flex items-center space-x-2">
            <Eye className="w-5 h-5 text-purple-400" />
            <h2 className="text-lg font-semibold">Advanced Layers</h2>
          </div>
          {expandedSections.advanced ? (
            <ChevronUp className="w-5 h-5" />
          ) : (
            <ChevronDown className="w-5 h-5" />
          )}
        </button>
        {expandedSections.advanced && (
          <div className="px-4 pb-4 space-y-1">
            {advancedLayers.map(({ key, label, icon: Icon, color }) => (
              <label
                key={key}
                className="flex items-center space-x-3 p-2.5 rounded-lg hover:bg-gray-700/50 cursor-pointer transition-all group"
              >
                <input
                  type="checkbox"
                  checked={filters[key]}
                  onChange={() => toggleFilter(key)}
                  className="w-4 h-4 rounded border-gray-600 text-purple-500 focus:ring-purple-500 focus:ring-offset-gray-800"
                />
                <Icon className={`w-4 h-4 ${color}`} />
                <span className="text-sm font-medium group-hover:text-white transition-colors">
                  {label}
                </span>
              </label>
            ))}
          </div>
        )}
      </div>

      {/* Statistics */}
      <div className="border-b border-gray-700">
        <button
          onClick={() => toggleSection('stats')}
          className="w-full p-4 flex items-center justify-between hover:bg-gray-800/50 transition-colors"
        >
          <div className="flex items-center space-x-2">
            <BarChart3 className="w-5 h-5 text-green-400" />
            <h2 className="text-lg font-semibold">Statistics</h2>
          </div>
          {expandedSections.stats ? (
            <ChevronUp className="w-5 h-5" />
          ) : (
            <ChevronDown className="w-5 h-5" />
          )}
        </button>
        {expandedSections.stats && (
          <div className="p-4 space-y-3">
            <div className="bg-gradient-to-br from-blue-900/40 to-blue-800/20 border border-blue-700/30 p-4 rounded-xl backdrop-blur-sm">
              <div className="flex items-center justify-between mb-2">
                <p className="text-xs font-medium text-blue-300 uppercase tracking-wide">Total Cameras</p>
                <Camera className="w-4 h-4 text-blue-400" />
              </div>
              <p className="text-3xl font-bold text-white">{cameras.length}</p>
            </div>
            <div className="bg-gradient-to-br from-red-900/40 to-red-800/20 border border-red-700/30 p-4 rounded-xl backdrop-blur-sm">
              <div className="flex items-center justify-between mb-2">
                <p className="text-xs font-medium text-red-300 uppercase tracking-wide">Active Accidents</p>
                <AlertTriangle className="w-4 h-4 text-red-400" />
              </div>
              <p className="text-3xl font-bold text-white">{activeAccidents.length}</p>
            </div>
            <div className="bg-gradient-to-br from-sky-900/40 to-sky-800/20 border border-sky-700/30 p-4 rounded-xl backdrop-blur-sm">
              <div className="flex items-center justify-between mb-2">
                <p className="text-xs font-medium text-sky-300 uppercase tracking-wide">Weather Stations</p>
                <Cloud className="w-4 h-4 text-sky-400" />
              </div>
              <p className="text-3xl font-bold text-white">{weather.length}</p>
            </div>
            <div className="bg-gradient-to-br from-amber-900/40 to-amber-800/20 border border-amber-700/30 p-4 rounded-xl backdrop-blur-sm">
              <div className="flex items-center justify-between mb-2">
                <p className="text-xs font-medium text-amber-300 uppercase tracking-wide">Air Quality</p>
                <Wind className="w-4 h-4 text-amber-400" />
              </div>
              <p className="text-3xl font-bold text-white">{airQuality.length}</p>
            </div>
            <div className="bg-gradient-to-br from-purple-900/40 to-purple-800/20 border border-purple-700/30 p-4 rounded-xl backdrop-blur-sm">
              <div className="flex items-center justify-between mb-2">
                <p className="text-xs font-medium text-purple-300 uppercase tracking-wide">Traffic Patterns</p>
                <Activity className="w-4 h-4 text-purple-400" />
              </div>
              <p className="text-3xl font-bold text-white">{patterns.length}</p>
            </div>
          </div>
        )}
      </div>

      {/* Map Legend */}
      <div className="border-b border-gray-700">
        <button
          onClick={() => toggleSection('legend')}
          className="w-full p-4 flex items-center justify-between hover:bg-gray-800/50 transition-colors"
        >
          <div className="flex items-center space-x-2">
            <Layers className="w-5 h-5 text-yellow-400" />
            <h2 className="text-lg font-semibold">Map Legend</h2>
          </div>
          {expandedSections.legend ? (
            <ChevronUp className="w-5 h-5" />
          ) : (
            <ChevronDown className="w-5 h-5" />
          )}
        </button>
        {expandedSections.legend && (
          <div className="px-4 pb-4 space-y-4">
            {/* Traffic Congestion Legend */}
            <div>
              <h4 className="text-xs font-bold text-gray-300 mb-2 uppercase tracking-wide">
                Traffic Congestion
              </h4>
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <div className="w-6 h-4 bg-green-500 rounded border border-green-600"></div>
                  <span className="text-xs text-gray-300">Low (Free Flow)</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-6 h-4 bg-yellow-400 rounded border border-yellow-500"></div>
                  <span className="text-xs text-gray-300">Medium (Moderate)</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-6 h-4 bg-orange-500 rounded border border-orange-600"></div>
                  <span className="text-xs text-gray-300">High (Heavy)</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-6 h-4 bg-red-600 rounded border border-red-700"></div>
                  <span className="text-xs text-gray-300">Severe</span>
                </div>
              </div>
            </div>

            {/* AQI Levels Legend */}
            <div className="border-t border-gray-700 pt-3">
              <h4 className="text-xs font-bold text-gray-300 mb-2 uppercase tracking-wide">
                AQI Levels
              </h4>
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <div className="w-6 h-4 bg-green-500 rounded border border-green-600"></div>
                  <span className="text-xs text-gray-300">Good (0-50)</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-6 h-4 bg-yellow-400 rounded border border-yellow-500"></div>
                  <span className="text-xs text-gray-300">Moderate (51-100)</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-6 h-4 bg-orange-500 rounded border border-orange-600"></div>
                  <span className="text-xs text-gray-300">Unhealthy (101-150)</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-6 h-4 bg-red-600 rounded border border-red-700"></div>
                  <span className="text-xs text-gray-300">Very Unhealthy (151-200)</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-6 h-4 bg-purple-600 rounded border border-purple-700"></div>
                  <span className="text-xs text-gray-300">Hazardous (200+)</span>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Weather View Controls */}
      <div className="border-b border-gray-700">
        <button
          onClick={() => toggleSection('weather')}
          className="w-full p-4 flex items-center justify-between hover:bg-gray-800/50 transition-colors"
        >
          <div className="flex items-center space-x-2">
            <Cloud className="w-5 h-5 text-sky-400" />
            <h2 className="text-lg font-semibold">Weather View</h2>
          </div>
          {expandedSections.weather ? (
            <ChevronUp className="w-5 h-5" />
          ) : (
            <ChevronDown className="w-5 h-5" />
          )}
        </button>
        {expandedSections.weather && (
          <div className="px-4 pb-4 space-y-2">
            <p className="text-xs text-gray-400 mb-2">Select weather data to display on map:</p>
            <button className="w-full py-2 px-3 rounded-lg text-sm font-medium bg-blue-500 text-white shadow-lg">
              All Weather Data
            </button>
            <button className="w-full py-2 px-3 rounded-lg text-sm font-medium bg-gray-700 text-gray-300 hover:bg-gray-600 transition-colors">
              Temperature Only
            </button>
            <button className="w-full py-2 px-3 rounded-lg text-sm font-medium bg-gray-700 text-gray-300 hover:bg-gray-600 transition-colors">
              Rain/Precipitation
            </button>
            <button className="w-full py-2 px-3 rounded-lg text-sm font-medium bg-gray-700 text-gray-300 hover:bg-gray-600 transition-colors">
              Wind Direction & Speed
            </button>
          </div>
        )}
      </div>

      {/* Accident Timeline */}
      <div className="border-b border-gray-700">
        <button
          onClick={() => toggleSection('accidents')}
          className="w-full p-4 flex items-center justify-between hover:bg-gray-800/50 transition-colors"
        >
          <div className="flex items-center space-x-2">
            <AlertTriangle className="w-5 h-5 text-rose-400" />
            <h2 className="text-lg font-semibold">Accident Timeline</h2>
          </div>
          {expandedSections.accidents ? (
            <ChevronUp className="w-5 h-5" />
          ) : (
            <ChevronDown className="w-5 h-5" />
          )}
        </button>
        {expandedSections.accidents && (
          <div className="px-4 pb-4 space-y-2">
            <p className="text-xs text-gray-400 mb-2">Filter accidents by time:</p>
            <button className="w-full py-2 px-3 rounded-lg text-sm font-medium bg-gray-700 text-gray-300 hover:bg-gray-600 transition-colors">
              Last Hour
            </button>
            <button className="w-full py-2 px-3 rounded-lg text-sm font-medium bg-gray-700 text-gray-300 hover:bg-gray-600 transition-colors">
              Last 6 Hours
            </button>
            <button className="w-full py-2 px-3 rounded-lg text-sm font-medium bg-gray-700 text-gray-300 hover:bg-gray-600 transition-colors">
              Last 24 Hours
            </button>
            <button className="w-full py-2 px-3 rounded-lg text-sm font-medium bg-gray-700 text-gray-300 hover:bg-gray-600 transition-colors">
              Last 7 Days
            </button>
            <button className="w-full py-2 px-3 rounded-lg text-sm font-medium bg-red-500 text-white shadow-lg">
              All Time
            </button>
            <div className="mt-3 pt-3 border-t border-gray-600 text-xs text-gray-400">
              <div><strong className="text-white">{activeAccidents.length}</strong> active accidents</div>
              <div className="mt-1">Auto-refresh: 60s</div>
            </div>
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="p-4 border-t border-gray-700 bg-gray-800/50">
        <p className="text-xs text-gray-400 text-center">
          © 2025 HCMC Traffic Monitor
        </p>
      </div>
    </div>
  );
};

export default Sidebar;
