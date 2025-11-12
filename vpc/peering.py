"""
Handle VPC peering by connecting two VPC bridges via a veth pair
and adding static routes. Simplified for HNG lab usage.

Features:
- Create veth pair named peer-{bridge1}-{bridge2} and attach ends to each bridge
- Add FORWARD rules for allowed CIDRs
- Idempotent: will not recreate existing veths
"""

import subprocess

def run(cmd):
    print(f"Running: {cmd}")
    result = subprocess.run(cmd, shell=True, text=True, capture_output=True)
    if result.returncode != 0:
        print(result.stderr)
        raise RuntimeError(f"Command failed: {cmd}")
    return result.stdout

def peer_vpcs(bridge1, bridge2, allowed_cidrs):
    """
    Connect two VPC bridges.

    Args:
        bridge1: first VPC bridge
        bridge2: second VPC bridge
        allowed_cidrs: list of CIDRs allowed to communicate
    """
    veth1 = f"peer_{bridge1}_{bridge2}"[:15]
    veth2 = f"peer_{bridge2}_{bridge1}"[:15]

    # 1) Create veth pair if missing
    existing = subprocess.run(f"ip link show {veth1}", shell=True, capture_output=True)
    if existing.returncode != 0:
        run(f"ip link add {veth1} type veth peer name {veth2}")

    # 2) Attach veth ends to bridges
    run(f"ip link set {veth1} master {bridge1}")
    run(f"ip link set {veth2} master {bridge2}")
    run(f"ip link set {veth1} up")
    run(f"ip link set {veth2} up")

    # 3) Add FORWARD rules for allowed CIDRs
    for cidr_pair in allowed_cidrs:
        src, dst = cidr_pair.split(":") if ":" in cidr_pair else (cidr_pair, cidr_pair)
        for (s, d) in [(src, dst), (dst, src)]:
            fwd_check = f"iptables -C FORWARD -s {s} -d {d} -j ACCEPT"
            if subprocess.run(fwd_check, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode != 0:
                run(f"iptables -A FORWARD -s {s} -d {d} -j ACCEPT")
            icmp_check = f"iptables -C FORWARD -p icmp -s {s} -d {d} -j ACCEPT"
            if subprocess.run(icmp_check, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode != 0:
                run(f"iptables -A FORWARD -p icmp -s {s} -d {d} -j ACCEPT")

    print(f"Peering established between {bridge1} and {bridge2}")
