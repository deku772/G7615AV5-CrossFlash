#!/usr/bin/env python3
"""重启设备并在恢复后自动做端口绑定/上网自检。"""
import os
import socket
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from inject_pppoe import Tel

HOST, USER, PWD = '192.168.1.1', 'root', '12345'


def port_open(host, port, timeout=3):
    try:
        s = socket.create_connection((host, port), timeout=timeout)
        s.close()
        return True
    except Exception:
        return False


def main():
    print('[1] 下发 reboot', flush=True)
    try:
        t = Tel(HOST, USER, PWD)
        if t.login():
            t.run('reboot', 1)
            t.close()
            print('    reboot 已下发', flush=True)
    except Exception as e:
        print('    reboot 异常(正常):', str(e)[:60], flush=True)

    print('[2] 等待设备恢复 ...', flush=True)
    t0 = time.time()
    while time.time() - t0 < 300:
        if port_open(HOST, 23):
            time.sleep(6)
            print('    telnet 已恢复，用时 %.0fs' % (time.time() - t0), flush=True)
            break
        time.sleep(8)
    else:
        print('    !! 超时未恢复', flush=True)
        return 1

    print('[3] 自检', flush=True)
    t = Tel(HOST, USER, PWD)
    for i in range(6):
        if t.login():
            break
        print('    登录重试', i + 1, flush=True)
        time.sleep(8)
    else:
        print('    !! 登录失败', flush=True)
        return 1

    out = t.run('cat /proc/uptime', 3)
    print('    uptime:', out.strip().splitlines()[-2:], flush=True)

    for cmd in ('sendcmd 1 DB p PortBinding',
                'sendcmd 1 DB p MultiWancConfProduct',
                'sendcmd 1 DB p WANC',
                'ifconfig ppp0'):
        print('\n===== %s =====' % cmd, flush=True)
        print(t.run(cmd, 4), flush=True)
    t.close()
    print('\n[DONE]', flush=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
