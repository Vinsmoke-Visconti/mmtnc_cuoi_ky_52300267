#!/bin/bash
# run_all.sh – Chay toan bo do an MMTNC Cuoi Ky
# Cach dung: chmod +x run_all.sh && sudo ./run_all.sh
# =====================================================
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

BLUE='\033[0;34m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'

echo -e "${BLUE}======================================================"
echo -e "  CAMPUS 3-TIER + DMZ – MMTNC CUOI KY – MSSV: 52300267"
echo -e "======================================================${NC}"

# 1. Kiem tra quyen root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}[ERROR] Can quyen root. Chay: sudo ./run_all.sh${NC}"
    exit 1
fi

# 2. Cai dat thu vien Python can thiet
echo -e "\n${YELLOW}[INFO] Kiem tra thu vien Python...${NC}"
python3 -c "import openpyxl"   2>/dev/null || { echo "[INFO] Cai openpyxl..."; pip3 install openpyxl -q; }
python3 -c "import matplotlib" 2>/dev/null || { echo "[INFO] Cai matplotlib..."; pip3 install matplotlib -q; }

# 3. Don dep tien trinh cu
echo -e "${YELLOW}[INFO] Don dep tien trinh cu...${NC}"
pkill -9 -f "python3 main_topology" 2>/dev/null || true
pkill -9 -f zebra  2>/dev/null || true
pkill -9 -f ospfd  2>/dev/null || true
pkill -9 -f "iperf -s" 2>/dev/null || true
pkill -9 -f "python3 -m http.server" 2>/dev/null || true
mn -c 2>/dev/null || true
sleep 1

# 4. Tao thu muc ket qua
mkdir -p results
echo -e "${GREEN}[INFO] Thu muc results/ san sang.${NC}"

# 5. Kiem tra FRR
if which zebra &>/dev/null || [ -f /usr/lib/frr/zebra ]; then
    echo -e "${GREEN}[INFO] FRR (zebra/ospfd) da cai dat.${NC}"
else
    echo -e "${YELLOW}[WARN] FRR chua cai. OSPF se khong chay, nhung static routes van OK.${NC}"
    echo "       Cai FRR: sudo apt install frr -y"
fi

# 6. Tao bao cao Excel mau (khong can Mininet)
echo -e "\n${YELLOW}[INFO] Tao bao cao Excel mau (du lieu demo)...${NC}"
python3 scripts/generate_report.py && echo -e "${GREEN}[OK] Bao cao mau tao thanh cong.${NC}" || true

echo ""
echo -e "${BLUE}======================================================${NC}"
echo -e "${YELLOW}[INFO] Khoi dong topology Mininet...${NC}"
echo "       Sau khi Mininet CLI xuat hien, co the chay:"
echo ""
echo "  [KIEM TRA CO BAN]"
echo "  mininet> h1 ping -c 4 192.168.20.11      # Inside-to-Inside"
echo "  mininet> h1 ping -c 4 10.10.10.11         # Inside-to-DMZ"
echo "  mininet> ext ping -c 4 100.0.0.11         # Ext -> Static NAT"
echo ""
echo "  [NAT & ACL]"
echo "  mininet> fw iptables -t nat -L -n -v"
echo "  mininet> fw iptables -L FORWARD -n -v"
echo "  mininet> py exec(open('scripts/nat_acl_test.py').read() + \"\\nrun_nat_acl_test(net)\", globals())"
echo ""
echo "  [HIEU NANG]"
echo "  mininet> py exec(open('scripts/performance_test.py').read() + \"\\nfull_test(net)\", globals())"
echo ""
echo "  [CAN BANG TAI]"
echo "  mininet> py exec(open('scripts/load_balancer.py').read() + \"\\ndemo_load_balance(net)\", globals())"
echo ""
echo "  [OSPF]"
echo "  mininet> fw   vtysh --vty_socket /tmp/frr_fw   -c 'show ip ospf neighbor'"
echo "  mininet> core vtysh --vty_socket /tmp/frr_core -c 'show ip route'"
echo ""
echo -e "${BLUE}======================================================${NC}"
echo ""

# 7. Chay topology chinh
python3 main_topology.py

# 8. Sau khi thoat Mininet, tao bao cao tu ket qua thuc te
echo -e "\n${YELLOW}[INFO] Tao bao cao Excel tu ket qua thuc te...${NC}"
python3 scripts/generate_report.py

echo ""
echo -e "${GREEN}[DONE] Hoan thanh! Ket qua trong thu muc results/${NC}"
ls -lh results/
