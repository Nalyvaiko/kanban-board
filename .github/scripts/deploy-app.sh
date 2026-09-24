#!/bin/bash
# Runs on the app EC2 instance via `aws ssm send-command` (see the deploy
# job in ../workflows/ci-cd.yml). Not invoked directly - the workflow
# substitutes __GIT_SHA__/__GITHUB_REPOSITORY__ before sending it.
set -euxo pipefail

# The instance's own first boot (see cloudformation/template.yaml's
# UserData) does its own initial clone+build; wait for that to finish so
# this doesn't race it on a brand-new instance.
cloud-init status --wait

REPO_DIR=/opt/kanban-board
if [ ! -d "$REPO_DIR/.git" ]; then
  git clone "https://github.com/__GITHUB_REPOSITORY__.git" "$REPO_DIR"
fi

cd "$REPO_DIR"
git fetch --depth 1 origin __GIT_SHA__
git checkout --force FETCH_HEAD

docker compose up -d --build
