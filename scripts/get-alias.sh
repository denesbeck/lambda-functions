#!/bin/bash

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
    echo "dev"
    ;;
  esac
}

get_alias "$1"
