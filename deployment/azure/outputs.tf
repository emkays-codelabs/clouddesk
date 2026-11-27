output "backend_url" { value = azurerm_container_app.backend.latest_revision_fqdn }
output "registry" { value = azurerm_container_registry.main.login_server }
