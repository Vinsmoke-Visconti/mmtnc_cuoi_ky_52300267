#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import time
from datetime import datetime

def get_session_dir():
    """
    Lay thu muc phien lam viec (session) hien tai. 
    Neu chua co hoac phien da qua 30 phut, tao moi thu muc: results/test_DDMMYYYY_HHMM
    """
    results_base = 'results'
    os.makedirs(results_base, exist_ok=True)
    session_file = os.path.join(results_base, '.latest_session')
    
    # Kiem tra xem co phien nao gan day khong (trong vong 30 phut)
    if os.path.exists(session_file):
        try:
            with open(session_file, 'r') as f:
                content = f.read().strip()
                if '|' in content:
                    path, ts = content.split('|')
                    if time.time() - float(ts) < 1800: # 30 phut
                        if os.path.exists(path):
                            return path
        except:
            pass

    # Tao phien moi
    now = datetime.now()
    # Dinh dang: test_29042026_1600
    folder_name = now.strftime('test_%d%m%Y_%H%M')
    session_dir = os.path.join(results_base, folder_name)
    os.makedirs(session_dir, exist_ok=True)
    
    # Luu lai phien moi nhat
    try:
        with open(session_file, 'w') as f:
            f.write(f"{session_dir}|{time.time()}")
    except:
        pass
        
    return session_dir
