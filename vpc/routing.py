"""
Setup routing and NAT for VPC subnets.

Responsibilities:
- Enable IP forwarding
- Create MASQUERADE NAT rules for public subnets
- Add FORWARD rules to allow traffic for bridge and between subnets
- Add explicit ICMP FORWARD rules so ping works between namespaces

Idempotent: rules are only added if missing.
"""

import subprocess

def run(cmd, check=True):
    print(f"Running: {cmd}")
    return subprocess.run(cmd, shell=True, check=check)

def rule_exists(cmd):
    """
    Check if an iptables rule exists.
    cmd should be the full iptables -C command
    """
    result = subprocess.run(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return result.returncode == 0

def setup_routing(bridge_name, subnets):
    """
    Enable routing between subnets and NAT for public subnets.

    Args:
        bridge_name: VPC bridge name
        subnets: list of dicts with keys 'cidr' and optional 'public'
    """
    # 1) Enable IP forwarding
    run("sysctl -w net.ipv4.ip_forward=1")

    # 2) Determine host public interface for NAT (default: eth0)
    public_interface = "eth0"

    # 3) NAT for public subnets
    for subnet in subnets:
        cidr = subnet["cidr"]
        if subnet.get("public", False):
            nat_check = f"iptables -t nat -C POSTROUTING -s {cidr} -o {public_interface} -j MASQUERADE"
            if not rule_exists(nat_check):
                run(f"iptables -t nat -A POSTROUTING -s {cidr} -o {public_interface} -j MASQUERADE")
                print(f"NAT enabled for {cidr}")

    # 4) Allow forwarding for bridge
    for direction in ["-i", "-o"]:
        fwd_check = f"iptables -C FORWARD {direction} {bridge_name} -j ACCEPT"
        if not rule_exists(fwd_check):
            run(f"iptables -A FORWARD {direction} {bridge_name} -j ACCEPT")

    # 5) Allow subnet <-> subnet traffic & ICMP
    for src in subnets:
        for dst in subnets:
            if src is dst:
                continue
            src_cidr = src["cidr"]
            dst_cidr = dst["cidr"]

            # generic forward
            forward_check = f"iptables -C FORWARD -s {src_cidr} -d {dst_cidr} -j ACCEPT"
            if not rule_exists(forward_check):
                run(f"iptables -A FORWARD -s {src_cidr} -d {dst_cidr} -j ACCEPT")

            # ICMP forward
            icmp_check = f"iptables -C FORWARD -p icmp -s {src_cidr} -d {dst_cidr} -j ACCEPT"
            if not rule_exists(icmp_check):
                run(f"iptables -A FORWARD -p icmp -s {src_cidr} -d {dst_cidr} -j ACCEPT")

    print(f"Routing and NAT setup complete for bridge {bridge_name}")
