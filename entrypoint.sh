#!/bin/sh
set -e

CONFIG_PATH="${CONFIG_PATH:-/app/config.yaml}"

exec python -m prometheus_persister "$CONFIG_PATH"
