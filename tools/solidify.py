#!/usr/bin/env python3
"""一次性完成固化：改配置文件 -> push -> cp(两个文件) -> 校验 -> rreset。

默认只改 TelnetCfg（telnet 常开）。可选一并处理：
  --admin 账号:密码      改 web 超级管理员（按 Level 定行，不认行号）
  --user  账号:密码      改 web 普通账号
  --tr069-off            关掉 TR-069 / ACS，防止插光纤后被运营商重新下发覆盖
  --reboot               写完后直接重启

★ 关键点：必须同时覆盖 db_user_cfg.xml 和 db_backup_cfg.xml，
  否则 rreset / 重启时备份会把修改回滚。

用法:
  python tools/solidify.py 192.168.1.1 <telnet用户> <telnet密码>
  python tools/solidify.py 192.168.1.1 root 12345 --admin cqadmin:cqunicom --user user:mypass --tr069-off --reboot
  python tools/solidify.py 192.168.1.1 root 12345 --admin a:b --dry-run
"""
import argparse
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


def _set_field(row, name, value):
    """改一行里的某个 DM 字段；字段不存在返回 None。"""
    pat = Z.re.compile(r'(<DM name="%s" val=")[^"]*(")' % Z.re.escape(name))
    if not pat.search(row):
        return None
    return pat.sub(lambda m: m.group(1) + str(value) + m.group(2), row, count=1)


def map_rows(xml_text, tbl, fn):
    """对表内每一行调用 fn(行号, 行XML) -> 新行XML，拼回原文。"""
    m = Z.re.search(r'(<Tbl name="%s" RowCount="\d+">)(.*?)(</Tbl>)'
                    % Z.re.escape(tbl), xml_text, Z.re.S)
    if not m:
        print('  !! 表 %s 未找到' % tbl)
        return xml_text
    body = m.group(2)
    out, last = [], 0
    for r in Z.re.finditer(r'<Row No="(\d+)">.*?</Row>', body, Z.re.S):
        out.append(body[last:r.start()])
        out.append(fn(r.group(1), r.group(0)))
        last = r.end()
    out.append(body[last:])
    return xml_text[:m.start(2)] + ''.join(out) + xml_text[m.end(2):]


def patch_web_accounts(xml_text, admin=None, user=None, admin_level=1):
    """按 Level 定位 web 账号行并改写，不认行号。

    admin/user 是 (用户名, 密码)。admin_level 指哪一级是超管：
    实机（联通 V3.0.5P1N4 / 重庆 306）验证 Level=1 = 管理维护账号、Level=2 = 普通账号。
    """
    if not (admin or user):
        return xml_text
    other = 2 if admin_level == 1 else 1
    hit = []

    def fn(no, row):
        lv = Z.re.search(r'<DM name="Level" val="(\d+)"/>', row)
        lvl = int(lv.group(1)) if lv else -1
        if lvl not in (admin_level, other):
            return row
        who, cred = ('超管', admin) if lvl == admin_level else ('普通', user)
        if not cred:
            return row
        u, p = cred
        old = Z.re.search(r'<DM name="User" val="([^"]*)"/>', row)
        hit.append('    Row%s Level=%d %s: %r -> %r / %r'
                   % (no, lvl, who, old.group(1) if old else '', u, p))
        row = _set_field(row, 'User', u) or row
        row = _set_field(row, 'Pass', p) or row
        row = _set_field(row, 'Enable', 1) or row
        return row

    out = map_rows(xml_text, 'DevAuthInfo', fn)
    for line in hit:
        print(line, flush=True)
    if not hit:
        print('  !! 没有找到 Level=%d/%d 的账号行，未改 web 密码' % (admin_level, other), flush=True)
    return out


def patch_tr069_off(xml_text):
    """关掉 TR-069：Tr069Enable=0 + 清 ACS 地址 + 停周期上报。"""
    def fn(no, row):
        if no != '0':
            return row
        for f, v in (('Tr069Enable', 0), ('PeriodicInformEnable', 0),
                     ('URL', ''), ('UDPConnectionRequestAddress', '')):
            row = _set_field(row, f, v) or row
        return row

    out = map_rows(xml_text, 'MgtServer', fn)
    print('    MgtServer Row0: Tr069Enable=0 / URL 清空', flush=True)
    return out


def _cred(s, what):
    if not s:
        return None
    if ':' not in s:
        raise SystemExit('%s 需要写成 账号:密码 的形式，例如 %s=CUAdmin:CUAdmin' % (what, what))
    u, p = s.split(':', 1)
    return (u, p)


def main():
    ap = argparse.ArgumentParser(description='G7615AV5 固化 + 改密 + 关 TR069')
    ap.add_argument('host')
    ap.add_argument('user')
    ap.add_argument('pwd')
    ap.add_argument('--admin', help='web 超管 账号:密码')
    ap.add_argument('--user', dest='web_user', help='web 普通账号 账号:密码')
    ap.add_argument('--admin-level', type=int, default=1, choices=(1, 2),
                    help='哪一级是超管，默认 1（本机实测；老固件可能是 2）')
    ap.add_argument('--tr069-off', action='store_true', help='关 TR-069 / ACS')
    ap.add_argument('--reboot', action='store_true', help='写完直接重启')
    ap.add_argument('--dry-run', action='store_true', help='只打印改动，不写设备')
    a = ap.parse_args()

    admin = _cred(a.admin, '--admin')
    web_user = _cred(a.web_user, '--user')

    t = Tel(a.host, a.user, a.pwd)
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
    newxml = patch_web_accounts(newxml, admin, web_user, a.admin_level)
    if a.tr069_off:
        newxml = patch_tr069_off(newxml)
    if newxml == plain:
        print('!! 无改动')
        t.close()
        return 3
    if a.dry_run:
        open(os.path.join(LOCAL_DIR, 'dryrun.xml'), 'w', encoding='utf-8').write(newxml)
        print('[dry-run] 已写出 .temp/dryrun.xml，未碰设备')
        t.close()
        return 0
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

    if a.reboot:
        print('[8] reboot（会断网 1~2 分钟）', flush=True)
        try:
            t.run('reboot', 5)
        except Exception as e:
            print('   会话断开(预期):', e, flush=True)
        t.close()
        print('[9] 已下发重启，等 60 秒后连 192.168.1.1:23 验证', flush=True)
        return 0

    print('[8] sendcmd 1 DB rreset (会断开会话)', flush=True)
    try:
        t.run('sendcmd 1 DB rreset', 10)
    except Exception as e:
        print('   会话断开(预期):', e, flush=True)
    t.close()
    print('[9] 完成（还没重启，配置需 reboot 后才算最终生效）', flush=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
