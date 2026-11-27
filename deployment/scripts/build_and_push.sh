#!/usr/bin/env bash
# Build both images tagged with the git SHA and push them: build_and_push.sh <aws|azure|gcp> <registry-url>
# The tag is always the commit, so the artifact that was tested is the artifact that ships.
set -euo pipefail

cloud="${1:?usage: build_and_push.sh <aws|azure|gcp> <registry-url>}"
registry="${2:?usage: build_and_push.sh <aws|azure|gcp> <registry-url>}"
sha="$(git rev-parse --short=12 HEAD)"

if [ -n "$(git status --porcelain)" ]; then
  echo "refused: the working tree has uncommitted changes, so the SHA would not describe the image" >&2
  exit 3
fi

docker build -f backend/Dockerfile -t "$registry/backend:$sha" .
docker build -f frontend/Dockerfile -t "$registry/frontend:$sha" frontend
docker push "$registry/backend:$sha"
docker push "$registry/frontend:$sha"
echo "pushed $cloud images tagged $sha"
