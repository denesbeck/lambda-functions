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
    echo "WARNING: Unrecognized branch pattern '$1', defaulting to 'dev'" >&2
    echo "dev"
    ;;
  esac
}

get_alias "$BRANCH"
