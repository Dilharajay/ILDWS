"""
Integration test fixtures for ILEWS end-to-end pipeline tests.

These tests require a running docker-compose environment.
Use `docker compose -f docker-compose.yml up -d` before running.
Mark: pytest -m integration
"""

import asyncio
import json
import os
import time
from typing import AsyncGenerator, Generator

import httpx
import paho.mqtt.client as mqtt_paho
import pytest
import pytest_asyncio
import websockets

# ── Configuration ──────────────────────────────────────────────────────

API_BASE = os.getenv("ILEWS_API_BASE", "http://localhost:8000")
WS_BASE = os.getenv("ILEWS_WS_BASE", "ws://localhost:8000")
MQTT_HOST = os.getenv("ILEWS_MQTT_HOST", "localhost")
MQTT_PORT = int(os.getenv("ILEWS_MQTT_PORT", "1883"))
ETL_BASE = os.getenv("ILEWS_ETL_BASE", "http://localhost:8001")
ML_BASE = os.getenv("ILEWS_ML_BASE", "http://localhost:8002")
NOTIF_BASE = os.getenv("ILEWS_NOTIF_BASE", "http://localhost:8003")

TEST_ADMIN_USER = os.getenv("ILEWS_TEST_ADMIN_USER", "admin@ilews.local")
TEST_ADMIN_PASS = os.getenv("ILEWS_TEST_ADMIN_PASS", "admin123")


# ── Helpers ────────────────────────────────────────────────────────────

def wait_for_service(url: str, timeout: int = 60) -> bool:
    """Wait for a service health endpoint to respond."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            resp = httpx.get(f"{url}/health", timeout=5)
            if resp.status_code == 200:
                return True
        except (httpx.ConnectError, httpx.ReadTimeout):
            pass
        time.sleep(2)
    return False


# ── Session-scoped fixtures ────────────────────────────────────────────

@pytest.fixture(scope="session")
def check_services():
    """Verify all required services are running before tests."""
    services = {
        "FastAPI Backend": API_BASE,
        "ETL Processor": ETL_BASE,
        "ML Inference": ML_BASE,
        "Notification Service": NOTIF_BASE,
    }
    missing = []
    for name, url in services.items():
        if not wait_for_service(url, timeout=10):
            missing.append(name)

    if missing:
        pytest.skip(
            f"Integration tests require running services: {', '.join(missing)}. "
            "Start with: docker compose up -d"
        )


@pytest.fixture(scope="session")
def auth_token(check_services) -> str:
    """Obtain an auth token for API requests."""
    resp = httpx.post(
        f"{API_BASE}/auth/token",
        data={"username": TEST_ADMIN_USER, "password": TEST_ADMIN_PASS},
        timeout=10,
    )
    if resp.status_code != 200:
        pytest.skip("Could not authenticate — seed admin user first")
    return resp.json()["data"]["access_token"]


# ── Function-scoped async fixtures ─────────────────────────────────────

@pytest_asyncio.fixture
async def api_client(auth_token) -> AsyncGenerator[httpx.AsyncClient, None]:
    """Async HTTP client with auth headers."""
    async with httpx.AsyncClient(
        base_url=API_BASE,
        headers={"Authorization": f"Bearer {auth_token}"},
        timeout=30,
    ) as client:
        yield client


@pytest_asyncio.fixture
async def ws_client(auth_token) -> AsyncGenerator:
    """WebSocket client connected to ILEWS WS endpoint."""
    uri = f"{WS_BASE}/ws?token={auth_token}"
    try:
        async with websockets.connect(uri) as ws:
            yield ws
    except Exception:
        pytest.skip("WebSocket connection failed")


@pytest.fixture
def mqtt_client() -> Generator[mqtt_paho.Client, None, None]:
    """MQTT client connected to the test broker."""
    client = mqtt_paho.Client(
        client_id="ilews-integration-test",
        protocol=mqtt_paho.MQTTv311,
    )
    try:
        client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
        client.loop_start()
        yield client
    except Exception:
        pytest.skip(f"Cannot connect to MQTT broker at {MQTT_HOST}:{MQTT_PORT}")
    finally:
        client.loop_stop()
        client.disconnect()


# ── Test data factories ────────────────────────────────────────────────

@pytest.fixture
def sample_sensor_packet():
    """Generate a sample LoRaWAN-like sensor data packet."""
    return {
        "node_id": "TEST-NODE-001",
        "timestamp": time.time(),
        "soil_moisture": 45.2,
        "tilt_x": 2.1,
        "tilt_y": 1.8,
        "rainfall_mm": 12.5,
        "vibration_freq": 0.3,
        "battery_voltage": 3.72,
        "rssi": -85,
        "snr": 7.5,
    }


@pytest.fixture
def sample_slope_id():
    """Default test slope ID."""
    return os.getenv("ILEWS_TEST_SLOPE_ID", "test-slope-001")


def publish_sensor_data(
    mqtt_client: mqtt_paho.Client,
    node_id: str,
    data: dict,
    topic_prefix: str = "ilews/sensors",
):
    """Publish a sensor data packet to MQTT."""
    topic = f"{topic_prefix}/{node_id}/data"
    payload = json.dumps(data)
    result = mqtt_client.publish(topic, payload, qos=1)
    result.wait_for_publish(timeout=5)
    return result
