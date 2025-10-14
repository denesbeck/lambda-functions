#!/bin/bash

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
  esac
}

install_packages "$1"
