#!/usr/bin/env python3
"""给 IPTV 桥接连接绑定 LAN1 / LAN2（单线复用用）。

背景：
  当前 IPTV(WCD4, VLAN3185 桥接) 只绑定了 WLAN4，没有任何 LAN 口。
  单线复用要求 IPTV tagged 帧和上网 untagged 帧共用同一根网线，
  因此需要把 IPTV 也绑到 LAN1、LAN2。

涉及两张表，必须同时改，否则网页显示与实际转发不一致：
  1. PortBinding                 —— 每行一条「WAN -> LAN」绑定
  2. MultiWancConfProduct.PortMask —— 端口位掩码（bit0=LAN1, bit1=LAN2,
                                     bit8=WLAN1, bit11=WLAN4, bit12=WLAN5）
     已由 INTERNET 行验证：4367 = bit0|1|2|3|8|12 -> LAN1~4 + WLAN1 + WLAN5

用法:
  python bind_lan_ports.py <host> <user> <pass> build
  python bind_lan_ports.py <host> <user> <pass> push
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import zte_cfg as Z
from inject_pppoe import Tel, TEMP, DEV_CFG, DEV_BAK, DEV_NEW, DEV_PTG

OUT_XML = os.path.join(TEMP, 'bind_lan.xml')
OUT_BIN = os.path.join(TEMP, 'bind_lan.bin')

IPTV_WAN = 'IGD.WD1.WCD4.WCIP1'          # IPTV 桥接 WAN
IPTV_WCD = 'IGD.WD1.WCD4'
IPTV_PORTS = ['IGD.LD1.ETH1', 'IGD.LD1.ETH2']
PORT_BIT = {'IGD.LD1.ETH1': 0, 'IGD.LD1.ETH2': 1, 'IGD.LD1.ETH3': 2,
            'IGD.LD1.ETH4': 3, 'IGD.LD1.WLAN1': 8, 'IGD.LD1.WLAN4': 11,
            'IGD.LD1.WLAN5': 12}


def get_table(xml, tbl):
    return re.search(r'(<Tbl name="%s"[^>]*RowCount=")(\d+)(">)(.*?)(</Tbl>)'
                     % re.escape(tbl), xml, re.S)


def table_rows(seg):
    return [m.group(0) for m in re.finditer(r'<Row No="\d+">.*?</Row>', seg, re.S)]


def rebuild_table(xml, tbl, rows):
    m = get_table(xml, tbl)
    if not m:
        raise RuntimeError('缺少表: %s' % tbl)
    body = ''
    for i, r in enumerate(rows):
        body += re.sub(r'^<Row No="\d+">', '<Row No="%d">' % i, r, count=1).rstrip('\n') + '\n'
    seg = m.group(1) + str(len(rows)) + m.group(3) + '\n' + body + m.group(5)
    return xml[:m.start()] + seg + xml[m.end():]


def dms(row):
    return dict(re.findall(r'<DM name="([^"]*)" val="([^"]*)"/>', row))


def set_dm(row, name, val):
    return re.sub(r'(<DM name="%s" val=")[^"]*(")' % re.escape(name),
                  lambda m: m.group(1) + val + m.group(2), row)


def dedupe_viewnames(rows, report):
    """PortBinding 里 ViewName 必须唯一，重复会让网页渲染错位。"""
    seen = set()
    fixed = []
    free = 1

    def next_free():
        nonlocal free
        while True:
            v = 'IGD.Binding%d' % free
            free += 1
            if v not in seen:
                return v

    out = []
    for r in rows:
        vn = dms(r).get('ViewName', '')
        if not vn or vn in seen:
            new = next_free()
            fixed.append('%s->%s' % (vn or '(空)', new))
            r = set_dm(r, 'ViewName', new)
            vn = new
        seen.add(vn)
        out.append(r)
    if fixed:
        report.append(('PortBinding', '改名', ', '.join(fixed)))
    return out


def patch_portbinding(xml, report):
    m = get_table(xml, 'PortBinding')
    if not m:
        raise RuntimeError('缺少 PortBinding 表')
    rows = table_rows(m.group(4))
    iptv_row = None
    for r in rows:
        d = dms(r)
        if d.get('WANViewName') == IPTV_WAN:
            iptv_row = r
            break
    if iptv_row is None:
        raise RuntimeError('PortBinding 里找不到 IPTV 行')

    have = set()
    used_vn = set()
    for r in rows:
        d = dms(r)
        used_vn.add(d.get('ViewName', ''))
        if d.get('WANViewName') == IPTV_WAN:
            have.add(d.get('LANViewName', ''))

    report.append(('PortBinding', '现状', 'IPTV 已绑: %s' % sorted(have)))

    # 先删掉不在目标列表里的 IPTV 绑定（例如 WLAN4）
    keep, dropped = [], []
    for r in rows:
        d = dms(r)
        if d.get('WANViewName') == IPTV_WAN and d.get('LANViewName') not in IPTV_PORTS:
            dropped.append(d.get('LANViewName'))
            continue
        keep.append(r)
    rows = keep
    if dropped:
        report.append(('PortBinding', '移除', 'IPTV 解绑 %s' % dropped))

    # 找空闲的 Binding 编号（现有 1,2,3,5,6,7,8，Binding4 空着）
    next_no = 1
    while ('IGD.Binding%d' % next_no) in used_vn:
        next_no += 1

    added = []
    for port in IPTV_PORTS:
        if port in have:
            continue
        new_row = set_dm(iptv_row, 'LANViewName', port)
        while ('IGD.Binding%d' % next_no) in used_vn:
            next_no += 1
        vn = 'IGD.Binding%d' % next_no
        new_row = set_dm(new_row, 'ViewName', vn)
        used_vn.add(vn)
        rows.append(new_row)
        added.append(port)

    rows = dedupe_viewnames(rows, report)

    if added or dropped:
        report.append(('PortBinding', '变更', '新增 %s / 移除 %s' % (added, dropped)))
    xml = rebuild_table(xml, 'PortBinding', rows)
    return xml


def patch_portmask(xml, report):
    m = get_table(xml, 'MultiWancConfProduct')
    if not m:
        raise RuntimeError('缺少 MultiWancConfProduct 表')
    rows = table_rows(m.group(4))
    pb = get_table(xml, 'PortBinding')
    iptv_ports = [dms(r).get('LANViewName') for r in table_rows(pb.group(4))
                  if dms(r).get('WANViewName') == IPTV_WAN]

    mask = 0
    for p in iptv_ports:
        mask |= 1 << PORT_BIT[p]

    old = None
    for i, r in enumerate(rows):
        d = dms(r)
        if d.get('WANCViewName') == IPTV_WAN:
            old = d.get('PortMask')
            rows[i] = set_dm(r, 'PortMask', str(mask))
            break
    if old is None:
        raise RuntimeError('MultiWancConfProduct 里找不到 IPTV 行')
    xml = rebuild_table(xml, 'MultiWancConfProduct', rows)
    report.append(('PortMask', 'IPTV', '%s -> %d (端口: %s)' % (old, mask, iptv_ports)))
    return xml


def verify(xml):
    pb = get_table(xml, 'PortBinding')
    rows = [dms(r) for r in table_rows(pb.group(4))]
    iptv = sorted({d['LANViewName'] for d in rows if d.get('WANViewName') == IPTV_WAN})
    inet = sorted({d['LANViewName'] for d in rows
                   if d.get('WANViewName') == 'IGD.WD1.WCD3.WCPPP1'})
    print('[guard] IPTV 绑定端口 :', iptv)
    print('[guard] INTERNET 绑定 :', inet)
    names = [d['ViewName'] for d in rows]
    print('[guard] ViewName: %s' % names)
    assert len(names) == len(set(names)), 'PortBinding ViewName 重复: %s' % names
    assert 'IGD.LD1.ETH1' in iptv, 'IPTV 未绑定 LAN1'
    assert 'IGD.LD1.ETH2' in iptv, 'IPTV 未绑定 LAN2'
    assert 'IGD.LD1.ETH1' in inet, 'INTERNET 丢失 LAN1 绑定'

    mc = get_table(xml, 'MultiWancConfProduct')
    for r in table_rows(mc.group(4)):
        d = dms(r)
        if d.get('WANCViewName') == IPTV_WAN:
            mask = int(d['PortMask'])
            print('[guard] IPTV PortMask = %d (bit0=%d bit1=%d bit11=%d)'
                  % (mask, mask & 1, (mask >> 1) & 1, (mask >> 11) & 1))
            assert mask & 1 and mask & 2, 'PortMask 未包含 LAN1/LAN2'
    return True


def main():
    host, user, pwd, phase = sys.argv[1:5]
    os.makedirs(TEMP, exist_ok=True)

    if phase == 'build':
        t = Tel(host, user, pwd)
        if not t.login():
            print('!! 登录失败')
            return 2
        print('[pull] 拉取当前配置 ...', flush=True)
        raw = t.pull(DEV_CFG)
        open(os.path.join(TEMP, 'bind_src.enc'), 'wb').write(raw)
        t.close()

        ks, ivs, km = Z.key_from_paramtag(os.path.join(TEMP, 'paramtag.bin'))
        k, iv = Z.derive_key_iv(ks, ivs, km)
        plain, _ = Z.decrypt(raw, k, iv)
        xml = Z.decompress(plain).decode('utf-8', 'replace')
        print('[load] 当前配置 %d bytes' % len(xml))

        report = []
        x = patch_portbinding(xml, report)
        x = patch_portmask(x, report)
        for a, b, c in report:
            print('   %-18s %-10s %s' % (a, b, c))

        verify(x)
        open(OUT_XML, 'w', encoding='utf-8').write(x)

        enc = Z.encrypt_raw(Z.compress(x.encode('utf-8')), k, iv)
        d2, _ = Z.decrypt(enc, k, iv)
        assert Z.decompress(d2).decode('utf-8', 'replace') == x, '往返校验失败'
        open(OUT_BIN, 'wb').write(enc)
        print('[pack] %d bytes，往返校验通过' % len(enc))
        return 0

    if phase == 'push':
        enc = open(OUT_BIN, 'rb').read()
        t = Tel(host, user, pwd)
        if not t.login():
            print('!! 登录失败')
            return 2
        print('[login ok]', flush=True)
        t.run('cp %s /tmp/db_user_cfg.bak3' % DEV_CFG, 2)
        t.run('cp %s /tmp/db_backup_cfg.bak3' % DEV_BAK, 2)
        print(t.push(enc, DEV_NEW), flush=True)
        t.run('cp %s %s' % (DEV_NEW, DEV_CFG), 3)
        t.run('cp %s %s' % (DEV_NEW, DEV_BAK), 3)
        t.run('sync', 3)
        print(t.run('md5sum %s %s' % (DEV_CFG, DEV_BAK), 3), flush=True)
        t.close()
        return 0

    if phase == 'reboot':
        t = Tel(host, user, pwd)
        if not t.login():
            print('!! 登录失败')
            return 2
        t.run('reboot', 1)
        t.close()
        print('[reboot] 已下发')
        return 0

    print('未知阶段')
    return 1


if __name__ == '__main__':
    sys.exit(main())
