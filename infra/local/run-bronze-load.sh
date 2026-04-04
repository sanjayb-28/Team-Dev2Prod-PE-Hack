#!/usr/bin/env bash
set -euo pipefail

docker compose -f infra/local/compose.yaml up -d --build db workload-api
docker compose -f infra/local/compose.yaml --profile scale run --rm \
  -e BASE_URL=http://workload-api:5000 \
  -e VUS=50 \
  k6 run /scripts/bronze-baseline.js
