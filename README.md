# ILEWS – Intelligent Landslide Early Warning System

A multi-layer IoT platform for real-time landslide risk monitoring and alerting.

## Architecture

| Layer | Technology | Path |
|-------|-----------|------|
| **Firmware** | ESP32 (PlatformIO / C++) | `firmware/` |
| **Edge** | Raspberry Pi gateway (Python) | `edge/` |
| **Cloud** | GCP microservices (FastAPI, K8s) | `cloud/` |
| **Dashboard** | Web-based monitoring UI | `dashboard/` |

## Quick Start

```bash
# Clone the repository
git clone <repo-url> && cd ilews

# Start cloud services locally
docker-compose up --build
```

## License

MIT
