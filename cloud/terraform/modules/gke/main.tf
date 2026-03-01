variable "project_id" { type = string }
variable "region" { type = string }
variable "environment" { type = string }
variable "network" { type = string }
variable "subnetwork" { type = string }
variable "gke_min_nodes" { type = number }
variable "gke_max_nodes" { type = number }

resource "google_container_cluster" "primary" {
  name     = "ilews-cluster-${var.environment}"
  location = var.region

  network    = var.network
  subnetwork = var.subnetwork

  # Remove default node pool
  remove_default_node_pool = true
  initial_node_count       = 1

  private_cluster_config {
    enable_private_nodes    = true
    enable_private_endpoint = false
    master_ipv4_cidr_block  = "172.16.0.0/28"
  }

  ip_allocation_policy {
    cluster_secondary_range_name  = "pods"
    services_secondary_range_name = "services"
  }

  workload_identity_config {
    workload_pool = "${var.project_id}.svc.id.goog"
  }

  release_channel {
    channel = "REGULAR"
  }
}

resource "google_container_node_pool" "general" {
  name       = "general-pool"
  location   = var.region
  cluster    = google_container_cluster.primary.name
  node_count = var.gke_min_nodes

  autoscaling {
    min_node_count = var.gke_min_nodes
    max_node_count = var.gke_max_nodes
  }

  node_config {
    machine_type = "e2-standard-2"
    disk_size_gb = 50

    oauth_scopes = [
      "https://www.googleapis.com/auth/cloud-platform",
    ]

    workload_metadata_config {
      mode = "GKE_METADATA"
    }

    labels = {
      environment = var.environment
      app         = "ilews"
    }
  }

  management {
    auto_repair  = true
    auto_upgrade = true
  }
}

output "cluster_name" { value = google_container_cluster.primary.name }
output "cluster_endpoint" { value = google_container_cluster.primary.endpoint }
