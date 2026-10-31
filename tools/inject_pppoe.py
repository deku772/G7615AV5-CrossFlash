#!/usr/bin/env python3
"""把 U 盘备份里的 PPPoE / IPTV 相关表行注入回设备当前配置。

背景：
  设备当前配置是从联通原厂备份里"删掉 PPPoE/IPTV 行"的状态，
  导致设备只有 2 条 TR069 WAN、没有业务连接、无法上网。
  本脚本以**设备实时配置**为基底（telnet 固化、超密、注册状态全部原样保留），
  按 ViewName 去重追加备份中缺失的行。

与 push_cfg2.py 的区别：
  push_cfg2 是"改字段"（单表单行），本脚本是"增行"（多表多行）。

用法:
  python inject_pppoe.py <host> <user> <pass> build   # 合并 + 加密 + 本地往返校验
  python inject_pppoe.py <host> <user> <pass> push    # 推送 + 覆盖双文件 + md5 校验
"""
import os
import re
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

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
TEMP = os.path.join(ROOT, '.temp')
BACKUP_DEC = os.path.join(TEMP, 'usb_cfg.dec')
OUT_XML = os.path.join(TEMP, 'merged_user_cfg.xml')
OUT_BIN = os.path.join(TEMP, 'merged_user_cfg.bin')
ORIG_XML = os.path.join(TEMP, 'merged_user_cfg.xml.orig')

# 需要从备份补齐的表（顺序即注入顺序）
TARGET_TABLES = [
    'WANCD',          # WCD3 / WCD4 设备
    'MultiWancd',     # WCD3(VLAN48) / WCD4(VLAN3185) 业务通道
    'WANCPPP',        # PPPoE 账号 clan2301317426 / 687708
    'WANCPPPComm',
    'WANCIP',
    'WANCIPOpts',
    'WANCIPOE',
    'WANC',           # 2_INTERNET_R_VID_48 / 3_IPTV_B_VID_3185
    'WANCServList',   # WAN→ServiceList 绑定
    'PDTWANCEXT',
    'MultiWancConfProduct',
    'PortBinding',    # WAN→LAN 口绑定
    'VLANBIND',
    'PrefixCfg',      # IPv6 PD 前缀绑定
    'DSSCfg',         # IPv6 PD 配发
    'E8OPT60S',
    'E8OPT125S',
    'L2BAvailIF',
    'MultiPortProduct',
    'IGMPWan',
    'IGMPProxy',
    'MLDWan',
    'LANDS',
    'DHCP6CComm',
    'DHCP6SPool',
    'DHCP6SHostCfg',
]

ROW_RE = re.compile(r'<Row No="(\d+)">(.*?)</Row>', re.S)

# 需要用备份值覆盖当前值的字段（同一张表、同一 ViewName 行的同名字段）。
# 只列业务相关且当前被改坏的；固化/超密/WiFi/注册态一律不动。
FIELD_PATCH = {
    # DNS 代理：当前是 AutoConfigured + 空上游（导致 LAN 侧 DNS 伪解析），
    # 备份是 Static + 联通/公共 DNS，恢复后客户端拿到的就是真 DNS。
    'DNSSettings': [
        'IPDNSConfigType', 'IPv6DNSConfigType',
        'SerIPAddress3', 'SerIPAddress4',
        'SerIPv6Address3', 'SerIPv6Address4',
    ],
}


def parse_tables(xml_text):
    """返回 {表名: [行文本, ...]}，行文本保留原始格式。"""
    out = {}
    for m in re.finditer(r'<Tbl name="([^"]+)" RowCount="(\d+)">(.*?)</Tbl>', xml_text, re.S):
        rows = [rm.group(0) for rm in ROW_RE.finditer(m.group(3))]
        out[m.group(1)] = rows
    return out


def viewname_of(row_text):
    m = re.search(r'<DM name="ViewName" val="([^"]*)"/>', row_text)
    return m.group(1) if m else None


def row_body(row_text):
    """行内的 DM 列表，用于整行比较。"""
    return re.findall(r'<DM name="([^"]*)" val="([^"]*)"/>', row_text)


def inject(cur_xml, back_xml):
    """把 back_xml 中 cur_xml 缺失的行追加进去。返回 (新 xml, 报告)。"""
    cur_tables = parse_tables(cur_xml)
    back_tables = parse_tables(back_xml)
    report = []

    for tbl in TARGET_TABLES:
        cur_rows = cur_tables.get(tbl)
        if cur_rows is None:
            continue
        back_rows = back_tables.get(tbl, [])
        if not back_rows:
            continue

        cur_vn = set(filter(None, (viewname_of(r) for r in cur_rows)))
        cur_body = set(tuple(row_body(r)) for r in cur_rows)

        add = []
        for r in back_rows:
            vn = viewname_of(r)
            if vn:
                if vn in cur_vn:
                    continue
            else:
                if tuple(row_body(r)) in cur_body:
                    continue
            add.append(r)

        if not add:
            continue

        # 定位表段并插入
        m = re.search(r'(<Tbl name="%s" RowCount=")(\d+)(">)(.*?)(</Tbl>)' % re.escape(tbl),
                      cur_xml, re.S)
        if not m:
            continue
        new_rows = cur_rows + add
        body = ''
        for i, r in enumerate(new_rows):
            body += re.sub(r'^<Row No="\d+">', '<Row No="%d">' % i, r, count=1) + '\n'
        seg = m.group(1) + str(len(new_rows)) + m.group(3) + '\n' + body + m.group(5)
        cur_xml = cur_xml[:m.start()] + seg + cur_xml[m.end():]
        cur_tables[tbl] = new_rows

        for r in add:
            vn = viewname_of(r)
            report.append((tbl, vn, {k: v for k, v in row_body(r) if v not in ('', '0', '-1')}))

    # ---- 字段级覆盖：把当前被改坏的业务字段恢复成备份值 ----
    cur_tables = parse_tables(cur_xml)
    back_tables = parse_tables(back_xml)
    for tbl, fields in FIELD_PATCH.items():
        cur_rows = cur_tables.get(tbl)
        back_rows = back_tables.get(tbl)
        if not cur_rows or not back_rows:
            continue
        back_by_vn = {viewname_of(r): dict(row_body(r)) for r in back_rows}
        new_rows = []
        for r in cur_rows:
            d = dict(row_body(r))
            vn = viewname_of(r)
            bd = back_by_vn.get(vn)
            if bd:
                for f in fields:
                    if f in bd and bd[f] != d.get(f):
                        report.append((tbl + '(覆盖)', vn, {f: '%s -> %s' % (d.get(f), bd[f])}))
                        d[f] = bd[f]
            # 重建行文本，保留原始字段顺序与换行风格
            body = ''.join('<DM name="%s" val="%s"/>\n' % (k, v) for k, v in d.items())
            new_rows.append('<Row No="%d">\n%s</Row>' % (len(new_rows), body))
        m = re.search(r'(<Tbl name="%s" RowCount=")(\d+)(">)(.*?)(</Tbl>)' % re.escape(tbl),
                      cur_xml, re.S)
        if not m:
            continue
        seg = m.group(1) + str(len(new_rows)) + m.group(3) + '\n' + '\n'.join(new_rows) + '\n' + m.group(5)
        cur_xml = cur_xml[:m.start()] + seg + cur_xml[m.end():]

    return cur_xml, report


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
        self.run('rm -f %s' % path, 1)
        esc = ''.join('\\x%02x' % b for b in data)
        n = len(esc)
        pos = 0
        first = True
        idx = 0
        total = (n + chunk - 1) // chunk
        while pos < n:
            piece = esc[pos:pos + chunk]
            pos += chunk
            redirect = '>' if first else '>>'
            self.run("printf '%s' %s %s" % (piece, redirect, path), 0.8)
            first = False
            idx += 1
            if idx % 5 == 0:
                print('   ... %d/%d chunks' % (idx, total), flush=True)
        return self.run('ls -l %s' % path, 2)

    def close(self):
        try:
            self.s.close()
        except Exception:
            pass


def main():
    host, user, pwd, phase = sys.argv[1:5]
    os.makedirs(TEMP, exist_ok=True)

    if phase == 'build':
        back_xml = open(BACKUP_DEC, encoding='latin1').read()
        t = Tel(host, user, pwd)
        if not t.login():
            print('!! 登录失败')
            return 2
        ptg = t.pull(DEV_PTG)
        ptg_path = os.path.join(TEMP, 'paramtag.bin')
        open(ptg_path, 'wb').write(ptg)
        cur = t.pull(DEV_CFG)
        open(ORIG_XML, 'wb').write(cur)
        t.close()
        print('[read] cfg=%d bytes' % len(cur), flush=True)

        ks, ivs, km = Z.key_from_paramtag(ptg_path)
        k, iv = Z.derive_key_iv(ks, ivs, km)
        dec, _ = Z.decrypt(cur, k, iv)
        plain = Z.decompress(dec).decode('utf-8', 'replace')
        print('[decrypt] xml=%d bytes' % len(plain), flush=True)

        merged, report = inject(plain, back_xml)
        print('[inject] 追加 %d 行:' % len(report), flush=True)
        for tbl, vn, d in report:
            print('   %-20s %-34s %s' % (tbl, vn, str(d)[:150]), flush=True)

        # 关键安全断言：固化与超密必须原样保留
        def grab(xml, tbl, field):
            m = re.search(r'<Tbl name="%s"[^>]*>(.*?)</Tbl>' % tbl, xml, re.S)
            if not m:
                return None
            mm = re.search(r'<DM name="%s" val="([^"]*)"/>' % field, m.group(1))
            return mm.group(1) if mm else None
        for f in ('Lan_Enable', 'TSLan_UName', 'TSLan_UPwd', 'Max_Con_Num', 'ExitTime', 'InitSecLvl'):
            a, b = grab(plain, 'TelnetCfg', f), grab(merged, 'TelnetCfg', f)
            assert a == b, 'TelnetCfg.%s 被改动: %s -> %s' % (f, a, b)
        for f in ('User', 'Pass', 'Level'):
            a = re.findall(r'<DM name="%s" val="([^"]*)"/>' % f,
                           re.search(r'<Tbl name="DevAuthInfo".*?</Tbl>', plain, re.S).group(0))
            b = re.findall(r'<DM name="%s" val="([^"]*)"/>' % f,
                           re.search(r'<Tbl name="DevAuthInfo".*?</Tbl>', merged, re.S).group(0))
            assert a == b, 'DevAuthInfo.%s 被改动' % f
        print('[guard] telnet 固化 + 超密均未被改动 ✔', flush=True)

        open(OUT_XML, 'w', encoding='utf-8').write(merged)
        enc = Z.encrypt_raw(Z.compress(merged.encode('utf-8')), k, iv)
        d2, _ = Z.decrypt(enc, k, iv)
        assert Z.decompress(d2).decode('utf-8', 'replace') == merged
        open(OUT_BIN, 'wb').write(enc)
        print('[pack] enc=%d bytes, 往返校验通过' % len(enc), flush=True)
        print('   -> %s' % OUT_BIN, flush=True)
        return 0

    if phase == 'push':
        enc = open(OUT_BIN, 'rb').read()
        t = Tel(host, user, pwd)
        if not t.login():
            print('!! 登录失败')
            return 2
        print('[login ok]', flush=True)
        # 设备端留一份原始文件保险
        t.run('cp %s /tmp/db_user_cfg.xml.bak' % DEV_CFG, 2)
        t.run('cp %s /tmp/db_backup_cfg.xml.bak' % DEV_BAK, 2)
        print('[push] -> %s' % DEV_NEW, flush=True)
        print(t.push(enc, DEV_NEW), flush=True)
        # ★ 必须同时覆盖两个文件，否则 RestoreFlag 机制会用 backup 盖回 user
        t.run('cp %s %s' % (DEV_NEW, DEV_CFG), 3)
        t.run('cp %s %s' % (DEV_NEW, DEV_BAK), 3)
        t.run('sync', 3)
        print(t.run('md5sum %s %s' % (DEV_CFG, DEV_BAK), 3), flush=True)
        print(t.run('ls -l /userconfig/cfg/', 2), flush=True)
        t.close()
        return 0

    print('未知阶段')
    return 1


if __name__ == '__main__':
    sys.exit(main())
