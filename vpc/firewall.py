"""
Firewall rules module for VPC subnets.
Applies rules inside a namespace or globally.
"""

import subprocess

def run(cmd):
    """Run a shell command and raise error if fails."""
    print(f"Running: {cmd}")
    result = subprocess.run(cmd, shell=True, text=True, capture_output=True)
    if result.returncode != 0:
        print(result.stderr)
        raise RuntimeError(f"Command failed: {cmd}")
    return result.stdout

def apply_firewall_rules(rules, namespace=None):
    """
    Apply firewall rules.
    Args:
        rules: list of dicts [{"protocol": "tcp", "port": 80, "action": "allow"}]
        namespace: namespace name or None for root
    """
    ns_prefix = f"ip netns exec {namespace} " if namespace else ""

    # Always allow loopback and established connections
    run(f"{ns_prefix}iptables -A INPUT -i lo -j ACCEPT")
    run(f"{ns_prefix}iptables -A INPUT -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT")

    for rule in rules:
        protocol = rule.get("protocol")
        port = rule.get("port")
        action = rule.get("action", "allow").lower()

        # Map JSON actions to iptables actions
        if action == "allow":
            action = "ACCEPT"
        elif action == "deny":
            action = "DROP"
        else:
            action = "ACCEPT"  # default fallback

        if protocol and port:
            run(f"{ns_prefix}iptables -A INPUT -p {protocol} --dport {port} -j {action}")
        elif protocol == "icmp":
            run(f"{ns_prefix}iptables -A INPUT -p icmp -j {action}")

    print(f"Firewall rules applied for {'namespace ' + namespace if namespace else 'root'}")
