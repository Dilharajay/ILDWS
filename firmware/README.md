# Firmware – ESP32 IoT Sensor Nodes

Embedded firmware for ESP32-based field sensor nodes that collect environmental data (soil moisture, rainfall, tilt, vibration) and transmit readings to the edge gateway.

## Structure

- `src/main.cpp` – Entry point
- `src/sensors/` – Sensor drivers and reading logic
- `src/comms/` – Communication protocols (LoRa / MQTT)
- `src/power/` – Power management and deep-sleep routines
- `include/` – Shared headers
- `platformio.ini` – PlatformIO build configuration
