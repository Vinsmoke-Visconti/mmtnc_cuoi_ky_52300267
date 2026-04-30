#!/bin/bash
# drop_acl.sh - Xoa bo toan bo ACL va tra ve trang thai ACCEPT mac dinh
# Su dung: sudo ./drop_acl.sh

iptables -F
iptables -t nat -F
iptables -X
iptables -Z
iptables -P FORWARD ACCEPT
iptables -P INPUT ACCEPT
iptables -P OUTPUT ACCEPT

echo "  [WARNING] All Firewall ACLs have been FLUSHED. Policy set to ACCEPT."
