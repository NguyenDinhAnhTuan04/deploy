# 🧪 TESTING GUIDE - Traffic Management System

## Prerequisites

Before testing, ensure the following services are running:

```bash
# 1. Backend API Server (Port 8080)
cd backend
npm run dev

# 2. WebSocket Server (Port 8081)
# (Usually started with backend)

# 3. Fuseki SPARQL Endpoint (Port 3030)
# Make sure Fuseki is running with the 'traffic' dataset

# 4. Frontend Development Server (Port 5173)
cd frontend
npm run dev
```

---

## 🎯 MANUAL TESTING PROCEDURES

### 1. API Service Layer Testing

#### Test Cache Functionality
```typescript
// Open browser console and run:
import { api } from './services/api';

// First call - should fetch from API
console.time('First call');
await api.cameras.getAll();
console.timeEnd('First call');

// Second call within 30s - should return from cache
console.time('Cached call');
await api.cameras.getAll();
console.timeEnd('Cached call'); // Should be < 5ms

// Wait 31 seconds and call again - should fetch from API
```

**Expected Results:**
- ✅ First call takes longer (network request)
- ✅ Second call is instantaneous (cached)
- ✅ After 30s, cache expires and fetches again

#### Test Retry Logic
```typescript
// Stop backend server temporarily
// Make API call
await api.cameras.getAll();

// Check console for retry attempts:
// [API] Retry 1/3 for /cameras
// [API] Retry 2/3 for /cameras
// [API] Retry 3/3 for /cameras
```

**Expected Results:**
- ✅ 3 retry attempts logged
- ✅ Exponential backoff: 1s, 2s, 4s delays
- ✅ Error thrown after 3 failed attempts

#### Test All Endpoints
```typescript
// Cameras
await api.cameras.getAll();
await api.cameras.getAll({ district: 'District 1' });
await api.cameras.getById('camera-1');

// Weather
await api.weather.getAll();
await api.weather.getAll('camera-1');

// Air Quality
await api.airQuality.getAll();
await api.airQuality.getAll({ level: 'Unhealthy', minAQI: 100 });

// Accidents
await api.accidents.getAll();
await api.accidents.getAll({ severity: 'severe', resolved: false });
await api.accidents.getByArea(10.8231, 106.6297, 5);
await api.accidents.getById('accident-1');

// Patterns
await api.patterns.getAll();
await api.patterns.getByRoadSegment('segment-1');
await api.patterns.getRoadSegments();

// Correlations
await api.correlations.getAll();
await api.correlations.getAccidentPatternCorrelation();

// Analytics
await api.analytics.getHotspots();

// Historical
await api.historical.getAQI({ days: 7, aggregation: 'daily' });

// Utilities
api.clearCache();
api.invalidateCache(/cameras/);
await api.healthCheck();
```

**Expected Results:**
- ✅ All endpoints return data without errors
- ✅ Filters are applied correctly
- ✅ Cache keys unique for different params

---

### 2. Zustand Store Testing

#### Test Initial Data Loading
```typescript
// In browser console:
const store = useTrafficStore.getState();

// Check initial state
console.log('Loading:', store.loading); // Should be false initially
console.log('Error:', store.error); // Should be null
console.log('Cameras:', store.cameras.length); // Should be 0

// Load data
await store.loadAllData();

// Check after loading
console.log('Loading:', store.loading); // Should be false
console.log('Cameras:', store.cameras.length); // Should be > 0
console.log('Last Update:', store.lastUpdate); // Should be Date object
```

**Expected Results:**
- ✅ `loading` is `true` during fetch
- ✅ `loading` is `false` after completion
- ✅ All arrays populated with data
- ✅ `lastUpdate` timestamp set

#### Test Filter Persistence
```typescript
// Update filters
store.updateFilters({
  districts: ['District 1', 'District 2'],
  severityFilter: ['severe', 'fatal']
});

// Refresh page
location.reload();

// After reload, check filters
const newStore = useTrafficStore.getState();
console.log(newStore.filters.districts); // Should be ['District 1', 'District 2']
console.log(newStore.filters.severityFilter); // Should be ['severe', 'fatal']
```

**Expected Results:**
- ✅ Filters persist after page refresh
- ✅ Other state (data arrays) resets
- ✅ localStorage contains 'traffic-store' key

#### Test Computed Values
```typescript
const store = useTrafficStore.getState();

// Add test data
store.updateFilters({ districts: ['District 1'] });

// Get filtered cameras
const cameras = store.getFilteredCameras();
console.log('Filtered cameras:', cameras);
// All cameras should be from District 1

// Get filtered accidents
store.updateFilters({ severityFilter: ['severe', 'fatal'] });
const accidents = store.getFilteredAccidents();
console.log('Severe accidents:', accidents);
// All accidents should be severe or fatal

// Get average AQI
const avgAQI = store.getAverageAQI();
console.log('Average AQI:', avgAQI);
// Should be number between 0-500

// Get accidents by district
const grouped = store.getAccidentsByDistrict();
console.log('Grouped accidents:', grouped);
// Should be object with district keys

// Get active patterns
const patterns = store.getActivePatterns();
console.log('Active patterns:', patterns);
// Should only include patterns active at current hour
```

**Expected Results:**
- ✅ Filtered data respects all filter criteria
- ✅ Multiple filters work together (AND logic)
- ✅ Computed values update when filters change
- ✅ No errors in console

---

### 3. Notification System Testing

#### Test All Notification Types
```typescript
const { showNotification } = useNotification();

// Info notification (blue)
showNotification({
  type: 'info',
  title: 'Information',
  message: 'This is an info message',
});
// Wait for auto-dismiss after 5 seconds

// Success notification (green)
showNotification({
  type: 'success',
  title: 'Success',
  message: 'Operation completed successfully',
});
// Wait for auto-dismiss after 5 seconds

// Warning notification (yellow)
showNotification({
  type: 'warning',
  title: 'Warning',
  message: 'Please check this warning',
});
// Wait for auto-dismiss after 5 seconds
// Should hear warning sound

// Error notification (red)
showNotification({
  type: 'error',
  title: 'Error',
  message: 'An error occurred',
});
// Wait for auto-dismiss after 10 seconds
// Should hear error sound
```

**Expected Results:**
- ✅ Info: Blue border, info icon, 5s auto-dismiss, no sound
- ✅ Success: Green border, checkmark icon, 5s auto-dismiss, no sound
- ✅ Warning: Yellow border, warning icon, 5s auto-dismiss, sound plays
- ✅ Error: Red border, error icon, 10s auto-dismiss, sound plays

#### Test Max 3 Toasts
```typescript
const { showNotification } = useNotification();

// Show 5 notifications rapidly
for (let i = 1; i <= 5; i++) {
  showNotification({
    type: 'info',
    title: `Notification ${i}`,
    message: `Message ${i}`,
  });
}

// Count visible toasts
const toasts = document.querySelectorAll('[role="alert"]');
console.log('Visible toasts:', toasts.length);
// Should be exactly 3
```

**Expected Results:**
- ✅ Only 3 toasts visible at a time
- ✅ Oldest toast removed when 4th is added (FIFO)
- ✅ All 5 notifications eventually displayed

#### Test Manual Close
```typescript
showNotification({
  type: 'info',
  title: 'Test',
  message: 'Click X to close',
});

// Click the X button
// Toast should slide out and disappear
```

**Expected Results:**
- ✅ Close button visible on hover
- ✅ Clicking X removes toast immediately
- ✅ Slide-out animation plays

#### Test Sound Toggle
```typescript
const { toggleSound } = useNotification();

// Disable sound
toggleSound(); // soundEnabled = false

// Show warning
showNotification({
  type: 'warning',
  title: 'Silent Warning',
  message: 'No sound should play',
});
// No sound should play

// Enable sound
toggleSound(); // soundEnabled = true

// Show warning again
showNotification({
  type: 'warning',
  title: 'Audible Warning',
  message: 'Sound should play',
});
// Sound should play
```

**Expected Results:**
- ✅ Sound plays when enabled
- ✅ Sound doesn't play when disabled
- ✅ Toggle state persists across notifications

#### Test "View on Map" Action
```typescript
showNotification({
  type: 'error',
  title: 'Accident Alert',
  message: 'Click to view on map',
  location: { latitude: 10.8231, longitude: 106.6297 },
  onViewOnMap: () => {
    console.log('Zoom to location');
    // Should zoom map to coordinates
  }
});

// Click "View on map" button
```

**Expected Results:**
- ✅ "View on map" button visible
- ✅ Clicking button calls onViewOnMap callback
- ✅ Map zooms to location
- ✅ Toast remains open after click

---

### 4. Time Machine Testing

#### Test Date Range Selection
```typescript
// Click "7 days" button
// Check date picker min/max bounds
const minDate = new Date();
minDate.setDate(minDate.getDate() - 7);
// Min date should be 7 days ago

// Click "14 days" button
// Min date should be 14 days ago

// Click "30 days" button
// Min date should be 30 days ago
```

**Expected Results:**
- ✅ Date picker bounds update correctly
- ✅ Selected date resets to today
- ✅ Time slider resets to 0

#### Test Time Slider
```typescript
// Drag slider to hour 12
// Check hour display shows "12:00"

// Drag to hour 23
// Check hour display shows "23:00"

// Check hour markers visible at: 00, 03, 06, 09, 12, 15, 18, 21
```

**Expected Results:**
- ✅ Slider updates hour display
- ✅ Hour markers visible every 3 hours
- ✅ Slider thumb is purple
- ✅ Hover effect scales thumb

#### Test Play/Pause
```typescript
// Select a date 7 days ago
// Set time to 00:00
// Click Play button

// Observe:
// - Hour increments every 1 second (at 1x speed)
// - Data refreshes each hour
// - Loading indicator shows during fetch

// Click Pause button
// - Animation stops
// - Hour remains at current value
```

**Expected Results:**
- ✅ Play button starts auto-advance
- ✅ Hour increments based on speed
- ✅ Pause button stops animation
- ✅ Data fetches each hour change
- ✅ Loading indicator shows during fetch

#### Test Speed Control
```typescript
// Click Play
// Click Speed button multiple times
// Observe speed changes: 1x → 2x → 4x → 8x → 1x

// At 2x: Hour increments every 500ms
// At 4x: Hour increments every 250ms
// At 8x: Hour increments every 125ms
```

**Expected Results:**
- ✅ Speed cycles through 1x/2x/4x/8x
- ✅ Animation speed matches selected speed
- ✅ Speed indicator updates

#### Test SPARQL Queries
```typescript
// Open browser DevTools Network tab
// Filter by "sparql"
// Click Play on Time Machine

// Check for 4 POST requests:
// 1. Weather query
// 2. AQI query
// 3. Traffic patterns query
// 4. Accidents query

// Check response data has results
```

**Expected Results:**
- ✅ 4 SPARQL queries executed
- ✅ Each query returns data
- ✅ No 500 errors
- ✅ Response time < 3s

#### Test Historical Data Display
```typescript
// Play time machine
// Check map updates with historical data:
// - Weather markers show historical temperature
// - AQI circles show historical pollution
// - Traffic patterns show historical congestion
// - Accident markers show historical incidents

// Verify banner shows:
// - Correct timestamp
// - Data counts (weather, AQI, patterns, accidents)
```

**Expected Results:**
- ✅ Map updates with historical data
- ✅ Banner displays correct timestamp
- ✅ Data counts match query results
- ✅ "Historical view" banner visible

#### Test Back to Live
```typescript
// Activate time machine
// Play historical data
// Click "Back to Live" button

// Verify:
// - Time machine closes
// - Banner disappears
// - Map shows live data
// - Current time restored
```

**Expected Results:**
- ✅ Time machine closes
- ✅ Banner removed
- ✅ Map shows current data
- ✅ WebSocket reconnects if needed

---

### 5. WebSocket Integration Testing

#### Test Connection
```typescript
// Open browser console
// Check for WebSocket messages:
// [WebSocket] Connected
// [WebSocket] Subscribed to: cameras, weather, air_quality, accidents, patterns

// Check connection status indicator
// Should show green "Connected"
```

**Expected Results:**
- ✅ WebSocket connects automatically
- ✅ Connection status shows "Connected"
- ✅ No connection errors in console

#### Test Real-time Updates
```typescript
// Trigger backend event (if possible):
// - Add new accident via backend API
// - Update AQI via backend API

// Observe:
// - Store updates with new data
// - Map markers update
// - Notification appears for severe events
```

**Expected Results:**
- ✅ Real-time data updates appear
- ✅ Store state updates
- ✅ Map re-renders with new data

#### Test Notification Triggers
```typescript
// Backend sends accident event
{
  type: 'new_accident',
  data: {
    id: 'accident-new',
    type: 'Collision',
    severity: 'severe',
    location: {
      address: 'District 1, Test Street',
      latitude: 10.8231,
      longitude: 106.6297
    },
    timestamp: new Date().toISOString()
  }
}

// Should trigger:
// - Error notification with title "New Accident Detected"
// - Message showing accident type and location
// - Sound plays
// - "View on map" button available
```

**Expected Results:**
- ✅ Notification appears automatically
- ✅ Correct notification type (error for accidents)
- ✅ Sound plays
- ✅ "View on map" zooms to accident location

#### Test Auto-Reconnect
```typescript
// Stop backend WebSocket server
// Wait 3 seconds
// Check console:
// [WebSocket] Connection lost, attempting reconnect...
// [WebSocket] Reconnect attempt 1

// Restart backend
// Check console:
// [WebSocket] Connected
```

**Expected Results:**
- ✅ Detects disconnection
- ✅ Attempts reconnect with exponential backoff
- ✅ Reconnects when server available
- ✅ Connection status updates

---

## 🐛 DEBUGGING TIPS

### Issue: API calls failing
```bash
# Check backend is running
curl http://localhost:8080/api/health

# Check CORS headers
# Open Network tab, check response headers

# Check environment variables
console.log(import.meta.env.VITE_API_URL);
```

### Issue: WebSocket not connecting
```bash
# Check WebSocket server
# Open browser console, look for WebSocket errors

# Test WebSocket manually
const ws = new WebSocket('ws://localhost:8081');
ws.onopen = () => console.log('Connected');
ws.onerror = (err) => console.error('Error:', err);
```

### Issue: SPARQL queries failing
```bash
# Check Fuseki is running
curl http://localhost:3030/$/ping

# Test SPARQL endpoint
curl -X POST http://localhost:3030/traffic/sparql \
  -H "Content-Type: application/sparql-query" \
  -d "SELECT * WHERE { ?s ?p ?o } LIMIT 10"
```

### Issue: Cache not working
```typescript
// Check localStorage
console.log(localStorage.getItem('traffic-store'));

// Clear cache manually
api.clearCache();

// Check cache entries
console.log(cache); // Should be private, but can inspect in debugger
```

### Issue: Notifications not showing
```typescript
// Check NotificationProvider is wrapping app
// In App.tsx, verify:
<NotificationProvider maxToasts={3}>
  {/* app content */}
</NotificationProvider>

// Check useNotification hook is called inside NotificationProvider
const { showNotification } = useNotification(); // Should not throw error
```

---

## ✅ TEST COMPLETION CHECKLIST

### API Service Layer
- [ ] All 18 endpoints return data
- [ ] Caching works (30s TTL verified)
- [ ] Retry logic triggers (tested with server down)
- [ ] Filters applied correctly
- [ ] Error messages user-friendly
- [ ] Loading events emitted
- [ ] Health check returns boolean

### Zustand Store
- [ ] Data loads on mount
- [ ] Filters persist to localStorage
- [ ] All 6 computed values work
- [ ] WebSocket updates trigger store updates
- [ ] loadAllData() successful
- [ ] refreshData() clears cache
- [ ] All filter types work (district, severity, date range, AQI level)

### Notification System
- [ ] All 4 types display correctly
- [ ] Colors match types (blue/green/yellow/red)
- [ ] Icons match types
- [ ] Sounds play on warning/error
- [ ] Sound toggle works
- [ ] Auto-dismiss timings correct (5s/10s)
- [ ] Max 3 toasts enforced
- [ ] FIFO queue works
- [ ] "View on map" action works
- [ ] Manual close works
- [ ] Progress bar animates
- [ ] Slide-in/out animations smooth

### Time Machine
- [ ] Date range buttons work
- [ ] Date picker bounds correct
- [ ] Time slider updates hour
- [ ] Hour markers displayed
- [ ] Play starts animation
- [ ] Pause stops animation
- [ ] Speed control cycles (1x/2x/4x/8x)
- [ ] All 4 SPARQL queries successful
- [ ] Historical data displays on map
- [ ] Loading indicator shows
- [ ] Error handling works
- [ ] "Back to Live" exits mode
- [ ] Banner shows with correct data

### WebSocket Integration
- [ ] Connection establishes
- [ ] Heartbeat maintains connection
- [ ] Real-time updates work
- [ ] Notifications triggered for severe events
- [ ] "View on map" zooms correctly
- [ ] Auto-reconnect works
- [ ] Connection status accurate

---

## 📊 PERFORMANCE BENCHMARKS

### Expected Performance
- **API Response Time**: < 500ms (first call)
- **Cached Response Time**: < 5ms
- **Map Render Time**: < 100ms for 100 markers
- **SPARQL Query Time**: < 3s for all 4 queries
- **Notification Animation**: 60 FPS
- **WebSocket Latency**: < 100ms
- **Store Update Time**: < 10ms

### Performance Testing
```typescript
// Test API performance
console.time('API Call');
await api.cameras.getAll();
console.timeEnd('API Call'); // Should be < 500ms

// Test cache performance
console.time('Cache Call');
await api.cameras.getAll();
console.timeEnd('Cache Call'); // Should be < 5ms

// Test store update
console.time('Store Update');
store.addAccident(newAccident);
console.timeEnd('Store Update'); // Should be < 10ms

// Test computed value
console.time('Computed Value');
const filtered = store.getFilteredAccidents();
console.timeEnd('Computed Value'); // Should be < 10ms
```

---

**Testing Completion Date**: _____________
**Tester Name**: _____________
**Pass Rate**: _____ / 100

---

**Status**: Ready for Testing ✅
**Last Updated**: November 11, 2025
