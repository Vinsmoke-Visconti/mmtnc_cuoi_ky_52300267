#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
performance_test.py – Do luong hieu nang Campus 3-tier + DMZ
Chay trong Mininet CLI:
  py exec(open('scripts/performance_test.py').read(), globals()); full_test(net)
"""
import os, re, time, json
from datetime import datetime

RESULTS_DIR = 'results'

def ensure_dir():
    os.makedirs(RESULTS_DIR, exist_ok=True)

def run_ping(src, dst_ip, count=20, interval=0.2):
    out = src.cmd(f'ping -c {count} -i {interval} -W 2 {dst_ip}')
    r = {'src': src.name, 'dst': dst_ip, 'sent': count,
         'loss_pct': 100.0, 'rtt_min': None, 'rtt_avg': None,
         'rtt_max': None, 'rtt_mdev': None}
    m = re.search(r'(\d+)% packet loss', out)
    if m: r['loss_pct'] = float(m.group(1))
    m = re.search(r'rtt min/avg/max/mdev = ([\d.]+)/([\d.]+)/([\d.]+)/([\d.]+)', out)
    if m:
        r['rtt_min'], r['rtt_avg'] = float(m.group(1)), float(m.group(2))
        r['rtt_max'], r['rtt_mdev'] = float(m.group(3)), float(m.group(4))
    return r, out

def run_iperf(server_host, client_host, duration=8, udp=False, bind_ip=None):
    srv_ip = bind_ip if bind_ip else server_host.IP()
    server_host.cmd(f'iperf -s {"-u" if udp else ""} -p 5201 &')
    time.sleep(0.8)
    if udp:
        out = client_host.cmd(f'iperf -c {srv_ip} -p 5201 -t {duration} -u -b 50M')
    else:
        out = client_host.cmd(f'iperf -c {srv_ip} -p 5201 -t {duration}')
    server_host.cmd('pkill -f "iperf -s" 2>/dev/null || true')
    r = {'src': client_host.name, 'dst': server_host.name,
         'mode': 'UDP' if udp else 'TCP',
         'bandwidth_mbps': None, 'jitter_ms': None, 'loss_pct': None}
    m = re.search(r'([\d.]+)\s+Mbits/sec', out)
    if m: r['bandwidth_mbps'] = float(m.group(1))
    if udp:
        m = re.search(r'([\d.]+)\s+ms\s+\d+/\d+\s+\(([\d.]+)%\)', out)
        if m: r['jitter_ms'], r['loss_pct'] = float(m.group(1)), float(m.group(2))
    return r, out

def run_traceroute(src, dst_ip):
    return src.cmd(f'traceroute -n -w 2 -q 1 {dst_ip}')

def full_test(net):
    ensure_dir()
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    report = {'timestamp': ts, 'ping_results': [], 'iperf_tcp': [],
              'iperf_udp': [], 'traceroutes': {}, 'nat_comparison': {}}
    h1, h3, ext = net.get('h1'), net.get('h3'), net.get('ext')
    web1, web2   = net.get('web1'), net.get('web2')
    fw           = net.get('fw')

    # [PRE-TEST] Mo tam thoi port iPerf (5201) tren Firewall de do luong
    print('\n[INFO] Mo port 5201 tren Firewall de do luong...')
    fw.cmd('iptables -I FORWARD -p tcp --dport 5201 -j ACCEPT')
    fw.cmd('iptables -I FORWARD -p udp --dport 5201 -j ACCEPT')

    # PING
    print('\n[1] PING TESTS')
    for src, dst, label in [
        (h1, '192.168.20.11', 'Inside-Inside h1->h3'),
        (h1, '10.10.10.11',   'Inside-DMZ h1->web1'),
        (ext,'100.0.0.11',    'Ext-StaticNAT->web1'),
    ]:
        print(f'  {label}...')
        r, raw = run_ping(src, dst, count=20)
        r['label'] = label
        report['ping_results'].append(r)
        print(f'    RTT avg={r["rtt_avg"]} ms | Loss={r["loss_pct"]}%')
        with open(f'{RESULTS_DIR}/ping_{label.replace(" ","_")}_{ts}.txt','w') as f: f.write(raw)

    # IPERF TCP
    print('\n[2] IPERF TCP')
    for srv, cli, sip, label in [
        (web1, h1, '10.10.10.11', 'Inside->web1 TCP'),
        (h1,   h3, None,          'Inside-Inside TCP'),
    ]:
        print(f'  {label}...')
        r, raw = run_iperf(srv, cli, duration=8, udp=False, bind_ip=sip)
        r['label'] = label; report['iperf_tcp'].append(r)
        print(f'    BW={r["bandwidth_mbps"]} Mbps')
        with open(f'{RESULTS_DIR}/iperf_tcp_{label.replace(" ","_")}_{ts}.txt','w') as f: f.write(raw)

    # IPERF UDP
    print('\n[3] IPERF UDP')
    for srv, cli, sip, label in [
        (web1, h1, '10.10.10.11', 'Inside->web1 UDP'),
        (h1,   h3, None,          'Inside-Inside UDP'),
    ]:
        print(f'  {label}...')
        r, raw = run_iperf(srv, cli, duration=8, udp=True, bind_ip=sip)
        r['label'] = label; report['iperf_udp'].append(r)
        print(f'    BW={r["bandwidth_mbps"]} | Jitter={r["jitter_ms"]} ms | Loss={r["loss_pct"]}%')
        with open(f'{RESULTS_DIR}/iperf_udp_{label.replace(" ","_")}_{ts}.txt','w') as f: f.write(raw)

    # TRACEROUTE
    print('\n[4] TRACEROUTE')
    for src, dst, label in [
        (h1, '10.10.10.11',  'h1_to_web1'),
        (h1, '192.168.20.11','h1_to_h3'),
        (ext,'100.0.0.11',   'ext_to_web1_NAT'),
    ]:
        print(f'  {label}...'); out = run_traceroute(src, dst)
        report['traceroutes'][label] = out; print(out)
        with open(f'{RESULTS_DIR}/traceroute_{label}_{ts}.txt','w') as f: f.write(out)

    # NAT vs NO-NAT comparison
    print('\n[5] SO SANH: Co NAT vs Khong NAT')
    r_nat, _ = run_ping(h1, '10.10.10.11', count=15)
    bw_nat, _ = run_iperf(web1, h1, duration=6, bind_ip='10.10.10.11')
    report['nat_comparison']['with_nat'] = {
        'rtt_avg': r_nat['rtt_avg'], 'loss_pct': r_nat['loss_pct'],
        'bandwidth_mbps': bw_nat['bandwidth_mbps']}
    print(f'  [Co NAT] RTT={r_nat["rtt_avg"]} ms | BW={bw_nat["bandwidth_mbps"]} Mbps')
    fw.cmd('iptables -t nat -F POSTROUTING 2>/dev/null')
    fw.cmd('iptables -P FORWARD ACCEPT')
    r_nn, _ = run_ping(h1, '10.10.10.11', count=15)
    bw_nn, _ = run_iperf(web1, h1, duration=6, bind_ip='10.10.10.11')
    report['nat_comparison']['without_nat'] = {
        'rtt_avg': r_nn['rtt_avg'], 'loss_pct': r_nn['loss_pct'],
        'bandwidth_mbps': bw_nn['bandwidth_mbps']}
    print(f'  [Ko NAT] RTT={r_nn["rtt_avg"]} ms | BW={bw_nn["bandwidth_mbps"]} Mbps')
    fw.cmd('iptables -t nat -A POSTROUTING -s 192.168.10.0/24 -o fw-eth0 -j MASQUERADE')
    fw.cmd('iptables -t nat -A POSTROUTING -s 192.168.20.0/24 -o fw-eth0 -j MASQUERADE')
    fw.cmd('iptables -P FORWARD DROP')

    # [POST-TEST] Dong port iPerf
    print('\n[INFO] Dong port 5201, khoi phuc trang thai bao mat...')
    fw.cmd('iptables -D FORWARD -p tcp --dport 5201 -j ACCEPT')
    fw.cmd('iptables -D FORWARD -p udp --dport 5201 -j ACCEPT')

    json_path = f'{RESULTS_DIR}/perf_report_{ts}.json'
    with open(json_path,'w',encoding='utf-8') as f: json.dump(report, f, indent=2, ensure_ascii=False)
    _print_summary(report)
    return report

def _print_summary(report):
    print('\n' + '='*65)
    print('  BANG THONG KE HIEU NANG – CAMPUS 3-TIER + DMZ')
    print('='*65)
    print(f'  Thoi gian: {report["timestamp"]}\n')
    print(f'  {"[PING]":<42} {"RTT Avg":>10} {"Loss":>8}')
    print('  ' + '-'*62)
    for r in report['ping_results']:
        rtt = f'{r["rtt_avg"]} ms' if r['rtt_avg'] else 'N/A'
        print(f'  {r.get("label",""):<42} {rtt:>10} {r["loss_pct"]:>7}%')
    print(f'\n  {"[IPERF TCP]":<42} {"Bandwidth":>14}')
    print('  ' + '-'*58)
    for r in report['iperf_tcp']:
        bw = f'{r["bandwidth_mbps"]} Mbps' if r['bandwidth_mbps'] else 'N/A'
        print(f'  {r.get("label",""):<42} {bw:>14}')
    cmp = report.get('nat_comparison', {})
    if cmp:
        print(f'\n  [SO SANH NAT]')
        for k, v in cmp.items():
            lbl = 'Co NAT' if k == 'with_nat' else 'Khong NAT'
            print(f'    {lbl}: RTT={v["rtt_avg"]} ms | BW={v["bandwidth_mbps"]} Mbps')
    print(f'\n  Chi tiet tai: results/')
    print('='*65)

if __name__ == '__main__':
    print('Chay tu Mininet CLI: py exec(open("scripts/performance_test.py").read(), globals()); full_test(net)')
