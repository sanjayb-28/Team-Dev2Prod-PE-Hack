#!/usr/bin/env bash
set -euo pipefail

docker compose -f infra/local/compose.yaml --profile scale up -d --build \
  db \
  workload-api-a \
  workload-api-b \
  scale-gateway

docker compose -f infra/local/compose.yaml --profile scale run --rm \
  -e BASE_URL=http://scale-gateway:8080 \
  -e VUS=200 \
  k6 run /scripts/silver-scale-out.js
