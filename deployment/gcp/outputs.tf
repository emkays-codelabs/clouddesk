output "backend_url" { value = google_cloud_run_v2_service.backend.uri }
output "registry" { value = google_artifact_registry_repository.main.repository_id }
