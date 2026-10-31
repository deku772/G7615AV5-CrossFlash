# -*- coding: utf-8 -*-
"""打开 USB恢复配置页，列出 U 盘内可恢复的备份文件"""
import os, sys

for k in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy", "ALL_PROXY", "all_proxy"):
    os.environ.pop(k, None)
os.environ["NO_PROXY"] = "192.168.1.1,127.0.0.1,localhost"

from playwright.sync_api import sync_playwright

BASE = "http://192.168.1.1"
PWD = os.environ.get("ZTE_ADMIN_PASS", "nE%jA@5b")
OUT = sys.argv[1] if len(sys.argv) > 1 else ".temp/usbrestore_list.txt"
log = []


def w(s=""):
    log.append(str(s))
    print(s, flush=True)


JS_SELECT = """(function(){var o=[];
  document.querySelectorAll('select').forEach(function(s){
    o.push('SELECT id='+s.id+' name='+s.name+' | '+Array.prototype.map.call(s.options,function(x){return x.value+'|'+x.text;}).join(' ;; '));
  });
  return o.join('\\n') || '(no select)';})()"""

JS_BTN = """(function(){var o=[];
  document.querySelectorAll('input,button,a').forEach(function(e){
    var t=(e.value||e.innerText||'').trim();
    if(t) o.push(e.tagName+' id='+e.id+' name='+e.name+' txt='+t+' oc='+(e.getAttribute('onclick')||'').slice(0,60));});
  return o.join('\\n');})()"""

with sync_playwright() as p:
    br = p.chromium.launch(channel="msedge", headless=True, args=["--no-first-run"])
    pg = br.new_page(viewport={"width": 1500, "height": 1000})
    pg.goto(BASE + "/", wait_until="domcontentloaded", timeout=40000)
    pg.wait_for_timeout(1500)
    pg.evaluate("GetAccessAccount('adm')")
    pg.fill("#Frm_Password", PWD)
    pg.click("#LoginId")
    pg.wait_for_timeout(5000)
    if pg.evaluate("!!document.getElementById('Frm_Password')"):
        w("!! 登录失败")
        br.close(); sys.exit(1)
    w("[登录成功]")

    for i in range(30):
        if pg.frame(name="topFrame") and pg.frame(name="mainFrame"):
            break
        try:
            pg.click("#menu0", timeout=2000)
        except Exception:
            pass
        pg.wait_for_timeout(600)
        if i == 8:
            try:
                pg.goto(BASE + "/unicom.html", wait_until="domcontentloaded", timeout=15000)
            except Exception:
                pass
    pg.wait_for_timeout(2000)
    mf = pg.frame(name="mainFrame")
    if not mf:
        w("!! 无 mainFrame"); br.close(); sys.exit(1)

    mf.evaluate("location.href='/getpage.gch?pid=1002&nextpage=usbrestore_t.gch'")
    pg.wait_for_timeout(4000)
    f = pg.frame(name="mainFrame")
    w("URL: " + f.evaluate("location.href"))
    w("--- 正文 ---")
    w(f.inner_text("body")[:1500])
    w("--- select ---")
    w(f.evaluate(JS_SELECT))
    w("--- 控件 ---")
    w(f.evaluate(JS_BTN))
    br.close()

os.makedirs(os.path.dirname(OUT) or ".", exist_ok=True)
open(OUT, "w", encoding="utf-8").write("\n".join(log))
print("saved", OUT)
