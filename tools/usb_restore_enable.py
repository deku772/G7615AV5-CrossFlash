# -*- coding: utf-8 -*-
"""USB 恢复配置：dump 控件 / --enable 勾选启用并提交"""
import os, sys

for k in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy", "ALL_PROXY", "all_proxy"):
    os.environ.pop(k, None)
os.environ["NO_PROXY"] = "192.168.1.1,127.0.0.1,localhost"

from playwright.sync_api import sync_playwright

BASE = "http://192.168.1.1"
PWD = os.environ.get("ZTE_ADMIN_PASS", "nE%jA@5b")
DO_ENABLE = "--enable" in sys.argv

log = []
def w(s=""):
    log.append(str(s)); print(s, flush=True)

JS_INPUTS = r"""(function(){var o=[];
  document.querySelectorAll('input,select,button').forEach(function(e){
    o.push(e.tagName+' type='+(e.type||'')+' id='+e.id+' name='+e.name
      +' value='+String(e.value||'').slice(0,25)+' checked='+e.checked
      +' disabled='+e.disabled+' display='+getComputedStyle(e).display
      +' oc='+String(e.getAttribute('onclick')||'').slice(0,60));});
  return o.join('\n');})()"""

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
        w("!! 登录失败"); br.close(); sys.exit(1)
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
    mf.evaluate("location.href='/getpage.gch?pid=1002&nextpage=usbrestore_t.gch'")
    pg.wait_for_timeout(4000)
    f = pg.frame(name="mainFrame")
    w("URL: " + f.evaluate("location.href"))
    w(f.evaluate(JS_INPUTS))

    if DO_ENABLE:
        w("")
        w("=== 勾选 启用 + 提交 ===")
        try:
            f.check("#Frm_RstEnable", timeout=8000)
            w("[勾选] ok")
        except Exception as e:
            w("[勾选失败] " + str(e)[:120])
        w("[勾选后状态] " + f.evaluate(
            "(function(){var c=document.getElementById('Frm_RstEnable');"
            "return 'checked='+c.checked+' hidden='+document.getElementById('RstEnable').value;})()"))
        try:
            f.click("#Btn_Submit", timeout=8000)
            w("[提交] ok")
        except Exception as e:
            w("[提交失败] " + str(e)[:120])
        pg.wait_for_timeout(5000)
        f2 = pg.frame(name="mainFrame")
        try:
            w("--- 提交后页面 ---")
            w(f2.inner_text("body")[:900])
        except Exception as e:
            w("[读页面失败] " + str(e)[:80])
    br.close()

os.makedirs(".temp", exist_ok=True)
open(".temp/usbrestore_enable.txt", "w", encoding="utf-8").write("\n".join(log))
print("saved .temp/usbrestore_enable.txt")
