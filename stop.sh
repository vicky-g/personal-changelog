#!/usr/bin/env bash
set -e

echo "Stopping dependencies..."
docker compose down
echo "Done."
