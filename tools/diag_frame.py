#!/usr/bin/env python3
"""登录后诊断：当前 URL / frame 列表 / body 摘要 / 截图。"""
import os
import sys

for k in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy", "ALL_PROXY", "all_proxy"):
    os.environ.pop(k, None)
os.environ["NO_PROXY"] = "192.168.1.1,127.0.0.1,localhost"
os.environ["no_proxy"] = os.environ["NO_PROXY"]

from playwright.sync_api import sync_playwright  # noqa: E402

BASE = "http://192.168.1.1"
PWD = os.environ.get("ZTE_ADMIN_PASS", "CUAdmin")
OUT = sys.argv[1] if len(sys.argv) > 1 else ".temp/diag_frame.txt"
log = []


def w(s=""):
    log.append(str(s))
    print(s, flush=True)


with sync_playwright() as p:
    browser = p.chromium.launch(channel="msedge", headless=False,
                                args=["--no-first-run", "--no-default-browser-check"])
    ctx = browser.new_context(viewport={"width": 1500, "height": 1000})
    page = ctx.new_page()
    page.goto(BASE + "/", wait_until="domcontentloaded", timeout=40000)
    page.wait_for_timeout(1500)
    w("pre-login url: " + page.url)
    if page.evaluate("!!document.getElementById('Frm_Password')"):
        page.evaluate("GetAccessAccount('adm')")
        page.fill("#Frm_Password", PWD)
        page.click("#LoginId")
        page.wait_for_timeout(5000)
    w("post-login url: " + page.url)
    w("frames: " + str([f.name for f in page.frames]))
    w("has #menu0: " + str(page.evaluate("!!document.getElementById('menu0')")))
    w("has Frm_Password: " + str(page.evaluate("!!document.getElementById('Frm_Password')")))
    w("--- a/area/onclick 概览 ---")
    w(page.evaluate("""(function(){
        var out=[];
        document.querySelectorAll('a,[onclick],area').forEach(function(e){
          if(out.length>40) return;
          out.push((e.tagName)+' | id='+(e.id||'')+' | txt='+(e.innerText||'').trim().slice(0,24)+' | oc='+(e.getAttribute('onclick')||'').slice(0,60));
        });
        return out.join('\\n');})()"""))
    w("--- body 摘要(前1200) ---")
    w(page.inner_text("body")[:1200])
    page.screenshot(path=".temp/diag_login.png", full_page=False)
    # 尝试点 menu0
    if page.evaluate("!!document.getElementById('menu0')"):
        page.click("#menu0")
        page.wait_for_timeout(3000)
        w("after menu0: frames=" + str([f.name for f in page.frames]) + " url=" + page.url)
        page.screenshot(path=".temp/diag_menu0.png", full_page=False)
    else:
        w("!! 无 menu0，尝试常见入口")
        for sel in ("#menu", "#mmStatu", "a:has-text('状态')", "text=状态"):
            try:
                page.click(sel, timeout=1500)
                page.wait_for_timeout(2500)
                w("click %s -> frames=%s" % (sel, [f.name for f in page.frames]))
                page.screenshot(path=".temp/diag_try.png")
                break
            except Exception as e:
                w("click %s 失败 %s" % (sel, str(e)[:80]))
    browser.close()

os.makedirs(os.path.dirname(OUT) or ".", exist_ok=True)
open(OUT, "w", encoding="utf-8").write("\n".join(log))
print("saved", OUT)
