# 🎨 Frontend WebSocket Handler Update Guide

**Purpose**: Hướng dẫn cập nhật frontend để nhận batch messages từ backend

---

## 📋 Summary

Backend đã được tối ưu để gửi **batch messages** (nhiều entities cùng lúc) thay vì individual messages.

**Before**: 240 messages/30s  
**After**: 4 messages/60s  
**Reduction**: 99.2%

Frontend cần cập nhật để xử lý cả 2 formats:
- ✅ Single message (backward compatible)
- ✅ Batch message (new format)

---

## 🔧 Changes Required

### File Location

Tìm file WebSocket handler trong frontend:
- `src/services/websocketService.ts`
- `src/services/websocket.ts`
- `src/utils/websocket.ts`
- Hoặc file tương tự xử lý WebSocket

---

## 💻 Code Updates

### 1. Update Message Handler

**Before (Current Code)**:
```typescript
ws.onmessage = (event) => {
  const message = JSON.parse(event.data);
  
  switch (message.type) {
    case 'camera':
      // Handle single camera
      updateMap(message.data);
      break;
      
    case 'weather':
      // Handle single weather
      updateWeather(message.data);
      break;
      
    case 'air_quality':
      // Handle single air quality
      updateAirQuality(message.data);
      break;
      
    case 'accident':
      // Handle single accident
      updateAccident(message.data);
      break;
  }
};
```

---

**After (Updated Code)**:
```typescript
ws.onmessage = (event) => {
  const message = JSON.parse(event.data);
  
  switch (message.type) {
    // ========== CAMERAS ==========
    case 'camera':
      // Single camera (backward compatible)
      updateCamera(message.data);
      break;
      
    case 'cameras':
      // Batch cameras (NEW)
      if (Array.isArray(message.data)) {
        message.data.forEach(camera => updateCamera(camera));
      }
      break;
    
    // ========== WEATHER ==========
    case 'weather':
      // Single weather (backward compatible)
      updateWeather(message.data);
      break;
      
    case 'weathers':
      // Batch weathers (NEW)
      if (Array.isArray(message.data)) {
        message.data.forEach(weather => updateWeather(weather));
      }
      break;
    
    // ========== AIR QUALITY ==========
    case 'air_quality':
      // Single air quality (backward compatible)
      updateAirQuality(message.data);
      break;
      
    case 'air_qualities':
      // Batch air qualities (NEW)
      if (Array.isArray(message.data)) {
        message.data.forEach(aqi => updateAirQuality(aqi));
      }
      break;
    
    // ========== ACCIDENTS ==========
    case 'accident':
      // Single accident (backward compatible)
      updateAccident(message.data);
      break;
      
    case 'accidents':
      // Batch accidents (NEW)
      if (Array.isArray(message.data)) {
        message.data.forEach(accident => updateAccident(accident));
      }
      break;
    
    // ========== TRAFFIC PATTERNS ==========
    case 'pattern':
      // Single pattern (backward compatible)
      updatePattern(message.data);
      break;
      
    case 'patterns':
      // Batch patterns (NEW)
      if (Array.isArray(message.data)) {
        message.data.forEach(pattern => updatePattern(pattern));
      }
      break;
  }
};
```

---

### 2. TypeScript Types (Optional but Recommended)

**Create/Update types file**: `src/types/websocket.ts`

```typescript
export type WebSocketMessageType =
  | 'camera'
  | 'cameras'
  | 'weather'
  | 'weathers'
  | 'air_quality'
  | 'air_qualities'
  | 'accident'
  | 'accidents'
  | 'pattern'
  | 'patterns'
  | 'update';

export interface Camera {
  id: string;
  location: { lat: number; lng: number };
  name: string;
  status: string;
  // ... other fields
}

export interface Weather {
  id: string;
  cameraId: string;
  location: { lat: number; lng: number };
  temperature: number;
  humidity: number;
  // ... other fields
}

export interface AirQuality {
  id: string;
  cameraId: string;
  location: { lat: number; lng: number };
  aqi: number;
  level: string;
  // ... other fields
}

export interface WebSocketMessage {
  type: WebSocketMessageType;
  data: any | any[]; // Single entity or array
  timestamp: string;
}
```

---

### 3. Generic Handler Function (Recommended)

Để tránh code duplication, tạo generic handler:

```typescript
/**
 * Handle both single and batch WebSocket messages
 */
function handleMessage(
  message: WebSocketMessage,
  singleType: string,
  batchType: string,
  handler: (data: any) => void
) {
  if (message.type === singleType) {
    // Single entity
    handler(message.data);
  } else if (message.type === batchType) {
    // Batch entities
    if (Array.isArray(message.data)) {
      message.data.forEach(item => handler(item));
    }
  }
}

// Usage:
ws.onmessage = (event) => {
  const message: WebSocketMessage = JSON.parse(event.data);
  
  // Handle cameras
  handleMessage(message, 'camera', 'cameras', updateCamera);
  
  // Handle weather
  handleMessage(message, 'weather', 'weathers', updateWeather);
  
  // Handle air quality
  handleMessage(message, 'air_quality', 'air_qualities', updateAirQuality);
  
  // Handle accidents
  handleMessage(message, 'accident', 'accidents', updateAccident);
  
  // Handle patterns
  handleMessage(message, 'pattern', 'patterns', updatePattern);
};
```

---

## 🧪 Testing

### 1. Console Logging

Thêm logging để verify messages:

```typescript
ws.onmessage = (event) => {
  const message = JSON.parse(event.data);
  
  console.log('📨 WebSocket message:', {
    type: message.type,
    count: Array.isArray(message.data) ? message.data.length : 1,
    timestamp: message.timestamp
  });
  
  // ... handle message
};
```

**Expected Output**:
```
📨 WebSocket message: { type: 'cameras', count: 40, timestamp: '...' }
📨 WebSocket message: { type: 'weathers', count: 100, timestamp: '...' }
📨 WebSocket message: { type: 'air_qualities', count: 100, timestamp: '...' }
```

---

### 2. Performance Check

```typescript
ws.onmessage = (event) => {
  const startTime = performance.now();
  
  const message = JSON.parse(event.data);
  // ... handle message
  
  const endTime = performance.now();
  console.log(`⏱️ Processed ${message.type} in ${endTime - startTime}ms`);
};
```

**Expected**: <50ms for batch of 100 items

---

### 3. UI Update Verification

Kiểm tra map updates mỗi 60 giây:

```typescript
let lastUpdateTime = Date.now();

ws.onmessage = (event) => {
  const now = Date.now();
  const timeSinceLastUpdate = (now - lastUpdateTime) / 1000;
  
  console.log(`🔄 Update received after ${timeSinceLastUpdate}s`);
  lastUpdateTime = now;
  
  // ... handle message
};
```

**Expected**: ~60 seconds between updates

---

## 🐛 Troubleshooting

### Issue 1: Not receiving batch messages

**Symptom**: Console still shows individual messages

**Solution**:
1. Restart backend: `npm run dev` (in backend folder)
2. Hard refresh frontend: Ctrl+Shift+R
3. Check backend logs for "in batch"

---

### Issue 2: Duplicate markers on map

**Symptom**: Multiple markers at same location

**Possible Cause**: Both single and batch handlers running

**Solution**:
```typescript
// Make sure to handle EITHER single OR batch, not both
if (message.type === 'cameras') {
  // Only handle batch
  message.data.forEach(updateCamera);
  return; // Exit early
}

if (message.type === 'camera') {
  // Only handle single
  updateCamera(message.data);
}
```

---

### Issue 3: Performance degradation

**Symptom**: UI freezes when receiving batch updates

**Solution**: Use requestAnimationFrame for batch updates

```typescript
case 'cameras':
  // Split into chunks to avoid blocking UI
  const chunkSize = 10;
  const chunks = [];
  
  for (let i = 0; i < message.data.length; i += chunkSize) {
    chunks.push(message.data.slice(i, i + chunkSize));
  }
  
  // Process chunks with RAF
  let chunkIndex = 0;
  const processChunk = () => {
    if (chunkIndex < chunks.length) {
      chunks[chunkIndex].forEach(updateCamera);
      chunkIndex++;
      requestAnimationFrame(processChunk);
    }
  };
  processChunk();
  break;
```

---

## 📊 Expected Results

### Before Optimization

```
14:00:00 📨 camera { count: 1 }
14:00:00 📨 camera { count: 1 }
14:00:00 📨 camera { count: 1 }
... (40 times)
14:00:02 📨 weather { count: 1 }
14:00:02 📨 weather { count: 1 }
... (100 times)
```

**Total**: 240 messages in 3-5 seconds

---

### After Optimization

```
14:00:00 📨 cameras { count: 40 }
14:00:01 📨 weathers { count: 100 }
14:00:01 📨 air_qualities { count: 100 }
14:00:01 📨 accidents { count: 0 }

... (wait 60 seconds)

14:01:00 📨 cameras { count: 40 }
14:01:01 📨 weathers { count: 100 }
...
```

**Total**: 4 messages in <1 second

---

## ✅ Verification Checklist

### Backend
- [x] Backend running without errors
- [x] Logs show "in batch" messages
- [x] Polling interval = 60 seconds
- [x] No PostgreSQL errors

### Frontend
- [ ] Updated message handler
- [ ] Added batch message types support
- [ ] Console shows batch messages
- [ ] Map updates every 60 seconds
- [ ] No duplicate markers
- [ ] No performance issues

---

## 🎯 Example Implementation (React)

```typescript
// src/hooks/useWebSocket.ts
import { useEffect, useRef } from 'react';

export function useWebSocket(url: string) {
  const ws = useRef<WebSocket | null>(null);
  
  useEffect(() => {
    ws.current = new WebSocket(url);
    
    ws.current.onopen = () => {
      console.log('✅ WebSocket connected');
    };
    
    ws.current.onmessage = (event) => {
      const message = JSON.parse(event.data);
      
      console.log('📨 Message:', {
        type: message.type,
        count: Array.isArray(message.data) ? message.data.length : 1
      });
      
      // Dispatch to Redux/Context or call handlers
      handleWebSocketMessage(message);
    };
    
    ws.current.onerror = (error) => {
      console.error('❌ WebSocket error:', error);
    };
    
    ws.current.onclose = () => {
      console.log('⚠️ WebSocket disconnected');
    };
    
    return () => {
      ws.current?.close();
    };
  }, [url]);
  
  return ws;
}

// Handler function
function handleWebSocketMessage(message: any) {
  switch (message.type) {
    case 'cameras':
      store.dispatch(updateCameras(message.data));
      break;
    case 'weathers':
      store.dispatch(updateWeathers(message.data));
      break;
    // ... etc
  }
}
```

---

## 📚 Additional Resources

- Backend optimization: `PERFORMANCE_OPTIMIZATION.md`
- Architecture guide: `DATA_ACCESS_GUIDE.md`
- Refactoring details: `BACKEND_REFACTORING_COMPLETE.md`

---

**Status**: Ready for implementation  
**Estimated Time**: 30-60 minutes  
**Difficulty**: Easy to Medium
