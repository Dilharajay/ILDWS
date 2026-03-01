/**
 * ILEWS Firmware – ESP32 Sensor Node
 * Entry point for the landslide early-warning sensor node.
 */

#include <Arduino.h>

void setup() {
    Serial.begin(115200);
    Serial.println("ILEWS sensor node starting...");
    // TODO: initialise sensors, comms, and power manager
}

void loop() {
    // TODO: read sensors, transmit data, enter deep sleep
}
