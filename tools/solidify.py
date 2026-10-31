#!/usr/bin/env python3
"""一次性完成固化：push -> cp(两个文件) -> 校验 -> rreset。

★ 关键点：必须同时覆盖 db_user_cfg.xml 和 db_backup_cfg.xml，
  否则 sendcmd 1 DB rreset 会把备份复制回来，前面的修改被回滚。
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
        self.s = socket.create_connection((host, port), timeout=20)
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
        self.read_until(b'ogin', 15)
        self.send(self.user)
        self.read_until(b'assword', 15)
        self.send(self.pwd)
        ok = self.read_until(b'/ # ', 18)
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
        self.run('rm -f %s' % path, 1)
        esc = ''.join('\\x%02x' % b for b in data)
        n = len(esc)
        pos, first, idx = 0, True, 0
        total = (n + chunk - 1) // chunk
        while pos < n:
            piece = esc[pos:pos + chunk]
            pos += chunk
            self.run("printf '%s' %s %s" % (piece, '>' if first else '>>', path), 0.8)
            first = False
            idx += 1
            if idx % 8 == 0:
                print('   ... %d/%d chunks' % (idx, total), flush=True)
        return self.run('md5sum %s' % path, 2)

    def close(self):
        try:
            self.s.close()
        except Exception:
            pass


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


def patch_xml(xml_text, changes):
    out = xml_text
    for tbl, fields in changes.items():
        m = Z.re.search(r'(<Tbl name="%s" RowCount="\d+">.*?</Tbl>)' % Z.re.escape(tbl), out, Z.re.S)
        if not m:
            print('  !! 表 %s 未找到' % tbl)
            continue
        seg = m.group(1)
        rs, re_ = seg.find('<Row'), seg.find('</Row>')
        head, row, tail = seg[:rs], seg[rs:re_], seg[re_:]
        newrow = row
        for f, v in fields.items():
            pat = Z.re.compile(r'(<DM name="%s" val=")[^"]*(")' % Z.re.escape(f))
            if pat.search(newrow):
                newrow = pat.sub(lambda mm: mm.group(1) + str(v) + mm.group(2), newrow, count=1)
            else:
                print('  !! 字段 %s.%s 不存在' % (tbl, f))
        out = out[:m.start(1)] + (head + newrow + tail) + out[m.end(1):]
    return out


def main():
    host, user, pwd = sys.argv[1:4]
    t = Tel(host, user, pwd)
    if not t.login():
        print('!! 登录失败')
        return 2
    print('[1] telnet 登录成功', flush=True)

    ptg = t.pull(DEV_PTG)
    ptg_path = os.path.join(LOCAL_DIR, 'paramtag.bin')
    open(ptg_path, 'wb').write(ptg)
    cur = t.pull(DEV_CFG)
    open(os.path.join(LOCAL_DIR, 'db_user_cfg.xml.orig'), 'wb').write(cur)
    print('[2] 读取当前配置 %d bytes' % len(cur), flush=True)

    ks, ivs, km = Z.key_from_paramtag(ptg_path)
    k, iv = Z.derive_key_iv(ks, ivs, km)
    dec, _ = Z.decrypt(cur, k, iv)
    plain = Z.decompress(dec).decode('utf-8', 'replace')
    print('[3] 解密成功 XML %d bytes' % len(plain), flush=True)

    newxml = patch_xml(plain, CHANGES)
    if newxml == plain:
        print('!! 无改动')
        t.close()
        return 3
    enc = Z.encrypt_raw(Z.compress(newxml.encode('utf-8')), k, iv)
    d2, _ = Z.decrypt(enc, k, iv)
    assert Z.decompress(d2).decode('utf-8', 'replace') == newxml
    print('[4] 打包 %d bytes, 往返校验通过' % len(enc), flush=True)

    print('[5] push -> %s' % DEV_NEW, flush=True)
    print('   ', t.push(enc, DEV_NEW).strip()[:120], flush=True)

    print('[6] cp 到两个文件', flush=True)
    t.run('cp %s %s' % (DEV_NEW, DEV_CFG), 3)
    t.run('cp %s %s' % (DEV_NEW, DEV_BAK), 3)
    chk = t.run('md5sum %s %s' % (DEV_CFG, DEV_BAK), 3)
    print(chk.strip()[:400], flush=True)

    import hashlib
    want = hashlib.md5(enc).hexdigest()
    ok = chk.count(want) == 2
    print('[7] MD5 校验: 期望 %s 出现2次 -> %s' % (want, 'OK' if ok else 'FAIL'), flush=True)
    if not ok:
        t.close()
        return 5

    print('[8] sendcmd 1 DB rreset (会断开会话)', flush=True)
    try:
        t.run('sendcmd 1 DB rreset', 10)
    except Exception as e:
        print('   会话断开(预期):', e, flush=True)
    t.close()
    print('[9] 完成', flush=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
