Chào bạn,
Chắc chắn rồi. Đây là một quy trình gồm 3 bước, yêu cầu bạn **tạo 1 agent mới** và **cập nhật 2 agent hiện có**.

Để "hoàn thành 100%" theo yêu cầu của bạn, dưới đây là 3 prompt (hướng dẫn) đầy đủ và chi tiết. Bạn có thể cung cấp lần lượt 3 prompt này cho GitHub Copilot để xây dựng và cập nhật các agent tương ứng.

-----

## 1\. 🚀 PROMPT 1: TẠO AGENT MỚI (EXTERNAL DATA COLLECTOR)

Đây là prompt để xây dựng agent `external_data_collector` (tác nhân 2️⃣ trong sơ đồ).

`# Xây dựng Tác nhân Thu thập Dữ liệu Bên ngoài (External Data Collector)`

`## WORKFLOW`

```
┌──────────────────────────────────────────────┐
│   WORKFLOW CỦA TÁC NHÂN THU THẬP BÊN NGOÀI     │
└──────────────────────────────────────────────┘

[Input: data/cameras_updated.json]
         ↓
    Đọc danh sách 40 camera
         ↓
    ┌──────────────────┐
    │  Với mỗi Camera  │
    └────────┬─────────┘
             │ (Lấy latitude & longitude)
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
    Gắn đối tượng 'weather' và 'air_quality'
    vào đối tượng camera gốc
             ↓
    [Output: data/cameras_enriched.json]
```

`## THỰC THI (IMPLEMENTATION)`

`Tạo file: agents/data_collection/external_data_collector_agent.py`

`YÊU CẦU QUAN TRỌNG:`
`1. DOMAIN-AGNOSTIC: Phải hoạt động với bất kỳ tên miền LOD nào.`
`2. CONFIG-DRIVEN: Tất cả API key và endpoint phải nằm trong file YAML.`
`3. INDEPENDENT: Có thể chạy độc lập, không phụ thuộc agent khác.`

`### Yêu cầu:`

  * **Input:** Đọc tệp `data/cameras_updated.json` (đây là một danh sách các đối tượng JSON).
  * Đọc cấu hình API (API keys, base URLs) từ `config/data_sources.yaml`.
  * Sử dụng `asyncio` và `aiohttp` để thực hiện các cuộc gọi API bất đồng bộ (parallel) cho tất cả 40 camera.
  * **Hành động 1 (Weather):** Với mỗi camera, sử dụng `latitude` và `longitude` để gọi API OpenWeatherMap.
  * **Hành động 2 (AQI):** Với mỗi camera, sử dụng `latitude` và `longitude` để gọi API OpenAQ.
  * **Làm giàu (Enrich):** KHÔNG thay đổi các trường hiện có. Thêm hai (2) khóa (key) JSON mới vào đối tượng camera: `weather` (chứa kết quả từ OpenWeatherMap) và `air_quality` (chứa kết quả từ OpenAQ).
  * **Output:** Ghi danh sách (list) 40 đối tượng camera đã được làm giàu vào tệp `data/cameras_enriched.json`.
  * Triển khai logic `Retry` (thử lại) 3 lần với `exponential backoff` (thời gian chờ tăng dần) nếu API thất bại.
  * Triển khai `Caching` (bộ đệm) bằng `async-lru` hoặc `redis` cho các phản hồi API (TTL: 10 phút) để tránh gọi lãng phí.
  * Ghi log (Logging) chi tiết (INFO, ERROR) cho từng camera.

`### Cấu hình (config/data_sources.yaml):`
`Phải đọc cấu hình từ mục 'external_apis' trong tệp YAML này:`

```yaml
external_apis:
  openweathermap:
    base_url: "https://api.openweathermap.org/data/2.5/weather"
    api_key: "YOUR_OPENWEATHERMAP_API_KEY"
    rate_limit: 60
    timeout: 5
  openaq:
    base_url: "https://api.openaq.org/v2/latest"
    api_key: "YOUR_OPENAQ_API_KEY"
    rate_limit: 60
    timeout: 5
  geo_match_radius: 5000 
```

`### Định dạng Output (data/cameras_enriched.json):`
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
    // ... (Tất cả các trường khác từ cameras_updated.json)
    
    // DỮ LIỆU MỚI ĐƯỢC LÀM GIÀU
    "weather": {
      "temperature": 29.5,
      "humidity": 72,
      "wind_speed": 5.1,
      "rain_1h": 0.5,
      "description": "scattered clouds",
      "timestamp": "2025-11-09T14:45:00Z"
    },
    "air_quality": {
      "aqi": 102,
      "pm25": 45.2,
      "pm10": 55.0,
      "co": 0.8,
      "o3": 25.1,
      "no2": 14.3,
      "so2": 3.1,
      "category": "Moderate",
      "timestamp": "2025-11-09T14:40:00Z"
    }
  }
  // ... (39 camera còn lại)
]
```

`### Yêu cầu Thử nghiệm (100% Coverage):`
`Viết các bài test trong tests/data_collection/test_external_data_collector_agent.py:`

1.  **Unit Tests:**
      * Test logic làm giàu (enrichment) (kiểm tra xem các trường `weather` và `aqi` có được thêm vào chính xác không).
      * Test logic Caching (cache hit/miss).
      * Test logic Retry (thử lại).
2.  **Integration Tests (Mock API):**
      * Sử dụng `pytest-mock` và `aiohttp.MockConnector` (hoặc thư viện `responses`) để giả lập (mock) các API OpenWeatherMap và OpenAQ.
      * Test một lượt chạy đầy đủ với 3-5 camera.
      * Test các trường hợp lỗi (API 404, 500, timeout) và xác minh agent vẫn tiếp tục xử lý các camera khác.
      * Kiểm tra cấu trúc tệp `cameras_enriched.json` đầu ra có chính xác không.

-----

## 2\. 🔄 PROMPT 2: CẬP NHẬT AGENT (NGSI-LD TRANSFORMER)

Đây là prompt để **cập nhật** agent `ngsi_ld_transformer_agent` (tác nhân 3️⃣). Nó phải đọc tệp "enriched" mới và tạo ra 3 loại thực thể.

`# CẬP NHẬT Tác nhân Chuyển đổi NGSI-LD (NGSI-LD Transformer)`

`## YÊU CẦU CẬP NHẬT`
`Agent này (agents/transformation/ngsi_ld_transformer_agent.py) phải được cập nhật để xử lý input mới và tạo ra các thực thể quan sát (Observation) bên cạnh thực thể Camera.`

`## WORKFLOW MỚI`

```
┌──────────────────────────────────────────────┐
│  WORKFLOW CẬP NHẬT CỦA NGSI-LD TRANSFORMER    │
└──────────────────────────────────────────────┘

[Input: data/cameras_enriched.json]
         ↓
    Đọc 40 đối tượng camera đã làm giàu
         ↓
    ┌──────────────────┐
    │  Với mỗi Camera  │
    └────────┬─────────┘
             │
      ┌──────┴────────┬────────────────┐
      ▼               ▼                ▼
  Tạo 1           Tạo 1            Tạo 1
  Thực thể         Thực thể          Thực thể
  'Camera'          'WeatherObserved' 'AirQualityObserved'
  (Như cũ)         (Mới)             (Mới)
      │               │                │
      │           (Thêm refDevice     │
      │            trỏ về Camera)    │
      │               │                │
      └──────┬────────┼────────────────┘
             │
             ▼
    Tổng hợp danh sách (120 thực thể)
         ↓
    [Output: data/ngsi_ld_entities.json]
```

`## THỰC THI (IMPLEMENTATION)`

`Cập nhật file: agents/transformation/ngsi_ld_transformer_agent.py`

`### Yêu cầu:`

  * **Input:** Thay đổi đầu vào. Đọc tệp `data/cameras_enriched.json`.
  * **Logic (Vòng lặp):** Lặp qua 40 đối tượng camera. Trong mỗi lần lặp, tạo ra BA (3) thực thể NGSI-LD:
    1.  **`Camera` Entity (Như cũ):** Tạo thực thể `Camera` dựa trên các trường `code`, `name`, `latitude`, `longitude`, v.v..
    2.  **`WeatherObserved` Entity (Mới):**
          * Tạo một thực thể `WeatherObserved` mới.
          * `id`: `urn:ngsi-ld:WeatherObserved:{camera_code}-{timestamp}`
          * `type`: `WeatherObserved`
          * `location`: Sao chép `GeoProperty` từ thực thể `Camera`.
          * `dateObserved`: Lấy từ `weather.timestamp`.
          * Ánh xạ các thuộc tính: `temperature`, `relativeHumidity` (từ `humidity`), `windSpeed`, `precipitation` (từ `rain_1h`).
          * **Relationship (Quan trọng):** Thêm thuộc tính `refDevice` (type: `Relationship`) trỏ đến `id` của `Camera` (ví dụ: `urn:ngsi-ld:Camera:TTH406`).
          * Thêm `@context` chính xác (xem bên dưới).
    3.  **`AirQualityObserved` Entity (Mới):**
          * Tạo một thực thể `AirQualityObserved` mới.
          * `id`: `urn:ngsi-ld:AirQualityObserved:{camera_code}-{timestamp}`
          * `type`: `AirQualityObserved`
          * `location`: Sao chép `GeoProperty` từ thực thể `Camera`.
          * `dateObserved`: Lấy từ `air_quality.timestamp`.
          * Ánh xạ các thuộc tính: `aqi`, `pm25`, `pm10`, `co`, `o3`, `no2`, `so2`.
          * **Relationship (Quan trọng):** Thêm thuộc tính `refDevice` (type: `Relationship`) trỏ đến `id` của `Camera`.
          * Thêm `@context` chính xác (xem bên dưới).
  * **Output:** Ghi danh sách (list) gồm 120 thực thể (40 `Camera` + 40 `WeatherObserved` + 40 `AirQualityObserved`) vào tệp `data/ngsi_ld_entities.json`.

`### Cấu hình (config/ngsi_ld_mappings.yaml):`
`Cập nhật tệp cấu hình này để hỗ trợ các loại thực thể mới và context của chúng.`

```yaml
# Cấu hình cho Camera (như cũ)
camera_mappings:
  entity_type: "Camera"
  uri_prefix: "urn:ngsi-ld:Camera:"
  id_field: "code"
  property_mappings:
    # ... (các mapping cũ)
  geo_property:
    # ... (như cũ)
  context_urls:
    - "https://uri.etsi.org/ngsi-ld/v1/ngsi-ld-core-context.jsonld"
    - "https://raw.githubusercontent.com/smart-data-models/dataModel.Device/master/context.jsonld"

# Cấu hình MỚI cho WeatherObserved
weather_mappings:
  entity_type: "WeatherObserved"
  uri_prefix: "urn:ngsi-ld:WeatherObserved:"
  ref_device_prefix: "urn:ngsi-ld:Camera:"
  source_field: "weather" # Lấy data từ key "weather"
  property_mappings:
    temperature: "temperature"
    relativeHumidity: "humidity"
    windSpeed: "wind_speed"
    precipitation: "rain_1h"
    dateObserved: "timestamp"
  context_urls:
    - "https://schema.lab.fiware.org/ld/context"
    - "https://smart-data-models.github.io/dataModel.Weather/WeatherObserved/context.jsonld"

# Cấu hình MỚI cho AirQualityObserved
airquality_mappings:
  entity_type: "AirQualityObserved"
  uri_prefix: "urn:ngsi-ld:AirQualityObserved:"
  ref_device_prefix: "urn:ngsi-ld:Camera:"
  source_field: "air_quality" # Lấy data từ key "air_quality"
  property_mappings:
    aqi: "aqi"
    pm25: "pm25"
    pm10: "pm10"
    co: "co"
    o3: "o3"
    no2: "no2"
    so2: "so2"
    dateObserved: "timestamp"
  context_urls:
    - "https://schema.lab.fiware.org/ld/context"
    - "https://smart-data-models.github.io/dataModel.Environment/AirQualityObserved/context.jsonld"
```

`### Yêu cầu Thử nghiệm (100% Coverage):`
`Cập nhật file: tests/transformation/test_ngsi_ld_transformer_agent.py`

1.  **Unit Tests (Mới):**
      * Test việc tạo `WeatherObserved` (kiểm tra `id`, `type`, `refDevice`, `@context`).
      * Test việc tạo `AirQualityObserved` (kiểm tra `id`, `type`, `refDevice`, `@context`).
2.  **Integration Tests (Cập nhật):**
      * Mock tệp `cameras_enriched.json` (với 2-3 camera).
      * Chạy agent.
      * Kiểm tra tệp `ngsi_ld_entities.json` đầu ra.
      * Xác minh rằng tệp chứa (Số camera x 3) thực thể.
      * Xác minh mối quan hệ `refDevice` là chính xác.

-----

## 3\. 🔄 PROMPT 3: CẬP NHẬT AGENT (SOSA/SSN MAPPER)

Đây là prompt để **cập nhật** agent `sosa_ssn_mapper_agent` (tác nhân 4️⃣). Nó phải thêm `sosa:Observation` vào các thực thể mới.

`# CẬP NHẬT Tác nhân Ánh xạ SOSA/SSN (SOSA/SSN Mapper)`

`## YÊU CẦU CẬP NHẬT`
`Agent này (agents/transformation/sosa_ssn_mapper_agent.py) phải được cập nhật để xử lý 3 loại thực thể đầu vào.`

`## WORKFLOW MỚI`

```
┌──────────────────────────────────────────────┐
│       WORKFLOW CẬP NHẬT CỦA SOSA MAPPER       │
└──────────────────────────────────────────────┘

[Input: data/ngsi_ld_entities.json (120 entities)]
         ↓
    ┌──────────────────┐
    │  Với mỗi Entity  │
    └────────┬─────────┘
             │
    ┌──────────────────┐
    │   Kiểm tra Type  │
    └────────┬─────────┘
             │
      ┌──────┴────────┬────────────────┐
      ▼               ▼                ▼
  Nếu là 'Camera'    Nếu là           Nếu là
  (Như cũ)         'WeatherObserved' 'AirQualityObserved'
      │               (Mới)             (Mới)
      ▼               │                │
  Thêm type       └───────┬────────┘
  'sosa:Sensor'           │
      │                   ▼
      │               Thêm type
      │               'sosa:Observation'
      │                   │
      └──────┬────────┼────────────────┘
             │
             ▼
    [Output: data/sosa_enhanced_entities.json (120 entities)]
```

`## THỰC THI (IMPLEMENTATION)`

`Cập nhật file: agents/transformation/sosa_ssn_mapper_agent.py`

`### Yêu cầu:`

  * **Input:** Đọc tệp `data/ngsi_ld_entities.json` (chứa 120 thực thể).
  * **Logic (Cập nhật):** Lặp qua từng thực thể:
    1.  Nếu `entity["type"]` chứa `"Camera"`: Áp dụng logic cũ, thêm `"sosa:Sensor"` vào mảng `type` và thêm các mối quan hệ (ví dụ: `sosa:isHostedBy`).
    2.  Nếu `entity["type"]` chứa `"WeatherObserved"`: Thêm `"sosa:Observation"` vào mảng `type`.
    3.  Nếu `entity["type"]` chứa `"AirQualityObserved"`: Thêm `"sosa:Observation"` vào mảng `type`.
  * **Context:** Đảm bảo `sosa_context` (ví dụ: "[http://www.w3.org/ns/sosa/](http://www.w3.org/ns/sosa/)") được thêm vào mảng `@context` của *tất cả* 120 thực thể.
  * **Output:** Ghi 120 thực thể đã được cập nhật vào `data/sosa_enhanced_entities.json`.

`### Cấu hình (sosa_mappings.yaml):`
`Cập nhật tệp cấu hình để bao gồm các loại mới:`

```yaml
# Cấu hình cho Sensor (Camera)
sensor_mappings:
  type_name: "Camera"
  sosa_type: "sosa:Sensor"
  relationships:
    - sosa:isHostedBy
    - sosa:observes
  platform:
    id: "urn:ngsi-ld:Platform:HCMCTrafficSystem"
    name: "Ho Chi Minh City Traffic Monitoring System"

# Cấu hình MỚI cho Observation
observation_mappings:
  - type_name: "WeatherObserved"
    sosa_type: "sosa:Observation"
  - type_name: "AirQualityObserved"
    sosa_type: "sosa:Observation"

# Context chung
sosa_context: "http://www.w3.org/ns/sosa/"
```

`### Yêu cầu Thử nghiệm (100% Coverage):`
`Cập nhật file: tests/transformation/test_sosa_ssn_mapper_agent.py`

1.  **Unit Tests (Mới):**
      * Test một thực thể `WeatherObserved` đầu vào và xác minh đầu ra có `type` bao gồm `sosa:Observation`.
      * Test một thực thể `AirQualityObserved` đầu vào và xác minh đầu ra có `type` bao gồm `sosa:Observation`.
2.  **Integration Tests (Cập nhật):**
      * Tạo một tệp `ngsi_ld_entities.json` giả lập chứa 1 `Camera`, 1 `WeatherObserved`, 1 `AirQualityObserved`.
      * Chạy agent.
      * Kiểm tra tệp `sosa_enhanced_entities.json` đầu ra.
      * Xác minh rằng cả 3 thực thể đều đã được ánh xạ SOSA một cách chính xác.
-----

## 4\. 🚀 PROMPT 4: CẬP NHẬT WORKFLOW ĐIỀU PHỐI

Đây là prompt để **cập nhật** tệp `config/workflow.yaml` (hoặc tệp tương tự).

`# CẬP NHẬT Tệp Điều phối Workflow (config/workflow.yaml)`

`## YÊU CẦU CẬP NHẬT`
`Phải cập nhật tệp điều phối (orchestrator configuration) để kích hoạt 'external_data_collector_agent' và đảm bảo nó chạy TUẦN TỰ (sequentially) sau 'image_refresh_agent'.`

`## WORKFLOW MỚI (PHASE 1)`

```
┌──────────────────────────────────────────────┐
│     WORKFLOW CẬP NHẬT (PHASE 1 - TUẦN TỰ)     │
└──────────────────────────────────────────────┘

[Input: data/cameras_raw.json]
         ↓
    1. Chạy 'image_refresh_agent'
       (Tạo ra 'cameras_updated.json')
         ↓
    2. Chạy 'external_data_collector_agent' (KÍCH HOẠT)
       (Đọc 'cameras_updated.json', tạo 'cameras_enriched.json')
         ↓
    [Output: Phase 1 hoàn tất]
```

`## THỰC THI (IMPLEMENTATION)`

`Cập nhật file: config/workflow.yaml` (hoặc tệp điều phối chính)

`### Yêu cầu:`

`Tìm đến định nghĩa cho "Phase 1: Data Collection".`

1.  **Kích hoạt Agent:** Đảm bảo `external_data_collector_agent` được liệt kê trong danh sách agent của Phase 1. Thay đổi trạng thái của nó từ `DISABLED` (vô hiệu hóa) sang `ENABLED` (kích hoạt).
2.  **Thiết lập Bắt buộc (Required):** Thay đổi trạng thái `required` (bắt buộc) của nó từ `No` (Không) thành `Yes` (Có).
3.  **Thiết lập Tuần tự (Sequential):** Đây là điều quan trọng nhất. Cấu hình `parallel` (song song) của Phase 1 phải được đặt là `false`. Điều này buộc các agent trong Phase 1 phải chạy theo thứ tự: `image_refresh_agent` chạy *trước*, sau đó `external_data_collector_agent` chạy *sau*.

`### Cấu hình (config/workflow.yaml) CẦN THAY ĐỔI:`
`Tệp của bạn có thể trông giống như thế này. Hãy đảm bảo bạn thay đổi 'parallel: true' thành 'parallel: false'.`

`TỪ (TRƯỚC KHI THAY ĐỔI):`

```yaml
workflow:
  phases:
    - name: "Data Collection"
      agents:
        - image_refresh_agent
        - external_data_collector_agent
      parallel: true  # ◀ (SAI - Chạy song song)
```

`THÀNH (SAU KHI THAY ĐỔI):`

```yaml
workflow:
  phases:
    - name: "Data Collection"
      agents:
        # 1. Chạy agent này trước
        - name: "image_refresh_agent"
          required: true
          enabled: true
        
        # 2. Sau đó, chạy agent này
        - name: "external_data_collector_agent"
          required: true
          enabled: true # ◀ (Đã kích hoạt)

      parallel: false # ◀ (ĐÚNG - Chạy tuần tự)
      
    - name: "Transformation"
      agents:
        # Agent này bây giờ sẽ tự động đọc output của agent cuối cùng
        # trong Phase 1 (tức là 'cameras_enriched.json')
        - name: "ngsi_ld_transformer_agent"
        - name: "sosa_ssn_mapper_agent"
      parallel: false
      
    # ... (Các phase còn lại)
```