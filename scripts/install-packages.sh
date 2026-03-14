#!/bin/bash
set -euo pipefail

install_packages() {
  case "$1" in
  node)
    npm install
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
    exit 1
    ;;
  esac
}

install_packages "$1"
