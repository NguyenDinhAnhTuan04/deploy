import React from 'react';
import { Wifi, WifiOff, Loader2, AlertTriangle } from 'lucide-react';

interface ConnectionStatusProps {
  connected: boolean;
  connecting: boolean;
  error: Error | null;
  reconnectCount?: number;
}

const ConnectionStatus: React.FC<ConnectionStatusProps> = ({
  connected,
  connecting,
  error,
  reconnectCount = 0
}) => {
  const getStatusConfig = () => {
    if (error) {
      return {
        bgColor: 'bg-gradient-to-r from-red-500 to-red-600',
        text: 'Connection Error',
        Icon: AlertTriangle,
        pulse: false,
        iconColor: 'text-white'
      };
    }
    if (connecting || reconnectCount > 0) {
      return {
        bgColor: 'bg-gradient-to-r from-amber-500 to-orange-500',
        text: reconnectCount > 0 ? `Reconnecting (${reconnectCount})...` : 'Connecting...',
        Icon: Loader2,
        pulse: true,
        iconColor: 'text-white'
      };
    }
    if (connected) {
      return {
        bgColor: 'bg-gradient-to-r from-emerald-500 to-green-600',
        text: 'Connected',
        Icon: Wifi,
        pulse: false,
        iconColor: 'text-white'
      };
    }
    return {
      bgColor: 'bg-gradient-to-r from-gray-500 to-gray-600',
      text: 'Disconnected',
      Icon: WifiOff,
      pulse: false,
      iconColor: 'text-white'
    };
  };

  const status = getStatusConfig();
  const Icon = status.Icon;

  return (
    <div className={`fixed top-4 right-4 z-[9999] ${status.bgColor} rounded-xl shadow-2xl border border-white/20 backdrop-blur-sm px-4 py-2.5 flex items-center gap-3 animate-slide-in-right`}>
      <div className="relative flex items-center justify-center">
        <Icon
          className={`w-5 h-5 ${status.iconColor} ${status.pulse ? 'animate-spin' : ''}`}
        />
      </div>
      <div>
        <div className="text-sm font-semibold text-white">{status.text}</div>
        {error && (
          <div className="text-xs text-white/90 mt-0.5">{error.message}</div>
        )}
      </div>
    </div>
  );
};

export default ConnectionStatus;
