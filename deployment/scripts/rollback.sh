#!/usr/bin/env bash
# Roll an environment back to an earlier image: rollback.sh <aws|azure|gcp> <dev|staging|prod> <git-sha>
# It re-applies the saved var-file with image_tag set to a SHA that was already built and pushed.
set -euo pipefail

cloud="${1:?usage: rollback.sh <aws|azure|gcp> <dev|staging|prod> <git-sha>}"
env="${2:?usage: rollback.sh <aws|azure|gcp> <dev|staging|prod> <git-sha>}"
sha="${3:?usage: rollback.sh <aws|azure|gcp> <dev|staging|prod> <git-sha>}"

root="$(cd "$(dirname "$0")/.." && pwd)"
cd "$root/$cloud"
terraform init -input=false -backend-config=backend.hcl
terraform plan -input=false -var-file="../environments/$env.tfvars" -var "image_tag=$sha" -out=tfplan
read -r -p "Roll $cloud/$env back to $sha? Type yes: " answer
[ "$answer" = "yes" ] || { echo "not applied"; exit 1; }
terraform apply -input=false tfplan
