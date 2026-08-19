#!/usr/bin/env bash

set -Eeuo pipefail

CONTAINER_NAME="ai-support-assistant"
DATA_DIRECTORY="/opt/ai-support-assistant/data"
ENVIRONMENT_FILE="/opt/ai-support-assistant/app.env"

required_variables=(
  IMAGE_URI
  OPENAI_API_KEY_PARAMETER
  APP_API_KEY_PARAMETER
  RAG_SNAPSHOT_S3_BUCKET
  RAG_SNAPSHOT_S3_KEY
)

for variable_name in "${required_variables[@]}"; do
  if [[ -z "${!variable_name:-}" ]]; then
    echo "Missing required deployment variable: ${variable_name}" >&2
    exit 1
  fi
done

openai_api_key=$(aws ssm get-parameter \
  --name "$OPENAI_API_KEY_PARAMETER" \
  --with-decryption \
  --query 'Parameter.Value' \
  --output text)

app_api_key=$(aws ssm get-parameter \
  --name "$APP_API_KEY_PARAMETER" \
  --with-decryption \
  --query 'Parameter.Value' \
  --output text)

install -d -m 0755 /opt/ai-support-assistant
install -m 0600 /dev/null "$ENVIRONMENT_FILE"
printf '%s\n' \
  'ENVIRONMENT=production' \
  "OPENAI_API_KEY=${openai_api_key}" \
  "APP_API_KEY=${app_api_key}" \
  'RAG_DATABASE_DIRECTORY=/app/data/chroma' \
  "RAG_SNAPSHOT_S3_BUCKET=${RAG_SNAPSHOT_S3_BUCKET}" \
  "RAG_SNAPSHOT_S3_KEY=${RAG_SNAPSHOT_S3_KEY}" \
  > "$ENVIRONMENT_FILE"
unset openai_api_key app_api_key

ecr_registry="${IMAGE_URI%%/*}"
ecr_region=$(printf '%s' "$ecr_registry" | cut -d. -f4)

if [[ -z "$ecr_registry" || -z "$ecr_region" ]]; then
  echo "Unable to determine the ECR registry or region from IMAGE_URI." >&2
  exit 1
fi

aws ecr get-login-password --region "$ecr_region" \
  | docker login \
    --username AWS \
    --password-stdin "$ecr_registry"

docker pull "$IMAGE_URI"

app_uid=$(docker run --rm --entrypoint id "$IMAGE_URI" -u)
app_gid=$(docker run --rm --entrypoint id "$IMAGE_URI" -g)
install -d -m 0755 "$DATA_DIRECTORY"
chown -R "${app_uid}:${app_gid}" "$DATA_DIRECTORY"

previous_image=""
if docker container inspect "$CONTAINER_NAME" >/dev/null 2>&1; then
  previous_image=$(docker container inspect \
    --format '{{.Config.Image}}' \
    "$CONTAINER_NAME")
  docker rm --force "$CONTAINER_NAME"
fi

start_application() {
  local image_uri="$1"

  docker run --detach \
    --name "$CONTAINER_NAME" \
    --restart unless-stopped \
    --publish 80:8000 \
    --publish 8000:8000 \
    --env-file "$ENVIRONMENT_FILE" \
    --volume "${DATA_DIRECTORY}:/app/data" \
    "$image_uri"
}

wait_for_health() {
  local attempts=24

  for ((attempt = 1; attempt <= attempts; attempt += 1)); do
    if curl --fail --silent --show-error \
      --max-time 5 \
      http://127.0.0.1:8000/health >/dev/null; then
      return 0
    fi

    sleep 5
  done

  return 1
}

start_application "$IMAGE_URI"

if wait_for_health; then
  echo "Deployment succeeded: ${IMAGE_URI}"
  exit 0
fi

echo "New container failed its health check." >&2
docker logs --tail 100 "$CONTAINER_NAME" >&2 || true
docker rm --force "$CONTAINER_NAME" >/dev/null 2>&1 || true

if [[ -z "$previous_image" ]]; then
  echo "No previous image is available for rollback." >&2
  exit 1
fi

echo "Rolling back to the previous image." >&2
start_application "$previous_image"

if wait_for_health; then
  echo "Rollback succeeded: ${previous_image}" >&2
else
  echo "Rollback failed; manual recovery is required." >&2
fi

exit 1
