variable "project_id" { type = string }

variable "region" {
  type    = string
  default = "asia-south1"
}

variable "environment" {
  type = string
  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "environment must be dev, staging or prod."
  }
}

variable "desired_count" { type = number }
variable "cpu" { type = number }
variable "memory" { type = number }
variable "image_tag" { type = string }

# Secrets arrive only through TF_VAR_llm_api_key and TF_VAR_jwt_secret.
variable "llm_api_key" {
  type      = string
  sensitive = true
  default   = ""
}

variable "jwt_secret" {
  type      = string
  sensitive = true
  default   = ""
}
