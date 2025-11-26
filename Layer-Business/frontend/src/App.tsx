import React, { useEffect, useState, useRef } from 'react';
import TrafficMap from './components/TrafficMap';
import Sidebar from './components/Sidebar';
import AnalyticsDashboard from './components/AnalyticsDashboard';
import { NotificationProvider } from './components/NotificationProvider';
import ErrorBoundary from './components/ErrorBoundary';
import { wsService } from './services/websocket';
import { useTrafficStore } from './store/trafficStore';
import './index.css';

const App: React.FC = () => {
  const { loadAllData, loading, error } = useTrafficStore();
  const [isAnalyticsOpen, setIsAnalyticsOpen] = useState(false);
  const [isInitialized, setIsInitialized] = useState(false);
  const trafficMapRef = useRef<any>(null);

  useEffect(() => {
    // Load initial data using store method
    const initializeApp = async () => {
      try {
        await loadAllData();
        setIsInitialized(true);

        // Connect WebSocket after data is loaded
        wsService.connect();
      } catch (err) {
        console.error('Failed to initialize app:', err);
        setIsInitialized(true); // Still mark as initialized to show the UI
      }
    };

    initializeApp();

    return () => {
      wsService.disconnect();
    };
  }, [loadAllData]);

  // Show loading screen while initializing
  if (!isInitialized || loading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gray-900">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-16 w-16 border-t-4 border-b-4 border-blue-500 mb-4"></div>
          <p className="text-white text-xl">Đang tải dữ liệu...</p>
          <p className="text-gray-400 text-sm mt-2">Vui lòng đợi trong giây lát</p>
        </div>
      </div>
    );
  }

  // Show error state if there's a critical error
  if (error && !isInitialized) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gray-900">
        <div className="text-center max-w-md">
          <div className="text-red-500 text-6xl mb-4">⚠️</div>
          <p className="text-white text-xl mb-2">Không thể tải dữ liệu</p>
          <p className="text-gray-400 text-sm mb-4">{error}</p>
          <button
            onClick={() => window.location.reload()}
            className="px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-semibold transition-colors"
          >
            Thử lại
          </button>
        </div>
      </div>
    );
  }

  return (
    <ErrorBoundary>
      <NotificationProvider maxToasts={3}>
        <div className="flex h-screen w-screen overflow-hidden bg-gray-900">
          <Sidebar
            onCameraSelect={(camera) => trafficMapRef.current?.handleCameraClick?.(camera)}
            onZoomToCamera={(camera) => trafficMapRef.current?.handleZoomToCamera?.(camera)}
            onZoomToDistrict={(bounds, center) => trafficMapRef.current?.handleZoomToDistrict?.(bounds, center)}
          />
          <div className="flex-1 relative">
            <TrafficMap ref={trafficMapRef} />
            <AnalyticsDashboard
              isOpen={isAnalyticsOpen}
              onToggle={() => setIsAnalyticsOpen(!isAnalyticsOpen)}
            />
          </div>
        </div>
      </NotificationProvider>
    </ErrorBoundary>
  );
};

export default App;
