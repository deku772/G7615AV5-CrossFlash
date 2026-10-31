#!/usr/bin/env python3
"""通过 telnet 拉取设备上的文件（hexdump 传输，规避二进制/控制字符问题）。

设备 busybox 无 base64，只有 /usr/bin/hexdump，所以用 hexdump 转十六进制后本地还原。

用法:
    python pull_file.py <host> <user> <pass> <remote_path> <local_path>
"""
import socket
import sys
import time

sys.path.insert(0, __file__.rsplit('\\', 1)[0].rsplit('/', 1)[0])
from telnet_session import telnet_negotiate_skip


def main():
    host, user, pwd, remote, local = sys.argv[1:6]

    s = socket.create_connection((host, 23), timeout=10)
    s.settimeout(0.5)
    buf = bytearray()

    def read_until(token, timeout):
        end = time.time() + timeout
        while time.time() < end:
            try:
                d = s.recv(65536)
                if not d:
                    break
                buf.extend(telnet_negotiate_skip(d))
                if token in bytes(buf):
                    return True
            except socket.timeout:
                pass
        return False

    def send(line):
        s.sendall(line.encode() + b'\r\n')

    read_until(b'ogin', 10)
    send(user)
    read_until(b'assword', 10)
    send(pwd)
    read_until(b'/ # ', 12)
    buf.clear()

    # hexdump -v 去掉重复行；-e '1/1 "%02x"' 每字节输出连续 hex
    cmd = "hexdump -v -e '1/1 \"%02x\"' " + remote
    send(cmd)
    read_until(b'/ # ', 300)
    text = bytes(buf).decode('latin1', 'ignore')

    hex_chars = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith('hexdump'):
            continue
        if line.startswith('/ #'):
            break
        for ch in line:
            if ch in '0123456789abcdefABCDEF':
                hex_chars.append(ch)
            else:
                break

    hx = ''.join(hex_chars)
    if len(hx) % 2:
        hx = hx[:-1]
    raw = bytes.fromhex(hx)

    with open(local, 'wb') as f:
        f.write(raw)
    print('拉取 %s -> %s (%d bytes, hexchars=%d)' % (remote, local, len(raw), len(hx)))
    s.close()


if __name__ == '__main__':
    main()
