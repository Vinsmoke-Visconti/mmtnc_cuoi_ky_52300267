#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================
DO AN CUOI KY - MMTNC - MSSV: 52300267
De tai: Toi Uu Hoa Bao Mat Da Lop va Can Bang Tai
        Dua Tren Nguong Trong Mo Hinh Campus 3 Lop
=============================================================
Kien truc:
  [Internet-Sim] --- [fw-router] --- [core-r]
                          |               |   \
                       [dmz-sw]       [dist1]  [dist2]
                       /     \           |          |
                   [web1] [web2]      [acc1]     [acc2]
                                     / \          / \
                                  [h1][h2]     [h3][h4]

NAT/PAT:
  - PAT Overload: Inside (192.168.10/20.x) -> Outside via fw-eth0
  - Static NAT:   10.10.10.11 <-> 100.0.0.11 (web1)
                  10.10.10.12 <-> 100.0.0.12 (web2)

Security:
  - Standard ACL: Block host 192.168.20.0/24 khoi truy cap DMZ truc tiep
  - Extended ACL: Chi cho phep port 80 va 443 tu Inside vao DMZ
  - Firewall (iptables): Default DROP inbound, chi mo port can thiet

OSPF:
  - fw-router, core-r, dist1, dist2 chay OSPF area 0
  - FRR daemons (zebra + ospfd)
=============================================================
FIX LOG:
  v1: Kien truc ban dau
  v2: Fix NAT iptables co the xung dot voi FORWARD chain
      Fix FRR socket path rieng cho tung node
      Fix rp_filter cho cac router
      Them wait sau khi start FRR de OSPF hoi tu
  v3: Fix switch canonical names (dmz->s1, acc1->s2, acc2->s3)
      Mininet OVS yeu cau ten switch dang s<number>
      Them ICMP FORWARD rule cho ext->DMZ ping Static NAT
=============================================================
"""

import os
import sys
import time

from mininet.net import Mininet
from mininet.node import Node, OVSKernelSwitch, Host
from mininet.link import TCLink
from mininet.cli import CLI
from mininet.log import setLogLevel, info


# ---------------------------------------------------------------
# CLASS: Linux Router (ip_forward + rp_filter)
# ---------------------------------------------------------------
class LinuxRouter(Node):
    def config(self, **params):
        super(LinuxRouter, self).config(**params)
        self.cmd('sysctl -w net.ipv4.ip_forward=1')
        self.cmd('sysctl -w net.ipv4.conf.all.rp_filter=0')
        self.cmd('sysctl -w net.ipv4.conf.default.rp_filter=0')

    def terminate(self):
        self.cmd('sysctl -w net.ipv4.ip_forward=0')
        self.cmd('pkill -f zebra  2>/dev/null || true')
        self.cmd('pkill -f ospfd  2>/dev/null || true')
        super(LinuxRouter, self).terminate()


# ---------------------------------------------------------------
# TOPOLOGY
# ---------------------------------------------------------------
def build_topology(net):
    info('*** [1/4] Them routers\n')

    # Firewall router (bien mang)
    fw   = net.addHost('fw',    cls=LinuxRouter, ip=None)
    # Core layer router
    core = net.addHost('core',  cls=LinuxRouter, ip=None)
    # Distribution layer (2 router)
    dist1 = net.addHost('dist1', cls=LinuxRouter, ip=None)
    dist2 = net.addHost('dist2', cls=LinuxRouter, ip=None)
    # Internet simulator (host gia lap ben ngoai)
    ext  = net.addHost('ext',   cls=LinuxRouter, ip=None)

    info('*** [2/4] Them switches (dung ten s<N> - Mininet canonical)\n')
    # NOTE: Mininet OVS bat buoc ten switch dang s<number> de tu dong sinh dpid
    dmz_sw = net.addSwitch('s1', cls=OVSKernelSwitch)   # s1 = DMZ switch
    acc1   = net.addSwitch('s2', cls=OVSKernelSwitch)   # s2 = Access switch 1
    acc2   = net.addSwitch('s3', cls=OVSKernelSwitch)   # s3 = Access switch 2

    info('*** [3/4] Them DMZ servers va Inside hosts\n')
    # DMZ Servers
    web1 = net.addHost('web1', ip='10.10.10.11/24', defaultRoute='via 10.10.10.1')
    web2 = net.addHost('web2', ip='10.10.10.12/24', defaultRoute='via 10.10.10.1')

    # Inside hosts - VLAN Access 1 (192.168.10.x)
    h1 = net.addHost('h1', ip='192.168.10.11/24', defaultRoute='via 192.168.10.1')
    h2 = net.addHost('h2', ip='192.168.10.12/24', defaultRoute='via 192.168.10.1')

    # Inside hosts - VLAN Access 2 (192.168.20.x)
    h3 = net.addHost('h3', ip='192.168.20.11/24', defaultRoute='via 192.168.20.1')
    h4 = net.addHost('h4', ip='192.168.20.12/24', defaultRoute='via 192.168.20.1')

    info('*** [4/4] Tao lien ket\n')

    # === WAN: External --- Firewall (100 Mbps, 10ms) ===
    net.addLink(ext,  fw,   intfName1='ext-eth0',   intfName2='fw-eth0',   bw=100, delay='10ms')

    # === Firewall --- Core (1 Gbps, 1ms) ===
    net.addLink(fw,   core, intfName1='fw-eth1',    intfName2='core-eth0', bw=1000, delay='1ms')

    # === Firewall --- DMZ Switch (100 Mbps, 2ms) ===
    net.addLink(fw,   dmz_sw, intfName1='fw-eth2')

    # === Core --- Distribution (1 Gbps, 1ms) ===
    net.addLink(core, dist1, intfName1='core-eth1', intfName2='dist1-eth0', bw=1000, delay='1ms')
    net.addLink(core, dist2, intfName1='core-eth2', intfName2='dist2-eth0', bw=1000, delay='1ms')

    # === Distribution --- Access switches (100 Mbps, 2ms) ===
    net.addLink(dist1, acc1, intfName1='dist1-eth1', bw=100, delay='2ms')
    net.addLink(dist2, acc2, intfName1='dist2-eth1', bw=100, delay='2ms')

    # === [UPGRADE MUC 3] Redundant Link (HA): dist1 --- dist2 (1 Gbps, 1ms) ===
    net.addLink(dist1, dist2, intfName1='dist1-eth2', intfName2='dist2-eth2', bw=1000, delay='1ms')

    # === Access --- Hosts ===
    net.addLink(acc1, h1)
    net.addLink(acc1, h2)
    net.addLink(acc2, h3)
    net.addLink(acc2, h4)

    # === DMZ Switch --- Servers ===
    net.addLink(dmz_sw, web1)
    net.addLink(dmz_sw, web2)


# ---------------------------------------------------------------
# SWITCH CONFIGURATION
# ---------------------------------------------------------------
def configure_switches(net):
    info('*** Cau hinh OVS switches (standalone, STP off)...\n')
    for sw in net.switches:
        sw.cmd('ovs-vsctl set Bridge %s fail-mode=standalone' % sw.name)
        sw.cmd('ovs-vsctl set Bridge %s stp_enable=false' % sw.name)
        info(f'  {sw.name}: standalone mode, STP disabled\n')


# ---------------------------------------------------------------
# IP CONFIGURATION
# ---------------------------------------------------------------
def configure_ip(net):
    info('\n*** Gan dia chi IP cho cac router...\n')

    # --- Loopbacks (OSPF router-id) ---
    net.get('fw').cmd('ip addr add 10.255.1.10/32 dev lo')
    net.get('core').cmd('ip addr add 10.255.1.1/32 dev lo')
    net.get('dist1').cmd('ip addr add 10.255.1.2/32 dev lo')
    net.get('dist2').cmd('ip addr add 10.255.1.3/32 dev lo')

    # --- External WAN: ext --- fw ---
    net.get('ext').cmd('ip addr add 203.0.113.1/30 dev ext-eth0')
    net.get('fw').cmd('ip addr add 203.0.113.2/30 dev fw-eth0')

    # --- fw --- core (internal backbone) ---
    net.get('fw').cmd('ip addr add 172.16.0.1/30 dev fw-eth1')
    net.get('core').cmd('ip addr add 172.16.0.2/30 dev core-eth0')

    # --- fw --- DMZ Switch ---
    net.get('fw').cmd('ip addr add 10.10.10.1/24 dev fw-eth2')

    # --- core --- dist1 ---
    net.get('core').cmd('ip addr add 172.16.1.1/30 dev core-eth1')
    net.get('dist1').cmd('ip addr add 172.16.1.2/30 dev dist1-eth0')

    # --- core --- dist2 ---
    net.get('core').cmd('ip addr add 172.16.2.1/30 dev core-eth2')
    net.get('dist2').cmd('ip addr add 172.16.2.2/30 dev dist2-eth0')

    # --- dist1 --- acc1 (gateway for 192.168.10.x) ---
    net.get('dist1').cmd('ip addr add 192.168.10.1/24 dev dist1-eth1')

    # --- dist2 --- acc2 (gateway for 192.168.20.x) ---
    net.get('dist2').cmd('ip addr add 192.168.20.1/24 dev dist2-eth1')

    # --- [UPGRADE MUC 3] dist1 --- dist2 (Redundant Link) ---
    net.get('dist1').cmd('ip addr add 172.16.3.1/30 dev dist1-eth2')
    net.get('dist2').cmd('ip addr add 172.16.3.2/30 dev dist2-eth2')

    # --- ext: default route huong vao fw (de gia lap internet) ---
    net.get('ext').cmd('ip route add 100.0.0.0/24 via 203.0.113.2')
    net.get('ext').cmd('ip route add 10.0.0.0/8 via 203.0.113.2')

    info('*** IP configuration done.\n')
    info('*** Them static routes bo sung (Linux kernel)...\n')

    # fw: biet duong den vung inside va dmz
    net.get('fw').cmd('ip route add 192.168.10.0/24 via 172.16.0.2')
    net.get('fw').cmd('ip route add 192.168.20.0/24 via 172.16.0.2')
    net.get('fw').cmd('ip route add default via 203.0.113.1')

    # core: biet duong den cac vung
    net.get('core').cmd('ip route add 10.10.10.0/24 via 172.16.0.1')
    net.get('core').cmd('ip route add 100.0.0.0/24 via 172.16.0.1')
    net.get('core').cmd('ip route add default via 172.16.0.1')

    # dist1: default qua core
    net.get('dist1').cmd('ip route add default via 172.16.1.1')
    net.get('dist1').cmd('ip route add 10.10.10.0/24 via 172.16.1.1')
    net.get('dist1').cmd('ip route add 192.168.20.0/24 via 172.16.1.1')

    # dist2: default qua core
    net.get('dist2').cmd('ip route add default via 172.16.2.1')
    net.get('dist2').cmd('ip route add 10.10.10.0/24 via 172.16.2.1')
    net.get('dist2').cmd('ip route add 192.168.10.0/24 via 172.16.2.1')

    info('*** Static routes configured.\n')


# ---------------------------------------------------------------
# NAT / PAT / STATIC NAT CONFIGURATION
# ---------------------------------------------------------------
def configure_nat(net):
    """
    Cau hinh NAT tren fw-router:
    1. PAT Overload (MASQUERADE): Inside (192.168.10/20.x) -> fw-eth0 (203.0.113.2)
    2. Static NAT:
        - 10.10.10.11 (web1) <-> 100.0.0.11
        - 10.10.10.12 (web2) <-> 100.0.0.12
    3. Them IP alias cho Static NAT public IPs
    """
    info('\n*** Cau hinh NAT/PAT tren fw-router...\n')
    fw = net.get('fw')

    # Xoa cac rule cu
    fw.cmd('iptables -t nat -F')
    fw.cmd('iptables -F')
    fw.cmd('iptables -t mangle -F')

    # Them IP alias cho Static NAT tren interface ngoai (100.0.0.x)
    fw.cmd('ip addr add 100.0.0.11/24 dev fw-eth0 2>/dev/null || true')
    fw.cmd('ip addr add 100.0.0.12/24 dev fw-eth0 2>/dev/null || true')
    # Them route 100.0.0.0/24 ra fw-eth0 de ext co the reach
    fw.cmd('ip route add 100.0.0.0/24 dev fw-eth0 2>/dev/null || true')

    # --- PAT Overload: Inside -> Internet ---
    # POSTROUTING: bat ki traffic tu inside ra ngoai qua fw-eth0 thi MASQUERADE
    fw.cmd('iptables -t nat -A POSTROUTING -s 192.168.10.0/24 -o fw-eth0 -j MASQUERADE')
    fw.cmd('iptables -t nat -A POSTROUTING -s 192.168.20.0/24 -o fw-eth0 -j MASQUERADE')

    # --- Static NAT cho DMZ servers ---
    # DNAT: traffic den 100.0.0.11 -> chuyen vao 10.10.10.11
    fw.cmd('iptables -t nat -A PREROUTING  -d 100.0.0.11 -j DNAT --to-destination 10.10.10.11')
    fw.cmd('iptables -t nat -A PREROUTING  -d 100.0.0.12 -j DNAT --to-destination 10.10.10.12')
    # SNAT: tra loi tu 10.10.10.11 -> nguon la 100.0.0.11
    fw.cmd('iptables -t nat -A POSTROUTING -s 10.10.10.11 -o fw-eth0 -j SNAT --to-source 100.0.0.11')
    fw.cmd('iptables -t nat -A POSTROUTING -s 10.10.10.12 -o fw-eth0 -j SNAT --to-source 100.0.0.12')

    # --- FORWARD chain: cho phep traffic hop le di qua ---
    # Cho phep cac ket noi da thiet lap
    fw.cmd('iptables -A FORWARD -m state --state ESTABLISHED,RELATED -j ACCEPT')

    # Inside -> DMZ: chi cho port 80 va 443 (Extended ACL)
    fw.cmd('iptables -A FORWARD -s 192.168.10.0/24 -d 10.10.10.0/24 -p tcp --dport 80  -j ACCEPT')
    fw.cmd('iptables -A FORWARD -s 192.168.10.0/24 -d 10.10.10.0/24 -p tcp --dport 443 -j ACCEPT')
    fw.cmd('iptables -A FORWARD -s 192.168.20.0/24 -d 10.10.10.0/24 -p tcp --dport 80  -j ACCEPT')
    fw.cmd('iptables -A FORWARD -s 192.168.20.0/24 -d 10.10.10.0/24 -p tcp --dport 443 -j ACCEPT')
    # ICMP cho phep tu Inside vao DMZ (de test ping)
    fw.cmd('iptables -A FORWARD -s 192.168.0.0/16   -d 10.10.10.0/24 -p icmp -j ACCEPT')

    # Standard ACL: Block 192.168.20.x truy cap SSH (port 22) vao DMZ
    fw.cmd('iptables -A FORWARD -s 192.168.20.0/24 -d 10.10.10.0/24 -p tcp --dport 22 -j DROP')

    # Inside -> Internet (PAT traffic): cho phep
    fw.cmd('iptables -A FORWARD -s 192.168.0.0/16   -o fw-eth0 -j ACCEPT')

    # External -> Static NAT servers: chi cho port 80/443 va ICMP (de ping test)
    fw.cmd('iptables -A FORWARD -d 10.10.10.0/24 -p tcp --dport 80  -j ACCEPT')
    fw.cmd('iptables -A FORWARD -d 10.10.10.0/24 -p tcp --dport 443 -j ACCEPT')
    fw.cmd('iptables -A FORWARD -d 10.10.10.0/24 -p icmp -j ACCEPT')

    # DMZ -> Inside: BLOCK (DMZ khong duoc phep khoi tao ket noi vao Inside)
    fw.cmd('iptables -A FORWARD -s 10.10.10.0/24 -d 192.168.0.0/16 -j DROP')

    # Default FORWARD policy: DROP
    fw.cmd('iptables -P FORWARD DROP')

    # --- [UPGRADE MUC 3] Logging cho Heatmap (Security Intelligence) ---
    fw.cmd('iptables -A FORWARD -m limit --limit 5/min -j LOG --log-prefix "ACL-DROP: " --log-level 4')

    # INPUT/OUTPUT: ACCEPT (router chinh no)
    fw.cmd('iptables -P INPUT  ACCEPT')
    fw.cmd('iptables -P OUTPUT ACCEPT')

    info('  [OK] PAT Overload: 192.168.10/20.x -> fw-eth0 (MASQUERADE)\n')
    info('  [OK] Static NAT:   10.10.10.11 <-> 100.0.0.11 (web1)\n')
    info('  [OK] Static NAT:   10.10.10.12 <-> 100.0.0.12 (web2)\n')
    info('  [OK] Extended ACL: Inside -> DMZ chi port 80/443\n')
    info('  [OK] Standard ACL: DMZ khong khoi tao ket noi vao Inside\n')
    info('  [OK] Firewall FORWARD policy: DROP by default\n')


# ---------------------------------------------------------------
# FRR CONFIGURATION (OSPF routing)
# ---------------------------------------------------------------
FRR_BIN_CANDIDATES = ['/usr/lib/frr', '/usr/local/lib/frr', '/usr/sbin', '/usr/local/sbin']


def _find_frr():
    for path in FRR_BIN_CANDIDATES:
        if os.path.isfile(f'{path}/zebra'):
            return path
    return None


def _write_frr_conf(name, cfg_dir):
    """Tao FRR config tu template trong thu muc configs/."""
    loopbacks = {
        'fw':    '10.255.1.10',
        'core':  '10.255.1.1',
        'dist1': '10.255.1.2',
        'dist2': '10.255.1.3',
    }
    template_map = {
        'fw':    'configs/frr_fw.conf',
        'core':  'configs/frr_core.conf',
        'dist1': 'configs/frr_dist.conf',
        'dist2': 'configs/frr_dist.conf',
    }
    tmpl_path = template_map.get(name, 'configs/frr_default.conf')
    with open(tmpl_path, 'r', encoding='utf-8') as f:
        tmpl = f.read()

    conf = tmpl.format(
        name=name,
        loopback_ip=loopbacks.get(name, '127.0.0.1')
    )
    with open(f'{cfg_dir}/frr.conf', 'w', encoding='utf-8') as f:
        f.write(conf)


def start_frr(net):
    info('\n*** Khoi dong FRR daemons (OSPF)...\n')
    frr_bin = _find_frr()
    if not frr_bin:
        info('[WARN] FRR khong tim thay - bo qua FRR. Static routes van hoat dong.\n')
        return

    info(f'  FRR found at: {frr_bin}\n')
    ospf_nodes = ['fw', 'core', 'dist1', 'dist2']

    for name in ospf_nodes:
        node = net.get(name)
        cfg_dir = f'/tmp/frr_{name}'
        os.makedirs(cfg_dir, exist_ok=True)

        # Kill cac tien trinh FRR cu
        node.cmd(f'kill $(cat {cfg_dir}/zebra.pid 2>/dev/null) 2>/dev/null || true')
        node.cmd(f'kill $(cat {cfg_dir}/ospfd.pid  2>/dev/null) 2>/dev/null || true')
        time.sleep(0.3)

        # Ghi config
        _write_frr_conf(name, cfg_dir)
        node.cmd(f'chmod -R 777 {cfg_dir}')

        sock    = f'{cfg_dir}/zserv.api'
        vty_dir = cfg_dir

        # Khoi dong zebra truoc
        node.cmd(
            f'{frr_bin}/zebra -d '
            f'-f {cfg_dir}/frr.conf '
            f'-z {sock} '
            f'-i {cfg_dir}/zebra.pid '
            f'--vty_socket {vty_dir} '
            f'> {cfg_dir}/zebra.log 2>&1'
        )
        time.sleep(1.0)

        # Khoi dong ospfd
        node.cmd(
            f'{frr_bin}/ospfd -d '
            f'-f {cfg_dir}/frr.conf '
            f'-z {sock} '
            f'-i {cfg_dir}/ospfd.pid '
            f'--vty_socket {vty_dir} '
            f'> {cfg_dir}/ospfd.log 2>&1'
        )
        time.sleep(0.5)
        info(f'  + {name}: zebra + ospfd started\n')

    info('*** Cho OSPF hoi tu (30 giay)...\n')
    time.sleep(30)

    # Kiem tra OSPF
    info('*** Kiem tra OSPF neighbors:\n')
    for name in ['fw', 'core']:
        node = net.get(name)
        vty  = f'/tmp/frr_{name}'
        out  = node.cmd(f'vtysh --vty_socket {vty} -c "show ip ospf neighbor" 2>/dev/null')
        ok   = 'Full' in out or 'Exchange' in out or '2-Way' in out
        info(f'  {name}: {"OK OSPF Full" if ok else "WARN - xem " + vty + "/ospfd.log"}\n')


# ---------------------------------------------------------------
# SETUP HTTP SERVERS (gia lap web service)
# ---------------------------------------------------------------
def setup_services(net):
    """Khoi dong HTTP server gia lap tren web1 va web2."""
    info('\n*** Khoi dong HTTP services tren DMZ servers...\n')
    for srv in ['web1', 'web2']:
        node = net.get(srv)
        # Tao thu muc web rieng cho tung server
        node.cmd(f'mkdir -p /tmp/www_{srv}')
        node.cmd(f'echo "<h1>Server {srv} - {node.IP()}</h1>" > /tmp/www_{srv}/index.html')
        # Khoi dong HTTP server tren port 80
        node.cmd(f'cd /tmp/www_{srv} && python3 -m http.server 80 > /tmp/http_{srv}.log 2>&1 &')
        # Khoi dong iperf server cho do luong
        node.cmd(f'iperf -s -p 5201 > /tmp/iperf_{srv}.log 2>&1 &')
        info(f'  {srv} ({node.IP()}): HTTP:80 + iPerf:5201 running\n')
    time.sleep(1)


# ---------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------
def run():
    if os.geteuid() != 0:
        print('[ERROR] Can quyen root: sudo python3 main_topology.py')
        sys.exit(1)

    # Don dep tien trinh cu
    os.system('pkill -9 -f zebra 2>/dev/null; pkill -9 -f ospfd 2>/dev/null; mn -c 2>/dev/null; true')
    time.sleep(1)

    setLogLevel('info')
    info('\n=== CAMPUS 3-TIER + DMZ – MMTNC CUOI KY 52300267 ===\n\n')

    net = Mininet(controller=None, link=TCLink, switch=OVSKernelSwitch, autoSetMacs=True)
    build_topology(net)
    net.build()

    info('\n*** Khoi dong mang...\n')
    net.start()

    configure_switches(net)
    time.sleep(1)

    configure_ip(net)
    configure_nat(net)
    start_frr(net)
    setup_services(net)

    info('\n=== MANG DA SAN SANG ===\n')
    info('--- Kiem tra co ban ---\n')
    info('  h1 ping -c 3 192.168.20.11     (Inside-to-Inside qua dist)\n')
    info('  h1 ping -c 3 10.10.10.11        (Inside -> DMZ)\n')
    info('  h1 curl -s 10.10.10.11:80       (HTTP tu Inside vao DMZ)\n')
    info('  ext ping -c 3 100.0.0.11        (External -> Static NAT web1)\n')
    info('  ext curl -s 100.0.0.11:80       (HTTP tu ngoai vao web1 qua Static NAT)\n')
    info('\n--- Kiem tra NAT ---\n')
    info('  fw iptables -t nat -L -n -v --line-numbers\n')
    info('  fw iptables -L FORWARD -n -v --line-numbers\n')
    info('\n--- Kiem tra OSPF ---\n')
    info('  fw vtysh --vty_socket /tmp/frr_fw -c "show ip ospf neighbor"\n')
    info('  core vtysh --vty_socket /tmp/frr_core -c "show ip route"\n')
    info('\n--- Can bang tai ---\n')
    info('  mininet> test_lb\n')
    info('\n--- Do hieu nang ---\n')
    info('  mininet> test_perf\n')
    info('\n--- Kiem tra NAT/ACL ---\n')
    info('  mininet> test_nat\n')
    info('\nGo "exit" de thoat.\n\n')

    class MyCLI(CLI):
        def do_test_nat(self, line):
            """Chay test NAT va ACL"""
            import scripts.nat_acl_test as nat
            nat.run_nat_acl_test(self.mn)
            
        def do_test_perf(self, line):
            """Chay do luong hieu nang"""
            import scripts.performance_test as pt
            pt.full_test(self.mn)
            
        def do_test_lb(self, line):
            """Chay test Can bang tai"""
            import scripts.load_balancer as lb
            lb.demo_load_balance(self.mn)

    MyCLI(net)

    info('\n*** Don dep...\n')
    os.system('killall -9 zebra ospfd 2>/dev/null || true')
    net.stop()
    info('*** Xong.\n')


if __name__ == '__main__':
    run()
