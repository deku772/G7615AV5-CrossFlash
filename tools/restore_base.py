#!/usr/bin/env python3
"""方案 A：以运营商原厂完整备份为基底，只把必须先保留的项注入进去。

背景：
  之前「以当前配置为基底、按表补行」的注入方式，虽然数据字段正确，
  但设备内部的 WAN 索引/关联体系没有随之重建，导致 Web UI 里
  WAN 模式被判成 PPP、用户名读空、点确定报「当前操作无效」，
  既不能删除也不能修改。

  本脚本反过来做：基底换成 U 盘里的原厂完整配置（设备自己导出的，
  Web UI 100% 兼容），只覆盖以下必须保留的项：
    1. TelnetCfg        —— telnet 固化（Lan_Enable/账号/密码/连接数/超时/权限）
    2. DevAuthInfo      —— 超级管理员凭据
    3. WLANPSK          —— WiFi 密码
    4. WLANCfg          —— WiFi 开关 / SSID / 加密方式
    5. WLANBase         —— 射频参数（信道/功率等）
    6. PDTCTUSERINFO.UserName —— LOID

用法:
  python restore_base.py <host> <user> <pass> build
  python restore_base.py <host> <user> <pass> push
  python restore_base.py <host> <user> <pass> reboot
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import zte_cfg as Z
from inject_pppoe import Tel, TEMP, DEV_CFG, DEV_BAK, DEV_NEW, DEV_PTG

BASE_DEC = os.path.join(TEMP, 'usb_cfg.dec')          # 原厂完整备份（基底）
SRC_XML = os.path.join(TEMP, 'merged_user_cfg.xml')   # 当前设备配置（取值来源）
OUT_XML = os.path.join(TEMP, 'restore_base.xml')
OUT_BIN = os.path.join(TEMP, 'restore_base.bin')

# 整表替换（当前 → 基底）
TABLE_REPLACE = ['TelnetCfg', 'DevAuthInfo']
# 按 ViewName 逐行覆盖（当前 → 基底）
ROW_REPLACE = ['WLANPSK', 'WLANCfg', 'WLANBase']
# 字段级覆盖（PDTCTUSERINFO 的 LOID 是运行时状态，配置文件里没有该字段，不做注入）
FIELD_PATCH = []


def get_table(xml, tbl):
    m = re.search(r'(<Tbl name="%s"[^>]*RowCount=")(\d+)(">)(.*?)(</Tbl>)' % re.escape(tbl), xml, re.S)
    return m


def table_rows(seg):
    return [rm.group(0) for rm in re.finditer(r'<Row No="\d+">.*?</Row>', seg, re.S)]


def viewname_of(row):
    m = re.search(r'<DM name="ViewName" val="([^"]*)"/>', row)
    return m.group(1) if m else None


def dms(row):
    return re.findall(r'<DM name="([^"]*)" val="([^"]*)"/>', row)


def rebuild_table(xml, tbl, rows):
    m = get_table(xml, tbl)
    if not m:
        raise RuntimeError('基底缺少表: %s' % tbl)
    body = ''
    for i, r in enumerate(rows):
        r = re.sub(r'^<Row No="\d+">', '<Row No="%d">' % i, r, count=1)
        body += r.rstrip('\n') + '\n'
    seg = m.group(1) + str(len(rows)) + m.group(3) + '\n' + body + m.group(5)
    return xml[:m.start()] + seg + xml[m.end():]


def do_replace_table(base, src, tbl, report):
    ms, mb = get_table(src, tbl), get_table(base, tbl)
    if not ms or not mb:
        report.append((tbl, '-', '!! 表缺失，跳过'))
        return base
    srows = table_rows(ms.group(4))
    brows = table_rows(mb.group(4))
    report.append((tbl, '-', '整表替换: 基底 %d 行 -> 源 %d 行' % (len(brows), len(srows))))
    return rebuild_table(base, tbl, srows)


def do_row_replace(base, src, tbl, report):
    ms, mb = get_table(src, tbl), get_table(base, tbl)
    if not ms or not mb:
        report.append((tbl, '-', '!! 表缺失，跳过'))
        return base
    srows = table_rows(ms.group(4))
    brows = table_rows(mb.group(4))
    smap = {viewname_of(r): r for r in srows if viewname_of(r)}
    out, hit = [], 0
    for r in brows:
        vn = viewname_of(r)
        if vn and vn in smap:
            out.append(smap[vn])
            hit += 1
        else:
            out.append(r)
    # 源里独有的行（基底没有的 ViewName）追加
    bvn = set(filter(None, (viewname_of(r) for r in brows)))
    extra = [r for r in srows if viewname_of(r) and viewname_of(r) not in bvn]
    out.extend(extra)
    report.append((tbl, '-', '按 ViewName 覆盖 %d 行，追加 %d 行（基底 %d 行）'
                   % (hit, len(extra), len(brows))))
    return rebuild_table(base, tbl, out)


def do_field_patch(base, src, tbl, field, report):
    ms, mb = get_table(src, tbl), get_table(base, tbl)
    if not ms or not mb:
        report.append((tbl, field, '!! 表缺失，跳过'))
        return base
    srows = table_rows(ms.group(4))
    brows = table_rows(mb.group(4))
    smap = {viewname_of(r) or '#0': r for r in srows}
    out = []
    for r in brows:
        vn = viewname_of(r) or '#0'
        sr = smap.get(vn)
        if sr:
            sd = dict(dms(sr))
            if field in sd:
                val = sd[field]
                newr, n = re.subn(r'(<DM name="%s" val=")[^"]*(")' % re.escape(field),
                                  lambda m: m.group(1) + val + m.group(2), r)
                report.append((tbl, vn, '%s -> %r' % (field, val)))
                r = newr
        out.append(r)
    return rebuild_table(base, tbl, out)


def grab(xml, tbl, field, row_no=0):
    m = get_table(xml, tbl)
    if not m:
        return None
    rows = table_rows(m.group(4))
    if row_no >= len(rows):
        return None
    mm = re.search(r'<DM name="%s" val="([^"]*)"/>' % re.escape(field), rows[row_no])
    return mm.group(1) if mm else None


def main():
    host, user, pwd, phase = sys.argv[1:5]
    os.makedirs(TEMP, exist_ok=True)

    if phase == 'build':
        if not os.path.exists(SRC_XML):
            print('!! 缺少当前配置快照 %s（可先运行 inject_pppoe.py build 生成）' % SRC_XML)
            return 2
        base = open(BASE_DEC, encoding='latin1').read()
        src = open(SRC_XML, encoding='latin1').read()
        print('[load] 基底(原厂备份)=%d bytes, 源(当前配置)=%d bytes' % (len(base), len(src)))

        report = []
        x = base
        for t in TABLE_REPLACE:
            x = do_replace_table(x, src, t, report)
        for t in ROW_REPLACE:
            x = do_row_replace(x, src, t, report)
        for t, f in FIELD_PATCH:
            x = do_field_patch(x, src, t, f, report)

        print('[inject] 明细:')
        for t, v, msg in report:
            print('   %-16s %-24s %s' % (t, v, msg))

        # ---- 安全断言 ----
        for f, want in (('Lan_Enable', '1'), ('TSLan_UName', 'root'),
                        ('TSLan_UPwd', '12345'), ('Max_Con_Num', '999'),
                        ('ExitTime', '999'), ('InitSecLvl', '3')):
            got = grab(x, 'TelnetCfg', f)
            assert got == want, 'TelnetCfg.%s 期望 %s 实际 %s' % (f, want, got)
        print('[guard] TelnetCfg 固化 6 字段全部正确 ✔')

        # DevAuthInfo：必须有一个启用的超管(Level=2) 和一个启用的普通用户(Level=1)
        m = get_table(x, 'DevAuthInfo')
        auth = [dict(dms(r)) for r in table_rows(m.group(4))]
        en = [a for a in auth if a.get('Enable') == '1']
        print('[guard] DevAuthInfo 启用账号 (Level, User):',
              [(a.get('Level'), a.get('User')) for a in en])
        assert any(a.get('Level') == '2' for a in en), '缺少 Level=2 超级管理员'
        assert any(a.get('Level') == '1' for a in en), '缺少 Level=1 普通用户'

        # WiFi 密码必须与当前一致
        m2 = get_table(x, 'WLANPSK')
        psk = [dict(dms(r)).get('KeyPassphrase') for r in table_rows(m2.group(4))]
        print('[guard] WLANPSK 口令:', psk)

        loid = grab(x, 'PDTCTUSERINFO', 'UserName')
        print('[info] PDTCTUSERINFO.UserName =', loid, '（该字段不落盘，重启后需在网页重新注册 LOID）')

        # WAN 必须是原厂结构
        m3 = get_table(x, 'WANC')
        wanc = [dict(dms(r)) for r in table_rows(m3.group(4))]
        print('[guard] WANC 行数 = %d' % len(wanc))
        for w in wanc:
            print('        %-28s ViewName=%-22s Enable=%s ConnType=%s VLAN=%s IsDefGW=%s'
                  % (w.get('WANCName'), w.get('ViewName'), w.get('Enable'),
                     w.get('ConnType'), w.get('VLANID'), w.get('IsDefGW')))

        open(OUT_XML, 'w', encoding='utf-8').write(x)

        # 用设备 paramtag 派生密钥
        ptg_path = os.path.join(TEMP, 'paramtag.bin')
        if not os.path.exists(ptg_path):
            t = Tel(host, user, pwd)
            if not t.login():
                print('!! 登录失败')
                return 2
            open(ptg_path, 'wb').write(t.pull(DEV_PTG))
            t.close()
        ks, ivs, km = Z.key_from_paramtag(ptg_path)
        k, iv = Z.derive_key_iv(ks, ivs, km)
        enc = Z.encrypt_raw(Z.compress(x.encode('utf-8')), k, iv)
        d2, _ = Z.decrypt(enc, k, iv)
        assert Z.decompress(d2).decode('utf-8', 'replace') == x, '往返校验失败'
        open(OUT_BIN, 'wb').write(enc)
        print('[pack] enc=%d bytes，往返校验通过 -> %s' % (len(enc), OUT_BIN))
        return 0

    if phase == 'push':
        enc = open(OUT_BIN, 'rb').read()
        t = Tel(host, user, pwd)
        if not t.login():
            print('!! 登录失败')
            return 2
        print('[login ok]', flush=True)
        t.run('cp %s /tmp/db_user_cfg.xml.bak2' % DEV_CFG, 2)
        t.run('cp %s /tmp/db_backup_cfg.xml.bak2' % DEV_BAK, 2)
        print('[push] -> %s' % DEV_NEW, flush=True)
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
        print('[reboot] 已下发重启指令')
        return 0

    print('未知阶段')
    return 1


if __name__ == '__main__':
    sys.exit(main())
