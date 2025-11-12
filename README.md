# Build Your Own Virtual Private Cloud (VPC) on Linux

This project recreates the fundamentals of a Virtual Private Cloud (VPC) entirely on Linux using native tools like **network namespaces, veth pairs, bridges, routing tables, and iptables**. It simulates public and private subnets, routing, NAT, firewall rules, and isolation.  

The project includes a custom CLI tool `vpcctl.py` to automate VPC lifecycle operations.

By the end of this tutorial, you will be able to:
- Create a VPC with public and private subnets.
- Route traffic between subnets and to the internet.
- Deploy a simple app in the public subnet.
- Verify NAT behavior, isolation, and firewall rules.

---

## 📂 Repository Contents

| File / Folder       | Description |
|--------------------|-------------|
| `vpcctl.py`         | CLI tool for creating, deleting, and managing VPCs and subnets. |
| `policies/policy.json` | JSON file defining subnet CIDRs, gateways, and firewall rules. |
| `logs/`             | Optional logs of VPC creation and teardown (auto-generated). |
| `README.md`         | This file. |
| `scripts/`          | Optional helper scripts for automation or cleanup. |

---

## ⚡ Features

- Create and manage a virtual VPC with public and private subnets.
- Automated routing between subnets through a Linux bridge.
- NAT gateway simulation for public subnets.
- Firewall rules applied at subnet level using iptables.
- Demonstrates VPC isolation (one VPC cannot reach another without peering).
- Deploy simple HTTP server apps in subnets to validate connectivity.

---

## 📝 Prerequisites

- Linux host (or Linux container) with root privileges.
- Python 3.x
- Docker (for macOS users)
- Internet connection (for NAT testing from public subnet)

> **Note for macOS users:** Docker is required because Linux network namespaces and iptables require a Linux kernel. The container simulates a Linux host environment where all VPC operations can run as expected.

---

## 🚀 Getting Started (macOS with Docker)

### 1. Start the Container & Enter Project Folder

```bash
docker start -ai vpc-lab
cd /hng13-stage-4
2. Clean Previous VPCs (Optional, for a fresh start)
bash
Copy code
ip netns del ifym_public 2>/dev/null
ip netns del ifym_private 2>/dev/null
ip link del vethh1 2>/dev/null
ip link del vethn1 2>/dev/null
ip link del vpc-ifym 2>/dev/null
3. Create VPC and Subnets
bash
Copy code
python3 vpcctl.py create --config policies/policy.json
4. Test Connectivity — Ping Gateways
bash
Copy code
ip netns exec ifym_public ping -c 2 10.0.1.1
ip netns exec ifym_private ping -c 2 10.0.2.1
5. Test Connectivity Between Subnets
bash
Copy code
ip netns exec ifym_public ping -c 2 10.0.2.10
ip netns exec ifym_private ping -c 2 10.0.1.10
6. Test NAT / Internet Access
bash
Copy code
# Public subnet outgoing (should succeed)
ip netns exec ifym_public curl -I https://example.com

# Private subnet outgoing (should fail)
ip netns exec ifym_private curl -I https://example.com
7. Deploy a Simple App (Public Subnet)
bash
Copy code
ip netns exec ifym_public python3 -m http.server 8080 &
ip netns exec ifym_public curl http://10.0.1.10:8080  # Should succeed
ip netns exec ifym_private curl http://10.0.1.10:8080 # Should fail
8. View Logs of Operations
bash
Copy code
cat /var/log/vpcctl.log
9. Clean Teardown
bash
Copy code
python3 vpcctl.py delete --config policies/policy.json
All network namespaces, veth pairs, bridges, and firewall rules will be removed.

📊 Architecture
nginx
Copy code
          Internet
             |
          NAT Gateway
             |
         vpc-ifym (Bridge)
          /       \
   ifym_public   ifym_private
(10.0.1.10/24) (10.0.2.10/24)
Public subnet can reach the internet via NAT.

Private subnet is internal-only unless routed explicitly.

Subnets can communicate within the same VPC.

✅ Expected Outcomes
Public subnet can ping the internet.

Private subnet cannot ping the internet.

Subnets communicate internally within the VPC.

Simple app deployed in the public subnet is reachable from the public namespace but not private.

VPC teardown removes all resources cleanly.

