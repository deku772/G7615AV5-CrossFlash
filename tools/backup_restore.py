#!/usr/bin/env python3
"""光猫配置备份 / 恢复 / 校验（针对单线复用 VLAN 绑定配置）。

备份内容：
  db_user_cfg.xml       设备原始加密配置（可直接推回，字节级还原）
  db_user_cfg.xml.dec   解密后的明文 XML（可读、可 diff、可人工核对）
  paramtag.bin          设备密钥参数（恢复明文时用得上）
  summary.md            关键表摘要 + 恢复说明

用法:
  python backup_restore.py <host> <user> <pass> backup [outdir]
  python backup_restore.py <host> <user> <pass> restore <file> [--reboot]
  python backup_restore.py <host> <user> <pass> verify <file>

注意：restore 会把设备 /userconfig/cfg/ 下当前配置先备份到 /tmp/rollback_*.xml，
      再写入目标配置。带 --reboot 才会重启生效。
"""
import os
import sys
import time
import re

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import zte_cfg as Z
from inject_pppoe import Tel, DEV_CFG, DEV_BAK, DEV_NEW, DEV_PTG, TEMP


def _tables(xml, names):
    out = {}
    for tn in names:
        m = re.search(r'<Tbl name="%s"[^>]*RowCount="(\d+)"[^>]*>(.*?)</Tbl>' % tn, xml, re.S)
        if not m:
            out[tn] = None
            continue
        rows = []
        for rm in re.finditer(r'<Row No="(\d+)">(.*?)</Row>', m.group(2), re.S):
            rows.append(dict(re.findall(r'<DM name="([^"]*)" val="([^"]*)"/>', rm.group(2))))
        out[tn] = (int(m.group(1)), rows)
    return out


KEY_TABLES = ('WANC', 'PortBinding', 'MultiWancConfProduct', 'WAND', 'WANCD')


def decode(raw, ptg_path):
    ks, ivs, km = Z.key_from_paramtag(ptg_path)
    k, iv = Z.derive_key_iv(ks, ivs, km)
    plain, _ = Z.decrypt(raw, k, iv)
    return Z.decompress(plain).decode('utf-8', 'replace'), k, iv


def do_backup(host, user, pwd, outdir):
    os.makedirs(outdir, exist_ok=True)
    t = Tel(host, user, pwd)
    if not t.login():
        print('!! telnet 登录失败')
        return 2
    print('[pull] 拉取配置 ...', flush=True)
    raw = t.pull(DEV_CFG)
    print('[pull] 拉取 paramtag ...', flush=True)
    try:
        ptg = t.pull(DEV_PTG)
    except Exception as e:
        print('!! paramtag 拉取失败:', e)
        ptg = None
    t.close()

    enc_path = os.path.join(outdir, 'db_user_cfg.xml')
    open(enc_path, 'wb').write(raw)
    print('[save] %s (%d bytes)' % (enc_path, len(raw)))

    ptg_path = os.path.join(outdir, 'paramtag.bin')
    if ptg:
        open(ptg_path, 'wb').write(ptg)
        print('[save] %s (%d bytes)' % (ptg_path, len(ptg)))
    else:
        ptg_path = os.path.join(TEMP, 'paramtag.bin')
        if not os.path.exists(ptg_path):
            print('!! 无 paramtag，无法解密')
            return 3

    xml, _, _ = decode(raw, ptg_path)
    dec_path = enc_path + '.dec'
    open(dec_path, 'w', encoding='utf-8').write(xml)
    print('[save] %s (%d bytes)' % (dec_path, len(xml)))

    tb = _tables(xml, KEY_TABLES)
    lines = ['# 光猫配置备份', '',
             '- 备份时间：%s' % time.strftime('%Y-%m-%d %H:%M:%S'),
             '- 设备地址：%s' % host,
             '- 加密配置：`db_user_cfg.xml`（%d 字节，可直接推回设备）' % len(raw),
             '- 明文配置：`db_user_cfg.xml.dec`（%d 字节）' % len(xml), '',
             '## 关键表', '']

    if tb['WANC']:
        lines += ['### WANC（WAN 连接）', '', '| WAN 名称 | 模式 | VLAN | 服务 |',
                  '|---|---|---|---|']
        for d in tb['WANC'][1]:
            mode = {'1': 'Route 路由', '2': 'Bridge 桥接'}.get(d.get('ConnType'), d.get('ConnType'))
            lines.append('| %s | %s | %s | %s |' % (d.get('WANCName'), mode, d.get('VLANID'), d.get('StrServList')))
        lines.append('')

    for tn in ('PortBinding', 'MultiWancConfProduct'):
        if tb[tn] is None:
            lines += ['### %s' % tn, '', '（表不存在）', '']
            continue
        cnt, rows = tb[tn]
        lines += ['### %s（%d 行）' % (tn, cnt), '']
        if cnt == 0:
            lines.append('空表 —— 说明未使用端口绑定，全部走 VLAN 绑定（Trunk）')
        else:
            lines += ['| 序号 | 字段 |', '|---|---|']
            for i, d in enumerate(rows):
                ne = {k: v for k, v in d.items() if v not in ('', '0')}
                lines.append('| %d | `%s` |' % (i, ', '.join('%s=%s' % (k, v) for k, v in ne.items())))
        lines.append('')

    lines += ['## 恢复方法', '',
              '```bash',
              '# 推回配置（不重启）',
              'python tools/backup_restore.py 192.168.1.1 root 12345 restore %s' % enc_path,
              '',
              '# 推回并重启生效',
              'python tools/backup_restore.py 192.168.1.1 root 12345 restore %s --reboot' % enc_path,
              '```', '',
              '## 当前组网要点', '',
              '- LAN1 = Trunk：INTERNET 打 VLAN48 标签、IPTV 打 VLAN3185 标签',
              '- LAN2~LAN4 = 普通口，untagged 上网',
              '- IPTV 桥接 + 机顶盒 PPPoE 拨号（专网 IP 10.x）',
              '- **不要**在网页「端口绑定」页面保存，那会重建 PortBinding 并破坏 Trunk 配置',
              '']
    open(os.path.join(outdir, 'summary.md'), 'w', encoding='utf-8').write('\n'.join(lines))
    print('[save] %s' % os.path.join(outdir, 'summary.md'))

    print('\n=== 校验 ===')
    for tn in ('WANC', 'PortBinding', 'MultiWancConfProduct'):
        v = tb[tn]
        print('  %-22s %s' % (tn, '缺失' if v is None else '%d 行' % v[0]))
    print('\n备份完成：', os.path.abspath(outdir))
    return 0


def do_restore(host, user, pwd, path, reboot=False):
    if not os.path.exists(path):
        print('!! 文件不存在:', path)
        return 2
    raw = open(path, 'rb').read()

    if path.endswith('.dec'):
        ptg_path = os.path.join(os.path.dirname(os.path.abspath(path)), 'paramtag.bin')
        if not os.path.exists(ptg_path):
            print('!! 恢复明文需要同目录 paramtag.bin')
            return 3
        ks, ivs, km = Z.key_from_paramtag(ptg_path)
        k, iv = Z.derive_key_iv(ks, ivs, km)
        raw = Z.encrypt_raw(Z.compress(raw.encode('utf-8')), k, iv)
        back, _ = Z.decrypt(raw, k, iv)
        assert Z.decompress(back) == open(path, 'rb').read(), '重新加密往返校验失败'
        print('[pack] 明文重新加密完成（%d bytes）' % len(raw))

    t = Tel(host, user, pwd)
    if not t.login():
        print('!! telnet 登录失败')
        return 2
    stamp = time.strftime('%Y%m%d%H%M%S')
    print('[rollback] 现场配置 -> /tmp/rollback_%s.xml' % stamp, flush=True)
    t.run('cp %s /tmp/rollback_%s.xml' % (DEV_CFG, stamp), 2)
    t.run('cp %s /tmp/rollback_bak_%s.xml' % (DEV_BAK, stamp), 2)

    print('[push] 写入 %s' % DEV_NEW, flush=True)
    print(t.push(raw, DEV_NEW), flush=True)
    t.run('cp %s %s' % (DEV_NEW, DEV_CFG), 3)
    t.run('cp %s %s' % (DEV_NEW, DEV_BAK), 3)
    t.run('sync', 3)
    print(t.run('md5sum %s %s' % (DEV_CFG, DEV_BAK), 3), flush=True)
    if reboot:
        t.run('reboot', 1)
        print('[reboot] 已下发')
    t.close()
    return 0


def do_verify(host, user, pwd, path):
    if not os.path.exists(path):
        print('!! 文件不存在:', path)
        return 2
    raw = open(path, 'rb').read()
    if path.endswith('.dec'):
        xml = open(path, encoding='utf-8', errors='replace').read()
    else:
        ptg_path = os.path.join(os.path.dirname(os.path.abspath(path)), 'paramtag.bin')
        if not os.path.exists(ptg_path):
            ptg_path = os.path.join(TEMP, 'paramtag.bin')
        xml, _, _ = decode(raw, ptg_path)
    tb = _tables(xml, ('WANC', 'PortBinding', 'MultiWancConfProduct'))
    for tn in ('WANC', 'PortBinding', 'MultiWancConfProduct'):
        v = tb[tn]
        print('=== %s ===' % tn)
        if v is None:
            print('  缺失'); continue
        cnt, rows = v
        print('  RowCount=%d' % cnt)
        for d in rows:
            ne = {k: val for k, val in d.items() if val not in ('', '0')}
            print('   ', ne)
    return 0


def main():
    if len(sys.argv) < 5:
        print(__doc__)
        return 1
    host, user, pwd, action = sys.argv[1:5]
    if action == 'backup':
        outdir = sys.argv[5] if len(sys.argv) > 5 else os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '..', 'backups',
            time.strftime('%Y-%m-%d_%H%M'))
        return do_backup(host, user, pwd, outdir)
    if action == 'restore':
        if len(sys.argv) < 6:
            print('用法: ... restore <file> [--reboot]'); return 1
        return do_restore(host, user, pwd, sys.argv[5], '--reboot' in sys.argv)
    if action == 'verify':
        if len(sys.argv) < 6:
            print('用法: ... verify <file>'); return 1
        return do_verify(host, user, pwd, sys.argv[5])
    print('未知动作:', action)
    return 1


if __name__ == '__main__':
    sys.exit(main())
