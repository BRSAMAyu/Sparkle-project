#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/../.."
PYTHONPATH=backend python3 scripts/stage23/check_rule_ah_dimension_registry.py
