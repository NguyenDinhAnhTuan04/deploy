import React, { useState, useMemo, useEffect } from 'react';
import { useMap } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet.heat';
import { useTrafficStore } from '../store/trafficStore';

interface AQIHeatmapProps {
  visible?: boolean;
}

declare module 'leaflet' {
  function heatLayer(
    latlngs: Array<[number, number, number]>,
    options?: {
      radius?: number;
      blur?: number;
      maxZoom?: number;
      max?: number;
      gradient?: Record<number, string>;
    }
  ): L.Layer;
}

const AQIHeatmap: React.FC<AQIHeatmapProps> = ({ visible = true }) => {
  const map = useMap();
  const { airQuality } = useTrafficStore();
  const [showLegend, setShowLegend] = useState(true);
  const [heatLayer, setHeatLayer] = useState<L.Layer | null>(null);

  const heatmapData = useMemo(() => {
    return airQuality
      .filter((aq) =>
        aq?.location?.latitude != null &&
        aq?.location?.longitude != null &&
        !isNaN(aq.location.latitude) &&
        !isNaN(aq.location.longitude) &&
        aq.aqi != null &&
        !isNaN(aq.aqi)
      )
      .map((aq) => {
        const intensity = Math.min(aq.aqi / 300, 1);
        return [aq.location.latitude, aq.location.longitude, intensity] as [number, number, number];
      });
  }, [airQuality]);

  useEffect(() => {
    if (!map || !visible || heatmapData.length === 0) {
      if (heatLayer) {
        map.removeLayer(heatLayer);
        setHeatLayer(null);
      }
      return;
    }

    if (heatLayer) {
      map.removeLayer(heatLayer);
    }

    const newHeatLayer = L.heatLayer(heatmapData, {
      radius: 30,
      blur: 20,
      maxZoom: 14,
      max: 1.0,
      gradient: {
        0.0: '#00ff00',
        0.3: '#ffff00',
        0.6: '#ff8800',
        0.8: '#ff0000',
        1.0: '#800080',
      },
    });

    newHeatLayer.addTo(map);
    setHeatLayer(newHeatLayer);

    return () => {
      if (newHeatLayer) {
        map.removeLayer(newHeatLayer);
      }
    };
  }, [map, visible, heatmapData]);

  return (
    <>
      {/* Legend removed - AQI levels shown in Sidebar (Map Legend section) */}
    </>
  );
};

export default AQIHeatmap;
