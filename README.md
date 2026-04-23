# MMTNC Cuoi Ky – Campus 3-Tier + DMZ
## MSSV: 52300267 | Truong DH Ton Duc Thang | Mon: Mang May Tinh Nang Cao

---

## 📌 De tai

**Bai Tap 3: Toi Uu Hoa Bao Mat Da Lop va Can Bang Tai Dua Tren Nguong Trong Mo Hinh Campus 3 Lop**

Thiet ke va trien khai he thong mang Campus 3 lop (Core – Distribution – Access) tich hop vung bien DMZ.
He thong tu dong dieu tiet luu luong giua cac Server khi dat nguong bang thong xac dinh va bao ve tai nguyen bang co che loc goi tin da tang.

---

## 📁 Cau truc thu muc

```
mmtnc_cuoi_ky_52300267/
├── main_topology.py           # Topology chinh Mininet (chay dau tien)
├── run_all.sh                 # Script chay toan bo tu dong
├── configs/                   # FRR config templates (OSPF)
│   ├── frr_core.conf          # Core router template
│   ├── frr_dist.conf          # Distribution router template
│   ├── frr_fw.conf            # Firewall router template
│   └── frr_default.conf       # Default (no routing)
├── scripts/
│   ├── load_balancer.py       # Giam sat tai + dieu huong tu dong + Matplotlib
│   ├── performance_test.py    # Do Throughput, Latency, NAT comparison
│   ├── nat_acl_test.py        # Kiem tra NAT/ACL + nhat ky su co
│   ├── generate_report.py     # Tao bao cao Excel da sheet + bieu do
│   └── draw_topology.py       # Ve so do topology mang (PNG)
├── results/                   # Ket qua: JSON, Excel, PNG
├── docs/                      # So do topology PNG, tai lieu
└── README.md                  # File nay
```

---

## 🌐 Kien truc mang

```
[ext - 203.0.113.1]
       |  WAN 100M/10ms
[fw-router] ← Firewall: NAT/PAT, ACL, iptables
  |    \
  |   [dmz-sw] ← DMZ
  |   /     \
  | [web1]  [web2]   ← 10.10.10.11/12 (Static NAT: 100.0.0.11/12)
  |                    (HTTP:80, iPerf:5201)
[core-r]
 /       \
[dist1]  [dist2]   ← OSPF, Gateway cho Inside
  |           |
[acc1]      [acc2]  ← Access Layer Switches
 / \          / \
h1  h2      h3  h4  ← 192.168.10.x / 192.168.20.x
```

---

## 📋 Bang dia chi IP

| Phan doan          | Subnet             | Ghi chu                     |
|--------------------|--------------------|-----------------------------|
| External WAN       | 203.0.113.0/30     | ext=.1, fw-eth0=.2          |
| fw → core          | 172.16.0.0/30      | fw=.1, core=.2              |
| fw → DMZ           | 10.10.10.0/24      | fw=.1, web1=.11, web2=.12   |
| core → dist1       | 172.16.1.0/30      | core=.1, dist1=.2           |
| core → dist2       | 172.16.2.0/30      | core=.1, dist2=.2           |
| Inside Access-1    | 192.168.10.0/24    | GW: dist1=.1                |
| Inside Access-2    | 192.168.20.0/24    | GW: dist2=.1                |
| Static NAT web1    | 100.0.0.11         | Public IP cho web1          |
| Static NAT web2    | 100.0.0.12         | Public IP cho web2          |
| Loopback fw        | 10.255.1.10/32     | OSPF Router-ID              |
| Loopback core      | 10.255.1.1/32      | OSPF Router-ID              |
| Loopback dist1     | 10.255.1.2/32      | OSPF Router-ID              |
| Loopback dist2     | 10.255.1.3/32      | OSPF Router-ID              |

---

## 🛡️ Chinh sach Bao mat

| Lop bao mat     | Cau hinh                                          |
|-----------------|---------------------------------------------------|
| Standard ACL    | Block SSH (port 22) tu 192.168.20.0/24 vao DMZ    |
| Extended ACL    | Chi cho port 80 va 443 tu Inside vao DMZ          |
| Firewall Policy | FORWARD chain: DROP by default                    |
| NAT/PAT         | MASQUERADE cho Inside; SNAT/DNAT cho Static NAT   |
| DMZ Isolation   | DMZ khong the khoi tao ket noi vao Inside         |

---

## 🚀 Huong dan chay

### Buoc 0: Chuan bi (khong can root)
```bash
cd mmtnc_cuoi_ky_52300267
pip3 install openpyxl matplotlib
python3 scripts/draw_topology.py       # Ve so do topology
python3 scripts/generate_report.py     # Tao bao cao Excel mau
```

### Buoc 1: Chay topology Mininet
```bash
sudo python3 main_topology.py
```

### Buoc 2: Kiem tra co ban (trong Mininet CLI)
```
mininet> h1 ping -c 4 192.168.20.11     # Inside-to-Inside (h1 -> h3)
mininet> h1 ping -c 4 10.10.10.11        # Inside-to-DMZ (h1 -> web1)
mininet> h1 curl -s http://10.10.10.11   # HTTP tu Inside vao web1
mininet> ext ping -c 4 100.0.0.11        # External -> Static NAT -> web1
mininet> ext curl -s http://100.0.0.11   # HTTP tu External qua Static NAT
```

### Buoc 3: Kiem tra NAT & ACL
```
mininet> fw iptables -t nat -L -n -v --line-numbers
mininet> fw iptables -L FORWARD -n -v --line-numbers
mininet> py exec(open('scripts/nat_acl_test.py').read(), globals()); run_nat_acl_test(net)
```

### Buoc 4: Do hieu nang
```
mininet> py exec(open('scripts/performance_test.py').read(), globals()); full_test(net)
```

### Buoc 5: Demo Can bang tai
```
mininet> py exec(open('scripts/load_balancer.py').read(), globals()); demo_load_balance(net)
```

### Buoc 6: Kiem tra OSPF (neu FRR da cai)
```
mininet> fw   vtysh --vty_socket /tmp/frr_fw   -c "show ip ospf neighbor"
mininet> core vtysh --vty_socket /tmp/frr_core -c "show ip route"
mininet> dist1 vtysh --vty_socket /tmp/frr_dist1 -c "show ip ospf database"
```

### Buoc 7: Tao bao cao (sau khi thoat Mininet)
```bash
python3 scripts/generate_report.py    # → results/mmtnc_report_YYYYMMDD.xlsx
```

### Chay tat ca 1 lenh
```bash
sudo bash run_all.sh
```

---

## 📊 Ket qua can dat

| Yeu cau                              | File                    | Status |
|--------------------------------------|-------------------------|--------|
| Topology Campus 3 lop + DMZ          | main_topology.py        | ✅     |
| OSPF (FRR zebra + ospfd)             | main_topology.py        | ✅     |
| PAT Overload (Inside -> Internet)    | main_topology.py        | ✅     |
| Static NAT (web1, web2)              | main_topology.py        | ✅     |
| Standard ACL (loc nguon)             | main_topology.py        | ✅     |
| Extended ACL (loc port 80/443)       | main_topology.py        | ✅     |
| Firewall bien (iptables DROP)        | main_topology.py        | ✅     |
| Giam sat tai theo nguong (>80/<20%)  | scripts/load_balancer.py| ✅     |
| Bieu do Line Chart Matplotlib        | scripts/load_balancer.py| ✅     |
| Do Throughput/Latency                | scripts/performance_test| ✅     |
| So sanh Co NAT vs Khong NAT          | scripts/performance_test| ✅     |
| Kiem tra ACL block/allow             | scripts/nat_acl_test.py | ✅     |
| Nhat ky su co NAT (Traceability)     | scripts/nat_acl_test.py | ✅     |
| Bao cao Excel da sheet               | scripts/generate_report | ✅     |
| So do topology PNG                   | scripts/draw_topology   | ✅     |

---

## 🛠️ Yeu cau he thong
- Ubuntu 20.04+ / Debian 11+
- Mininet >= 2.3.0
- FRRouting (FRR) >= 8.0 (tuy chon, static routes van OK neu thieu)
- Python 3.8+
- `pip3 install openpyxl matplotlib`
- `sudo apt install iperf netcat-openbsd curl traceroute`
