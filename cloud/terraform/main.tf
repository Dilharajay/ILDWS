terraform {
  required_version = ">= 1.5.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }

  backend "gcs" {
    bucket = "ilews-terraform-state"
    prefix = "terraform/state"
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# Networking
module "networking" {
  source      = "./modules/networking"
  project_id  = var.project_id
  region      = var.region
  environment = var.environment
}

# GKE Cluster
module "gke" {
  source         = "./modules/gke"
  project_id     = var.project_id
  region         = var.region
  environment    = var.environment
  network        = module.networking.network_name
  subnetwork     = module.networking.subnetwork_name
  gke_min_nodes  = var.gke_min_nodes
  gke_max_nodes  = var.gke_max_nodes
  depends_on     = [module.networking]
}

# Cloud SQL PostgreSQL
module "cloudsql" {
  source      = "./modules/cloudsql"
  project_id  = var.project_id
  region      = var.region
  environment = var.environment
  network_id  = module.networking.network_id
  db_tier     = var.db_tier
  depends_on  = [module.networking]
}

# Memorystore Redis
module "redis" {
  source      = "./modules/redis"
  project_id  = var.project_id
  region      = var.region
  environment = var.environment
  network_id  = module.networking.network_id
  depends_on  = [module.networking]
}

# GCS Buckets
resource "google_storage_bucket" "data_archive" {
  name          = "${var.project_id}-ilews-data-archive"
  location      = var.region
  storage_class = "STANDARD"
  versioning { enabled = true }
  lifecycle_rule {
    action { type = "Delete" }
    condition { age = 2555 } # 7 years
  }
}

resource "google_storage_bucket" "firmware" {
  name          = "${var.project_id}-ilews-firmware"
  location      = var.region
  storage_class = "STANDARD"
  versioning { enabled = true }
}

resource "google_storage_bucket" "dashboard" {
  name          = "${var.project_id}-ilews-dashboard-${var.environment}"
  location      = var.region
  storage_class = "STANDARD"
  website {
    main_page_suffix = "index.html"
    not_found_page   = "index.html"
  }
}

resource "google_storage_bucket" "backups" {
  name          = "${var.project_id}-ilews-backups"
  location      = var.region
  storage_class = "NEARLINE"
  lifecycle_rule {
    action { type = "Delete" }
    condition { age = 365 }
  }
}

# Artifact Registry
resource "google_artifact_registry_repository" "ilews_services" {
  location      = var.region
  repository_id = "ilews-services"
  format        = "DOCKER"
  description   = "ILEWS Docker images"
}

# Secret Manager
resource "google_secret_manager_secret" "secrets" {
  for_each  = toset([
    "ilews-mqtt-password",
    "ilews-db-password",
    "ilews-twilio-auth-token",
    "ilews-twilio-account-sid",
    "ilews-fcm-service-account",
    "ilews-jwt-private-key",
  ])

  secret_id = each.key

  replication {
    auto {}
  }
}

# Cloud NAT for GKE outbound internet
resource "google_compute_router" "nat_router" {
  name    = "ilews-nat-router-${var.environment}"
  network = module.networking.network_name
  region  = var.region
}

resource "google_compute_router_nat" "nat" {
  name                               = "ilews-nat-${var.environment}"
  router                             = google_compute_router.nat_router.name
  region                             = var.region
  nat_ip_allocate_option            = "AUTO_ONLY"
  source_subnetwork_ip_ranges_to_nat = "ALL_SUBNETWORKS_ALL_IP_RANGES"
}
