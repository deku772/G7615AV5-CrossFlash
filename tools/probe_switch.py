# -*- coding: utf-8 -*-
"""dump 协议开关页（net_optimizing_switch_t.gch）等候选页面的控件"""
import os, sys

for k in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy", "ALL_PROXY", "all_proxy"):
    os.environ.pop(k, None)
os.environ["NO_PROXY"] = "192.168.1.1,127.0.0.1,localhost"

from playwright.sync_api import sync_playwright

BASE = "http://192.168.1.1"
PWD = os.environ.get("ZTE_ADMIN_PASS", "nE%jA@5b")
PAGES = [
    ("协议开关", "/getpage.gch?pid=1002&nextpage=net_optimizing_switch_t.gch"),
    ("强制推送配置", "/getpage.gch?pid=1002&nextpage=forcepushflg_t.gch"),
]

JS_INPUTS = r"""(function(){var o=[];
  document.querySelectorAll('input,select').forEach(function(e){
    if(e.type==='hidden') return;
    o.push(e.tagName+' type='+(e.type||'')+' id='+e.id+' name='+e.name
      +' value='+String(e.value||'').slice(0,25)+' checked='+e.checked);});
  return o.join('\n')||'(none)';})()"""

log = []
def w(s=""):
    log.append(str(s)); print(s, flush=True)

with sync_playwright() as p:
    br = p.chromium.launch(channel="msedge", headless=True, args=["--no-first-run"])
    pg = br.new_page(viewport={"width": 1500, "height": 1000})
    pg.goto(BASE + "/", wait_until="domcontentloaded", timeout=40000)
    pg.wait_for_timeout(1500)
    pg.evaluate("GetAccessAccount('adm')")
    pg.fill("#Frm_Password", PWD)
    pg.click("#LoginId")
    pg.wait_for_timeout(5000)
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

    for title, url in PAGES:
        w("")
        w("=" * 18 + " " + title + " " + "=" * 18)
        try:
            mf.evaluate("location.href='%s'" % url)
            pg.wait_for_timeout(3800)
            f = pg.frame(name="mainFrame")
            w("URL: " + f.evaluate("location.href"))
            w(f.inner_text("body")[:1400])
            w("--- 可见控件 ---")
            w(f.evaluate(JS_INPUTS))
        except Exception as e:
            w("[失败] " + str(e)[:120])
    br.close()

os.makedirs(".temp", exist_ok=True)
open(".temp/probe_switch.txt", "w", encoding="utf-8").write("\n".join(log))
print("saved .temp/probe_switch.txt")
