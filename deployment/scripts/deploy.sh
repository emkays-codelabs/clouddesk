#!/usr/bin/env bash
# Plan and apply one cloud and environment: deploy.sh <aws|azure|gcp> <dev|staging|prod> [--auto-approve]
# --auto-approve is refused for staging and prod. Secrets come from TF_VAR_* variables only.
set -euo pipefail

cloud="${1:?usage: deploy.sh <aws|azure|gcp> <dev|staging|prod> [--auto-approve]}"
env="${2:?usage: deploy.sh <aws|azure|gcp> <dev|staging|prod> [--auto-approve]}"
flag="${3:-}"

case "$cloud" in aws | azure | gcp) ;; *) echo "unknown cloud: $cloud" >&2; exit 2 ;; esac
case "$env" in dev | staging | prod) ;; *) echo "unknown environment: $env" >&2; exit 2 ;; esac

if [ "$flag" = "--auto-approve" ] && [ "$env" != "dev" ]; then
  echo "refused: --auto-approve is only allowed for dev, not $env" >&2
  exit 3
fi

root="$(cd "$(dirname "$0")/.." && pwd)"
cd "$root/$cloud"
terraform init -input=false -backend-config=backend.hcl
terraform plan -input=false -var-file="../environments/$env.tfvars" -out=tfplan

if [ "$flag" = "--auto-approve" ]; then
  terraform apply -input=false tfplan
else
  read -r -p "Apply this plan to $cloud/$env? Type yes: " answer
  [ "$answer" = "yes" ] || { echo "not applied"; exit 1; }
  terraform apply -input=false tfplan
fi
