#!/usr/bin/env bash
# Deploy all ILEWS Kubernetes manifests in dependency order
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=== Deploying ILEWS to Kubernetes ==="

echo "[1/5] Creating namespace..."
kubectl apply -f "$SCRIPT_DIR/namespace.yaml"

echo "[2/5] Deploying services..."
kubectl apply -f "$SCRIPT_DIR/fastapi-backend.yaml"
kubectl apply -f "$SCRIPT_DIR/etl-processor.yaml"
kubectl apply -f "$SCRIPT_DIR/notification-svc.yaml"
kubectl apply -f "$SCRIPT_DIR/ml-inference.yaml"

echo "[3/5] Deploying HPAs..."
kubectl apply -f "$SCRIPT_DIR/hpa/"

echo "[4/5] Deploying Ingress..."
kubectl apply -f "$SCRIPT_DIR/ingress.yaml"

echo "[5/5] Verifying deployments..."
kubectl -n ilews-production get deployments
kubectl -n ilews-production get services
kubectl -n ilews-production get hpa

echo "=== ILEWS deployment complete ==="
