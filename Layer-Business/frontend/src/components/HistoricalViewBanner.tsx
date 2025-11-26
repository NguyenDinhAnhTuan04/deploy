import React from 'react';
import { Clock, AlertTriangle, X } from 'lucide-react';

interface HistoricalViewBannerProps {
  timestamp: Date;
  dataCount: {
    weather: number;
    airQuality: number;
    patterns: number;
    accidents: number;
  };
  onClose?: () => void;
}

const HistoricalViewBanner: React.FC<HistoricalViewBannerProps> = ({ timestamp, dataCount, onClose }) => {
  return (
    <div className="fixed top-4 left-1/2 transform -translate-x-1/2 z-[1000] pointer-events-none animate-slide-in-right">
      <div className="bg-gradient-to-r from-purple-600 via-purple-500 to-fuchsia-600 text-white px-4 py-2 rounded-xl shadow-2xl border border-white/30 backdrop-blur-sm pointer-events-auto">
        <div className="flex items-center gap-3">
          {/* Icon */}
          <div className="flex-shrink-0 bg-white/20 rounded-full p-1.5">
            <Clock className="w-4 h-4 animate-pulse" />
          </div>

          {/* Content */}
          <div>
            <div className="font-bold text-sm mb-0.5 flex items-center gap-2">
              Historical View Mode
            </div>
            <div className="text-xs opacity-95 font-medium">
              Viewing data from{' '}
              <span className="font-bold bg-white/20 px-1.5 py-0.5 rounded">
                {timestamp.toLocaleDateString('en-US', {
                  weekday: 'short',
                  year: 'numeric',
                  month: 'short',
                  day: 'numeric'
                })}
                {' at '}
                {timestamp.toLocaleTimeString('en-US', {
                  hour: '2-digit',
                  minute: '2-digit'
                })}
              </span>
            </div>
          </div>

          {/* Stats */}
          <div className="flex gap-2 ml-3 border-l border-white/30 pl-3">
            <div className="text-center bg-white/10 px-2 py-1 rounded-lg">
              <div className="text-base font-bold">{dataCount.weather}</div>
              <div className="text-[9px] opacity-80 uppercase tracking-wide">Weather</div>
            </div>
            <div className="text-center bg-white/10 px-2 py-1 rounded-lg">
              <div className="text-base font-bold">{dataCount.airQuality}</div>
              <div className="text-[9px] opacity-80 uppercase tracking-wide">AQI</div>
            </div>
            <div className="text-center bg-white/10 px-2 py-1 rounded-lg">
              <div className="text-base font-bold">{dataCount.patterns}</div>
              <div className="text-[9px] opacity-80 uppercase tracking-wide">Patterns</div>
            </div>
            <div className="text-center bg-white/10 px-2 py-1 rounded-lg">
              <div className="text-base font-bold">{dataCount.accidents}</div>
              <div className="text-[9px] opacity-80 uppercase tracking-wide">Accidents</div>
            </div>
          </div>

          {/* Warning Icon */}
          <div className="flex-shrink-0">
            <div className="bg-yellow-400 text-purple-900 rounded-full p-1.5 shadow-lg">
              <AlertTriangle className="w-4 h-4" />
            </div>
          </div>

          {/* Close Button */}
          {onClose && (
            <button
              onClick={onClose}
              className="flex-shrink-0 ml-2 bg-red-600 hover:bg-red-700 rounded-lg p-2 transition-all hover:scale-110 active:scale-95 shadow-2xl border-2 border-white"
              title="Close Historical View"
            >
              <X className="w-5 h-5" strokeWidth={3} />
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

export default HistoricalViewBanner;
