#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

if ! dpkg -s python3-tk >/dev/null 2>&1; then
  sudo apt-get update
  sudo DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends python3-tk
fi

python3 -m pip install --break-system-packages -r requirements.txt
