import React, { useState, useEffect, useCallback } from 'react';
import { useMap } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet.heat';

declare module 'leaflet' {
  function heatLayer(
    latlngs: [number, number, number][],
    options?: HeatLayerOptions
  ): any;

  interface HeatLayerOptions {
    minOpacity?: number;
    maxZoom?: number;
    max?: number;
    radius?: number;
    blur?: number;
    gradient?: { [key: number]: string };
  }
}

interface VehicleHeatmapProps {
  visible?: boolean;
}

interface HeatmapPoint {
  lat: number;
  lng: number;
  intensity: number;
}

interface VehicleHeatmapResponse {
  success: boolean;
  data: {
    heatmapData: HeatmapPoint[];
    metadata: {
      totalPoints: number;
      maxIntensity: number;
      minIntensity: number;
      timestamp: string;
    };
  };
}

export const VehicleHeatmap: React.FC<VehicleHeatmapProps> = ({ visible = false }) => {
  // Early return BEFORE any hooks
  if (!visible) return null;

  const map = useMap();
  const [heatmapData, setHeatmapData] = useState<HeatmapPoint[]>([]);
  const [heatLayer, setHeatLayer] = useState<any>(null);

  // Heatmap configuration
  const heatmapConfig = {
    radius: 40,
    blur: 25,
    maxZoom: 18,
    max: 1.0,
    gradient: {
      0.0: 'blue',
      0.5: 'yellow',
      0.8: 'orange',
      1.0: 'red',
    },
  };

  const fetchHeatmapData = useCallback(async () => {
    try {
      const response = await fetch('http://localhost:3001/api/patterns/vehicle-heatmap');

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const result: VehicleHeatmapResponse = await response.json();

      if (result.success && result.data.heatmapData) {
        setHeatmapData(result.data.heatmapData);
      }
    } catch (err) {
      console.error('Error fetching vehicle heatmap:', err);
    }
  }, []);

  useEffect(() => {
    if (visible) {
      fetchHeatmapData();
    }
  }, [visible, fetchHeatmapData]);

  useEffect(() => {
    if (!map || !visible) {
      if (heatLayer) {
        map?.removeLayer(heatLayer);
        setHeatLayer(null);
      }
      return;
    }

    // Remove existing layer
    if (heatLayer) {
      map.removeLayer(heatLayer);
    }

    if (heatmapData.length === 0) {
      return;
    }

    // Convert data to leaflet.heat format: [lat, lng, intensity]
    // Filter out invalid coordinates
    const heatPoints: [number, number, number][] = heatmapData
      .filter(point =>
        point?.lat != null &&
        point?.lng != null &&
        point?.intensity != null &&
        !isNaN(point.lat) &&
        !isNaN(point.lng) &&
        !isNaN(point.intensity)
      )
      .map(point => [
        point.lat,
        point.lng,
        point.intensity,
      ]);

    // Don't create heatmap if no valid points
    if (heatPoints.length === 0) {
      return;
    }

    // Create heat layer
    const newHeatLayer = L.heatLayer(heatPoints, heatmapConfig);
    newHeatLayer.addTo(map);
    setHeatLayer(newHeatLayer);

    return () => {
      if (newHeatLayer) {
        map.removeLayer(newHeatLayer);
      }
    };
  }, [map, heatmapData, visible]);

  return (
    <>
      {/* Control Panel removed - toggle available in Sidebar (Layer Visibility -> Vehicle Heatmap) */}
      {/* Heatmap layer is controlled via useEffect */}
    </>
  );
};

export default VehicleHeatmap;
