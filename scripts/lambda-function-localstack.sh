#!/bin/bash

lambda_function_localstack() {
  FUNCTION_PATH=$1
  REGION="${2:-"eu-central-1"}"

  APP=$(echo "$FUNCTION_PATH" | cut -d'/' -f2)
  LAMBDA=$(echo "$FUNCTION_PATH" | cut -d'/' -f3)

  CONFIG_FILE="${FUNCTION_PATH}/config.json"
  if [[ ! -f "$CONFIG_FILE" ]]; then
    echo "Missing config.json in $FUNCTION_PATH, skipping..."
    continue
  fi

  FUNCTION_NAME=$(jq -r .function_name "$CONFIG_FILE")
  RUNTIME=$(jq -r .runtime "$CONFIG_FILE")
  HANDLER=$(jq -r .handler "$CONFIG_FILE")
  IAM_ROLE_ARN=$(jq -r .role "$CONFIG_FILE" | awk -F':' '{ $4="000000000000"; OFS=":"; print $0 }')
  LAYERS=$(jq -r '.layers | join(" ")' "$CONFIG_FILE")

  zip -r output.zip $FUNCTION_PATH
  awslocal lambda update-function-code \
    --function-name "$FUNCTION_NAME" \
    --zip-file fileb://output.zip \
  --region "$REGION"

  rm -rf output.zip
}

lambda_function_localstack "$1"
