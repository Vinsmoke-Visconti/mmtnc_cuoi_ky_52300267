#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
draw_topology_manual_guide.py
----------------------------
Tạo bản vẽ sơ đồ mạng chi tiết để hỗ trợ vẽ thủ công trên Draw.io.
Ghi rõ tên Interface, IP và vai trò thiết bị.
"""
import os, sys
try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    from matplotlib.patches import FancyBboxPatch
except ImportError:
    print('[ERROR] pip3 install matplotlib'); sys.exit(1)

RESULTS_DIR = 'docs'
os.makedirs(RESULTS_DIR, exist_ok=True)

def draw():
    # Sử dụng nền trắng để dễ nhìn khi vẽ lại
    fig, ax = plt.subplots(figsize=(18, 12))
    ax.set_xlim(0, 18); ax.set_ylim(0, 12)
    ax.axis('off')
    fig.patch.set_facecolor('white')
    ax.set_facecolor('white')

    # Bảng màu cho Draw.io (tương đương)
    C = {
        'internet': '#f8cecc', 'fw':     '#fff2cc', 'dmz':    '#e1d5e7',
        'core':     '#dae8fc', 'dist':   '#d5e8d4', 'access': '#f5f5f5',
        'host':     '#ffffff', 'server': '#e1d5e7', 'text':   'black',
        'link':     '#666666', 'warn':   '#ff0000',
    }

    def box(x, y, w, h, color, label, sublabel='', fontsize=10):
        rect = FancyBboxPatch((x - w/2, y - h/2), w, h,
                               boxstyle='round,pad=0.1',
                               facecolor=color, edgecolor='black',
                               linewidth=1.5, zorder=3)
        ax.add_patch(rect)
        ax.text(x, y + (0.2 if sublabel else 0), label,
                ha='center', va='center', fontsize=fontsize,
                fontweight='bold', color='black', zorder=4)
        if sublabel:
            ax.text(x, y - 0.2, sublabel,
                    ha='center', va='center', fontsize=8,
                    color='black', zorder=4)

    def link(x1, y1, x2, y2, label1='', label2='', midline_label='', color='#666666', lw=1.5, ls='-'):
        # Vẽ dây nối
        ax.plot([x1, x2], [y1, y2], color=color, linewidth=lw, linestyle=ls, zorder=2)
        
        # Nhãn ở đầu dây 1 (gần node 1)
        if label1:
            dx, dy = (x2-x1), (y2-y1)
            ax.text(x1 + dx*0.15, y1 + dy*0.15, label1, fontsize=8, color='blue', fontweight='bold', zorder=5)
        
        # Nhãn ở đầu dây 2 (gần node 2)
        if label2:
            dx, dy = (x1-x2), (y1-y2)
            ax.text(x2 + dx*0.15, y2 + dy*0.15, label2, fontsize=8, color='blue', fontweight='bold', zorder=5)
            
        # Nhãn ở giữa dây
        if midline_label:
            mx, my = (x1+x2)/2, (y1+y2)/2
            ax.text(mx, my + 0.1, midline_label, fontsize=8, color='red', ha='center', zorder=5)

    # --- TITLE ---
    ax.text(9, 11.5, 'SƠ ĐỒ HƯỚNG DẪN VẼ DRAW.IO - CAMPUS 3-TIER + DMZ', 
            ha='center', va='center', fontsize=16, fontweight='bold')
    ax.text(9, 11.1, '(Ghi chú: Xanh dương = Tên Interface | Đỏ = Subnet/Thông tin dây)', 
            ha='center', va='center', fontsize=10, color='gray')

    # --- TOPOLOGY ---
    
    # Internet / Ext
    box(4, 10, 2, 0.8, C['internet'], 'External (ext)', '203.0.113.1\nLinux Router')
    box(9, 11, 1.5, 0.6, C['internet'], 'Internet\nCloud')
    
    # Firewall
    box(9, 9, 2.8, 1.0, C['fw'], 'Firewall (fw)', 'Linux Router / Iptables\nRouter-ID: 10.255.1.10')
    
    # Links Ext -> FW
    link(4, 10, 9, 9, label1='ext-eth0', label2='fw-eth0', midline_label='203.0.113.0/30\n(WAN)')

    # DMZ Zone
    box(14, 9, 2, 0.7, C['dmz'], 'DMZ Switch (s1)', 'OVS Layer 2')
    link(9+1.4, 9, 14-1.0, 9, label1='fw-eth2 (.1)', label2='s1-port', midline_label='10.10.10.0/24')
    
    box(13, 7.5, 1.8, 0.8, C['server'], 'Web Server 1', '10.10.10.11\n(NAT: 100.0.0.11)')
    box(15.5, 7.5, 1.8, 0.8, C['server'], 'Web Server 2', '10.10.10.12\n(NAT: 100.0.0.12)')
    link(14, 9-0.35, 13, 7.5+0.4, label2='eth0')
    link(14, 9-0.35, 15.5, 7.5+0.4, label2='eth0')

    # Core Layer
    box(9, 7, 3, 1.0, C['core'], 'Core Router (core)', 'OSPF Area 0\nRouter-ID: 10.255.1.1')
    link(9, 9-0.5, 9, 7+0.5, label1='fw-eth1 (.1)', label2='core-eth0 (.2)', midline_label='172.16.0.0/30')

    # Distribution Layer
    box(6, 5, 2.5, 0.8, C['dist'], 'Dist Router 1', 'OSPF Area 0\nRouter-ID: 10.255.1.2')
    box(12, 5, 2.5, 0.8, C['dist'], 'Dist Router 2', 'OSPF Area 0\nRouter-ID: 10.255.1.3')
    
    link(9-0.5, 7-0.5, 6, 5+0.4, label1='core-eth1 (.1)', label2='dist1-eth0 (.2)', midline_label='172.16.1.0/30')
    link(9+0.5, 7-0.5, 12, 5+0.4, label1='core-eth2 (.1)', label2='dist2-eth0 (.2)', midline_label='172.16.2.0/30')
    
    # Redundant HA Link
    link(6+1.25, 5.2, 12-1.25, 5.2, label1='eth2 (.1)', label2='eth2 (.2)', 
         midline_label='172.16.3.0/30 (HA)', color='red', ls='--')

    # Access Layer
    box(6, 3, 2, 0.7, C['access'], 'Access SW 1 (s2)', 'OVS Layer 2')
    box(12, 3, 2, 0.7, C['access'], 'Access SW 2 (s3)', 'OVS Layer 2')
    
    link(6, 5-0.4, 6, 3+0.35, label1='dist1-eth1 (.1)', label2='s2-p1', midline_label='GW: 192.168.10.1')
    link(12, 5-0.4, 12, 3+0.35, label1='dist2-eth1 (.1)', label2='s3-p1', midline_label='GW: 192.168.20.1')

    # End Hosts
    box(5, 1.5, 1.2, 0.6, C['host'], 'h1', '192.168.10.11')
    box(7, 1.5, 1.2, 0.6, C['host'], 'h2', '192.168.10.12')
    box(11, 1.5, 1.2, 0.6, C['host'], 'h3', '192.168.20.11')
    box(13, 1.5, 1.2, 0.6, C['host'], 'h4', '192.168.20.12')
    
    link(6, 3-0.35, 5, 1.5+0.3)
    link(6, 3-0.35, 7, 1.5+0.3)
    link(12, 3-0.35, 11, 1.5+0.3)
    link(12, 3-0.35, 13, 1.5+0.3)

    # Legends / Annotations
    ax.text(1, 1, 'Ghi chú cho Draw.io:\n1. Router: Dùng icon Router (L3)\n2. Switch: Dùng icon Switch (L2)\n3. Firewall: Dùng icon Firewall (Brick Wall)\n4. Cloud: Dùng icon Cloud cho Internet', 
            fontsize=10, ha='left', va='bottom', bbox=dict(boxstyle='round', facecolor='#ffffcc', alpha=0.5))

    plt.tight_layout()
    out = os.path.join(RESULTS_DIR, 'network_topology_for_drawio.png')
    plt.savefig(out, dpi=150, bbox_inches='tight')
    plt.close()
    print(f'[OK] Sơ đồ hướng dẫn vẽ Draw.io đã tạo: {out}')
    return out

if __name__ == '__main__':
    draw()
