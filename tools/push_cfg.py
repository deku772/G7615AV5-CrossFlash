#!/usr/bin/env python3
"""把修改后的 ZTE 配置写回光猫（db_user_cfg.xml ver4）。

设备无 base64，但 busybox printf 支持 \\xNN，故用 printf 转义串写二进制。

用法:
  python push_cfg.py <host> <user> <pass> [--apply] [--changes JSON]
"""
import json
import os
import socket
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from telnet_session import telnet_negotiate_skip
import zte_cfg as Z

DEV_CFG = '/userconfig/cfg/db_user_cfg.xml'
DEV_NEW = '/tmp/db_user_cfg.xml.new'
DEV_PTG = '/tagparam/paramtag'
LOCAL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '.temp')


class Tel:
    def __init__(self, host, user, pwd, port=23):
        self.s = socket.create_connection((host, port), timeout=10)
        self.s.settimeout(0.5)
        self.buf = bytearray()
        self.user, self.pwd = user, pwd

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

    def send(self, line):
        self.s.sendall(line.encode() + b'\r\n')

    def login(self):
        self.read_until(b'ogin', 10)
        self.send(self.user)
        self.read_until(b'assword', 10)
        self.send(self.pwd)
        ok = self.read_until(b'/ # ', 12)
        self.buf.clear()
        return ok

    def run(self, cmd, wait=3.0):
        self.buf.clear()
        self.send(cmd)
        time.sleep(wait)
        out = bytes(self.buf).decode('latin1', 'ignore')
        self.buf.clear()
        return out

    def pull(self, path, timeout=300):
        self.buf.clear()
        self.send("hexdump -v -e '1/1 \"%02x\"' " + path)
        self.read_until(b'/ # ', timeout)
        text = bytes(self.buf).decode('latin1', 'ignore')
        self.buf.clear()
        hexc = []
        for line in text.splitlines():
            line = line.strip()
            if not line or line.startswith('hexdump') or line.startswith('/ #'):
                continue
            for ch in line:
                if ch in '0123456789abcdefABCDEF':
                    hexc.append(ch)
                else:
                    break
        hx = ''.join(hexc)
        if len(hx) % 2:
            hx = hx[:-1]
        return bytes.fromhex(hx)

    def push(self, data, path, chunk=4000):
        """用 printf \\xNN 转义串写入二进制文件。"""
        self.run('rm -f %s' % path, 1)
        esc = ''.join('\\x%02x' % b for b in data)
        n = len(esc)
        pos = 0
        first = True
        while pos < n:
            piece = esc[pos:pos + chunk]
            pos += chunk
            redirect = '>' if first else '>>'
            self.run("printf '%s' %s %s" % (piece, redirect, path), 1.0)
            first = False
        out = self.run('ls -l %s' % path, 2)
        return out

    def close(self):
        try:
            self.s.close()
        except Exception:
            pass


def patch_xml(xml_text, changes):
    out = xml_text
    for tbl, fields in changes.items():
        m = Z.re.search(r'(<Tbl name="%s" RowCount="\d+">.*?</Tbl>)' % Z.re.escape(tbl), out, Z.re.S)
        if not m:
            print('  !! 表 %s 未找到' % tbl)
            continue
        seg = m.group(1)
        rs = seg.find('<Row')
        re_ = seg.find('</Row>')
        if rs < 0 or re_ < 0:
            continue
        head, row, tail = seg[:rs], seg[rs:re_], seg[re_:]
        newrow = row
        for f, v in fields.items():
            pat = Z.re.compile(r'(<DM name="%s" val=")[^"]*(")' % Z.re.escape(f))
            if pat.search(newrow):
                newrow = pat.sub(lambda mm: mm.group(1) + str(v) + mm.group(2), newrow, count=1)
            else:
                print('  !! 字段 %s.%s 不存在' % (tbl, f))
        newseg = head + newrow + tail
        out = out[:m.start(1)] + newseg + out[m.end(1):]
    return out


def main():
    if len(sys.argv) < 4:
        print(__doc__)
        return 1
    host, user, pwd = sys.argv[1:4]
    apply = '--apply' in sys.argv
    changes = {
        'TelnetCfg': {
            'Lan_Enable': 1,
            'TSLan_UName': 'root',
            'TSLan_UPwd': '12345',
            'Max_Con_Num': 999,
            'ExitTime': 999,
            'InitSecLvl': 3,
        },
    }
    for i, a in enumerate(sys.argv):
        if a == '--changes':
            changes = json.loads(sys.argv[i + 1])

    t = Tel(host, user, pwd)
    if not t.login():
        print('!! 登录失败')
        return 2
    print('[1] telnet 登录成功')

    ptg = t.pull(DEV_PTG)
    ptg_path = os.path.join(LOCAL_DIR, 'paramtag.bin')
    open(ptg_path, 'wb').write(ptg)
    print('[2] paramtag %d bytes' % len(ptg))

    cur = t.pull(DEV_CFG)
    bak = os.path.join(LOCAL_DIR, 'db_user_cfg.xml.orig')
    open(bak, 'wb').write(cur)
    print('[3] 当前配置 %d bytes, 已备份 -> %s' % (len(cur), bak))

    ks, ivs, km = Z.key_from_paramtag(ptg_path)
    k, iv = Z.derive_key_iv(ks, ivs, km)
    dec, _ = Z.decrypt(cur, k, iv)
    plain = Z.decompress(dec).decode('utf-8', 'replace')
    print('[4] 解密成功, XML %d bytes' % len(plain))

    newxml = patch_xml(plain, changes)
    if newxml == plain:
        print('!! 无改动, 中止')
        t.close()
        return 3

    newdec = Z.compress(newxml.encode('utf-8'))
    enc = Z.encrypt_raw(newdec, k, iv)
    # 往返校验
    d2, _ = Z.decrypt(enc, k, iv)
    if Z.decompress(d2).decode('utf-8', 'replace') != newxml:
        print('!! 往返校验失败, 中止')
        t.close()
        return 4
    print('[5] 重新打包 %d bytes, 往返校验通过' % len(enc))
    outp = os.path.join(LOCAL_DIR, 'db_user_cfg.xml.new')
    open(outp, 'wb').write(enc)

    if not apply:
        open(os.path.join(LOCAL_DIR, 'db_user_cfg.xml.dec'), 'w', encoding='utf-8', newline='').write(newxml)
        print('[!] 仅本地模式, 新配置 ->', outp)
        t.close()
        return 0

    print('[6] 写入设备 %s ...' % DEV_NEW)
    info = t.push(enc, DEV_NEW)
    print('   ', info.strip()[:200])
    print('[7] 覆盖 %s' % DEV_CFG)
    print(t.run('cp %s %s' % (DEV_NEW, DEV_CFG), 3).strip()[:300])
    print(t.run('ls -l %s' % DEV_CFG, 2).strip()[:200])
    print('[8] 重载数据库 sendcmd 1 DB rreset')
    print(t.run('sendcmd 1 DB rreset', 8).strip()[:300])
    time.sleep(3)
    print('[9] 校验 TelnetCfg')
    print(t.run('sendcmd 1 DB p TelnetCfg', 4).strip()[:1500])
    t.close()
    return 0


if __name__ == '__main__':
    sys.exit(main())
