#!/usr/bin/env python3
"""
中兴光猫 telnet 自动化会话工具
适用于 ZXHN G7615AV5 / F7607P 等中兴系 GPON/XGPON 光猫 (busybox telnetd)

用法:
    python telnet_session.py <光猫IP> <用户名> <密码> [命令1] [命令2] ...

命令支持自定义等待时长（刷写类长命令必用）:
    python telnet_session.py 192.168.1.1 root Zte521 \
        "nand kerase /dev/mtd7 0x0 0x3000000@@240" \
        "nand kwrite /dev/mtd7 0x0 0x2aa0000 /upgtempfile/kernel.bin@@480"

    格式: "命令@@秒数"，默认 2.5 秒。
    长时间 nand 写入后 telnetd 可能回收会话，重新登录即可。

典型场景:
    1. ZTElnet26 / go_build_zte_go 等工厂模式工具开出临时账号后，
       用本脚本批量执行命令并抓取输出（Windows 自带 telnet.exe 无法自动化）。
    2. 备份分区、刷写固件、sendcmd 改库等全流程自动化。
"""
import socket, sys, time


def telnet_negotiate_skip(data: bytes) -> bytes:
    """剥离 telnet 协商序列 (IAC) 与 NUL，只留有效数据。"""
    out = bytearray()
    i = 0
    n = len(data)
    while i < n:
        b = data[i]
        if b == 0xFF and i + 1 < n:
            cmd = data[i + 1]
            if 0xFB <= cmd <= 0xFE:
                i += 3
            elif cmd == 0xFA:  # 子协商，跳到 IAC SE
                i += 2
                while i < n:
                    if data[i] == 0xFF and i + 1 < n and data[i + 1] == 0xF0:
                        i += 2
                        break
                    i += 1
            elif cmd == 0xFF:
                out.append(0xFF)
                i += 2
            else:
                i += 2
        elif b == 0x00:
            i += 1
        else:
            out.append(b)
            i += 1
    return bytes(out)


class TelnetSession:
    def __init__(self, host, port=23, timeout=10):
        self.sock = socket.create_connection((host, port), timeout=timeout)
        self.sock.settimeout(0.5)
        self.buf = bytearray()

    def read_for(self, seconds):
        """读取 seconds 秒内的数据；有数据流动时自动延长窗口。"""
        end = time.time() + seconds
        got = bytearray()
        while time.time() < end:
            try:
                data = self.sock.recv(8192)
                if data:
                    got += telnet_negotiate_skip(data)
                    end = max(end, time.time() + 0.8)
                else:
                    break  # EOF（设备重启等）
            except socket.timeout:
                pass
        self.buf += got
        return got.decode('utf-8', errors='replace')

    def wait_for(self, pattern, timeout):
        end = time.time() + timeout
        while time.time() < end:
            data = self.read_for(0.3)
            if pattern in data:
                return True
        return False

    def send_line(self, line):
        self.sock.sendall(line.encode() + b'\r\n')

    def close(self):
        try:
            self.sock.close()
        except Exception:
            pass


def main():
    host = sys.argv[1] if len(sys.argv) > 1 else '192.168.1.1'
    user = sys.argv[2]
    pwd = sys.argv[3]
    commands = sys.argv[4:]
    wait = 2.5
    if commands and commands[0].startswith('--wait='):
        wait = float(commands[0][7:])
        commands = commands[1:]

    sess = TelnetSession(host)
    try:
        ok_login = sess.wait_for('ogin', 10)
        print(f'[login-prompt] {ok_login}')
        sess.send_line(user)
        ok_pwd = sess.wait_for('assword', 10)
        print(f'[password-prompt] {ok_pwd}')
        sess.send_line(pwd)
        shell_ok = False
        end = time.time() + 12
        while time.time() < end:
            data = sess.read_for(0.5)
            if any(k in data for k in ('incorrect', 'failed', 'denied')):
                print('[AUTH FAILED]')
                sys.exit(2)
            if data.rstrip().endswith(('#', '>', '$')):
                shell_ok = True
                break
        print(f'[shell] {shell_ok}')
        if not shell_ok:
            sys.exit(2)
        for cmd in commands:
            w = wait
            if '@@' in cmd:
                cmd, wstr = cmd.rsplit('@@', 1)
                w = float(wstr)
            print(f'===== CMD: {cmd} (wait {w}s) =====')
            sess.send_line(cmd)
            print(sess.read_for(w))
        try:
            sess.send_line('exit')
            sess.read_for(0.5)
        except Exception:
            pass  # 重启后 socket 断开属预期
    finally:
        sess.close()
    print('===== SESSION DONE =====')


if __name__ == '__main__':
    main()
