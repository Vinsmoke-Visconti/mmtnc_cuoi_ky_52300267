#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
nat_acl_test.py
---------------
Kiem tra NAT/ACL va in bang nhật ký sự cố.
Chay trong Mininet CLI:
  py exec(open('scripts/nat_acl_test.py').read(), globals()); run_nat_acl_test(net)
"""
import os, re, time, json
from datetime import datetime

RESULTS_DIR = 'results'

def ensure_dir():
    os.makedirs(RESULTS_DIR, exist_ok=True)

def show_nat_table(fw):
    """In bang NAT translation hien tai."""
    print('\n' + '='*60)
    print('  BANG NAT TRANSLATION (iptables -t nat -L -n -v)')
    print('='*60)
    out = fw.cmd('iptables -t nat -L -n -v --line-numbers 2>/dev/null')
    print(out)
    return out

def show_acl_rules(fw):
    """In cac ACL rules (FORWARD chain)."""
    print('\n' + '='*60)
    print('  BANG ACL – FORWARD CHAIN (iptables -L FORWARD -n -v)')
    print('='*60)
    out = fw.cmd('iptables -L FORWARD -n -v --line-numbers 2>/dev/null')
    print(out)
    return out

def test_acl_block(net):
    """
    Kiem tra Standard ACL: Block ket noi khong hop le.
    - h3 (192.168.20.x) khong duoc SSH vao DMZ
    - h3 (192.168.20.x) DUOC truy cap HTTP (port 80)
    """
    h1, h3 = net.get('h1'), net.get('h3')
    fw = net.get('fw')
    results = []

    print('\n[ACL TEST 1] h3 (192.168.20.11) -> web1 port 80 (SHOULD ALLOW)')
    out = h3.cmd('curl -s --connect-timeout 3 -o /dev/null -w "%{http_code}" http://10.10.10.11:80 2>/dev/null')
    allowed = '200' in out or '000' not in out
    r1 = {'test': 'h3->web1:80', 'expected': 'ALLOW', 'result': 'ALLOW' if allowed else 'BLOCK', 'raw': out.strip()}
    results.append(r1)
    print(f'  Result: {r1["result"]} (expected: {r1["expected"]}) | HTTP code: {out.strip()}')

    print('[ACL TEST 2] h3 (192.168.20.11) -> web1 port 22 SSH (SHOULD BLOCK)')
    out2 = h3.cmd('nc -z -w 2 10.10.10.11 22 2>&1; echo "exit:$?"')
    blocked = 'exit:1' in out2 or 'refused' in out2 or 'timed out' in out2.lower()
    r2 = {'test': 'h3->web1:22', 'expected': 'BLOCK', 'result': 'BLOCK' if blocked else 'ALLOW', 'raw': out2.strip()}
    results.append(r2)
    print(f'  Result: {r2["result"]} (expected: {r2["expected"]})')

    print('[ACL TEST 3] web1 (DMZ) -> h1 (Inside) SHOULD BLOCK (DMZ cannot initiate)')
    out3 = net.get('web1').cmd('ping -c 3 -W 1 192.168.10.11 2>&1')
    blocked3 = '100% packet loss' in out3 or '3 packets transmitted, 0' in out3
    r3 = {'test': 'web1->h1 (DMZ->Inside)', 'expected': 'BLOCK', 'result': 'BLOCK' if blocked3 else 'ALLOW', 'raw': out3[-200:]}
    results.append(r3)
    print(f'  Result: {r3["result"]} (expected: {r3["expected"]})')

    return results

def test_nat_translation(net):
    """
    Tao traffic va doc bang NAT conntrack de xem ban dich.
    """
    h1, fw = net.get('h1'), net.get('fw')
    print('\n[NAT TEST] Tao traffic tu h1 -> external de tao NAT entry...')
    h1.cmd('curl -s --connect-timeout 2 http://203.0.113.1 2>/dev/null &')
    time.sleep(1)
    # Xem conntrack neu co
    ct_out = fw.cmd('conntrack -L -p tcp 2>/dev/null | head -20 || echo "conntrack not available"')
    nat_out = fw.cmd('iptables -t nat -L -n -v 2>/dev/null')
    print('[CONNTRACK TABLE (top 20 entries)]')
    print(ct_out)
    return nat_out, ct_out

def nat_traceability_issues():
    """
    Nhat ky cac loi pho bien khi NAT pha vo tinh truy vet (Traceability).
    """
    issues = [
        {
            'stt': 1,
            'van_de': 'Khong xac dinh duoc IP that cua client',
            'mo_ta': 'Sau khi MASQUERADE, tat ca traffic xuat hien tu IP cua firewall. Server chi thay IP cua fw-eth0, khong thay 192.168.10.x.',
            'nguyen_nhan': 'PAT Overload thay the IP nguon thanh IP cua interface ngoai',
            'khac_phuc': 'Ghi log PREROUTING truoc khi NAT: iptables -t mangle -A PREROUTING -j LOG --log-prefix "PRE-NAT: " --log-level 4',
        },
        {
            'stt': 2,
            'van_de': 'Khong theo doi session cu the',
            'mo_ta': 'Khi nhieu user dung chung 1 IP public, phan biet session dua vao port tam thoi (ephemeral port). Neu port bi tai su dung, log nham.',
            'nguyen_nhan': 'Port so ephemeral duoc cap phat dong, co the trung lap theo thoi gian',
            'khac_phuc': 'Ghi log ca SOURCE PORT: iptables -t nat -A POSTROUTING -j LOG --log-prefix "SNAT-PORT: "',
        },
        {
            'stt': 3,
            'van_de': 'Static NAT bi che khuat khi debug',
            'mo_ta': 'DNAT doi IP dich truoc khi vao FORWARD chain. Tool debug chi thay IP private, khong thay public IP ban dau.',
            'nguyen_nhan': 'PREROUTING thay doi packet truoc khi routing decision',
            'khac_phuc': 'Su dung: iptables -t raw -A PREROUTING -j TRACE de ghi tat ca buoc xu ly goi tin',
        },
        {
            'stt': 4,
            'van_de': 'Conntrack table day (connection tracking overflow)',
            'mo_ta': 'Khi so luong ket noi dong thoi qua lon, bang conntrack bi day, NAT ngung hoat dong.',
            'nguyen_nhan': 'Gia tri net.netfilter.nf_conntrack_max qua thap',
            'khac_phuc': 'Tang gia tri: sysctl -w net.netfilter.nf_conntrack_max=131072\nGiam timeout: sysctl -w net.netfilter.nf_conntrack_tcp_timeout_established=300',
        },
    ]
    return issues

def run_nat_acl_test(net):
    """Ham chinh: chay tat ca kiem tra NAT/ACL va xuat bao cao."""
    ensure_dir()
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    fw = net.get('fw')

    print('\n' + '='*65)
    print('  KIEM TRA NAT / ACL – CAMPUS 3-TIER + DMZ')
    print('='*65)

    # In bang NAT va ACL
    nat_table = show_nat_table(fw)
    acl_rules  = show_acl_rules(fw)

    # Test ACL block/allow
    acl_results = test_acl_block(net)

    # Test NAT translation
    nat_out, ct_out = test_nat_translation(net)

    # Nhat ky su co
    issues = nat_traceability_issues()

    print('\n[NHAT KY SU CO NAT – TRACEABILITY ISSUES]')
    print('='*65)
    for iss in issues:
        print(f"\n  [{iss['stt']}] {iss['van_de']}")
        print(f"      Mo ta    : {iss['mo_ta'][:80]}...")
        print(f"      Nguyen nhan: {iss['nguyen_nhan']}")
        print(f"      Khac phuc  : {iss['khac_phuc'][:80]}")

    # Tong hop ket qua ACL
    print('\n[TONG HOP ACL TEST]')
    print(f'  {"Kich ban":<35} {"Ket qua":<10} {"Mong doi":<10} {"Pass?"}')
    print('  ' + '-'*60)
    for r in acl_results:
        passed = r['result'] == r['expected']
        print(f'  {r["test"]:<35} {r["result"]:<10} {r["expected"]:<10} {"PASS" if passed else "FAIL"}')

    # Luu bao cao JSON
    report = {
        'timestamp': ts,
        'nat_table_raw': nat_table,
        'acl_rules_raw': acl_rules,
        'acl_test_results': acl_results,
        'traceability_issues': issues,
        'conntrack_raw': ct_out,
    }
    json_path = f'{RESULTS_DIR}/nat_acl_report_{ts}.json'
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f'\n[OK] Bao cao NAT/ACL luu tai: {json_path}')
    return report

if __name__ == '__main__':
    print('Chay tu Mininet CLI: py exec(open("scripts/nat_acl_test.py").read(), globals()); run_nat_acl_test(net)')
