"""
VPCManager: Handles creation/deletion of VPCs, subnets, bridges, routing, and peering.

This module orchestrates:
 - creating a Linux bridge per VPC
 - creating namespaces (subnets)
 - connecting subnets to bridge via veth pairs
 - assigning IP addresses and default routes inside namespaces
 - applying firewall rules (per-subnet and global)
 - calling routing setup and peering helpers
"""

import subprocess
from .routing import setup_routing
from .firewall import apply_firewall_rules
from .peering import peer_vpcs

def sanitize_name(name):
    """Replace invalid chars and hyphens for Linux netns/interface names."""
    return name.replace("-", "_")

class VPCManager:
    def __init__(self, config):
        """
        config expected keys:
        {
          "name": "ifym",
          "cidr": "10.0.0.0/16",
          "subnets": [
            {"name": "ifym-public", "cidr": "10.0.1.0/24", "public": True, "ingress": [...]},
            {"name": "ifym-private", "cidr": "10.0.2.0/24", "public": False, "ingress": [...]}
          ],
          "firewall_rules": [...],  # optional global rules
          "peers": [  # optional peering declarations
             {"other_vpc_bridge": "vpc-other", "allowed_cidrs": ["10.1.1.0/24"]}
          ]
        }
        """
        self.name = config["name"]
        self.cidr = config["cidr"]
        self.subnets = config.get("subnets", [])
        self.firewall_rules = config.get("firewall_rules", [])
        self.peers = config.get("peers", [])
        self.bridge_name = f"vpc-{sanitize_name(self.name)}"

    def run(self, cmd, check=True):
        print(f"Running: {cmd}")
        return subprocess.run(cmd, shell=True, check=check)

    def exists_bridge(self):
        result = subprocess.run(f"ip link show {self.bridge_name}", shell=True, capture_output=True)
        return result.returncode == 0

    def exists_namespace(self, ns_name):
        result = subprocess.run(f"ip netns list | grep -w {ns_name}", shell=True, capture_output=True)
        return result.returncode == 0

    def route_exists(self, ns_name, gateway_ip):
        result = subprocess.run(f"ip netns exec {ns_name} ip route | grep -w 'default via {gateway_ip}'", shell=True, capture_output=True)
        return result.returncode == 0

    # ---------------------------
    # Lifecycle: create / delete
    # ---------------------------
    def create_vpc(self):
        """Create bridge, subnets, routing, firewall, peering."""
        # 1) Create bridge if missing
        if not self.exists_bridge():
            self.run(f"ip link add name {self.bridge_name} type bridge")
        self.run(f"ip link set {self.bridge_name} up")

        # 2) Subnets
        for idx, subnet in enumerate(self.subnets, start=1):
            self.create_subnet(subnet, idx)

            # Apply per-subnet firewall
            if "ingress" in subnet:
                ns_name = sanitize_name(subnet["name"])
                apply_firewall_rules(subnet["ingress"], namespace=ns_name)

        # 3) Routing & NAT
        setup_routing(self.bridge_name, self.subnets)

        # 4) Global firewall
        if self.firewall_rules:
            apply_firewall_rules(self.firewall_rules, namespace=None)

        # 5) Peering
        for peer in self.peers:
            other_bridge = peer.get("other_vpc_bridge")
            allowed = peer.get("allowed_cidrs", [])
            if other_bridge:
                peer_vpcs(self.bridge_name, other_bridge, allowed)

        print(f"VPC {self.name} created successfully!")

    def delete_vpc(self):
        """Delete namespaces and bridge."""
        # Delete subnets
        for subnet in self.subnets:
            ns_name = sanitize_name(subnet["name"])
            if self.exists_namespace(ns_name):
                self.run(f"ip netns del {ns_name} || true", check=False)

        # Delete bridge
        if self.exists_bridge():
            self.run(f"ip link set {self.bridge_name} down || true", check=False)
            self.run(f"ip link del {self.bridge_name} || true", check=False)

        print(f"VPC {self.name} deleted successfully!")

    # ---------------------------
    # Subnet creation
    # ---------------------------
    def create_subnet(self, subnet, idx):
        ns_name = sanitize_name(subnet["name"])
        host_veth = f"vethh{idx}"[:15]
        ns_veth = f"vethn{idx}"[:15]

        # 1) Create namespace first
        if not self.exists_namespace(ns_name):
            self.run(f"ip netns add {ns_name}")

        # 2) Create veth pair
        res = subprocess.run(f"ip link show {host_veth}", shell=True, capture_output=True)
        if res.returncode != 0:
            self.run(f"ip link add {host_veth} type veth peer name {ns_veth}")

        # 3) Attach host veth to bridge
        self.run(f"ip link set {host_veth} master {self.bridge_name}")
        self.run(f"ip link set {host_veth} up")

        # 4) Move ns veth into namespace
        self.run(f"ip link set {ns_veth} netns {ns_name}")
        self.run(f"ip netns exec {ns_name} ip link set {ns_veth} up")
        self.run(f"ip netns exec {ns_name} ip link set lo up")

        # 5) Assign IPs
        subnet_base = subnet["cidr"].rsplit(".", 1)[0]
        gateway_ip = f"{subnet_base}.1"
        ns_ip = f"{subnet_base}.10/24"

        self.run(f"ip addr add {gateway_ip}/24 dev {self.bridge_name} || true", check=False)
        self.run(f"ip netns exec {ns_name} ip addr add {ns_ip} dev {ns_veth} || true", check=False)

        # 6) Default route
        if not self.route_exists(ns_name, gateway_ip):
            self.run(f"ip netns exec {ns_name} ip route add default via {gateway_ip}")

        print(f"Subnet {ns_name} created: gateway {gateway_ip}, namespace_ip {ns_ip}")
