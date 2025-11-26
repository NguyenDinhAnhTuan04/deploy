import { useEffect, useRef, useState, useCallback } from 'react';
import { useTrafficStore } from '../store/trafficStore';
import { WebSocketMessage, Camera, Weather, AirQuality, Accident, TrafficPattern } from '../types';
import { useNotification } from '../components/NotificationProvider';

interface WebSocketConfig {
  url: string;
  reconnectInterval?: number;
  maxReconnectAttempts?: number;
  heartbeatInterval?: number;
}

interface WebSocketState {
  connected: boolean;
  connecting: boolean;
  error: Error | null;
  reconnectCount: number;
  lastMessage: WebSocketMessage | null;
}

export const useWebSocket = (config: WebSocketConfig) => {
  const {
    url = import.meta.env.VITE_WS_URL || 'ws://localhost:5001',
    reconnectInterval = 3000,
    maxReconnectAttempts = Infinity,
    heartbeatInterval = 10000
  } = config;

  const [state, setState] = useState<WebSocketState>({
    connected: false,
    connecting: false,
    error: null,
    reconnectCount: 0,
    lastMessage: null
  });

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<number | null>(null);
  const heartbeatIntervalRef = useRef<number | null>(null);
  const reconnectAttemptsRef = useRef(0);

  const store = useTrafficStore();
  const { showNotification } = useNotification();

  // Calculate exponential backoff delay
  const getReconnectDelay = useCallback(() => {
    const baseDelay = reconnectInterval;
    const maxDelay = 30000; // 30 seconds max
    const delay = Math.min(baseDelay * Math.pow(2, reconnectAttemptsRef.current), maxDelay);
    return delay;
  }, [reconnectInterval]);

  // Start heartbeat ping
  const startHeartbeat = useCallback(() => {
    if (heartbeatIntervalRef.current) {
      clearInterval(heartbeatIntervalRef.current);
    }

    heartbeatIntervalRef.current = window.setInterval(() => {
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        try {
          wsRef.current.send(JSON.stringify({
            type: 'ping',
            timestamp: new Date().toISOString()
          }));
        } catch (error) {
          console.error('Error sending heartbeat:', error);
        }
      }
    }, heartbeatInterval);
  }, [heartbeatInterval]);

  // Stop heartbeat
  const stopHeartbeat = useCallback(() => {
    if (heartbeatIntervalRef.current) {
      clearInterval(heartbeatIntervalRef.current);
      heartbeatIntervalRef.current = null;
    }
  }, []);

  // Handle incoming WebSocket messages
  const handleMessage = useCallback((event: MessageEvent) => {
    try {
      const message: WebSocketMessage = JSON.parse(event.data);

      setState(prev => ({
        ...prev,
        lastMessage: message,
        error: null
      }));

      // Handle different message types
      switch (message.type) {
        case 'initial':
          // Initial data load
          if (message.data) {
            if (message.data.cameras) store.setCameras(message.data.cameras);
            if (message.data.weather) store.setWeather(message.data.weather);
            if (message.data.airQuality) store.setAirQuality(message.data.airQuality);
            if (message.data.accidents) store.setAccidents(message.data.accidents);
            if (message.data.patterns) store.setPatterns(message.data.patterns);
          }
          break;

        // Batch updates from backend (plural)
        case 'cameras':
          if (message.data && Array.isArray(message.data)) {
            message.data.forEach((camera: Camera) => store.addCamera(camera));
            console.log(`📹 Received ${message.data.length} camera updates`);
          }
          break;

        case 'weathers':
          if (message.data && Array.isArray(message.data)) {
            message.data.forEach((weather: Weather) => store.addWeather(weather));
            console.log(`🌤️ Received ${message.data.length} weather updates`);
          }
          break;

        case 'air_qualities':
          if (message.data && Array.isArray(message.data)) {
            message.data.forEach((airQuality: AirQuality) => store.addAirQuality(airQuality));
            console.log(`💨 Received ${message.data.length} air quality updates`);
          }
          break;

        case 'accidents':
          if (message.data && Array.isArray(message.data)) {
            message.data.forEach((accident: Accident) => store.addAccident(accident));
            console.log(`🚨 Received ${message.data.length} accident updates`);
          }
          break;

        case 'patterns':
          if (message.data && Array.isArray(message.data)) {
            message.data.forEach((pattern: TrafficPattern) => store.addPattern(pattern));
            console.log(`📊 Received ${message.data.length} pattern updates`);
          }
          break;

        // Single updates (backward compatibility)
        case 'camera_update':
        case 'camera':
          // Update or add camera
          if (message.data) {
            const camera = message.data as Camera;
            store.addCamera(camera);
          }
          break;

        case 'weather_update':
        case 'weather':
          // Update or add weather data
          if (message.data) {
            const weather = message.data as Weather;
            store.addWeather(weather);
          }
          break;

        case 'aqi_update':
        case 'air_quality':
          // Update or add air quality data
          if (message.data) {
            const airQuality = message.data as AirQuality;
            store.addAirQuality(airQuality);
          }
          break;

        case 'new_accident':
        case 'accident':
          // Add new accident
          if (message.data) {
            const accident = message.data as Accident;
            store.addAccident(accident);

            // Show notification for new accident
            showNotification({
              type: accident.severity === 'fatal' || accident.severity === 'severe' ? 'error' : 'warning',
              title: 'New Accident Detected',
              message: `${accident.type} accident at ${accident.location.address}`,
              location: { latitude: accident.location.latitude, longitude: accident.location.longitude }
            });
          }
          break;

        case 'accident_alert':
          // High priority accident alert
          if (message.data) {
            const accident = message.data as Accident;
            store.addAccident(accident);

            // Show urgent error notification for severe accidents
            showNotification({
              type: 'error',
              title: '🚨 URGENT: Severe Accident',
              message: `${accident.type} accident with ${accident.severity} severity at ${accident.location.address}`,
              location: { latitude: accident.location.latitude, longitude: accident.location.longitude },
              duration: 10000 // 10 seconds for urgent alerts
            });
          }
          break;

        case 'aqi_warning':
          // AQI warning notification
          if (message.data) {
            const airQuality = message.data as AirQuality;
            store.addAirQuality(airQuality);

            // Show warning notification
            showNotification({
              type: 'warning',
              title: 'Air Quality Warning',
              message: `High AQI detected: ${airQuality.aqi} (${airQuality.level})`,
              location: { latitude: airQuality.location.latitude, longitude: airQuality.location.longitude }
            });
          }
          break;

        case 'pattern_change':
        case 'pattern':
          // Update traffic pattern
          if (message.data) {
            const pattern = message.data as TrafficPattern;
            store.addPattern(pattern);
          }
          break;

        case 'pong':
          // Heartbeat response - connection is alive
          break;

        case 'connection':
        case 'subscribed':
          // Connection confirmation
          console.log('WebSocket connection confirmed:', message.message);
          break;

        case 'update':
          // Generic update message
          if (message.data) {
            console.log('Generic update received:', message.data);
          }
          break;

        default:
          console.warn('Unknown message type:', message.type);
      }
    } catch (error) {
      console.error('Error parsing WebSocket message:', error);
      setState(prev => ({
        ...prev,
        error: error as Error
      }));
    }
  }, [store]);

  // Connect to WebSocket
  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN ||
      wsRef.current?.readyState === WebSocket.CONNECTING) {
      return;
    }

    setState(prev => ({ ...prev, connecting: true, error: null }));

    try {
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log('WebSocket connected');
        setState(prev => ({
          ...prev,
          connected: true,
          connecting: false,
          error: null,
          reconnectCount: 0
        }));

        store.setIsConnected(true);
        reconnectAttemptsRef.current = 0;
        startHeartbeat();

        // Subscribe to updates
        ws.send(JSON.stringify({
          type: 'subscribe',
          channels: ['cameras', 'weather', 'air_quality', 'accidents', 'patterns'],
          timestamp: new Date().toISOString()
        }));
      };

      ws.onmessage = handleMessage;

      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        setState(prev => ({
          ...prev,
          error: new Error('WebSocket connection error'),
          connecting: false
        }));
      };

      ws.onclose = (event) => {
        console.log('WebSocket closed:', event.code, event.reason);
        setState(prev => ({
          ...prev,
          connected: false,
          connecting: false
        }));

        store.setIsConnected(false);
        stopHeartbeat();

        // Attempt reconnect if not manually closed
        if (event.code !== 1000 && reconnectAttemptsRef.current < maxReconnectAttempts) {
          reconnectAttemptsRef.current++;
          const delay = getReconnectDelay();

          console.log(`Reconnecting in ${delay}ms... (attempt ${reconnectAttemptsRef.current})`);

          setState(prev => ({
            ...prev,
            reconnectCount: reconnectAttemptsRef.current
          }));

          reconnectTimeoutRef.current = window.setTimeout(() => {
            connect();
          }, delay);
        } else if (reconnectAttemptsRef.current >= maxReconnectAttempts) {
          setState(prev => ({
            ...prev,
            error: new Error('Max reconnect attempts reached')
          }));
        }
      };
    } catch (error) {
      console.error('Error creating WebSocket:', error);
      setState(prev => ({
        ...prev,
        error: error as Error,
        connecting: false
      }));
    }
  }, [url, maxReconnectAttempts, getReconnectDelay, handleMessage, startHeartbeat, stopHeartbeat, store]);

  // Disconnect from WebSocket
  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    stopHeartbeat();

    if (wsRef.current) {
      wsRef.current.close(1000, 'Manual disconnect');
      wsRef.current = null;
    }

    reconnectAttemptsRef.current = 0;
    setState({
      connected: false,
      connecting: false,
      error: null,
      reconnectCount: 0,
      lastMessage: null
    });

    store.setIsConnected(false);
  }, [stopHeartbeat, store]);

  // Send message through WebSocket
  const send = useCallback((data: any) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      try {
        wsRef.current.send(JSON.stringify(data));
        return true;
      } catch (error) {
        console.error('Error sending WebSocket message:', error);
        setState(prev => ({
          ...prev,
          error: error as Error
        }));
        return false;
      }
    }
    return false;
  }, []);

  // Connect on mount
  useEffect(() => {
    connect();

    return () => {
      disconnect();
    };
  }, [url]); // Only reconnect if URL changes

  return {
    connected: state.connected,
    connecting: state.connecting,
    error: state.error,
    reconnectCount: state.reconnectCount,
    lastMessage: state.lastMessage,
    connect,
    disconnect,
    send
  };
};

export default useWebSocket;
