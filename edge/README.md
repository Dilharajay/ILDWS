# Edge – Raspberry Pi Gateway

Python services running on a Raspberry Pi that aggregate sensor data from field nodes, perform local inference, and forward results to the cloud.

## Structure

- `gateway_processor/` – Receives and pre-processes sensor packets
- `local_inference/` – Lightweight on-device ML inference
- `config/` – Gateway configuration files
- `requirements.txt` – Python dependencies
