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

# Validate required fields exist in config.json
for field in function_name runtime handler role; do
  value=$(jq -r ".$field // empty" "$CONFIG_FILE")
  if [[ -z "$value" ]]; then
    echo "ERROR: Missing required field '$field' in $CONFIG_FILE" >&2
    return 1
  fi
done

# Parse basic fields
FUNCTION_NAME=$(jq -r .function_name "$CONFIG_FILE")
RUNTIME=$(jq -r .runtime "$CONFIG_FILE")
HANDLER=$(jq -r .handler "$CONFIG_FILE")

ROLE_NAME=$(jq -r .role "$CONFIG_FILE")
IAM_ROLE_ARN="arn:aws:iam::${ACCOUNT_NUMBER}:role/${ROLE_NAME}"

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
echo "RUNTIME=$RUNTIME"
echo "HANDLER=$HANDLER"
echo "IAM_ROLE_ARN=$IAM_ROLE_ARN"
echo "LAYERS=$LAYERS"

# Export for use in calling script
export FUNCTION_NAME
export RUNTIME
export HANDLER
export IAM_ROLE_ARN
export LAYERS
