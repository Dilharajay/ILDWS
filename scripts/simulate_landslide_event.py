#!/usr/bin/env python3
"""
ILEWS Landslide Event Simulator

Simulates a progressive landslide precursor event by publishing
sensor data that gradually increases soil moisture, tilt, and vibration
to demonstrate the system transitioning from GREEN → YELLOW → ORANGE → RED.

Usage:
    python scripts/simulate_landslide_event.py \
        --slope-id SLP-001 \
        --duration-minutes 10 \
        --speed-multiplier 2

Requires: paho-mqtt, httpx (or requests)
"""

import argparse
import json
import math
import os
import sys
import time
from datetime import datetime, timezone

try:
    import paho.mqtt.client as mqtt
except ImportError:
    print("Install paho-mqtt: pip install paho-mqtt")
    sys.exit(1)


# ── Risk level thresholds ──────────────────────────────────────────────
RISK_LEVELS = {
    "GREEN": (0.0, 0.39),
    "YELLOW": (0.40, 0.64),
    "ORANGE": (0.65, 0.84),
    "RED": (0.85, 1.0),
}


def get_risk_label(progress: float) -> str:
    """Get risk level label based on simulation progress (0.0 to 1.0)."""
    for level, (low, high) in RISK_LEVELS.items():
        if low <= progress <= high:
            return level
    return "RED"


def generate_sensor_data(
    node_id: str,
    progress: float,
    base_moisture: float = 25.0,
    base_tilt: float = 1.0,
) -> dict:
    """
    Generate sensor data that escalates with progress.

    progress: 0.0 (normal) → 1.0 (critical landslide conditions)
    """
    # Soil moisture: 25% (dry) → 95% (saturated)
    soil_moisture = base_moisture + (70.0 * progress)

    # Tilt: 1° (stable) → 15° (significant movement)
    tilt_x = base_tilt + (14.0 * progress) + (0.5 * math.sin(progress * 10))
    tilt_y = 0.5 + (5.0 * progress)

    # Rainfall: 0mm → 80mm (heavy)
    rainfall = 2.0 + (78.0 * progress ** 1.5)

    # Vibration: 0.1 Hz (baseline) → 2.5 Hz (active sliding)
    vibration = 0.1 + (2.4 * progress ** 2)

    # Battery: slowly draining
    battery = 3.8 - (0.3 * progress)

    return {
        "node_id": node_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "soil_moisture": round(soil_moisture, 1),
        "tilt_x": round(tilt_x, 2),
        "tilt_y": round(tilt_y, 2),
        "rainfall_mm": round(rainfall, 1),
        "vibration_freq": round(vibration, 3),
        "battery_voltage": round(battery, 2),
        "rssi": -75 - int(10 * progress),
        "snr": 8.0 - (3.0 * progress),
    }


def run_simulation(args):
    """Execute the landslide simulation."""
    mqtt_host = os.getenv("MQTT_HOST", "localhost")
    mqtt_port = int(os.getenv("MQTT_PORT", "1883"))
    topic_prefix = os.getenv("MQTT_TOPIC_PREFIX", "ilews/sensors")

    node_ids = [f"{args.slope_id}-NODE-{i:03d}" for i in range(1, 4)]

    # Calculate timing
    total_seconds = args.duration_minutes * 60 / args.speed_multiplier
    interval = max(1.0, total_seconds / 100)  # ~100 data points
    steps = int(total_seconds / interval)

    print(f"{'=' * 60}")
    print(f"  ILEWS Landslide Event Simulator")
    print(f"{'=' * 60}")
    print(f"  Slope ID:         {args.slope_id}")
    print(f"  Nodes:            {', '.join(node_ids)}")
    print(f"  Duration:         {args.duration_minutes} min (real: {total_seconds:.0f}s)")
    print(f"  Speed:            {args.speed_multiplier}x")
    print(f"  MQTT broker:      {mqtt_host}:{mqtt_port}")
    print(f"  Data points:      ~{steps * len(node_ids)}")
    print(f"{'=' * 60}")
    print()

    # Connect MQTT
    client = mqtt.Client(
        client_id="ilews-simulator",
        protocol=mqtt.MQTTv311,
    )
    try:
        client.connect(mqtt_host, mqtt_port, keepalive=60)
        client.loop_start()
        print(f"✅ Connected to MQTT broker at {mqtt_host}:{mqtt_port}")
    except Exception as e:
        print(f"❌ Cannot connect to MQTT: {e}")
        print("   Start the broker with: docker compose up -d mosquitto")
        sys.exit(1)

    try:
        prev_level = None
        for step in range(steps + 1):
            progress = step / steps  # 0.0 → 1.0
            risk_label = get_risk_label(progress)

            # Print level transition
            if risk_label != prev_level:
                colors = {
                    "GREEN": "\033[92m",
                    "YELLOW": "\033[93m",
                    "ORANGE": "\033[33m",
                    "RED": "\033[91m",
                }
                reset = "\033[0m"
                color = colors.get(risk_label, "")
                print(
                    f"\n{'🔔' if risk_label == 'RED' else '📊'} "
                    f"Risk Level: {color}{risk_label}{reset} "
                    f"(progress: {progress:.0%})"
                )
                prev_level = risk_label

            # Publish data for each node
            for node_id in node_ids:
                data = generate_sensor_data(node_id, progress)
                topic = f"{topic_prefix}/{node_id}/data"
                payload = json.dumps(data)
                client.publish(topic, payload, qos=1)

            # Progress indicator
            bar_len = 40
            filled = int(bar_len * progress)
            bar = "█" * filled + "░" * (bar_len - filled)
            sys.stdout.write(
                f"\r  [{bar}] {progress:.0%} | "
                f"Step {step}/{steps} | "
                f"Moisture: {25 + 70 * progress:.0f}% | "
                f"Tilt: {1 + 14 * progress:.1f}°"
            )
            sys.stdout.flush()

            if step < steps:
                time.sleep(interval)

        print(f"\n\n✅ Simulation complete! Published {steps * len(node_ids)} packets.")
        print(f"   Check dashboard for risk level changes on slope {args.slope_id}.")

    except KeyboardInterrupt:
        print("\n\n⚠️  Simulation interrupted by user.")
    finally:
        client.loop_stop()
        client.disconnect()


def main():
    parser = argparse.ArgumentParser(
        description="Simulate a progressive landslide event for ILEWS demo"
    )
    parser.add_argument(
        "--slope-id",
        default="SLP-001",
        help="Target slope ID (default: SLP-001)",
    )
    parser.add_argument(
        "--duration-minutes",
        type=float,
        default=10,
        help="Simulation duration in minutes (default: 10)",
    )
    parser.add_argument(
        "--speed-multiplier",
        type=float,
        default=1.0,
        help="Speed multiplier (2.0 = twice as fast, default: 1.0)",
    )
    args = parser.parse_args()
    run_simulation(args)


if __name__ == "__main__":
    main()
