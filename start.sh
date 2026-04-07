#!/usr/bin/env bash
set -e

echo "Starting dependencies..."
docker compose up -d db

echo "Waiting for database to be ready..."
until docker compose exec db pg_isready -U postgres > /dev/null 2>&1; do
  sleep 1
done

echo "Running migrations..."
alembic upgrade head

echo "Starting server... woohoo"
uvicorn app.main:app --reload
