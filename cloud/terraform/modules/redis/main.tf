variable "project_id" { type = string }
variable "region" { type = string }
variable "environment" { type = string }
variable "network_id" { type = string }

resource "google_redis_instance" "cache" {
  name           = "ilews-redis-${var.environment}"
  tier           = "STANDARD_HA"
  memory_size_gb = 1
  region         = var.region

  authorized_network = var.network_id

  redis_version = "REDIS_7_0"

  display_name = "ILEWS Redis ${var.environment}"

  labels = {
    environment = var.environment
    app         = "ilews"
  }
}

output "host" { value = google_redis_instance.cache.host }
output "port" { value = google_redis_instance.cache.port }
