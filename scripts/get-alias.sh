#!/bin/bash
set -euo pipefail

# Usage: ./get-alias.sh <branch-name>

BRANCH="${1:?Usage: get-alias.sh <branch-name>}"

get_alias() {
  case "$1" in
  main)
    echo "prod"
    ;;
  test/*)
    echo "test"
    ;;
  release/*)
    echo "staging"
    ;;
  feature/*)
    echo "dev"
    ;;
  *)
    echo "ERROR: Unrecognized branch pattern '$1'. Expected main, test/*, release/* or feature/*" >&2
    exit 1
    ;;
  esac
}

get_alias "$BRANCH"
