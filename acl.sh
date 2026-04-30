#!/bin/bash
# acl.sh - Script cau hinh Firewall ACL va NAT cho Router FW
# Su dung: sudo ./acl.sh

# 1. Reset iptables
iptables -F
iptables -t nat -F
iptables -X
iptables -Z

# 2. PAT (Overload) cho Inside users
iptables -t nat -A POSTROUTING -s 192.168.10.0/24 -o fw-eth0 -j MASQUERADE
iptables -t nat -A POSTROUTING -s 192.168.20.0/24 -o fw-eth0 -j MASQUERADE

# 3. Static NAT cho DMZ Web Servers
iptables -t nat -A PREROUTING  -d 100.0.0.11 -j DNAT --to-destination 10.10.10.11
iptables -t nat -A POSTROUTING -s 10.10.10.11 -o fw-eth0 -j SNAT --to-source 100.0.0.11

iptables -t nat -A PREROUTING  -d 100.0.0.12 -j DNAT --to-destination 10.10.10.12
iptables -t nat -A POSTROUTING -s 10.10.10.12 -o fw-eth0 -j SNAT --to-source 100.0.0.12

# 4. FORWARD Rules (ACL)
# Cho phep cac ket noi tra ve (Established/Related)
iptables -A FORWARD -m state --state ESTABLISHED,RELATED -j ACCEPT

# ICMP cho phep tu Inside vao DMZ
iptables -A FORWARD -s 192.168.0.0/16 -d 10.10.10.0/24 -p icmp -j ACCEPT

# Extended ACL: Inside -> DMZ chi cho phep port 80/443
iptables -A FORWARD -s 192.168.0.0/16 -d 10.10.10.0/24 -p tcp --dport 80  -j ACCEPT
iptables -A FORWARD -s 192.168.0.0/16 -d 10.10.10.0/24 -p tcp --dport 443 -j ACCEPT

# Standard ACL: Block mang 20.x truy cap SSH (port 22) vao DMZ
iptables -A FORWARD -s 192.168.20.0/24 -d 10.10.10.0/24 -p tcp --dport 22 -j DROP

# Inside -> Internet: cho phep
iptables -A FORWARD -s 192.168.0.0/16 -o fw-eth0 -j ACCEPT

# External -> Static NAT: chi cho phep 80/443 va ICMP
iptables -A FORWARD -d 10.10.10.0/24 -p tcp --dport 80  -j ACCEPT
iptables -A FORWARD -d 10.10.10.0/24 -p tcp --dport 443 -j ACCEPT
iptables -A FORWARD -d 10.10.10.0/24 -p icmp -j ACCEPT

# DMZ -> Inside: BLOCK
iptables -A FORWARD -s 10.10.10.0/24 -d 192.168.0.0/16 -j DROP

# Default policy
iptables -P FORWARD DROP

# Logging cho Heatmap
iptables -A FORWARD -m limit --limit 5/min -j LOG --log-prefix "ACL-DROP: " --log-level 4

# Router local traffic
iptables -P INPUT ACCEPT
iptables -P OUTPUT ACCEPT

echo "  [OK] Firewall ACL and NAT applied successfully."
