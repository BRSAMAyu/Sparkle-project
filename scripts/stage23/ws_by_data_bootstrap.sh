#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/../.."
PYTHONPATH=backend python3 scripts/stage23/bootstrap_synthetic_density.py
PYTHONPATH=backend python3 scripts/stage23/check_data_density.py
