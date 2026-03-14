#!/bin/bash
set -euo pipefail

# Usage: ./install-packages.sh <type>
# Supported types: node, golang, ruby, pip

TYPE="${1:?Usage: install-packages.sh <type>}"

install_packages() {
  echo "Installing packages for type: $1"
  case "$1" in
  node)
    npm install --production
    ;;
  golang)
    go mod tidy
    ;;
  ruby)
    bundle install
    ;;
  pip)
    pip install -r requirements.txt
    ;;
  *)
    echo "ERROR: Unknown package type: $1" >&2
    echo "Supported types: node, golang, ruby, pip" >&2
    exit 1
    ;;
  esac
  echo "Package installation completed for type: $1"
}

install_packages "$TYPE"
