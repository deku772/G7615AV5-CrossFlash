# -*- coding: utf-8 -*-
"""尝试用 factorymode/nE%jA@5b 登录 web，并顺带枚举登录页的账号类型选项"""
import os, sys, re

for k in ('HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy', 'ALL_PROXY', 'all_proxy'):
    os.environ.pop(k, None)
os.environ['NO_PROXY'] = '192.168.1.1,127.0.0.1,localhost'

from playwright.sync_api import sync_playwright

OUT = sys.argv[1] if len(sys.argv) > 1 else '.temp/fac_login.txt'
lines = []
w = lines.append

with sync_playwright() as p:
    br = p.chromium.launch(channel='msedge', headless=True, args=['--no-first-run'])
    pg = br.new_page()
    pg.goto('http://192.168.1.1/', wait_until='domcontentloaded', timeout=30000)
    pg.wait_for_timeout(2000)

    # 枚举登录页所有 input/select
    w('=== 登录页表单元素 ===')
    w(pg.evaluate("""(function(){var o=[];
        document.querySelectorAll('input,select,button').forEach(function(e){
          o.push(e.tagName+' type='+(e.type||'')+' id='+(e.id||'')+' name='+(e.name||'')
                 +' value='+(e.value||'').slice(0,30)+' display='+(getComputedStyle(e).display));});
        return o.join('\\n');})()"""))

    # 找账号类型相关 JS
    w('')
    w('=== GetAccessAccount 相关 JS ===')
    js = pg.evaluate("""(function(){
        var s='';
        document.querySelectorAll('script').forEach(function(t){s+=t.textContent;});
        return s;})()""")
    for m in re.finditer(r'function\s+GetAccessAccount[^}]*\}', js):
        w(m.group(0)[:400])
    for name in ('Frm_UserName', 'Frm_AccountType', 'accountType'):
        hits = [l for l in js.split('\n') if name in l]
        for h in hits[:6]:
            w('JS> ' + h.strip()[:200])

    # 尝试1: adm 模式 + factorymode 用户名（若存在用户名输入框则填）
    w('')
    w('=== 尝试 factorymode 登录 ===')
    has_user = pg.evaluate('!!document.getElementById("Frm_UserName")')
    w('Frm_UserName 输入框存在: %s' % has_user)
    if has_user:
        pg.fill('#Frm_UserName', 'factorymode')
    pg.evaluate("GetAccessAccount('adm')")
    pg.fill('#Frm_Password', 'nE%jA@5b')
    pg.click('#LoginId')
    pg.wait_for_timeout(5000)
    still = pg.evaluate('!!document.getElementById("Frm_Password")')
    w('结果: %s' % ('✘ 仍停在登录页' if still else '✔ 登录成功'))
    if not still:
        w('URL: ' + pg.url)
        pg.wait_for_timeout(2000)
        pg.screenshot(path='.temp/fac_login_ok.png')
    else:
        html = pg.content()
        for pat in ('Lognumber', 'Status', 'Result'):
            m = re.search(r'var\s+%s\s*=\s*[^;]+' % pat, html)
            if m: w(m.group(0))
    br.close()

out = '\n'.join(lines)
print(out)
with open(OUT, 'w', encoding='utf-8') as f:
    f.write(out)
