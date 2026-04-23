#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
load_balancer.py
----------------
Script giam sat tai va can bang tai tu dong giua web1 va web2 trong DMZ.

Thuat toan:
  - Polling bandwidth tren web1 va web2 moi POLL_INTERVAL giay
  - Neu web1 load > UPPER_THRESH (80%) => chuyen luong moi sang web2
  - Neu web1 load < LOWER_THRESH (20%) => chuyen luong tro ve web1
  - Ghi log timestamp + bandwidth vao JSON va PNG (Matplotlib)

Chay tu Mininet CLI:
  py exec(open('scripts/load_balancer.py').read(), globals()); demo_load_balance(net)
"""

import os
import re
import time
import json
import subprocess
import threading
from datetime import datetime

try:
    import matplotlib
    matplotlib.use('Agg')   # Khong can display (Mininet env)
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False
    print('[WARN] matplotlib chua cai. Chi ghi log, khong ve bieu do.')
    print('       Chay: pip3 install matplotlib')

RESULTS_DIR  = 'results'
POLL_INTERVAL = 2.0    # giay
UPPER_THRESH  = 80.0   # %: nguong tren, chuyen sang backup
LOWER_THRESH  = 20.0   # %: nguong duoi, chuyen ve primary
MAX_BW_MBPS   = 100.0  # Mbps (bang thong WAN link)
IPERF_DURATION = POLL_INTERVAL - 0.5


# ---------------------------------------------------------------
def ensure_dir():
    os.makedirs(RESULTS_DIR, exist_ok=True)


def _measure_bw(host, server_ip, port=5201, duration=1.5):
    """
    Chay iperf TCP trong thoi gian ngan de do bandwidth.
    Tra ve Mbps hoac 0 neu that bai.
    """
    out = host.cmd(
        f'iperf -c {server_ip} -p {port} -t {duration:.0f} -f m 2>/dev/null'
    )
    m = re.search(r'([\d.]+)\s+Mbits/sec', out)
    if m:
        return float(m.group(1))
    return 0.0


def _redirect_to(fw, target_ip):
    """
    Thay doi DNAT rule cua fw-router de huong external traffic vao target_ip.
    Chi gia lap bang cach thay doi DNAT cho 100.0.0.11.
    """
    fw.cmd('iptables -t nat -D PREROUTING -d 100.0.0.11 -j DNAT --to-destination 10.10.10.11 2>/dev/null || true')
    fw.cmd('iptables -t nat -D PREROUTING -d 100.0.0.11 -j DNAT --to-destination 10.10.10.12 2>/dev/null || true')
    fw.cmd(f'iptables -t nat -A PREROUTING -d 100.0.0.11 -j DNAT --to-destination {target_ip}')


# ---------------------------------------------------------------
def demo_load_balance(net, cycles=15):
    """
    Demo can bang tai trong <cycles> chu ky poll.
    Gia lap tai bang cach chay iperf tu h1 den web1/web2.
    """
    ensure_dir()
    timestamp   = datetime.now().strftime('%Y%m%d_%H%M%S')
    log         = []
    current_srv = 'web1'   # Primary server ban dau
    fw          = net.get('fw')
    h1          = net.get('h1')
    h3          = net.get('h3')
    web1        = net.get('web1')
    web2        = net.get('web2')

    # Bat iperf server tren ca 2
    web1.cmd('pkill -f "iperf -s" 2>/dev/null; iperf -s -p 5201 &')
    web2.cmd('pkill -f "iperf -s" 2>/dev/null; iperf -s -p 5201 &')
    time.sleep(0.5)

    print('\n' + '='*65)
    print('  CAN BANG TAI THEO NGUONG – GIAM SAT REAL-TIME')
    print(f'  Nguong tren: {UPPER_THRESH}% | Nguong duoi: {LOWER_THRESH}%')
    print(f'  Chu ky poll: {POLL_INTERVAL}s | Toi da: {MAX_BW_MBPS} Mbps')
    print('='*65)
    print(f'  {"Chu ky":<7} {"Thoi gian":<12} {"web1 (Mbps)":<14} {"web2 (Mbps)":<14} {"Tai web1 %":<12} {"Server dang dung":<18} {"Hanh dong"}')
    print('  ' + '-'*90)

    # Gia lap phat sinh tai: h1 gui traffic den web1 ban dau
    _redirect_to(fw, web1.IP())
    # Phat sinh 1 luong tai lon vao web1 tu h3 (gia lap nhieu client)
    h3.cmd(f'iperf -c {web1.IP()} -p 5201 -t {int(cycles * POLL_INTERVAL + 5)} -b 70M &')
    time.sleep(0.3)

    for i in range(cycles):
        t_start = time.time()
        ts      = datetime.now().strftime('%H:%M:%S')

        # Do bandwidth tren web1 va web2
        bw1 = _measure_bw(h1, web1.IP(), duration=POLL_INTERVAL - 0.5)
        bw2 = _measure_bw(h1, web2.IP(), duration=POLL_INTERVAL - 0.5)
        load1_pct = min((bw1 / MAX_BW_MBPS) * 100.0, 100.0)
        action    = '-'

        # Logic chuyen luong theo nguong
        if load1_pct > UPPER_THRESH and current_srv == 'web1':
            _redirect_to(fw, web2.IP())
            current_srv = 'web2'
            action = '>> CHUYEN -> web2 (tai web1 > 80%)'
        elif load1_pct < LOWER_THRESH and current_srv == 'web2':
            _redirect_to(fw, web1.IP())
            current_srv = 'web1'
            action = '<< TRO VE web1 (tai web1 < 20%)'

        entry = {
            'cycle':      i + 1,
            'timestamp':  ts,
            'bw_web1':    round(bw1, 2),
            'bw_web2':    round(bw2, 2),
            'load1_pct':  round(load1_pct, 1),
            'active_srv': current_srv,
            'action':     action,
        }
        log.append(entry)

        print(f'  {i+1:<7} {ts:<12} {bw1:<14.2f} {bw2:<14.2f} {load1_pct:<12.1f} {current_srv:<18} {action}')

        # Giam tai sau chu ky thu 7 (gia lap giam tai)
        if i == 7:
            print('  [SIM] Giam tai gia lap (kill iperf thu 3)...')
            h3.cmd('pkill -f iperf 2>/dev/null || true')
            time.sleep(0.3)

        # Dam bao moi chu ky xap xi POLL_INTERVAL
        elapsed = time.time() - t_start
        if elapsed < POLL_INTERVAL:
            time.sleep(POLL_INTERVAL - elapsed)

    # Dung iperf
    h3.cmd('pkill -f iperf 2>/dev/null || true')
    web1.cmd('pkill -f "iperf -s" 2>/dev/null || true')
    web2.cmd('pkill -f "iperf -s" 2>/dev/null || true')

    print('\n' + '='*65)
    print('  KET QUA TONG HOP:')
    print(f'  Tong chu ky: {cycles}')
    actions = [e['action'] for e in log if e['action'] != '-']
    print(f'  Lan chuyen luong: {len(actions)}')
    for a in actions:
        print(f'    • {a}')
    print('='*65)

    # Luu JSON log
    json_path = os.path.join(RESULTS_DIR, f'lb_log_{timestamp}.json')
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(log, f, indent=2, ensure_ascii=False)
    print(f'\n[OK] Log luu tai: {json_path}')

    # Ve bieu do
    if HAS_MATPLOTLIB:
        _plot_lb(log, timestamp)
    else:
        print('[WARN] Khong ve duoc bieu do (matplotlib chua cai).')

    return log


# ---------------------------------------------------------------
def _plot_lb(log, timestamp):
    """Ve Line Chart thay doi bandwidth theo thoi gian."""
    cycles  = [e['cycle']    for e in log]
    bw1     = [e['bw_web1']  for e in log]
    bw2     = [e['bw_web2']  for e in log]
    load1   = [e['load1_pct'] for e in log]

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))
    fig.suptitle('Cân Bằng Tải Theo Ngưỡng – DMZ Servers\n'
                 f'Ngưỡng Trên: {UPPER_THRESH}% | Ngưỡng Dưới: {LOWER_THRESH}%',
                 fontsize=13, fontweight='bold')

    # Bieu do 1: Bandwidth Mbps
    ax1.plot(cycles, bw1, 'o-', color='#2196F3', linewidth=2,
             label='web1 (Primary)', markersize=5)
    ax1.plot(cycles, bw2, 's--', color='#FF9800', linewidth=2,
             label='web2 (Backup)', markersize=5)
    ax1.axhline(y=MAX_BW_MBPS * UPPER_THRESH / 100, color='red',
                linestyle=':', linewidth=1.5, label=f'Ngưỡng trên ({UPPER_THRESH}%)')
    ax1.axhline(y=MAX_BW_MBPS * LOWER_THRESH / 100, color='green',
                linestyle=':', linewidth=1.5, label=f'Ngưỡng dưới ({LOWER_THRESH}%)')
    ax1.set_xlabel('Chu kỳ')
    ax1.set_ylabel('Bandwidth (Mbps)')
    ax1.set_title('Băng thông trên từng Server DMZ theo thời gian')
    ax1.legend(loc='upper right')
    ax1.set_ylim(0, MAX_BW_MBPS * 1.1)
    ax1.grid(True, alpha=0.3)
    ax1.set_xticks(cycles)

    # Danh dau cac diem chuyen luong
    for e in log:
        if '>' in e['action'] or '<' in e['action']:
            ax1.axvline(x=e['cycle'], color='purple', linestyle='--', alpha=0.5)
            ax1.annotate('Switch', xy=(e['cycle'], bw1[e['cycle']-1]),
                         fontsize=7, color='purple', rotation=90,
                         xytext=(e['cycle']+0.1, bw1[e['cycle']-1]+2))

    # Bieu do 2: Phan tram tai web1
    ax2.fill_between(cycles, load1, alpha=0.3, color='#2196F3')
    ax2.plot(cycles, load1, 'o-', color='#2196F3', linewidth=2, markersize=5)
    ax2.axhline(y=UPPER_THRESH, color='red',   linestyle='--', linewidth=2,
                label=f'Ngưỡng trên ({UPPER_THRESH}%)')
    ax2.axhline(y=LOWER_THRESH, color='green', linestyle='--', linewidth=2,
                label=f'Ngưỡng dưới ({LOWER_THRESH}%)')
    ax2.set_xlabel('Chu kỳ')
    ax2.set_ylabel('Tải web1 (%)')
    ax2.set_title('Phần trăm tải trên web1 – Kích hoạt điều hướng khi vượt ngưỡng')
    ax2.legend(loc='upper right')
    ax2.set_ylim(0, 110)
    ax2.grid(True, alpha=0.3)
    ax2.set_xticks(cycles)

    plt.tight_layout()
    png_path = os.path.join(RESULTS_DIR, f'lb_chart_{timestamp}.png')
    plt.savefig(png_path, dpi=120, bbox_inches='tight')
    plt.close()
    print(f'[OK] Bieu do luu tai: {png_path}')


# ---------------------------------------------------------------
if __name__ == '__main__':
    print('[INFO] Chay script nay tu Mininet CLI:')
    print('  py exec(open("scripts/load_balancer.py").read(), globals()); demo_load_balance(net)')
