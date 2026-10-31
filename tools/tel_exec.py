#!/usr/bin/env python3
"""telnet 会话工具：登录并执行命令序列，输出完整回显。

用法: python tools/tel_exec.py <user> <pass> cmd1 [cmd2 ...]
"""
import os
import socket
import sys
import time

HOST = "192.168.1.1"


def run(user, pwd, cmds, wait_login=3.0, wait_cmd=2.5):
    s = socket.create_connection((HOST, 23), timeout=10)
    buf = b""

    def rd(t):
        nonlocal buf
        s.settimeout(t)
        try:
            while True:
                c = s.recv(4096)
                if not c:
                    return False
                buf += c
        except Exception:
            return True

    rd(wait_login)
    if b"ogin" not in buf:
        print("!! 未看到 Login 提示:", buf[-100:])
        return None
    s.sendall(user.encode() + b"\r\n")
    rd(2)
    s.sendall(pwd.encode() + b"\r\n")
    rd(4)
    if b"denied" in buf.lower():
        print("!! 登录被拒")
        print(buf.decode("latin1", "replace")[-300:])
        s.close()
        return None
    out = []
    for cmd in cmds:
        pre = len(buf)
        s.sendall(cmd.encode() + b"\r\n")
        rd(wait_cmd)
        out.append(("$ %s\n" % cmd) + buf[pre:].decode("latin1", "replace"))
    s.close()
    return "\n".join(out)


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print(__doc__)
        sys.exit(1)
    u, p = sys.argv[1], sys.argv[2]
    r = run(u, p, sys.argv[3:], wait_cmd=float(os.environ.get("TEL_WAIT", "2.5")))
    print(r)
