# DIAGRAMS - Smart Energy Monitoring System

All diagrams below use Mermaid syntax. Render them at https://mermaid.live/ or in any Markdown editor with Mermaid support.

---

## 1. Complete System Architecture

```mermaid
graph TB
    subgraph SENSORS ["Sensor Layer"]
        ACS[ACS712<br/>Current Sensor]
        ZMP[ZMPT101B<br/>Voltage Sensor]
        CAM[ESP32-CAM<br/>Face Camera]
    end

    subgraph EDGE ["Edge Computing Layer"]
        ESP[ESP32 DevKit<br/>Main Controller]
        OLED[OLED Display<br/>Local Monitor]
        REL[4-CH Relay<br/>Load Control]
    end

    subgraph NETWORK ["Network Layer"]
        MQTT[MQTT Broker<br/>Mosquitto]
        WiFi[WiFi Network<br/>802.11n]
    end

    subgraph SERVER ["Server Layer"]
        FLASK[Flask Backend<br/>API Server]
        FACE[Face Recognition<br/>OpenCV Service]
        DB[(Database<br/>SQLite/Firebase)]
        ML[ML Prediction<br/>LSTM Model]
    end

    subgraph PRESENTATION ["Presentation Layer"]
        WEB[Web Dashboard<br/>Chart.js]
        ALERT[Alert System<br/>Email/SMS]
        APP[Mobile App<br/>Optional]
    end

    ACS -->|Analog| ESP
    ZMP -->|Analog| ESP
    CAM -->|UART/WiFi| FACE
    ESP -->|I2C| OLED
    ESP -->|GPIO| REL
    ESP -->|MQTT over| WiFi
    WiFi --> MQTT
    MQTT --> FLASK
    FLASK --> DB
    FLASK --> ML
    FLASK --> FACE
    FLASK --> WEB
    FLASK --> ALERT
    WEB --> APP

    style SENSORS fill:#e1f5fe
    style EDGE fill:#fff3e0
    style NETWORK fill:#f3e5f5
    style SERVER fill:#e8f5e9
    style PRESENTATION fill:#fce4ec
```

---

## 2. Energy Monitoring Flowchart

```mermaid
flowchart TD
    A[System Start] --> B[Initialize ESP32]
    B --> C[Connect to WiFi]
    C --> D{WiFi Connected?}
    D -->|No| E[Retry Connection]
    E --> C
    D -->|Yes| F[Connect to MQTT Broker]
    F --> G{MQTT Connected?}
    G -->|No| H[Retry Connection]
    H --> F
    G -->|Yes| I[Initialize Sensors]
    I --> J[Calibrate ACS712]
    J --> K[Calibrate ZMPT101B]
    K --> L{Enter Main Loop}

    L --> M[Read ADC - Current]
    M --> N[Read ADC - Voltage]
    N --> O[Calculate RMS Values]
    O --> P[Calculate Power = V x I x PF]
    P --> Q[Accumulate Energy kWh]
    Q --> R[Update OLED Display]
    R --> S[Publish to MQTT]
    S --> T{Check Thresholds}
    T -->|Exceeded| U[Trigger Alert]
    U --> V[Check Relay Rules]
    T -->|Normal| V
    V --> W{Relay Action?}
    W -->|Yes| X[Toggle Relay]
    W -->|No| Y[Wait 2 seconds]
    X --> Y
    Y --> L

    style A fill:#4CAF50,color:#fff
    style L fill:#2196F3,color:#fff
    style U fill:#FF9800,color:#fff
    style X fill:#F44336,color:#fff
```

---

## 3. Face Recognition Flowchart

```mermaid
flowchart TD
    A[User Approaches] --> B[ESP32-CAM Captures Image]
    B --> C[Send Image to Server]
    C --> D{Face Detected?}
    D -->|No| E[Show Error: No Face]
    E --> F{Retry?}
    F -->|Yes| B
    F -->|No| G[Access Denied]

    D -->|Yes| H[Extract Face Encoding<br/>128-D Vector]
    H --> I[Load Registered Faces<br/>from Database]
    I --> J[Compare with All<br/>Stored Encodings]
    J --> K[Find Minimum<br/>Euclidean Distance]
    K --> L{Distance < 0.6?}

    L -->|No| M[Show Error: Unknown Face]
    M --> N{Retry?}
    N -->|Yes| B
    N -->|No| G

    L -->|Yes| O[Identify User]
    O --> P[Generate JWT Token]
    P --> Q[Log Access Event]
    Q --> R[Grant Dashboard Access]
    R --> S[Show Welcome Message]

    style A fill:#4CAF50,color:#fff
    style G fill:#F44336,color:#fff
    style R fill:#2196F3,color:#fff
    style S fill:#4CAF50,color:#fff
```

---

## 4. ML Prediction Pipeline

```mermaid
flowchart LR
    subgraph DATA ["Data Collection"]
        A1[Historical<br/>Energy Data]
        A2[Weather<br/>Data API]
        A3[Calendar<br/>Events]
    end

    subgraph PREP ["Data Preparation"]
        B1[Data Cleaning<br/>Remove Outliers]
        B2[Feature Engineering<br/>Lag, Rolling, Cyclic]
        B3[Normalization<br/>MinMax Scaling]
        B4[Train/Test Split<br/>80/20]
    end

    subgraph TRAIN ["Model Training"]
        C1[LSTM Architecture<br/>64-32-16-1]
        C2[Compile Model<br/>Adam Optimizer]
        C3[Train 100 Epochs<br/>Batch Size 32]
        C4[Early Stopping<br/>Patience 10]
        C5[Save Best Model<br/>.h5 file]
    end

    subgraph DEPLOY ["Deployment"]
        D1[Load Model<br/>on Server]
        D2[Schedule Job<br/>Every 1 Hour]
        D3[Fetch Latest<br/>Data Window]
        D4[Generate<br/>Predictions]
        D5[Store Results<br/>in Database]
        D6[Update<br/>Dashboard]
    end

    A1 --> B1
    A2 --> B1
    A3 --> B1
    B1 --> B2
    B2 --> B3
    B3 --> B4
    B4 --> C1
    C1 --> C2
    C2 --> C3
    C3 --> C4
    C4 --> C5
    C5 --> D1
    D1 --> D2
    D2 --> D3
    D3 --> D4
    D4 --> D5
    D5 --> D6

    style DATA fill:#e3f2fd
    style PREP fill:#fff3e0
    style TRAIN fill:#e8f5e9
    style DEPLOY fill:#fce4ec
```

---

## 5. Sequence Diagram - Complete Operation

```mermaid
sequenceDiagram
    participant User
    participant Camera as ESP32-CAM
    participant ESP as ESP32
    participant MQTT as MQTT Broker
    participant Server as Flask Server
    participant DB as Database
    participant ML as ML Model
    participant Dashboard as Web UI

    Note over User,Dashboard: Face Authentication Phase
    User->>Camera: Stand in front of camera
    Camera->>Server: POST /api/auth/face (image)
    Server->>Server: Detect face & extract encoding
    Server->>DB: Query registered faces
    DB-->>Server: Return face encodings
    Server->>Server: Compare & match
    alt Face Matched
        Server-->>Camera: 200 OK + JWT Token
        Camera-->>User: Access Granted LED
    else Face Not Matched
        Server-->>Camera: 401 Unauthorized
        Camera-->>User: Access Denied LED
    end

    Note over User,Dashboard: Energy Monitoring Phase
    loop Every 2 seconds
        ESP->>ESP: Read ACS712 (Current)
        ESP->>ESP: Read ZMPT101B (Voltage)
        ESP->>ESP: Calculate Power & Energy
        ESP->>MQTT: Publish energy/voltage
        ESP->>MQTT: Publish energy/current
        ESP->>MQTT: Publish energy/power
        MQTT->>Server: Forward to subscriber
        Server->>DB: Insert reading
        Server->>Dashboard: Push via WebSocket
        Dashboard->>Dashboard: Update charts
    end

    Note over User,Dashboard: Prediction Phase
    Note over ML: Scheduled every 1 hour
    ML->>DB: Fetch last 168h data
    DB-->>ML: Historical readings
    ML->>ML: Preprocess features
    ML->>ML: LSTM forward pass
    ML->>DB: Store predictions
    DB-->>Dashboard: Update prediction chart

    Note over User,Dashboard: Alert Phase
    alt Power > Threshold
        Server->>Server: Detect threshold breach
        Server->>Dashboard: Show alert notification
        Server->>User: Send Email/SMS
    end
```

---

## 6. Data Flow Diagram - Level 1

```mermaid
flowchart LR
    subgraph EXT ["External Entities"]
        U[User]
        LOAD[Electrical Load]
        ADMIN[Administrator]
    end

    subgraph PROC ["Processes"]
        P1[1.0<br/>Authenticate<br/>User]
        P2[2.0<br/>Acquire<br/>Sensor Data]
        P3[3.0<br/>Process &<br/>Store Data]
        P4[4.0<br/>Generate<br/>Predictions]
        P5[5.0<br/>Display<br/>Dashboard]
        P6[6.0<br/>Manage<br/>Alerts]
        P7[7.0<br/>Control<br/>Relays]
    end

    subgraph STORE ["Data Stores"]
        D1[(D1: User<br/>Database)]
        D2[(D2: Energy<br/>Readings)]
        D3[(D3: Prediction<br/>Results)]
        D4[(D4: Alert<br/>Logs)]
    end

    U -->|Login Request| P1
    P1 -->|Verify| D1
    D1 -->|Auth Result| P1
    P1 -->|Access Granted| U

    LOAD -->|Energy Data| P2
    P2 -->|Raw Readings| P3
    P3 -->|Store| D2

    D2 -->|Historical Data| P4
    P4 -->|Predictions| D3

    D2 -->|Live Data| P5
    D3 -->|Forecast Data| P5
    D4 -->|Alert History| P5
    P5 -->|Dashboard| U
    P5 -->|Dashboard| ADMIN

    D2 -->|Check Threshold| P6
    P6 -->|Store Alert| D4
    P6 -->|Notify| ADMIN

    P3 -->|Trigger Rule| P7
    U -->|Manual Control| P7
    P7 -->|Relay Command| LOAD

    style EXT fill:#e3f2fd
    style PROC fill:#fff3e0
    style STORE fill:#e8f5e9
```

---

## 7. Use Case Diagram

```mermaid
graph TB
    subgraph ACTORS ["Actors"]
        USER[👤 User]
        ADMIN[👤 Admin]
        SYS[⚙️ System]
    end

    subgraph USECASES ["Use Cases"]
        UC1[Monitor Real-time<br/>Energy Data]
        UC2[View Historical<br/>Consumption]
        UC3[View Predictions]
        UC4[Authenticate via<br/>Face Recognition]
        UC5[Control Relays<br/>Manually]
        UC6[Configure Alerts]
        UC7[Register New<br/>User Face]
        UC8[View Energy<br/>Reports]
        UC9[Auto-trigger<br/>Relay on Alert]
        UC10[Generate<br/>Prediction]
        UC11[Send Alert<br/>Notification]
    end

    USER --> UC1
    USER --> UC2
    USER --> UC3
    USER --> UC4
    USER --> UC5
    USER --> UC6
    USER --> UC8

    ADMIN --> UC1
    ADMIN --> UC4
    ADMIN --> UC7
    ADMIN --> UC6
    ADMIN --> UC8

    SYS --> UC9
    SYS --> UC10
    SYS --> UC11

    UC1 -.->|include| UC4
    UC5 -.->|include| UC4
    UC10 -.->|extends| UC2
    UC11 -.->|extends| UC1

    style ACTORS fill:#e3f2fd
    style USECASES fill:#fff3e0
```

---

## 8. State Diagram - Relay Control

```mermaid
stateDiagram-v2
    [*] --> IDLE: System Start
    IDLE --> MONITORING: Initialize Complete
    MONITORING --> CHECKING: New Sensor Data

    state CHECKING {
        [*] --> EVALUATE
        EVALUATE --> NORMAL: Power < Threshold
        EVALUATE --> WARNING: Power > 80% Threshold
        EVALUATE --> CRITICAL: Power > Threshold
    }

    CHECKING --> MONITORING: NORMAL
    CHECKING --> ALERTING: WARNING or CRITICAL

    state ALERTING {
        [*] --> SEND_ALERT
        SEND_ALERT --> WAIT_ACK: Alert Sent
        WAIT_ACK --> AUTO_OFF: No Response in 30s
        WAIT_ACK --> MONITORING: ACK Received
    }

    AUTO_OFF --> RELAY_OFF: Cut Load
    RELAY_OFF --> MONITORING: After 5 min cooldown

    MANUAL_ON --> MONITORING: User Override
    MANUAL_OFF --> MONITORING: User Request

    MONITORING --> MANUAL_ON: User Command
    MONITORING --> MANUAL_OFF: User Command

    MANUAL_ON --> RELAY_ON: Authenticated
    MANUAL_OFF --> RELAY_OFF: Any User

    RELAY_ON --> MONITORING: Load Active
    RELAY_OFF --> MONITORING: Load Inactive

    state MONITORING <<choice>>
    state CHECKING <<choice>>
```

---

## 9. ER Diagram - Database Schema

```mermaid
erDiagram
    USERS ||--o{ ALERTS : receives
    USERS ||--o{ ACCESS_LOGS : generates
    ENERGY_READINGS ||--o{ PREDICTIONS : used_for

    USERS {
        int id PK
        string name
        string face_encoding
        string role
        datetime created_at
    }

    ENERGY_READINGS {
        int id PK
        datetime timestamp
        float voltage
        float current
        float power
        float energy
        float power_factor
    }

    PREDICTIONS {
        int id PK
        datetime predicted_at
        datetime target_time
        float predicted_power
        float actual_power
        string model_version
    }

    ALERTS {
        int id PK
        datetime timestamp
        string type
        string message
        boolean acknowledged
        int user_id FK
    }

    ACCESS_LOGS {
        int id PK
        datetime timestamp
        int user_id FK
        string action
        boolean success
        string ip_address
    }

    RELAY_STATE {
        int id PK
        int channel
        boolean state
        datetime last_changed
        string triggered_by
    }
```

---

## 10. Gantt Chart - Project Timeline

```mermaid
gantt
    title Smart Energy Monitoring - Project Timeline
    dateFormat  YYYY-MM-DD
    axisFormat  %b %d

    section Hardware
    Component Procurement     :2025-01-06, 7d
    Circuit Assembly          :2025-01-13, 14d
    Sensor Calibration        :2025-01-27, 7d
    Relay Integration         :2025-02-03, 7d

    section Firmware
    ESP32 Sensor Code         :2025-01-20, 14d
    MQTT Communication        :2025-02-03, 7d
    OLED Display Code         :2025-02-10, 7d
    Face Camera Integration   :2025-02-17, 14d

    section Backend
    Flask Server Setup        :2025-02-10, 7d
    Database Design           :2025-02-17, 7d
    REST API Development      :2025-02-24, 14d
    WebSocket Integration     :2025-03-10, 7d

    section ML
    Data Collection           :2025-02-17, 21d
    Feature Engineering       :2025-03-10, 7d
    Model Training            :2025-03-17, 14d
    Model Evaluation          :2025-03-31, 7d

    section Frontend
    Dashboard UI              :2025-03-17, 14d
    Chart Integration         :2025-03-31, 7d
    Alert Panel               :2025-04-07, 7d

    section Integration
    System Integration        :2025-04-07, 14d
    Testing & Debugging       :2025-04-21, 14d
    Documentation             :2025-04-07, 21d
    Final Demo Preparation    :2025-05-05, 7d
```
