#!/usr/bin/env bash
set -euo pipefail

# Usage: source ./expand-config.sh path/to/config.json

CONFIG_FILE="${1:?Usage: expand-config.sh <path/to/config.json>}"

if [[ ! -f "$CONFIG_FILE" ]]; then
  echo "ERROR: Config file not found: $CONFIG_FILE" >&2
  return 1
fi

# Ensure required ENV vars are set
: "${ACCOUNT_NUMBER:?Missing ACCOUNT_NUMBER env var}"
: "${REGION:?Missing REGION env var}"

# This repo owns only function code and layer attachment. The function itself
# (name, runtime, handler, role, memory, timeout, env) is defined in Terraform.
for field in function_name runtime handler role; do
  if jq -e "has(\"$field\")" "$CONFIG_FILE" >/dev/null; then
    echo "ERROR: '$field' in $CONFIG_FILE is owned by Terraform (lambda-functions-tf), remove it" >&2
    return 1
  fi
done

# The directory name is the kebab-case form of the Terraform function name,
# mirroring Terraform's replace(title(name), "-", ""):
# functions/<app>/lambda-layer-cleanup -> LambdaLayerCleanup
LAMBDA_DIR=$(basename "$(dirname "$CONFIG_FILE")")
FUNCTION_NAME=$(echo "$LAMBDA_DIR" | awk -F- '{for (i = 1; i <= NF; i++) $i = toupper(substr($i, 1, 1)) substr($i, 2)} 1' OFS="")

# Handle region-specific layer parsing
LAYER_ARNS=""

# Check if layers array is not empty
LAYERS_ENTRY=$(jq -r '.layers[0] // empty' "$CONFIG_FILE")

if [[ -n "$LAYERS_ENTRY" ]]; then
  REGION_LAYERS=$(jq -r --arg REGION "$REGION" '.layers[0][$REGION] // empty | .[]?' "$CONFIG_FILE")

  for LAYER in $REGION_LAYERS; do
    LAYER_NAME=$(echo "$LAYER" | cut -d':' -f1)
    LAYER_VERSION=$(echo "$LAYER" | cut -d':' -f2)
    LAYER_ARNS+="arn:aws:lambda:${REGION}:${ACCOUNT_NUMBER}:layer:${LAYER_NAME}:${LAYER_VERSION} "
  done

  LAYERS="${LAYER_ARNS%% }"  # Trim trailing space
else
  LAYERS=""
fi

# Output values for debug/logging
echo "Expanded config for $CONFIG_FILE:"
echo "FUNCTION_NAME=$FUNCTION_NAME"
echo "LAYERS=$LAYERS"

# Export for use in calling script
export FUNCTION_NAME
export LAYERS
