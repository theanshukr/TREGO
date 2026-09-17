#!/usr/bin/env bash
# Stop the trego backend stack. Preserves the postgres data volume
# (trego-db-data) so seeds survive across restarts.
set -e
cd "$(dirname "$0")/../.."   # repo root
docker compose down
echo "[stop_all] stopped. (volume trego-db-data preserved)"
