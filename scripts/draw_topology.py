#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
draw_topology.py
----------------
Ve so do topology mang Campus 3 lop + DMZ bang matplotlib.
Chay: python3 scripts/draw_topology.py
"""
import os, sys
try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
except ImportError:
    print('[ERROR] pip3 install matplotlib'); sys.exit(1)

RESULTS_DIR = 'docs'
os.makedirs(RESULTS_DIR, exist_ok=True)

def draw():
    fig, ax = plt.subplots(figsize=(16, 11))
    ax.set_xlim(0, 16); ax.set_ylim(0, 11)
    ax.axis('off')
    fig.patch.set_facecolor('#0D1B2A')
    ax.set_facecolor('#0D1B2A')

    # Color palette
    C = {
        'internet': '#E74C3C', 'fw':     '#E67E22', 'dmz':    '#8E44AD',
        'core':     '#2980B9', 'dist':   '#27AE60', 'access': '#16A085',
        'host':     '#2C3E50', 'server': '#6C3483', 'text':   'white',
        'link':     '#7F8C8D', 'warn':   '#F1C40F',
    }

    def box(x, y, w, h, color, label, sublabel='', fontsize=9):
        rect = FancyBboxPatch((x - w/2, y - h/2), w, h,
                               boxstyle='round,pad=0.08',
                               facecolor=color, edgecolor='white',
                               linewidth=1.2, zorder=3)
        ax.add_patch(rect)
        ax.text(x, y + (0.15 if sublabel else 0), label,
                ha='center', va='center', fontsize=fontsize,
                fontweight='bold', color='white', zorder=4)
        if sublabel:
            ax.text(x, y - 0.25, sublabel,
                    ha='center', va='center', fontsize=7,
                    color='#BDC3C7', zorder=4)

    def link(x1, y1, x2, y2, color='#7F8C8D', lw=1.5, label='', ls='-'):
        ax.plot([x1, x2], [y1, y2], color=color, linewidth=lw,
                linestyle=ls, zorder=2)
        if label:
            mx, my = (x1+x2)/2, (y1+y2)/2
            ax.text(mx + 0.1, my, label, fontsize=6.5,
                    color='#F1C40F', zorder=5, ha='left')

    def cloud(x, y, label, sublabel=''):
        circle = plt.Circle((x, y), 0.65, color=C['internet'],
                             alpha=0.9, zorder=3)
        ax.add_patch(circle)
        ax.text(x, y + (0.15 if sublabel else 0), label,
                ha='center', va='center', fontsize=8.5,
                fontweight='bold', color='white', zorder=4)
        if sublabel:
            ax.text(x, y - 0.25, sublabel,
                    ha='center', va='center', fontsize=6.5,
                    color='#FADBD8', zorder=4)

    # --- TITLE ---
    ax.text(8, 10.5,
            'Campus 3-Tier + DMZ  –  MMTNC Cuoi Ky  (MSSV: 52300267)',
            ha='center', va='center', fontsize=13, fontweight='bold',
            color='white', zorder=5)
    ax.text(8, 10.1,
            'OSPF  |  NAT/PAT  |  Static NAT  |  ACL  |  Firewall  |  Load Balancing',
            ha='center', va='center', fontsize=9, color='#BDC3C7', zorder=5)

    # --- INTERNET / EXTERNAL ---
    cloud(8, 9.3, 'INTERNET', '203.0.113.0/30')
    box(4.5, 9.3, 2.2, 0.7, C['internet'], 'ext', '203.0.113.1')
    link(4.5+1.1, 9.3, 8-0.65, 9.3, color='#E74C3C', lw=2, label='WAN 100M/10ms')

    # --- FIREWALL ---
    box(8, 7.9, 2.4, 0.75, C['fw'], 'fw-router (Firewall)',
        'fw-eth0: 203.0.113.2 | fw-eth1: 172.16.0.1\nfw-eth2: 10.10.10.1 (DMZ)')
    link(8, 9.3-0.65, 8, 7.9+0.375, color='#E67E22', lw=2.5,
         label='203.0.113.0/30')

    # ACL/NAT badge
    ax.text(9.5, 7.9, 'iptables\nNAT+ACL', ha='center', va='center',
            fontsize=7, color='#F1C40F',
            bbox=dict(boxstyle='round', facecolor='#1A252F', edgecolor='#F1C40F', lw=1))

    # --- DMZ ---
    box(11.5, 7.9, 1.8, 0.65, C['dmz'], 'dmz-sw', 'OVS Switch')
    link(8+1.2, 7.9, 11.5-0.9, 7.9, color='#8E44AD', lw=2, label='10.10.10.0/24')
    ax.text(11.5, 7.2, 'DMZ', ha='center', va='center', fontsize=10,
            fontweight='bold', color='#8E44AD')
    box(10.5, 6.3, 1.9, 0.65, C['server'], 'web1\n(Primary)', '10.10.10.11\n100.0.0.11 (Static NAT)', 8)
    box(12.5, 6.3, 1.9, 0.65, C['server'], 'web2\n(Backup)', '10.10.10.12\n100.0.0.12 (Static NAT)', 8)
    link(11.5, 7.9-0.325, 10.5, 6.3+0.325, color='#8E44AD', lw=1.8)
    link(11.5, 7.9-0.325, 12.5, 6.3+0.325, color='#8E44AD', lw=1.8)

    # LB arrow
    ax.annotate('', xy=(12.5, 6.6), xytext=(10.5, 6.6),
                arrowprops=dict(arrowstyle='<->', color='#F1C40F', lw=1.5))
    ax.text(11.5, 6.75, 'Load Balance\n>80% / <20%', ha='center', fontsize=6.5, color='#F1C40F')

    # --- CORE ---
    box(8, 6.5, 2.6, 0.75, C['core'], 'core-r (Core Layer)',
        '172.16.0.2 | 172.16.1.1 | 172.16.2.1\nOSPF Area 0 | Router-ID: 10.255.1.1')
    link(8, 7.9-0.375, 8, 6.5+0.375, color='#2980B9', lw=2.5,
         label='172.16.0.0/30')

    # --- DISTRIBUTION ---
    box(5.5, 5.0, 2.5, 0.7, C['dist'], 'dist1 (Distribution)',
        '172.16.1.2 | 192.168.10.1\nOSPF Area 0 | Router-ID: 10.255.1.2')
    box(10.5, 5.0, 2.5, 0.7, C['dist'], 'dist2 (Distribution)',
        '172.16.2.2 | 192.168.20.1\nOSPF Area 0 | Router-ID: 10.255.1.3')
    link(8-1.3, 6.5, 5.5+1.25, 5.0+0.35, color='#27AE60', lw=2, label='172.16.1.0/30')
    link(8+1.3, 6.5, 10.5-1.25, 5.0+0.35, color='#27AE60', lw=2, label='172.16.2.0/30')

    # --- ACCESS ---
    box(5.5, 3.5, 1.8, 0.6, C['access'], 'acc1', 'Access Switch 1')
    box(10.5, 3.5, 1.8, 0.6, C['access'], 'acc2', 'Access Switch 2')
    link(5.5, 5.0-0.35, 5.5, 3.5+0.3, color='#16A085', lw=1.8, label='100M/2ms')
    link(10.5, 5.0-0.35, 10.5, 3.5+0.3, color='#16A085', lw=1.8, label='100M/2ms')

    # --- HOSTS ---
    box(4.0, 2.2, 1.6, 0.6, C['host'], 'h1', '192.168.10.11')
    box(7.0, 2.2, 1.6, 0.6, C['host'], 'h2', '192.168.10.12')
    box(9.2, 2.2, 1.6, 0.6, C['host'], 'h3', '192.168.20.11')
    box(11.8, 2.2, 1.6, 0.6, C['host'], 'h4', '192.168.20.12')
    link(5.5-0.5, 3.5-0.3, 4.0+0.5, 2.2+0.3, color='#7F8C8D', lw=1.5)
    link(5.5+0.5, 3.5-0.3, 7.0-0.5, 2.2+0.3, color='#7F8C8D', lw=1.5)
    link(10.5-0.7, 3.5-0.3, 9.2+0.5, 2.2+0.3, color='#7F8C8D', lw=1.5)
    link(10.5+0.7, 3.5-0.3, 11.8-0.5, 2.2+0.3, color='#7F8C8D', lw=1.5)

    # --- SUBNET labels ---
    ax.text(5.5, 4.2, '192.168.10.0/24', ha='center', fontsize=7.5,
            color='#82E0AA',
            bbox=dict(boxstyle='round', facecolor='#1D3A27', edgecolor='#27AE60', lw=0.8))
    ax.text(10.5, 4.2, '192.168.20.0/24', ha='center', fontsize=7.5,
            color='#82E0AA',
            bbox=dict(boxstyle='round', facecolor='#1D3A27', edgecolor='#27AE60', lw=0.8))

    # --- LAYER labels (left side) ---
    layers = [
        (9.3, 'External / WAN',   '#E74C3C'),
        (7.9, 'Firewall + NAT',   '#E67E22'),
        (6.5, 'Core Layer',       '#2980B9'),
        (5.0, 'Distribution',     '#27AE60'),
        (3.5, 'Access Layer',     '#16A085'),
        (2.2, 'End Hosts (Inside)','#7F8C8D'),
    ]
    for y, label, color in layers:
        ax.text(1.0, y, label, ha='center', va='center', fontsize=8,
                color=color, fontweight='bold', rotation=0,
                bbox=dict(boxstyle='round', facecolor='#0D1B2A',
                          edgecolor=color, lw=1, alpha=0.7))

    # --- LEGEND ---
    legend_items = [
        mpatches.Patch(color=C['internet'], label='External/Internet'),
        mpatches.Patch(color=C['fw'],       label='Firewall Router'),
        mpatches.Patch(color=C['dmz'],      label='DMZ / Servers'),
        mpatches.Patch(color=C['core'],     label='Core Router (OSPF)'),
        mpatches.Patch(color=C['dist'],     label='Distribution Router'),
        mpatches.Patch(color=C['access'],   label='Access Switch'),
        mpatches.Patch(color=C['host'],     label='End Hosts (Inside)'),
    ]
    ax.legend(handles=legend_items, loc='lower left', fontsize=8,
              facecolor='#1A252F', edgecolor='white',
              labelcolor='white', framealpha=0.9)

    plt.tight_layout()
    out = os.path.join(RESULTS_DIR, 'network_topology.png')
    plt.savefig(out, dpi=140, bbox_inches='tight', facecolor=fig.get_facecolor())
    plt.close()
    print(f'[OK] Topology ve xong: {out}')
    return out

if __name__ == '__main__':
    draw()
