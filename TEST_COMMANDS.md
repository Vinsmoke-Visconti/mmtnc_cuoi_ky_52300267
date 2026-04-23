# Lenh Kiem Tra – MMTNC Cuoi Ky (MSSV: 52300267)

## Trước khi chạy Mininet
```bash
# Cai thu vien
pip3 install openpyxl matplotlib

# Ve so do topology
python3 scripts/draw_topology.py

# Tao bao cao Excel mau (khong can Mininet)
python3 scripts/generate_report.py
```

## Khởi động
```bash
sudo python3 main_topology.py
```

## Kiem tra co ban (trong Mininet CLI)
```
# Inside-to-Inside (qua dist1 - core - dist2 - acc2)
mininet> h1 ping -c 4 192.168.20.11

# Inside -> DMZ (qua fw NAT)
mininet> h1 ping -c 4 10.10.10.11
mininet> h1 curl -s http://10.10.10.11

# External -> Static NAT -> DMZ
mininet> ext ping -c 4 100.0.0.11
mininet> ext curl -s http://100.0.0.11
mininet> ext curl -s http://100.0.0.12
```

## Kiem tra NAT
```
# Bang NAT table
mininet> fw iptables -t nat -L -n -v --line-numbers

# Bang FORWARD chain
mininet> fw iptables -L FORWARD -n -v --line-numbers

# Test NAT/ACL tu dong
mininet> py exec(open('scripts/nat_acl_test.py').read() + "\nrun_nat_acl_test(net)", globals())
```

## Do hieu nang
```
mininet> py exec(open('scripts/performance_test.py').read() + "\nfull_test(net)", globals())
```

## Can bang tai
```
mininet> py exec(open('scripts/load_balancer.py').read() + "\ndemo_load_balance(net)", globals())
```

## Kiem tra OSPF (neu FRR da cai)
```
mininet> fw   vtysh --vty_socket /tmp/frr_fw   -c "show ip ospf neighbor"
mininet> core vtysh --vty_socket /tmp/frr_core -c "show ip ospf neighbor"
mininet> core vtysh --vty_socket /tmp/frr_core -c "show ip route"
mininet> dist1 vtysh --vty_socket /tmp/frr_dist1 -c "show ip route"
```

## Sau khi thoat Mininet
```bash
python3 scripts/generate_report.py
ls -lh results/
```
