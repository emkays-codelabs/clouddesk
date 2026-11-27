# CloudDesk on GCP: Artifact Registry, Cloud Run, Secret Manager, Cloud Logging and Memorystore Redis.
# Scaffold only: validated with `terraform validate`, never applied (CLAUDE.md 15.1).
terraform {
  required_version = ">= 1.6"
  required_providers {
    google = { source = "hashicorp/google", version = "~> 5.0" }
  }
  backend "gcs" {} # configured with -backend-config=backend.hcl (git-ignored)
}

provider "google" {
  project = var.project_id
  region  = var.region
}

locals {
  name   = "clouddesk-${var.environment}"
  labels = { project = "clouddesk", environment = var.environment }
}

# ---- networking ----
resource "google_compute_network" "main" {
  name                    = local.name
  auto_create_subnetworks = false
}

resource "google_compute_subnetwork" "main" {
  name          = local.name
  region        = var.region
  network       = google_compute_network.main.id
  ip_cidr_range = "10.40.0.0/20"
}

# ---- container registry ----
resource "google_artifact_registry_repository" "main" {
  repository_id = local.name
  location      = var.region
  format        = "DOCKER"
  labels        = local.labels
}

# ---- secrets ----
resource "google_secret_manager_secret" "llm_api_key" {
  secret_id = "${local.name}-llm-api-key"
  labels    = local.labels
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "llm_api_key" {
  secret      = google_secret_manager_secret.llm_api_key.id
  secret_data = var.llm_api_key
}

resource "google_secret_manager_secret" "jwt_secret" {
  secret_id = "${local.name}-jwt-secret"
  labels    = local.labels
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "jwt_secret" {
  secret      = google_secret_manager_secret.jwt_secret.id
  secret_data = var.jwt_secret
}

# ---- monitoring ----
resource "google_logging_project_bucket_config" "app" {
  project        = var.project_id
  location       = "global"
  bucket_id      = local.name
  retention_days = var.environment == "prod" ? 90 : 30
}

# ---- redis ----
resource "google_redis_instance" "main" {
  name               = local.name
  tier               = "BASIC"
  memory_size_gb     = 1
  region             = var.region
  authorized_network = google_compute_network.main.id
  labels             = local.labels
}

# ---- compute and load balancer (Cloud Run fronts its own load balancer) ----
resource "google_service_account" "backend" {
  account_id = "${local.name}-backend"
}

resource "google_cloud_run_v2_service" "backend" {
  name     = "${local.name}-backend"
  location = var.region
  labels   = local.labels

  template {
    service_account = google_service_account.backend.email
    scaling {
      min_instance_count = var.desired_count
    }
    containers {
      image = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.main.repository_id}/backend:${var.image_tag}"
      resources {
        limits = {
          cpu    = tostring(var.cpu / 1024)
          memory = "${var.memory}Mi"
        }
      }
      env {
        name  = "DEMO_MODE"
        value = "false"
      }
      env {
        name  = "REDIS_URL"
        value = "redis://${google_redis_instance.main.host}:6379/0"
      }
      env {
        name = "LLM_API_KEY"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.llm_api_key.secret_id
            version = "latest"
          }
        }
      }
      env {
        name = "JWT_SECRET"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.jwt_secret.secret_id
            version = "latest"
          }
        }
      }
    }
  }
}
