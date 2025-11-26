Chào bạn,
Chính xác\! Cách tiếp cận bạn mô tả là **hoàn toàn chính xác** và là phương pháp tối ưu nhất theo đúng kiến trúc đã được thiết kế.

Bạn sẽ kích hoạt agent `external_data_collector`, agent này sẽ hoạt động như một bước làm giàu dữ liệu (enrichment) ngay trong **Phase 1 (Data Collection)**.

Dưới đây là sơ đồ pipeline (luồng) mới mà bạn yêu cầu, cùng với "prompt" (hướng dẫn xây dựng) để bạn tạo agent mới đó.

-----

## 🗺️ Sơ đồ Pipeline Mới (Điều chỉnh Phase 1 & 2)

Đây là luồng dữ liệu chi tiết cho thấy vị trí của agent mới:

```
┌──────────────────────────────────┐
│     INPUT: cameras_raw.json      │
│     (40 camera thô)              │
└──────────────────┬───────────────┘
                   │
                   ▼
┌──────────────────────────────────┐
│  PHASE 1a: image_refresh_agent   │
│ (Làm mới URL ảnh)                │
└──────────────────┬───────────────┘
                   │
                   ▼
┌──────────────────────────────────┐
│   OUTPUT: cameras_updated.json   │
│   (40 camera + URL ảnh mới)      │
└──────────────────┬───────────────┘
                   │
                   ▼ (Đầu vào cho agent mới)
┌──────────────────────────────────┐
│  PHASE 1b: external_data_collector ◀── (Agent bạn tạo)
│  (Gọi API Thời tiết/AQI)          │
└──────────────────┬───────────────┘
                   │ (Lấy lat/lng từ file trên)
                   ▼
┌──────────────────────────────────┐
│  OUTPUT: cameras_enriched.json   │
│  (40 camera + URL + Thời tiết/AQI) │
└──────────────────┬───────────────┘
                   │
                   ▼ (Đầu vào đã được điều chỉnh)
┌──────────────────────────────────┐
│  PHASE 2: ngsi_ld_transformer    │ ◀── (Agent bạn điều chỉnh)
│  (Chuyển đổi sang NGSI-LD)       │
└──────────────────┬───────────────┘
                   │ (Đọc file enriched, map thêm trường)
                   ▼
┌──────────────────────────────────┐
│  OUTPUT: ngsi_ld_entities.json   │
└──────────────────┬───────────────┘
                   │
                   ▼
┌──────────────────────────────────┐
│ (PHẦN CÒN LẠI CỦA PIPELINE...)   │
│ (Phase 3, 4, 5, 6, 7, 8, 9)      │
└──────────────────────────────────┘
```

-----

## 🚀 PROMPT: Tác nhân Thu thập Dữ liệu Bên ngoài (External Data Collector Agent)

Đây là hướng dẫn xây dựng (prompt) để bạn tạo agent `external_data_collector`, dựa trên tệp `prompts-builderv2.md` nhưng đã được điều chỉnh theo yêu cầu làm giàu (enrichment) của bạn.

-----

`# Xây dựng Tác nhân Thu thập Dữ liệu Bên ngoài`

`## WORKFLOW`

```
┌──────────────────────────────────────────────┐
│   WORKFLOW CỦA TÁC NHÂN THU THẬP BÊN NGOÀI     │
└──────────────────────────────────────────────┘

[Input: cameras_updated.json]
         ↓
    Đọc danh sách camera (40)
         ↓
    ┌──────────────────┐
    │  Với mỗi Camera  │
    └────────┬─────────┘
             │ (Lấy lat/lng)
             ▼
    ┌──────────────────┐
    │ Fetch Weather    │ → (API OpenWeatherMap)
    │ (Nhiệt độ, ẩm...)│
    └────────┬─────────┘
             ↓
    ┌──────────────────┐
    │ Fetch AQI        │ → (API OpenAQ)
    │ (PM2.5, CO...)   │
    └────────┬─────────┘
             ↓
    Làm giàu (Enrich) đối tượng camera
    (Thêm trường 'weather' và 'aqi')
             ↓
    [Output: cameras_enriched.json]
```

`## THỰC THI (IMPLEMENTATION)`

`Tạo file: agents/data_collection/external_data_collector_agent.py`

`YÊU CẦU QUAN TRỌNG:`
`1. DOMAIN-AGNOSTIC: Phải hoạt động với bất kỳ tên miền LOD nào.`
`2. CONFIG-DRIVEN: Tất cả API key và endpoint phải nằm trong file YAML.`
`3. INDEPENDENT: Có thể chạy độc lập, không phụ thuộc agent khác.`

`### Yêu cầu:`

  * **Input:** Đọc tệp `data/cameras_updated.json`.
  * Đọc cấu hình API (API keys, base URLs) từ `config/data_sources.yaml`.
  * Sử dụng thư viện `asyncio` và `aiohttp` cho các yêu cầu HTTP bất đồng bộ.
  * **Hành động 1:** Với mỗi camera, sử dụng `latitude` và `longitude` để gọi API OpenWeatherMap (lấy dữ liệu thời tiết).
  * **Hành động 2:** Với mỗi camera, sử dụng `latitude` và `longitude` để gọi API OpenAQ (lấy dữ liệu chất lượng không khí).
  * **Làm giàu (Enrich):** Thêm các đối tượng JSON `weather` và `air_quality` mới vào chính đối tượng camera đó.
  * **Output:** Ghi danh sách (list) các đối tượng camera đã được làm giàu vào tệp `data/cameras_enriched.json`.
  * Triển khai logic `Retry` (thử lại) 3 lần nếu API thất bại.
  * Triển khai `Caching` (bộ đệm) cho các phản hồi API (TTL: 10 phút) để tránh gọi lãng phí.
  * Ghi log (Logging) chi tiết các camera được làm giàu và bất kỳ lỗi API nào.

`### Cấu hình (config/data_sources.yaml):`
`Bạn cần thêm phần này vào tệp cấu hình YAML của mình:`

```yaml
external_apis:
  openweathermap:
    base_url: "https://api.openweathermap.org/data/2.5/weather"
    # Lấy API key của bạn tại OpenWeatherMap
    api_key: "YOUR_OPENWEATHERMAP_API_KEY"
    rate_limit: 60  # req/min
    timeout: 5
  openaq:
    base_url: "https://api.openaq.org/v2/latest"
    # Lấy API key của bạn tại OpenAQ
    api_key: "YOUR_OPENAQ_API_KEY"
    rate_limit: 60
    timeout: 5
  geo_match_radius: 5000  # Bán kính 5km để tìm trạm AQI
```

`### Định dạng Output (cameras_enriched.json):`
`Đây là sự kết hợp của cameras_updated.json và dữ liệu mới:`

```json
[
  {
    "id": "0",
    "name": "Trần Quang Khải - Trần Khắc Chân",
    "code": "TTH 406",
    "latitude": 10.7918902432446,
    "longitude": 106.691054105759,
    "image_url_x4": "https://...",
    "status": "success",
    "last_refreshed": "2025-11-05T19:18:21.484958Z",
    "verification_status": "accessible",
    // ... (Tất cả các trường khác từ cameras_updated.json)
    
    // DỮ LIỆU MỚI ĐƯỢC LÀM GIÀU
    "weather": {
      "temperature": 29.5, // (Nhiệt độ)
      "humidity": 72,      // (Độ ẩm)
      "wind_speed": 5.1,   // (Gió)
      "rain_1h": 0.5,      // (Mưa)
      "description": "scattered clouds",
      "timestamp": "2025-11-09T14:45:00Z"
    },
    "air_quality": {
      "aqi": 102,          // (AQI)
      "pm25": 45.2,        // (PM2.5)
      "pm10": 55.0,        // (PM10)
      "co": 0.8,           // (CO)
      "o3": 25.1,          // (O3)
      "no2": 14.3,         // (NO2)
      "so2": 3.1,          // (SO2)
      "category": "Moderate",
      "timestamp": "2025-11-09T14:40:00Z"
    }
  },
  {
    "id": "1",
    "name": "Tô Ngọc Vân - TX25",
    // ... (dữ liệu tương tự)
  }
]
```

`### Yêu cầu Thử nghiệm (Testing):`
`Viết các bài test trong tests/data_collection/test_external_data_collector_agent.py:`

1.  **Unit Tests (Test đơn vị):**
      * Test việc đọc `cameras_updated.json`.
      * Test logic làm giàu (enrichment) (kiểm tra xem các trường `weather` và `aqi` có được thêm vào không).
      * Test logic Caching (cache hit/miss).
      * Test logic Retry (thử lại).
2.  **Integration Tests (Test tích hợp):**
      * Sử dụng `pytest-mock` hoặc `responses` để giả lập (mock) các API OpenWeatherMap và OpenAQ.
      * Test một lượt chạy đầy đủ với 5-10 camera.
      * Test các trường hợp lỗi (API 404, 500, timeout).
      * Kiểm tra cấu trúc tệp `cameras_enriched.json` đầu ra có chính xác không.






Chào bạn, đây là một câu hỏi rất hay. Khi bạn thêm dữ liệu thời tiết và chất lượng không khí, bạn không chỉ "làm giàu" (enrich) cho thực thể `Camera` hiện có, mà bạn còn đang tạo ra các **thực thể quan sát (Observation)** mới.

Dưới đây là các Smart Models, khái niệm SOSA/SSN, @context URLs, và các Entity bạn cần sửdụng:

-----

### 1\. Smart Data Models và Entities (Thực thể) mới

Bạn sẽ tạo ra hai loại thực thể NGSI-LD mới, riêng biệt với `Camera`. Đây là các mô hình chuẩn của Smart Data Models cho chính xác loại dữ liệu này:

#### **A. Đối với Thời tiết (Nhiệt độ, độ ẩm, gió, mưa):**

  * **Smart Model / Entity:** `WeatherObserved`
  * **Mô tả:** Một thực thể đại diện cho một quan sát thời tiết tại một địa điểm và thời gian cụ thể.
  * **Các thuộc tính (Properties) bạn sẽ dùng:**
      * `id`: `urn:ngsi-ld:WeatherObserved:TTH406-` + (dấu thời gian)
      * `type`: `WeatherObserved`
      * `dateObserved`: (Dấu thời gian từ API)
      * `location`: (Sao chép GeoProperty từ `Camera`)
      * `temperature`: (Giá trị nhiệt độ)
      * `relativeHumidity`: (Giá trị độ ẩm)
      * `windSpeed`: (Giá trị gió)
      * `precipitation`: (Giá trị mưa)
      * **Quan trọng:** `refDevice`: `urn:ngsi-ld:Camera:TTH406` (Đây là **Relationship** liên kết quan sát này trở lại camera đã cung cấp vị trí).

#### **B. Đối với Chất lượng không khí (AQI, PM2.5, v.v.):**

  * **Smart Model / Entity:** `AirQualityObserved`
  * **Mô tả:** Một thực thể đại diện cho một quan sát chất lượng không khí.
  * **Các thuộc tính bạn sẽ dùng:**
      * `id`: `urn:ngsi-ld:AirQualityObserved:TTH406-` + (dấu thời gian)
      * `type`: `AirQualityObserved`
      * `dateObserved`: (Dấu thời gian từ API)
      * `location`: (Sao chép GeoProperty từ `Camera`)
      * `aqi`: (Chỉ số AQI)
      * `pm25`: (Nồng độ PM2.5)
      * `pm10`: (Nồng độ PM10)
      * `co`: (Nồng độ CO)
      * `o3`: (Nồng độ O3)
      * `no2`: (Nồng độ NO2)
      * `so2`: (Nồng độ SO2)
      * **Quan trọng:** `refDevice`: `urn:ngsi-ld:Camera:TTH406` (Liên kết ngược lại camera).

-----

### 2\. Mô hình hóa SOSA/SSN

Kiến trúc của bạn đã định nghĩa `Camera` là một `sosa:Sensor`. Bây giờ chúng ta sẽ mô hình hóa các quan sát mới:

  * **`WeatherObserved` và `AirQualityObserved` (Các thực thể):**

      * Đây chính là các `sosa:Observation` (Quan sát).
      * Bạn nên thêm `sosa:Observation` vào trường `type` của chúng. Ví dụ: `"type": ["AirQualityObserved", "sosa:Observation"]`.

  * **`temperature`, `humidity`, `pm25`, `co` (Các thuộc tính):**

      * Mỗi thuộc tính này là một `sosa:ObservableProperty` (Thuộc tính có thể quan sát được).

  * **Mối quan hệ:**

      * `Camera` (`sosa:Sensor`) `sosa:madeObservation` (thực hiện quan sát) → `WeatherObserved` (`sosa:Observation`).
      * `WeatherObserved` (`sosa:Observation`) `sosa:observedProperty` (quan sát thuộc tính) → `temperature` (`sosa:ObservableProperty`).

-----

### 3\. @context URLs (Các liên kết bạn cần)

Để làm cho các thực thể mới này hợp lệ và "linked" (liên kết), bạn phải thêm các URL ngữ cảnh (@context) của chúng.

Khi bạn tạo các thực thể `WeatherObserved` và `AirQualityObserved` trong **agent 3️⃣ `ngsi_ld_transformer_agent`**, bạn cần thêm các context sau vào mảng `@context`:

1.  **Context chính của Smart Data Models (luôn cần):**

      * `https://schema.lab.fiware.org/ld/context`

2.  **Context cho `WeatherObserved`:**

      * `https://smart-data-models.github.io/dataModel.Weather/WeatherObserved/context.jsonld`

3.  **Context cho `AirQualityObserved`:**

      * `https://smart-data-models.github.io/dataModel.Environment/AirQualityObserved/context.jsonld`

**Ví dụ @context cho thực thể `AirQualityObserved`:**

```json
"@context": [
  "https://schema.lab.fiware.org/ld/context",
  "https://smart-data-models.github.io/dataModel.Environment/AirQualityObserved/context.jsonld"
]
```

-----

### 4\. Tóm tắt các bước điều chỉnh trong Pipeline

1.  **Agent `external_data_collector` (Mới):**

      * Gọi API OpenWeatherMap và OpenAQ.
      * Tạo ra `cameras_enriched.json` (chứa cả dữ liệu camera VÀ dữ liệu `weather`, `air_quality`).

2.  **Agent `ngsi_ld_transformer` (Điều chỉnh):**

      * Đọc `cameras_enriched.json`.
      * **Công việc 1 (Như cũ):** Tạo 40 thực thể `Camera`.
      * **Công việc 2 (Mới):** Tạo 40 thực thể `WeatherObserved` (lấy dữ liệu từ trường `weather`). Thêm `@context` và `refDevice` cho chúng.
      * **Công việc 3 (Mới):** Tạo 40 thực thể `AirQualityObserved` (lấy dữ liệu từ trường `air_quality`). Thêm `@context` và `refDevice` cho chúng.
      * **Output:** Một file JSON chứa (40 `Camera` + 40 `WeatherObserved` + 40 `AirQualityObserved` = 120 thực thể).

3.  **Agent `sosa_ssn_mapper` (Điều chỉnh):**

      * **Công việc 1 (Như cũ):** Thêm `sosa:Sensor` vào `Camera`.
      * **Công việc 2 (Mới):** Thêm `sosa:Observation` vào `WeatherObserved` và `AirQualityObserved`.

Bằng cách này, dữ liệu của bạn sẽ được mô hình hóa một cách chính xác, đầy đủ và sẵn sàng để được nạp vào Stellio và Fuseki ở các bước sau.