#!/usr/bin/env python3
"""分步把新配置写回设备（可分阶段执行，便于排错）。

阶段:
  push  - 生成加密配置并 printf 写入 /tmp/db_user_cfg.xml.new
  cp    - 覆盖 /userconfig/cfg/db_user_cfg.xml
  rreset- sendcmd 1 DB rreset 重载
  check - 读取校验

用法:
  python push_cfg2.py <host> <user> <pass> <phase>
"""
import os
import socket
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from telnet_session import telnet_negotiate_skip
import zte_cfg as Z

DEV_CFG = '/userconfig/cfg/db_user_cfg.xml'
DEV_BAK = '/userconfig/cfg/db_backup_cfg.xml'
DEV_NEW = '/tmp/db_user_cfg.xml.new'
DEV_PTG = '/tagparam/paramtag'
LOCAL_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '.temp'))


class Tel:
    def __init__(self, host, user, pwd, port=23):
        self.s = socket.create_connection((host, port), timeout=15)
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
        self.read_until(b'ogin', 12)
        self.send(self.user)
        self.read_until(b'assword', 12)
        self.send(self.pwd)
        ok = self.read_until(b'/ # ', 15)
        self.buf.clear()
        return ok

    def run(self, cmd, wait=2.0):
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

    def push(self, data, path, chunk=6000):
        """printf \\xNN 写入二进制。chunk 越大命令越少、越快。"""
        self.run('rm -f %s' % path, 1)
        esc = ''.join('\\x%02x' % b for b in data)
        n = len(esc)
        pos = 0
        first = True
        idx = 0
        while pos < n:
            piece = esc[pos:pos + chunk]
            pos += chunk
            redirect = '>' if first else '>>'
            self.run("printf '%s' %s %s" % (piece, redirect, path), 0.8)
            first = False
            idx += 1
            if idx % 5 == 0:
                print('   ... %d/%d chunks' % (idx, (n + chunk - 1) // chunk), flush=True)
        return self.run('ls -l %s' % path, 2)

    def close(self):
        try:
            self.s.close()
        except Exception:
            pass


def build_new_cfg():
    """拉当前配置 -> 解密 -> 打补丁 -> 重新打包 -> 返回加密字节。"""
    t = None
    return None


def patch_xml(xml_text, changes):
    out = xml_text
    for tbl, fields in changes.items():
        m = Z.re.search(r'(<Tbl name="%s" RowCount="\d+">.*?</Tbl>)' % Z.re.escape(tbl), out, Z.re.S)
        if not m:
            print('  !! 表 %s 未找到' % tbl)
            continue
        seg = m.group(1)
        rs, re_ = seg.find('<Row'), seg.find('</Row>')
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


CHANGES = {
    'TelnetCfg': {
        'Lan_Enable': 1,
        'TSLan_UName': 'root',
        'TSLan_UPwd': '12345',
        'Max_Con_Num': 999,
        'ExitTime': 999,
        'InitSecLvl': 3,
    },
}


def main():
    host, user, pwd, phase = sys.argv[1:5]
    t = Tel(host, user, pwd)
    if not t.login():
        print('!! 登录失败')
        return 2
    print('[login ok]', flush=True)

    if phase == 'push':
        ptg = t.pull(DEV_PTG)
        ptg_path = os.path.join(LOCAL_DIR, 'paramtag.bin')
        open(ptg_path, 'wb').write(ptg)
        cur = t.pull(DEV_CFG)
        open(os.path.join(LOCAL_DIR, 'db_user_cfg.xml.orig'), 'wb').write(cur)
        print('[read] cfg=%d bytes' % len(cur), flush=True)

        ks, ivs, km = Z.key_from_paramtag(ptg_path)
        k, iv = Z.derive_key_iv(ks, ivs, km)
        dec, _ = Z.decrypt(cur, k, iv)
        plain = Z.decompress(dec).decode('utf-8', 'replace')
        print('[decrypt] xml=%d bytes' % len(plain), flush=True)

        newxml = patch_xml(plain, CHANGES)
        if newxml == plain:
            print('!! 无改动')
            t.close()
            return 3
        enc = Z.encrypt_raw(Z.compress(newxml.encode('utf-8')), k, iv)
        d2, _ = Z.decrypt(enc, k, iv)
        assert Z.decompress(d2).decode('utf-8', 'replace') == newxml
        print('[pack] enc=%d bytes, 往返校验通过' % len(enc), flush=True)
        open(os.path.join(LOCAL_DIR, 'db_user_cfg.xml.new'), 'wb').write(enc)

        print('[push] ->', DEV_NEW, flush=True)
        info = t.push(enc, DEV_NEW)
        print('[push done]', info.strip()[:200], flush=True)
        t.close()
        return 0

    if phase == 'cp':
        # ★ 关键：db_backup_cfg.xml 也必须一起覆盖。
        #   实测 sendcmd 1 DB rreset 会把 db_backup_cfg.xml 复制回 db_user_cfg.xml，
        #   只改 db_user_cfg.xml 会在 rreset 后被回滚（MD5 变回原值）。
        print(t.run('cp %s %s' % (DEV_NEW, DEV_CFG), 3), flush=True)
        print(t.run('cp %s %s' % (DEV_NEW, DEV_BAK), 3), flush=True)
        print(t.run('md5sum %s %s' % (DEV_CFG, DEV_BAK), 3), flush=True)
        t.close()
        return 0

    if phase == 'rreset':
        print(t.run('sendcmd 1 DB rreset', 10), flush=True)
        time.sleep(4)
        print(t.run('sendcmd 1 DB p TelnetCfg', 4), flush=True)
        t.close()
        return 0

    if phase == 'check':
        print(t.run('ls -l %s' % DEV_CFG, 2), flush=True)
        print(t.run('sendcmd 1 DB p TelnetCfg', 4), flush=True)
        t.close()
        return 0

    print('未知阶段')
    t.close()
    return 1


if __name__ == '__main__':
    sys.exit(main())
