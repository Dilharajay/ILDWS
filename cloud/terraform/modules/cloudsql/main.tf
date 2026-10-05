variable "project_id" { type = string }
variable "region" { type = string }
variable "environment" { type = string }
variable "network_id" { type = string }
variable "db_tier" { type = string }

resource "google_sql_database_instance" "postgres" {
  name             = "ilews-db-${var.environment}"
  database_version = "POSTGRES_16"
  region           = var.region

  settings {
    tier              = var.db_tier
    availability_type = "REGIONAL"

    ip_configuration {
      ipv4_enabled    = false
      private_network = var.network_id
    }

    backup_configuration {
      enabled                        = true
      start_time                     = "02:00"
      point_in_time_recovery_enabled = true
      transaction_log_retention_days = 7
      backup_retention_settings {
        retained_backups = 30
      }
    }

    database_flags {
      name  = "shared_preload_libraries"
      value = "timescaledb"
    }

    insights_config {
      query_insights_enabled = true
    }
  }

  deletion_protection = true
}

resource "google_sql_database" "ilews" {
  name     = "ilews"
  instance = google_sql_database_instance.postgres.name
}

resource "google_sql_user" "ilews" {
  name     = "ilews_app"
  instance = google_sql_database_instance.postgres.name
  password = "CHANGE_ME"  # Set via Secret Manager in production
}

output "connection_name" { value = google_sql_database_instance.postgres.connection_name }
output "private_ip" { value = google_sql_database_instance.postgres.private_ip_address }
