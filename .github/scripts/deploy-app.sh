#!/bin/bash
# Runs on the app EC2 instance via `aws ssm send-command` (see the
# deploy-dev job in ../workflows/ci-cd.yml and the deploy-to-prod job in
# ../workflows/promote-to-production.yml). Not invoked directly - the
# caller substitutes __GIT_SHA__/__GITHUB_REPOSITORY__/__IMAGE__/
# __ENVIRONMENT__ before sending it. __IMAGE__ is the full pushed
# reference, e.g.
# 123456789012.dkr.ecr.us-east-1.amazonaws.com/kanban-board:20260818-163457-83242da
# - already built and pushed by ci-cd.yml's build job (or, when this
# runs for a promotion, already pushed as part of some earlier dev
# deploy). This script only ever pulls; it never builds on the instance.
# __ENVIRONMENT__ is just "dev" or "production" - which caller this is.
set -euxo pipefail

# The instance's own first boot (see cloudformation/template.yaml's
# UserData) does its own initial clone+build from source; wait for that
# to finish so this doesn't race it on a brand-new instance.
cloud-init status --wait

REPO_DIR=/opt/kanban-board
if [ ! -d "$REPO_DIR/.git" ]; then
  git clone "https://github.com/__GITHUB_REPOSITORY__.git" "$REPO_DIR"
fi

cd "$REPO_DIR"
git fetch --depth 1 origin __GIT_SHA__
git checkout --force FETCH_HEAD

# Derive the ECR registry (and its region) from the image reference
# itself rather than requiring a separate placeholder - this keeps the
# script correct even when promoting to a prod stack in a different
# region than the one that built the image.
IMAGE="__IMAGE__"
REGISTRY="${IMAGE%%/*}"
REGION=$(echo "$REGISTRY" | sed -E 's/.*\.ecr\.([a-z0-9-]+)\.amazonaws\.com$/\1/')

aws ecr get-login-password --region "$REGION" \
  | docker login --username AWS --password-stdin "$REGISTRY"

# docker-compose.yml's `app` service reads these from the environment
# (or, as here, a .env file in the same directory) - APP_IMAGE to know
# which tag to pull, APP_VERSION/ENVIRONMENT to identify this
# deployment in telemetry (see backend/src/kanban_backend/telemetry.py).
# APP_VERSION is just the tag portion of IMAGE - the same string that
# identifies this exact build everywhere else (ECR, the SSM comment
# below, this image reference itself).
{
  echo "APP_IMAGE=$IMAGE"
  echo "APP_VERSION=${IMAGE##*:}"
  echo "ENVIRONMENT=__ENVIRONMENT__"
} > .env

docker compose pull app
docker compose up -d
