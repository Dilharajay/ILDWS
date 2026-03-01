# Cloud – GCP Microservices

Cloud-hosted backend services for data ingestion, ML inference, alerting, and API access.

## Structure

- `services/etl-processor/` – Data ingestion and transformation pipeline
- `services/fastapi-backend/` – REST API backend
- `services/ml-inference/` – Cloud-based ML model serving
- `services/notification-svc/` – Alert and notification delivery
- `ml/` – ML model training and evaluation
- `k8s/` – Kubernetes manifests
- `terraform/` – Infrastructure-as-code (GCP)
- `helm/` – Helm charts
