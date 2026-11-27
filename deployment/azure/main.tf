# CloudDesk on Azure: ACR, Container Apps, Key Vault, Log Analytics and Azure Cache for Redis.
# Scaffold only: validated with `terraform validate`, never applied (CLAUDE.md 15.1).
terraform {
  required_version = ">= 1.6"
  required_providers {
    azurerm = { source = "hashicorp/azurerm", version = "~> 3.100" }
  }
  backend "azurerm" {} # configured with -backend-config=backend.hcl (git-ignored)
}

provider "azurerm" {
  features {}
}

locals {
  name = "clouddesk-${var.environment}"
  tags = { project = "clouddesk", environment = var.environment }
}

data "azurerm_client_config" "current" {}

resource "azurerm_resource_group" "main" {
  name     = local.name
  location = var.location
  tags     = local.tags
}

# ---- networking ----
resource "azurerm_virtual_network" "main" {
  name                = local.name
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  address_space       = ["10.30.0.0/16"]
  tags                = local.tags
}

# ---- container registry ----
resource "azurerm_container_registry" "main" {
  name                = "clouddesk${var.environment}acr"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  sku                 = "Standard"
  admin_enabled       = false
  tags                = local.tags
}

# ---- secrets ----
resource "azurerm_key_vault" "main" {
  name                       = "clouddesk-${var.environment}-kv"
  location                   = azurerm_resource_group.main.location
  resource_group_name        = azurerm_resource_group.main.name
  tenant_id                  = data.azurerm_client_config.current.tenant_id
  sku_name                   = "standard"
  purge_protection_enabled   = true
  soft_delete_retention_days = 7
  tags                       = local.tags
}

# ---- monitoring ----
resource "azurerm_log_analytics_workspace" "main" {
  name                = local.name
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  sku                 = "PerGB2018"
  retention_in_days   = var.environment == "prod" ? 90 : 30
  tags                = local.tags
}

# ---- redis ----
resource "azurerm_redis_cache" "main" {
  name                = local.name
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  capacity            = 0
  family              = "C"
  sku_name            = "Basic"
  minimum_tls_version = "1.2"
  tags                = local.tags
}

# ---- compute and ingress (the Container Apps environment is the load balancer) ----
resource "azurerm_container_app_environment" "main" {
  name                       = local.name
  location                   = azurerm_resource_group.main.location
  resource_group_name        = azurerm_resource_group.main.name
  log_analytics_workspace_id = azurerm_log_analytics_workspace.main.id
  tags                       = local.tags
}

resource "azurerm_container_app" "backend" {
  name                         = "backend"
  container_app_environment_id = azurerm_container_app_environment.main.id
  resource_group_name          = azurerm_resource_group.main.name
  revision_mode                = "Single"
  tags                         = local.tags

  secret {
    name  = "llm-api-key"
    value = var.llm_api_key
  }
  secret {
    name  = "jwt-secret"
    value = var.jwt_secret
  }

  template {
    min_replicas = var.desired_count
    container {
      name   = "backend"
      image  = "${azurerm_container_registry.main.login_server}/backend:${var.image_tag}"
      cpu    = var.cpu / 1024
      memory = "${var.memory / 1024}Gi"
      env {
        name  = "DEMO_MODE"
        value = "false"
      }
      env {
        name        = "LLM_API_KEY"
        secret_name = "llm-api-key"
      }
      env {
        name        = "JWT_SECRET"
        secret_name = "jwt-secret"
      }
    }
  }

  ingress {
    external_enabled = true
    target_port      = 8000
    traffic_weight {
      percentage      = 100
      latest_revision = true
    }
  }
}
