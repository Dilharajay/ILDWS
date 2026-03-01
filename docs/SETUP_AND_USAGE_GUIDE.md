# ILEWS – Setup & Usage Guide

Complete guide for setting up, running, testing, and operating the Intelligent Landslide Early Warning System.

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Prerequisites](#2-prerequisites)
3. [Repository Structure](#3-repository-structure)
4. [Local Development Setup](#4-local-development-setup)
   - 4.1 [Clone & Configure](#41-clone--configure)
   - 4.2 [Environment Variables](#42-environment-variables)
   - 4.3 [Starting Services with Docker Compose](#43-starting-services-with-docker-compose)
   - 4.4 [Database Migrations & Seeding](#44-database-migrations--seeding)
   - 4.5 [Dashboard Development Server](#45-dashboard-development-server)
5. [Running Without Docker (Manual Setup)](#5-running-without-docker-manual-setup)
   - 5.1 [PostgreSQL + TimescaleDB](#51-postgresql--timescaledb)
   - 5.2 [Redis](#52-redis)
   - 5.3 [MQTT Broker (Mosquitto)](#53-mqtt-broker-mosquitto)
   - 5.4 [FastAPI Backend](#54-fastapi-backend)
   - 5.5 [ETL Processor](#55-etl-processor)
   - 5.6 [ML Inference Service](#56-ml-inference-service)
   - 5.7 [Notification Service](#57-notification-service)
   - 5.8 [Dashboard](#58-dashboard)
6. [Edge Gateway Setup](#6-edge-gateway-setup)
7. [Firmware (ESP32 Sensor Nodes)](#7-firmware-esp32-sensor-nodes)
8. [Using the System](#8-using-the-system)
   - 8.1 [Dashboard Navigation](#81-dashboard-navigation)
   - 8.2 [API Endpoints](#82-api-endpoints)
   - 8.3 [Authentication](#83-authentication)
   - 8.4 [WebSocket Real-Time Feed](#84-websocket-real-time-feed)
   - 8.5 [Running a Landslide Simulation](#85-running-a-landslide-simulation)
9. [Testing](#9-testing)
10. [Monitoring & Observability](#10-monitoring--observability)
11. [Production Deployment](#11-production-deployment)
    - 11.1 [GCP Infrastructure with Terraform](#111-gcp-infrastructure-with-terraform)
    - 11.2 [Kubernetes Deployment](#112-kubernetes-deployment)
    - 11.3 [CI/CD Pipeline](#113-cicd-pipeline)
12. [Operational Scripts](#12-operational-scripts)
13. [Troubleshooting](#13-troubleshooting)
14. [Environment Variable Reference](#14-environment-variable-reference)

---

## 1. System Overview

ILEWS is a three-layer IoT platform for real-time landslide risk monitoring:

| Layer | Components | Purpose |
|-------|-----------|---------|
| **Sensing** | ESP32 nodes with soil moisture, tilt, rainfall, vibration sensors | Collect geotechnical data via LoRaWAN |
| **Edge** | Raspberry Pi gateway with TFLite inference, SQLite buffer | Local ML inference, offline alerting, data forwarding |
| **Cloud** | FastAPI + PostgreSQL/TimescaleDB + Redis + React dashboard | Central processing, ML inference, notifications, visualization |

**Risk Levels:**

| Level | Score Range | Meaning |
|-------|------------|---------|
| 🟢 GREEN | 0.00 – 0.39 | Normal conditions |
| 🟡 YELLOW | 0.40 – 0.64 | Increased monitoring |
| 🟠 ORANGE | 0.65 – 0.84 | Advisory alerts issued |
| 🔴 RED | 0.85 – 1.00 | Emergency: sirens + SMS + push |

---

## 2. Prerequisites

### For Local Development (Docker-based — recommended)

| Software | Minimum Version | Purpose |
|----------|----------------|---------|
| Docker | 24.0+ | Container runtime |
| Docker Compose | 2.20+ (included with Docker Desktop) | Multi-service orchestration |
| Git | 2.30+ | Version control |

### For Manual / Full Development

| Software | Minimum Version | Purpose |
|----------|----------------|---------|
| Python | 3.11+ | Backend services, ML, edge gateway |
| Node.js | 20+ | Dashboard (Vite 7 requires Node ≥ 20) |
| npm | 9+ | Dashboard dependency management |
| PostgreSQL | 16 | Database (with TimescaleDB extension) |
| Redis | 7+ | Caching, pub/sub, deduplication |
| Mosquitto | 2.0+ | MQTT broker |
| PlatformIO | Latest | ESP32 firmware builds |
| Terraform | 1.5+ | GCP infrastructure provisioning |
| kubectl | 1.28+ | Kubernetes cluster management |
| gcloud CLI | Latest | GCP authentication & management |

---

## 3. Repository Structure

```
ildws/
├── cloud/
│   ├── services/
│   │   ├── fastapi-backend/       # REST + WebSocket API
│   │   ├── etl-processor/         # MQTT → PostgreSQL ETL pipeline
│   │   ├── ml-inference/          # Cloud ML scoring service
│   │   └── notification-svc/      # SMS (Twilio) + Push (FCM) alerts
│   ├── ml/                        # LSTM training pipeline + MLflow
│   ├── k8s/                       # Kubernetes manifests
│   │   ├── monitoring/            # ServiceMonitors + Grafana dashboards
│   │   └── hpa/                   # Horizontal Pod Autoscalers
│   ├── terraform/                 # GCP infrastructure as code
│   └── helm/                      # Helm charts (future)
├── dashboard/                     # React 18 + TypeScript + Vite + Tailwind
├── edge/
│   ├── gateway_processor/         # LoRa decoder, SQLite buffer, cloud sync
│   └── local_inference/           # TFLite inference, feature builder, alerts
├── firmware/                      # ESP32 PlatformIO C++ project
├── config/
│   └── mosquitto.conf             # MQTT broker config
├── scripts/
│   ├── health_check.sh            # System health verification
│   └── simulate_landslide_event.py # Demo landslide progression
├── tests/
│   └── integration/               # End-to-end pipeline tests
├── docs/                          # Engineering documents (SRS, SDD, API spec, etc.)
├── docker-compose.yml             # Local development stack (9 services)
├── Makefile                       # Convenience targets
├── .env.example                   # Environment variable template
└── .github/workflows/             # CI/CD pipelines
```

---

## 4. Local Development Setup

### 4.1 Clone & Configure

```bash
# Clone the repository
git clone <repo-url> ildws
cd ildws

# Switch to the develop branch
git checkout develop
```

### 4.2 Environment Variables

Copy the example environment file and customise as needed:

```bash
cp .env.example .env
```

**For each service, create a `.env` file** (or use the existing ones):

```bash
# FastAPI Backend
cat > cloud/services/fastapi-backend/.env << 'EOF'
ENVIRONMENT=development
DATABASE_URL=postgresql+asyncpg://ilews_dev:ilews_dev_pass@postgres:5432/ilews
REDIS_URL=redis://redis:6379/0
JWT_SECRET_KEY=dev-secret-change-in-production
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_HOURS=8
EOF

# ETL Processor
cat > cloud/services/etl-processor/.env << 'EOF'
ENVIRONMENT=development
DATABASE_URL=postgresql+asyncpg://ilews_dev:ilews_dev_pass@postgres:5432/ilews
REDIS_URL=redis://redis:6379/0
MQTT_HOST=mosquitto
MQTT_PORT=1883
EOF

# ML Inference
cat > cloud/services/ml-inference/.env << 'EOF'
ENVIRONMENT=development
DATABASE_URL=postgresql+asyncpg://ilews_dev:ilews_dev_pass@postgres:5432/ilews
REDIS_URL=redis://redis:6379/0
MLFLOW_TRACKING_URI=http://mlflow:5000
EOF

# Notification Service
cat > cloud/services/notification-svc/.env << 'EOF'
ENVIRONMENT=development
REDIS_URL=redis://redis:6379/0
TWILIO_ACCOUNT_SID=test
TWILIO_AUTH_TOKEN=test
TWILIO_FROM_NUMBER=+10000000000
FCM_SERVER_KEY=test
EOF
```

> **Important:** Inside Docker Compose, services reference each other by container name (`postgres`, `redis`, `mosquitto`). For host-based development, use `localhost` instead.

### 4.3 Starting Services with Docker Compose

```bash
# Start all services (builds images on first run)
make dev-up
# or equivalently:
docker compose up -d --build

# Check all services are running
docker compose ps

# View logs
make dev-logs
# or for a specific service:
docker compose logs -f fastapi-backend
```

**Services and Ports:**

| Service | URL | Description |
|---------|-----|-------------|
| FastAPI Backend | http://localhost:8000 | REST API + WebSocket |
| Swagger UI | http://localhost:8000/docs | Interactive API documentation |
| ReDoc | http://localhost:8000/redoc | Alternative API docs |
| ETL Processor | http://localhost:8001 | MQTT ingestion pipeline |
| Notification Service | http://localhost:8002 | Alert dispatching |
| ML Inference | http://localhost:8003 | Risk scoring engine |
| Dashboard | http://localhost:3080 | Monitoring UI (production build via nginx) |
| PostgreSQL | localhost:5432 | Database |
| Redis | localhost:6379 | Cache & pub/sub |
| MQTT Broker | localhost:1883 | Sensor data ingestion |
| MQTT WebSocket | localhost:9001 | Browser-based MQTT |
| MLflow | http://localhost:5000 | ML experiment tracking |

### 4.4 Database Migrations & Seeding

```bash
# Run Alembic migrations (creates all tables)
make db-migrate
# or:
docker compose exec fastapi-backend alembic upgrade head

# Seed the database with sample data (admin user, slopes, nodes)
make db-seed
# or:
docker compose exec fastapi-backend python -m scripts.seed_data
```

**Seeded Data:**

| Entity | Details |
|--------|---------|
| Admin User | `admin@ilews.gov` / `changeme123` (role: `system_admin`) |
| Slopes | Bukit Antarabangsa (`SLOPE_BKT_01`), Cameron Highlands (`SLOPE_CMH_01`) |
| Sensor Nodes | 3 nodes per slope (6 total): `BKT01-A1/A2/A3`, `CMH01-B1/B2/B3` |

### 4.5 Dashboard Development Server

For active dashboard development with hot module replacement:

```bash
cd dashboard

# If using nvm (Node 20+ required)
nvm use 20  # or: nvm install 20

# Install dependencies
npm install

# Start development server
npm run dev
# → Dashboard at http://localhost:5173 with API proxy to backend
```

---

## 5. Running Without Docker (Manual Setup)

For debugging or when Docker is not available.

### 5.1 PostgreSQL + TimescaleDB

```bash
# Install TimescaleDB (Ubuntu/Debian)
sudo apt install postgresql-16 postgresql-16-timescaledb

# Create database and user
sudo -u postgres psql << 'SQL'
CREATE USER ilews_dev WITH PASSWORD 'ilews_dev_pass';
CREATE DATABASE ilews OWNER ilews_dev;
\c ilews
CREATE EXTENSION IF NOT EXISTS timescaledb;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
SQL
```

### 5.2 Redis

```bash
sudo apt install redis-server
redis-cli ping  # Should return PONG
```

### 5.3 MQTT Broker (Mosquitto)

```bash
sudo apt install mosquitto
# Config is at config/mosquitto.conf (anonymous access for dev)
mosquitto -c config/mosquitto.conf -d
```

### 5.4 FastAPI Backend

```bash
cd cloud/services/fastapi-backend

# Create virtual environment
python3.11 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -e ".[dev]"  # or: pip install -r requirements.txt

# Configure for localhost
export DATABASE_URL="postgresql+asyncpg://ilews_dev:ilews_dev_pass@localhost:5432/ilews"
export REDIS_URL="redis://localhost:6379/0"
export JWT_SECRET_KEY="dev-secret"
export JWT_ALGORITHM="HS256"

# Run migrations
alembic upgrade head

# Seed data
python -m scripts.seed_data

# Start the server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 5.5 ETL Processor

```bash
cd cloud/services/etl-processor
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

export DATABASE_URL="postgresql+asyncpg://ilews_dev:ilews_dev_pass@localhost:5432/ilews"
export REDIS_URL="redis://localhost:6379/0"
export MQTT_HOST="localhost"
export MQTT_PORT="1883"

python -m app.main
```

### 5.6 ML Inference Service

```bash
cd cloud/services/ml-inference
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

export DATABASE_URL="postgresql+asyncpg://ilews_dev:ilews_dev_pass@localhost:5432/ilews"
export REDIS_URL="redis://localhost:6379/0"

uvicorn app.main:app --host 0.0.0.0 --port 8003 --reload
```

### 5.7 Notification Service

```bash
cd cloud/services/notification-svc
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

export REDIS_URL="redis://localhost:6379/0"

uvicorn app.main:app --host 0.0.0.0 --port 8002 --reload
```

### 5.8 Dashboard

```bash
cd dashboard
nvm use 20  # Node 20+ required
npm install
npm run dev
# → http://localhost:5173
```

---

## 6. Edge Gateway Setup

The edge gateway runs on a Raspberry Pi connected to sensor nodes via LoRaWAN.

### Hardware Requirements

- Raspberry Pi 4 (4GB+ RAM recommended)
- RAK2245 or similar LoRaWAN concentrator HAT
- SD card (32GB+)
- Power supply, enclosure, antenna

### Software Setup

```bash
# On the Raspberry Pi
cd edge

# Install system dependencies
sudo apt install python3.11 python3.11-venv

# Gateway processor
cd gateway_processor
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Local inference engine
cd ../local_inference
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Configure
cat > .env << 'EOF'
MQTT_HOST=localhost
MQTT_PORT=1883
CLOUD_API_URL=https://api.ilews.example.com
CLOUD_MQTT_HOST=cloud-mqtt.ilews.example.com
CLOUD_MQTT_PORT=8883
SQLITE_DB_PATH=/var/lib/ilews/buffer.db
EOF

# Start the gateway processor
python -m app.main
```

### ChirpStack LoRaWAN Server

Install ChirpStack on the Raspberry Pi to manage LoRaWAN device registration and decoding. See [ChirpStack documentation](https://www.chirpstack.io/docs/) for installation instructions.

### Offline Operation

The edge gateway is designed to operate fully offline:
- Sensor data is buffered in SQLite when cloud connectivity is lost
- Local TFLite model runs inference independently
- Sirens can be activated locally based on edge-computed risk scores
- When connectivity is restored, all buffered data is forwarded and deduplicated

---

## 7. Firmware (ESP32 Sensor Nodes)

### Hardware Bill of Materials (per node, < $200 USD)

| Component | Model | Purpose |
|-----------|-------|---------|
| MCU | ESP32-WROOM-32 | Main controller |
| LoRa Module | SX1276 | LoRaWAN communication |
| Soil Moisture | Capacitive v1.2 | Volumetric water content |
| Tilt Sensor | ADXL345 or MPU6050 | Slope inclination |
| Rain Gauge | Tipping bucket | Rainfall intensity |
| Vibration | SW-420 or ADXL345 | Ground movement detection |
| Battery | 18650 Li-ion + solar | Power supply |

### Building & Flashing

```bash
cd firmware

# Install PlatformIO (if not already installed)
pip install platformio

# Build the firmware
make firmware-build
# or:
platformio run

# Flash to a connected ESP32
platformio run --target upload

# Monitor serial output
platformio device monitor
```

### Node Coordinate Configuration

> **Important:** Node coordinates are entered MANUALLY from topographic surveys or satellite imagery. There is no GPS hardware on the sensor nodes. Coordinates are set via the API or dashboard admin panel.

---

## 8. Using the System

### 8.1 Dashboard Navigation

After starting the system and seeding data, open the dashboard:
- **Docker**: http://localhost:3080
- **Dev server**: http://localhost:5173

**Login Credentials:**
- Email: `admin@ilews.gov`
- Password: `changeme123`

**Views:**

| View | Path | Description |
|------|------|-------------|
| **Map** | `/map` | Interactive Leaflet map with sensor nodes as coloured markers (colour = risk level). Click a node to see detail panel with readings and sparklines. Risk zones shown as polygons. |
| **Alerts** | `/alerts` | Filterable table of all alerts. Acknowledge or resolve alerts. Filter by risk level and date range. |
| **Nodes** | `/nodes` | Searchable table of all sensor nodes. View status, battery level, last reading time. Admin users can edit node coordinates. |
| **Reports** | `/reports` | Generate and download reports (daily summaries, incident reports, compliance audits). |
| **Admin** | `/admin` | System health overview, user management, service status. Admin role required. |

**Real-Time Features:**
- WebSocket connection (shown as WiFi icon in sidebar — green = connected, red = disconnected)
- Risk level changes update map markers in real-time
- RED alerts trigger a full-screen modal with audio alarm
- Toast notifications for new alerts

### 8.2 API Endpoints

Full interactive documentation is available at:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

**Key Endpoints:**

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/auth/token` | Login (returns JWT access token) |
| `POST` | `/auth/refresh` | Refresh access token |
| `GET` | `/v1/slopes` | List all monitored slopes |
| `POST` | `/v1/slopes` | Create a new slope |
| `GET` | `/v1/slopes/{id}` | Get slope details |
| `GET` | `/v1/slopes/{id}/risk` | Get current risk score |
| `GET` | `/v1/slopes/risk/overview` | Risk overview for all slopes |
| `GET` | `/v1/nodes` | List all sensor nodes |
| `POST` | `/v1/nodes` | Register a new sensor node |
| `GET` | `/v1/readings` | Query sensor readings (paginated) |
| `GET` | `/v1/alerts` | List alerts (filterable) |
| `PATCH` | `/v1/alerts/{id}/acknowledge` | Acknowledge an alert |
| `PATCH` | `/v1/alerts/{id}/resolve` | Resolve an alert |
| `GET` | `/v1/map/overview` | Map data (nodes + risk zones) |
| `GET` | `/v1/system/health` | System health status |
| `GET` | `/health` | Service health check |
| `GET` | `/metrics` | Prometheus metrics |
| `WS` | `/v1/ws?token=<jwt>` | WebSocket real-time feed |

**Response Format:**

All API responses follow a standard envelope:

```json
// Success
{
  "status": "success",
  "data": { ... },
  "meta": { "total": 42, "page": 1, "per_page": 20 }
}

// Error
{
  "status": "error",
  "error": {
    "code": "UNAUTHORIZED",
    "message": "Invalid or expired token"
  }
}
```

### 8.3 Authentication

```bash
# Login to get a token
curl -X POST http://localhost:8000/auth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin@ilews.gov&password=changeme123"

# Use the token for authenticated requests
TOKEN="<access_token from response>"
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/v1/slopes
```

**Roles:**
| Role | Permissions |
|------|------------|
| `system_admin` | Full access: manage users, slopes, nodes, settings |
| `operator` | Monitor, acknowledge/resolve alerts, view data |
| `viewer` | Read-only access to dashboard and data |

### 8.4 WebSocket Real-Time Feed

Connect to the WebSocket endpoint for live updates:

```javascript
const ws = new WebSocket('ws://localhost:8000/v1/ws?token=<jwt>');

// Subscribe to specific slopes
ws.send(JSON.stringify({
  action: 'subscribe',
  slope_ids: ['SLOPE_BKT_01', 'SLOPE_CMH_01']
}));

// Receive events
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  // data.type: 'RISK_UPDATE', 'ALERT_TRIGGERED', 'SENSOR_DATA', 'NODE_STATUS'
  console.log(data);
};
```

### 8.5 Running a Landslide Simulation

The simulator publishes progressively worsening sensor data to demonstrate the full alert chain:

```bash
# Quick demo (2 minutes, 10x speed)
python scripts/simulate_landslide_event.py \
  --slope-id SLOPE_BKT_01 \
  --duration-minutes 2 \
  --speed-multiplier 10

# Realistic simulation (10 minutes)
python scripts/simulate_landslide_event.py \
  --slope-id SLOPE_BKT_01 \
  --duration-minutes 10 \
  --speed-multiplier 1
```

**What happens during simulation:**
1. Soil moisture rises from 25% → 95%
2. Tilt increases from 1° → 15°
3. Rainfall ramps from 2mm → 80mm
4. Risk progresses: GREEN → YELLOW → ORANGE → RED
5. When RED is reached, alerts fire (SMS + push + siren)
6. Dashboard map markers change colour in real-time
7. RED alert modal appears with audio alarm

---

## 9. Testing

### Unit Tests

Each service has its own test suite:

```bash
# FastAPI Backend (57 tests)
cd cloud/services/fastapi-backend
source .venv/bin/activate
pytest tests/ -v

# ETL Processor (28 tests)
cd cloud/services/etl-processor
source .venv/bin/activate
pytest tests/ -v

# ML Inference Service (13 tests)
cd cloud/services/ml-inference
source .venv/bin/activate
pytest tests/ -v

# Notification Service (13 tests)
cd cloud/services/notification-svc
source .venv/bin/activate
pytest tests/ -v

# ML Pipeline (18 tests)
cd cloud/ml
source .venv/bin/activate
pytest tests/ -v

# Edge Gateway (8 tests)
cd edge/gateway_processor
source .venv/bin/activate
pytest tests/ -v

# Edge Local Inference (10 tests)
cd edge/local_inference
source .venv/bin/activate
pytest tests/ -v

# Dashboard (20 tests)
cd dashboard
npm test
```

### Run All Tests

```bash
make test-all
```

### Integration Tests

Require a running Docker Compose environment:

```bash
# Start services
make dev-up

# Run integration tests
pytest tests/integration/ -m integration -v
```

**Integration test coverage:**
- `test_full_pipeline.py` — Sensor → ETL → ML → Alert → WebSocket end-to-end
- `test_edge_failover.py` — Offline buffering, resync, ordering, deduplication

### Linting

```bash
# Python (flake8 + black)
make lint
# or:
flake8 cloud/ edge/ --max-line-length=100
black --check cloud/ edge/

# Dashboard (ESLint)
cd dashboard && npm run lint
```

---

## 10. Monitoring & Observability

### Prometheus Metrics

Every service exposes a `/metrics` endpoint in Prometheus format:

| Service | Metrics URL | Key Metrics |
|---------|-------------|-------------|
| FastAPI Backend | http://localhost:8000/metrics | `ilews_http_requests_total`, `ilews_http_request_duration_seconds`, `ilews_active_websocket_connections`, `ilews_active_red_alerts_total` |
| ETL Processor | http://localhost:8001/metrics | `ilews_etl_mqtt_messages_received_total`, `ilews_etl_mqtt_messages_valid_total`, `ilews_etl_end_to_end_ingestion_latency_seconds` |
| ML Inference | http://localhost:8003/metrics | `ilews_ml_inference_requests_total`, `ilews_ml_inference_latency_seconds`, `ilews_ml_current_risk_level` |
| Notification | http://localhost:8002/metrics | Standard Python process metrics |

### Grafana Dashboards

Pre-built dashboard JSONs are in `cloud/k8s/monitoring/dashboards/`:

| Dashboard | File | Contents |
|-----------|------|----------|
| System Overview | `system-overview.json` | Active RED alerts, WebSocket connections, HTTP request rate, API health, ingestion/request latency |
| Sensor Network | `sensor-network.json` | MQTT message rates, valid/invalid breakdown, duplicates, active nodes, ingestion latency percentiles |
| ML Performance | `ml-performance.json` | Inference request rate, latency percentiles, risk level distribution, model version info |

**To import into Grafana:**
1. Open Grafana (http://localhost:3000 if running locally)
2. Go to Dashboards → Import
3. Upload the JSON file or paste its contents

### Kubernetes ServiceMonitors

Defined in `cloud/k8s/monitoring/service-monitors.yaml` — Prometheus Operator auto-discovers and scrapes all ILEWS services at 15-second intervals.

---

## 11. Production Deployment

### 11.1 GCP Infrastructure with Terraform

```bash
cd cloud/terraform

# Initialise Terraform
terraform init

# Review the plan
terraform plan -var-file=environments/production.tfvars

# Apply (creates VPC, GKE cluster, Cloud SQL, Redis, GCS, etc.)
terraform apply -var-file=environments/production.tfvars
```

**Resources provisioned:**
- VPC with private subnets and Cloud NAT
- GKE private cluster (3 nodes, e2-standard-4)
- Cloud SQL PostgreSQL 16 with HA (TimescaleDB)
- Memorystore Redis (STANDARD_HA, 2GB)
- GCS buckets for ML models and backups
- Artifact Registry for Docker images
- Secret Manager for credentials

**Staging environment:**
```bash
terraform plan -var-file=environments/staging.tfvars
terraform apply -var-file=environments/staging.tfvars
```

### 11.2 Kubernetes Deployment

```bash
cd cloud/k8s

# Ensure kubectl is configured for the GKE cluster
gcloud container clusters get-credentials ilews-production --region asia-southeast1

# Deploy all services
./deploy-all.sh

# Or deploy individually
kubectl apply -f namespace.yaml
kubectl apply -f fastapi-backend.yaml
kubectl apply -f etl-processor.yaml
kubectl apply -f ml-inference.yaml
kubectl apply -f notification-svc.yaml
kubectl apply -f ingress.yaml
kubectl apply -f hpa/
kubectl apply -f monitoring/
```

**Kubernetes Resources:**
- Namespace: `ilews-production`
- Deployments with resource limits and readiness/liveness probes
- Horizontal Pod Autoscalers (CPU threshold: 70%, min: 2, max: 10)
- Ingress with TLS termination
- ServiceMonitors for Prometheus scraping

### 11.3 CI/CD Pipeline

**GitHub Actions Workflows** (`.github/workflows/`):

| Workflow | Trigger | Actions |
|----------|---------|---------|
| `ci.yml` | Push to any branch, PRs to `main`/`develop` | Lint (flake8, ESLint), test (pytest, vitest), security scan |
| `build-push.yml` | Push to `main`/`develop` | Build Docker images, push to Artifact Registry |
| `deploy-staging.yml` | Push to `develop` | Deploy to staging GKE cluster |
| `deploy-production.yml` | Push to `main` (manual approval) | Deploy to production GKE cluster |

**Required GitHub Secrets:**

| Secret | Description |
|--------|-------------|
| `GCP_SA_KEY` | GCP service account JSON key |
| `GCP_PROJECT_ID` | GCP project ID |
| `GKE_CLUSTER_NAME` | GKE cluster name |
| `GKE_CLUSTER_ZONE` | GKE cluster region/zone |

---

## 12. Operational Scripts

### Health Check

```bash
# Check all system components
./scripts/health_check.sh

# Quiet mode (only shows failures)
./scripts/health_check.sh --quiet

# Custom service URLs
ILEWS_API_BASE=https://api.ilews.example.com ./scripts/health_check.sh
```

Exit codes: `0` = all healthy, `1` = critical service down. Suitable for cron jobs or monitoring.

### Landslide Simulator

```bash
python scripts/simulate_landslide_event.py \
  --slope-id SLOPE_BKT_01 \
  --duration-minutes 5 \
  --speed-multiplier 10
```

| Argument | Default | Description |
|----------|---------|-------------|
| `--slope-id` | `SLP-001` | Target slope to simulate |
| `--duration-minutes` | `10` | Simulation length |
| `--speed-multiplier` | `1.0` | Time acceleration factor |

---

## 13. Troubleshooting

### Common Issues

**Docker services won't start:**
```bash
# Check which services failed
docker compose ps

# View specific service logs
docker compose logs fastapi-backend

# Rebuild from scratch
docker compose down -v  # WARNING: deletes all data
docker compose up -d --build
```

**Database connection errors:**
```bash
# Verify PostgreSQL is running
docker compose exec postgres pg_isready -U ilews_dev

# Check if TimescaleDB extension is loaded
docker compose exec postgres psql -U ilews_dev -d ilews -c "SELECT extname FROM pg_extension;"
```

**Dashboard shows "Loading..." permanently:**
- Check that the FastAPI backend is running and healthy
- Verify the API proxy in `dashboard/vite.config.ts` or that `VITE_API_BASE_URL` is correct
- Check browser console for CORS or network errors

**WebSocket disconnects frequently:**
- Ensure the JWT token is valid (check expiry with `jwt.io`)
- The WebSocket auto-reconnects with exponential backoff (1s → 30s max)
- Check `ilews_active_websocket_connections` metric

**MQTT messages not being ingested:**
```bash
# Subscribe to MQTT topic to verify messages arrive
mosquitto_sub -h localhost -t "ilews/sensors/#" -v

# Check ETL processor health
curl http://localhost:8001/health
```

**Edge gateway not syncing:**
- Check SQLite buffer: `sqlite3 /var/lib/ilews/buffer.db "SELECT COUNT(*) FROM sensor_buffer WHERE synced = 0;"`
- Verify cloud MQTT connectivity
- Check edge logs for connection errors

**Node.js version issues (dashboard):**
```bash
# Vite 7 requires Node 20+
nvm install 20
nvm use 20
node --version  # Should show v20.x.x
```

### Useful Debug Commands

```bash
# Check all service health endpoints
curl -s http://localhost:8000/health | python3 -m json.tool
curl -s http://localhost:8001/health | python3 -m json.tool
curl -s http://localhost:8002/health | python3 -m json.tool
curl -s http://localhost:8003/health | python3 -m json.tool

# Check database connectivity via API
curl -s http://localhost:8000/v1/system/health | python3 -m json.tool

# View recent sensor readings
curl -s -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/v1/readings?limit=5" | python3 -m json.tool

# Check Redis
redis-cli ping
redis-cli keys "ilews:*"

# Check MQTT broker
mosquitto_sub -h localhost -t "#" -v  # Subscribe to ALL topics
```

---

## 14. Environment Variable Reference

### FastAPI Backend

| Variable | Default | Description |
|----------|---------|-------------|
| `ENVIRONMENT` | `development` | Runtime environment (`development`, `staging`, `production`) |
| `DATABASE_URL` | — | PostgreSQL async connection string |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection string |
| `JWT_SECRET_KEY` | — | **Required.** Secret key for JWT signing |
| `JWT_ALGORITHM` | `HS256` | JWT algorithm (`HS256` for dev, `RS256` for production) |
| `ACCESS_TOKEN_EXPIRE_HOURS` | `8` | Token expiry in hours |

### ETL Processor

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | — | PostgreSQL async connection string |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection string |
| `MQTT_HOST` | `localhost` | MQTT broker hostname |
| `MQTT_PORT` | `1883` | MQTT broker port |

### ML Inference Service

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | — | PostgreSQL async connection string |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection string |
| `MLFLOW_TRACKING_URI` | `http://localhost:5000` | MLflow server URL |
| `MODEL_PATH` | — | Path to TFLite/SavedModel |

### Notification Service

| Variable | Default | Description |
|----------|---------|-------------|
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection string |
| `TWILIO_ACCOUNT_SID` | — | Twilio account SID for SMS |
| `TWILIO_AUTH_TOKEN` | — | Twilio auth token |
| `TWILIO_FROM_NUMBER` | — | Twilio sender phone number |
| `FCM_SERVER_KEY` | — | Firebase Cloud Messaging server key |

### Dashboard

| Variable | Default | Description |
|----------|---------|-------------|
| `VITE_API_BASE_URL` | `/api` | Backend API base URL |
| `VITE_WS_URL` | `ws://localhost:8000/v1/ws` | WebSocket endpoint URL |

### Edge Gateway

| Variable | Default | Description |
|----------|---------|-------------|
| `MQTT_HOST` | `localhost` | Local MQTT broker |
| `MQTT_PORT` | `1883` | Local MQTT port |
| `CLOUD_API_URL` | — | Cloud API endpoint |
| `CLOUD_MQTT_HOST` | — | Cloud MQTT broker |
| `CLOUD_MQTT_PORT` | `8883` | Cloud MQTT port (TLS) |
| `SQLITE_DB_PATH` | `buffer.db` | SQLite buffer file path |

---

*Last updated: March 2026*
*ILEWS v1.0 — Intelligent Landslide Early Warning System*
