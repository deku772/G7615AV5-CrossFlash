#!/usr/bin/env python3
"""等待光猫重启完成，并做一次全面体检。

检查项:
  1. telnet 23 端口恢复
  2. root/12345 能否登录（固化是否存活）
  3. TelnetCfg 固化字段
  4. WANC 表（PPPoE / IPTV 状态）
  5. 内核接口与 PPP 会话
  6. 默认路由 / 外网连通性
"""
import os
import socket
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from telnet_session import telnet_negotiate_skip

HOST = '192.168.1.1'
USER, PWD = 'root', '12345'


def wait_port(port=23, timeout=420):
    end = time.time() + timeout
    while time.time() < end:
        try:
            s = socket.create_connection((HOST, port), timeout=5)
            s.close()
            return True
        except Exception:
            time.sleep(5)
    return False


class Tel:
    def __init__(self):
        self.s = socket.create_connection((HOST, 23), timeout=15)
        self.s.settimeout(0.5)
        self.buf = bytearray()

    def read_until(self, token, timeout):
        end = time.time() + timeout
        while time.time() < end:
            try:
                d = self.s.recv(65536)
                if not d:
                    break
                self.buf.extend(telnet_negotiate_skip(d))
                if token in bytes(self.buf):
                    return True
            except socket.timeout:
                pass
        return False

    def run(self, cmd, wait=3.0):
        self.buf.clear()
        self.s.sendall(cmd.encode() + b'\r\n')
        time.sleep(wait)
        out = bytes(self.buf).decode('latin1', 'ignore')
        self.buf.clear()
        return out

    def login(self):
        self.read_until(b'ogin', 15)
        self.s.sendall(USER.encode() + b'\r\n')
        self.read_until(b'assword', 15)
        self.s.sendall(PWD.encode() + b'\r\n')
        return self.read_until(b'/ # ', 20)


def show(title, text, limit=2600):
    print('\n' + '=' * 18, title, '=' * 18, flush=True)
    print(text[:limit], flush=True)


def main():
    print('[wait] 等待 telnet 恢复...', flush=True)
    if not wait_port():
        print('!! 300s 内 telnet 未恢复')
        return 1
    print('[wait] 端口已开，等待服务就绪...', flush=True)
    time.sleep(12)

    t = Tel()
    if not t.login():
        print('!! root/12345 登录失败 —— 固化可能已丢失')
        return 2
    print('[login] root/12345 OK ✔', flush=True)

    show('TelnetCfg 固化字段', t.run('sendcmd 1 DB p TelnetCfg', 4))
    show('WANC 表', t.run('sendcmd 1 DB p WANC', 5), 4000)
    show('WANCPPP', t.run('sendcmd 1 DB p WANCPPP', 4))
    show('内核接口', t.run('ifconfig 2>/dev/null | head -60', 4), 3000)
    show('路由表', t.run('route -n 2>/dev/null || netstat -rn 2>/dev/null | head -20', 4), 1800)
    show('PPP 会话', t.run('cat /var/ppp/*.pid 2>/dev/null; ps | grep -i ppp | head -5', 4), 1200)
    show('外网连通性', t.run('ping -c 3 -W 3 114.114.114.114 2>&1 | tail -5', 12), 900)
    show('DNS 解析', t.run('nslookup www.10010.com 2>&1 | tail -8', 10), 900)
    show('注册状态', t.run('sendcmd 1 DB p PDTCTUSERINFO', 4), 2000)

    t.s.close()
    return 0


if __name__ == '__main__':
    sys.exit(main())
