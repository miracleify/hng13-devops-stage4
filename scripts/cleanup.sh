#!/usr/bin/env bash
# cleanup.sh - convenience script to call vpcctl delete against your policy.json
# usage: bash scripts/cleanup.sh policies/policy.json

CONFIG=${1:-policies/policy.json}
python3 vpcctl.py delete --config "$CONFIG"
