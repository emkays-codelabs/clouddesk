#!/usr/bin/env bash
# Tear one environment down: destroy.sh <aws|azure|gcp> <dev|staging|prod>
# Never takes --auto-approve, and prod additionally needs the environment name typed back.
set -euo pipefail

cloud="${1:?usage: destroy.sh <aws|azure|gcp> <dev|staging|prod>}"
env="${2:?usage: destroy.sh <aws|azure|gcp> <dev|staging|prod>}"

root="$(cd "$(dirname "$0")/.." && pwd)"
cd "$root/$cloud"
terraform init -input=false -backend-config=backend.hcl
terraform plan -destroy -input=false -var-file="../environments/$env.tfvars" -out=tfplan

if [ "$env" = "prod" ]; then
  read -r -p "This destroys PROD on $cloud. Type the word prod to continue: " answer
  [ "$answer" = "prod" ] || { echo "not destroyed"; exit 1; }
else
  read -r -p "Destroy $cloud/$env? Type yes: " answer
  [ "$answer" = "yes" ] || { echo "not destroyed"; exit 1; }
fi
terraform apply -input=false tfplan
