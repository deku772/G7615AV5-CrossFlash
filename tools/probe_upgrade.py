#!/usr/bin/env python3
"""探测 web 版本升级页（只读）：是否有上传入口、当前主备分区版本。"""
import os
import sys

for k in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy", "ALL_PROXY", "all_proxy"):
    os.environ.pop(k, None)
os.environ["NO_PROXY"] = "192.168.1.1,127.0.0.1,localhost"
os.environ["no_proxy"] = os.environ["NO_PROXY"]

from playwright.sync_api import sync_playwright  # noqa: E402

BASE = "http://192.168.1.1"
PWD = os.environ.get("ZTE_ADMIN_PASS", "CUAdmin")
OUT = sys.argv[1] if len(sys.argv) > 1 else ".temp/probe_upgrade.txt"
log = []


def w(s=""):
    log.append(str(s))
    print(s, flush=True)


with sync_playwright() as p:
    br = p.chromium.launch(channel="msedge", headless=False,
                           args=["--no-first-run", "--no-default-browser-check"])
    ctx = br.new_context(viewport={"width": 1500, "height": 1000})
    pg = ctx.new_page()
    pg.goto(BASE + "/", wait_until="domcontentloaded", timeout=40000)
    pg.wait_for_timeout(1500)
    if pg.evaluate("!!document.getElementById('Frm_Password')"):
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
    top = pg.frame(name="topFrame")
    mf = pg.frame(name="mainFrame")
    w("frames=" + str([f.name for f in pg.frames]))

    # 列出 设备管理 下的二级菜单
    top.click("#mmManager")
    pg.wait_for_timeout(2200)
    w("--- 设备管理 二级菜单 ---")
    w(mf.evaluate("""(function(){var o=[];document.querySelectorAll('a,[onclick],td,li').forEach(function(e){
        var t=(e.innerText||'').trim(); if(t && t.length<20) o.push(t);}); return Array.from(new Set(o)).join(' | ');})()"""))

    # 直接访问升级页（用 JS 跳转，避免 frame detach）
    for url in ("/getpage.gch?pid=1001&hidden=upgrade",
                "/getpage.gch?pid=1002&nextpage=manager_upgrade_t.gch"):
        try:
            mf.evaluate("location.href='%s'" % url)
            got = None
            for i in range(24):
                pg.wait_for_timeout(500)
                f = pg.frame(name="mainFrame")
                if f is not None:
                    try:
                        if f.evaluate("document.readyState") in ("complete", "interactive"):
                            got = f
                            break
                    except Exception:
                        pass
            w("")
            w("### " + url)
            if got is None:
                w("!! mainFrame 未恢复")
                continue
            mf = got
            w("实际: " + mf.evaluate("location.href"))
            w(mf.inner_text("body")[:2000])
            w("--- 表单/输入 ---")
            w(mf.evaluate("""(function(){var o=[];
                document.querySelectorAll('input,form').forEach(function(e){
                  o.push(e.tagName+' type='+(e.type||'')+' id='+(e.id||'')+' name='+(e.name||'')+' accept='+(e.getAttribute('accept')||'')+' action='+(e.getAttribute('action')||''));});
                return o.join('\\n');})()"""))
            pg.screenshot(path=".temp/upgrade_%s.png" % url.replace("/", "_").replace("?", "_")[:40])
        except Exception as e:
            w("[%s 失败] %s" % (url, str(e)[:150]))
        try:
            pg.goto(BASE + "/", wait_until="domcontentloaded", timeout=20000)
            pg.wait_for_timeout(1500)
            for i in range(25):
                if pg.frame(name="topFrame") and pg.frame(name="mainFrame"):
                    break
                try:
                    pg.click("#menu0", timeout=1500)
                except Exception:
                    pass
                pg.wait_for_timeout(500)
            top = pg.frame(name="topFrame")
            mf = pg.frame(name="mainFrame")
        except Exception as e:
            w("[回框架页失败] " + str(e)[:120])

    # 也从菜单点一次"版本升级"
    try:
        top.click("#mmManager")
        pg.wait_for_timeout(2000)
        mf.locator("text=版本升级").first.click()
        pg.wait_for_timeout(2500)
        w("")
        w("### 菜单点击 版本升级")
        w("URL: " + mf.evaluate("location.href"))
        w(mf.inner_text("body")[:1200])
        w("--- 输入项 ---")
        w(mf.evaluate("""(function(){var o=[];
            document.querySelectorAll('input').forEach(function(e){
              o.push('type='+(e.type||'')+' id='+(e.id||'')+' name='+(e.name||''));});
            return o.join('\\n');})()"""))
    except Exception as e:
        w("[版本升级 点击失败] " + str(e)[:150])

    pg.screenshot(path=".temp/upgrade_page.png")
    br.close()

os.makedirs(os.path.dirname(OUT) or ".", exist_ok=True)
open(OUT, "w", encoding="utf-8").write("\n".join(log))
print("saved", OUT)
