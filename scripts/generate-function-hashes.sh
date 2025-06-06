#!/bin/bash
set -euo pipefail

echo "Generating code and config hashes for all Lambda functions..."

# Root directory containing all Lambda functions
FUNCTIONS_ROOT="functions"

# Loop over all <app>/<lambda> directories
find "$FUNCTIONS_ROOT" -mindepth 2 -maxdepth 2 -type d -not -path '*/.*' | sort | while read -r func_dir; do
  echo ""
  echo "Processing: $func_dir"

  # ----- Generate code hash (excluding config.json) -----
  CODE_HASH=$(find "$func_dir" -type f ! -name "config.json" -exec sha256sum {} + | sort | sha256sum | awk '{print $1}')

  # ----- Generate config hash (only config.json) -----
  CONFIG_FILE="$func_dir/config.json"
  if [[ -f "$CONFIG_FILE" ]]; then
    CONFIG_HASH=$(sha256sum "$CONFIG_FILE" | awk '{print $1}')
  else
    CONFIG_HASH="N/A"
  fi

  echo "Code Hash: $CODE_HASH"
  echo "Config Hash: $CONFIG_HASH"

  # ----- Write to file for later comparison
  echo "$CODE_HASH" >"$func_dir/.code.hash"
  echo "$CONFIG_HASH" >"$func_dir/.config.hash"

done

echo ""
echo "Done hashing all functions."
