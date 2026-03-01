#!/usr/bin/env bash
#
# ILEWS System Health Check
# Checks all system components and reports status.
# Exit 0 = all healthy, Exit 1 = critical service down.
#
# Usage: ./scripts/health_check.sh [--quiet]
#
set -euo pipefail

# ── Configuration ──────────────────────────────────────────────────────
API_BASE="${ILEWS_API_BASE:-http://localhost:8000}"
ETL_BASE="${ILEWS_ETL_BASE:-http://localhost:8001}"
ML_BASE="${ILEWS_ML_BASE:-http://localhost:8002}"
NOTIF_BASE="${ILEWS_NOTIF_BASE:-http://localhost:8003}"
PG_HOST="${POSTGRES_HOST:-localhost}"
PG_PORT="${POSTGRES_PORT:-5432}"
REDIS_HOST="${REDIS_HOST:-localhost}"
REDIS_PORT="${REDIS_PORT:-6379}"
MQTT_HOST="${MQTT_HOST:-localhost}"
MQTT_PORT="${MQTT_PORT:-1883}"

QUIET="${1:-}"
FAILURES=0

# ── Helpers ────────────────────────────────────────────────────────────
check_http() {
    local name="$1" url="$2"
    if curl -sf --max-time 5 "$url" > /dev/null 2>&1; then
        [ "$QUIET" != "--quiet" ] && echo "✅ $name: healthy"
    else
        echo "❌ $name: UNREACHABLE ($url)"
        FAILURES=$((FAILURES + 1))
    fi
}

check_tcp() {
    local name="$1" host="$2" port="$3"
    if timeout 5 bash -c "echo > /dev/tcp/$host/$port" 2>/dev/null; then
        [ "$QUIET" != "--quiet" ] && echo "✅ $name: reachable ($host:$port)"
    else
        echo "❌ $name: UNREACHABLE ($host:$port)"
        FAILURES=$((FAILURES + 1))
    fi
}

# ── Application Services ──────────────────────────────────────────────
echo "=== ILEWS System Health Check ==="
echo ""

echo "── Application Services ──"
check_http "FastAPI Backend" "$API_BASE/health"
check_http "ETL Processor"   "$ETL_BASE/health"
check_http "ML Inference"    "$ML_BASE/health"
check_http "Notification"    "$NOTIF_BASE/health"

# ── Infrastructure ────────────────────────────────────────────────────
echo ""
echo "── Infrastructure ──"
check_tcp "PostgreSQL" "$PG_HOST" "$PG_PORT"
check_tcp "Redis"      "$REDIS_HOST" "$REDIS_PORT"
check_tcp "MQTT Broker" "$MQTT_HOST" "$MQTT_PORT"

# ── Offline Nodes ─────────────────────────────────────────────────────
echo ""
echo "── Sensor Network ──"
OFFLINE_RESP=$(curl -sf --max-time 5 "$API_BASE/v1/system/health" 2>/dev/null || echo "")
if [ -n "$OFFLINE_RESP" ]; then
    OFFLINE_COUNT=$(echo "$OFFLINE_RESP" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    data = d.get('data', {})
    print(data.get('offline_nodes', 'N/A'))
except Exception:
    print('N/A')
" 2>/dev/null || echo "N/A")
    [ "$QUIET" != "--quiet" ] && echo "📡 Offline nodes: $OFFLINE_COUNT"
else
    echo "⚠️  Could not fetch sensor network status"
fi

# ── Summary ───────────────────────────────────────────────────────────
echo ""
if [ "$FAILURES" -eq 0 ]; then
    echo "✅ All systems operational."
    exit 0
else
    echo "❌ $FAILURES critical service(s) down!"
    exit 1
fi
