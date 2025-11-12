#!/usr/bin/env python3
"""
CLI for HNG VPC Lab
Usage:
  python3 vpcctl.py create --config policies/policy.json
  python3 vpcctl.py delete --config policies/policy.json
"""

import argparse
import json
import sys
from vpc.vpc_manager import VPCManager

def main():
    parser = argparse.ArgumentParser(description="vpcctl: Virtual VPC Manager")
    parser.add_argument("action", choices=["create", "delete"], help="Action to perform")
    parser.add_argument("--config", required=True, help="Path to JSON policy file")
    args = parser.parse_args()

    try:
        with open(args.config) as f:
            config = json.load(f)
    except FileNotFoundError:
        print(f"Error: Config file '{args.config}' not found.")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON: {e}")
        sys.exit(1)

    vpcs = config.get("vpcs", [])
    if not vpcs:
        print("Warning: No VPCs defined in config.")
        sys.exit(0)

    for vpc_cfg in vpcs:
        vpc_name = vpc_cfg.get("name", "unnamed")
        print(f"\n=== Processing VPC: {vpc_name} ===")
        try:
            vpc = VPCManager(vpc_cfg)
            if args.action == "create":
                vpc.create_vpc()
            elif args.action == "delete":
                vpc.delete_vpc()
        except Exception as e:
            print(f"Error processing VPC '{vpc_name}': {e}")
            continue

if __name__ == "__main__":
    main()
