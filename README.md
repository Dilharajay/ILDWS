# ILEWS – Intelligent Landslide Early Warning System

A mission-critical, real-time IoT and AI-driven platform that predicts and detects slope failures using geotechnical sensors, edge computing, and cloud-based deep learning. ILEWS monitors soil moisture, tilt, rainfall, and ground vibration across multiple slopes, runs LSTM-based predictive models both on-edge and in the cloud, and delivers multi-channel alerts (SMS, push, siren) with a target false alarm rate below 5% and lead time exceeding 2 hours.

The system operates across three layers — ESP32 sensor nodes communicating via LoRaWAN, Raspberry Pi edge gateways running local ML inference with offline alerting capability, and a GCP-hosted Kubernetes microservice backend with a React dashboard. All sensor node coordinates are set by manual topographic survey entry (no GPS hardware). Data is retained for 7 years minimum for post-event forensic analysis and government audit compliance.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        CLOUD LAYER (GCP/GKE)                        │
│                                                                     │
│  ┌──────────┐  ┌───────────┐  ┌──────────┐  ┌───────────────────┐  │
│  │ FastAPI   │  │ ETL       │  │ ML       │  │ Notification      │  │
│  │ Backend   │  │ Processor │  │ Inference│  │ Service           │  │
│  └────┬─────┘  └─────┬─────┘  └────┬─────┘  └────────┬──────────┘  │
│       │              │              │                  │             │
│  ┌────┴──────────────┴──────────────┴──────────────────┴──────────┐  │
│  │              PostgreSQL 16 + TimescaleDB  │  Redis             │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                 React Dashboard (Vite + Tailwind)             │   │
│  └──────────────────────────────────────────────────────────────┘   │
└──────────────────────────────┬──────────────────────────────────────┘
                               │ MQTT / HTTPS
                    ┌──────────┴──────────┐
                    │   EDGE LAYER        │
                    │   Raspberry Pi      │
                    │   • LoRaWAN Server  │
                    │   • SQLite Buffer   │
                    │   • TFLite Inference│
                    │   • Local Siren     │
                    └──────────┬──────────┘
                               │ LoRaWAN
              ┌────────────────┼────────────────┐
              │                │                │
        ┌─────┴─────┐   ┌─────┴─────┐   ┌─────┴─────┐
        │ ESP32     │   │ ESP32     │   │ ESP32     │
        │ Node 1    │   │ Node 2    │   │ Node N    │
        │ Sensors:  │   │ Sensors:  │   │ Sensors:  │
        │ • Moisture│   │ • Moisture│   │ • Moisture│
        │ • Tilt    │   │ • Tilt    │   │ • Tilt    │
        │ • Rain    │   │ • Rain    │   │ • Rain    │
        │ • Vibrate │   │ • Vibrate │   │ • Vibrate │
        └───────────┘   └───────────┘   └───────────┘
```

## Risk Levels

| Level  | Score Range | Action |
|--------|------------|--------|
| 🟢 GREEN  | 0.00 – 0.39 | Normal monitoring |
| 🟡 YELLOW | 0.40 – 0.64 | Increased monitoring frequency |
| 🟠 ORANGE | 0.65 – 0.84 | Advisory alerts, prepare evacuation |
| 🔴 RED    | 0.85 – 1.00 | Emergency alerts, activate sirens |

## Project Structure

| Path | Description |
|------|-------------|
| `firmware/` | ESP32 PlatformIO C++ firmware |
| `edge/` | Raspberry Pi gateway (Python): LoRa decoder, SQLite buffer, TFLite inference |
| `cloud/services/fastapi-backend/` | FastAPI REST + WebSocket API |
| `cloud/services/etl-processor/` | MQTT→PostgreSQL ETL pipeline |
| `cloud/services/ml-inference/` | Cloud ML inference service |
| `cloud/services/notification-svc/` | SMS (Twilio) + push (FCM) notifications |
| `cloud/ml/` | LSTM training pipeline, MLflow integration |
| `cloud/terraform/` | Terraform IaC for GCP (VPC, GKE, Cloud SQL, Redis) |
| `cloud/k8s/` | Kubernetes manifests, HPAs, Ingress, ServiceMonitors |
| `dashboard/` | React 18 + TypeScript + Vite + Tailwind dashboard |
| `.github/workflows/` | CI/CD: lint, test, build, deploy |
| `scripts/` | Health check, landslide simulator |
| `docs/` | SRS, SDD, API spec, DB schema, deployment guide |

## Prerequisites

- **Docker** ≥ 24.0 and **Docker Compose** ≥ 2.20
- **Python** ≥ 3.11
- **Node.js** ≥ 20 (for dashboard)
- **PlatformIO** (for firmware builds)
- **Terraform** ≥ 1.5 (for GCP infrastructure)
- **kubectl** + **gcloud CLI** (for production deployment)

## Quick Start

```bash
# 1. Clone and enter the project
git clone <repo-url> && cd ildws

# 2. Copy environment files
cp cloud/services/fastapi-backend/.env.example cloud/services/fastapi-backend/.env
# Edit .env files as needed for each service

# 3. Start all services locally
docker compose up -d --build

# 4. Run database migrations
docker compose exec fastapi-backend alembic upgrade head

# 5. Open the dashboard
open http://localhost:5173

# 6. API documentation (Swagger UI)
open http://localhost:8000/docs
```

## Testing

```bash
# Backend unit tests
cd cloud/services/fastapi-backend && source .venv/bin/activate
pytest tests/ -v

# ETL processor tests
cd cloud/services/etl-processor && source .venv/bin/activate
pytest tests/ -v

# ML inference tests
cd cloud/services/ml-inference && source .venv/bin/activate
pytest tests/ -v

# Dashboard tests
cd dashboard && npm test

# Integration tests (requires running docker-compose)
pytest tests/integration/ -m integration -v

# Health check all services
./scripts/health_check.sh
```

## Simulation & Demo

```bash
# Simulate a progressive landslide event
python scripts/simulate_landslide_event.py \
    --slope-id SLP-001 \
    --duration-minutes 10 \
    --speed-multiplier 5
```

## API Documentation

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`
- **Full API Spec**: [`docs/03_API_Specification_ILEWS.txt`](docs/03_API_Specification_ILEWS.txt)

## Environment Variables

See `.env.example` files in each service directory:
- [`cloud/services/fastapi-backend/.env.example`](cloud/services/fastapi-backend/.env.example)
- [`cloud/services/etl-processor/.env`](cloud/services/etl-processor/.env)
- [`cloud/services/ml-inference/.env`](cloud/services/ml-inference/.env)
- [`cloud/services/notification-svc/.env`](cloud/services/notification-svc/.env)

## Monitoring

- **Prometheus metrics**: Each service exposes `/metrics`
- **Grafana dashboards**: [`cloud/k8s/monitoring/dashboards/`](cloud/k8s/monitoring/dashboards/)
- **ServiceMonitors**: [`cloud/k8s/monitoring/service-monitors.yaml`](cloud/k8s/monitoring/service-monitors.yaml)

## Infrastructure

```bash
# Deploy GCP infrastructure with Terraform
cd cloud/terraform
terraform init
terraform plan -var-file=environments/production.tfvars
terraform apply -var-file=environments/production.tfvars

# Deploy to Kubernetes
cd cloud/k8s
./deploy-all.sh
```

## License

MIT
