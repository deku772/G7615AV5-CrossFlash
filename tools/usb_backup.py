#!/usr/bin/env python3
"""执行 设备管理 > 设备管理 > USB备份配置：把 usercfg 备份到已插的 U 盘。

只点备份按钮，不做任何其他写操作。
"""
import os
import sys

for k in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy", "ALL_PROXY", "all_proxy"):
    os.environ.pop(k, None)
os.environ["NO_PROXY"] = "192.168.1.1,127.0.0.1,localhost"
os.environ["no_proxy"] = os.environ["NO_PROXY"]

from playwright.sync_api import sync_playwright  # noqa: E402

BASE = "http://192.168.1.1"
PWD = os.environ.get("ZTE_ADMIN_PASS", "CUAdmin")
OUT = sys.argv[1] if len(sys.argv) > 1 else ".temp/usb_backup.txt"
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
    if top is None or mf is None:
        w("!! 未进入框架页")
        br.close()
        sys.exit(1)

    # 设备管理 → 设备管理（第一个二级项）——用 JS click 绕过遮挡
    top.click("#mmManager")
    pg.wait_for_timeout(2200)
    r = mf.evaluate("""(function(){
      var els=Array.from(document.querySelectorAll('a,li,td,font,div,span'));
      for(var i=0;i<els.length;i++){var e=els[i];
        if((e.innerText||'').trim()==='设备管理' && e.getAttribute('onclick')){e.click();return 'clicked-oc '+e.tagName;}}
      for(var i=0;i<els.length;i++){var e=els[i];
        if((e.innerText||'').trim()==='设备管理'){e.click();return 'clicked-any '+e.tagName;}}
      return 'not found';})()""")
    w("[JS click 二级菜单] " + r)
    pg.wait_for_timeout(3000)
    try:
        mf = pg.frame(name="mainFrame")
    except Exception:
        pass
    w("URL: " + mf.evaluate("location.href"))
    w(mf.inner_text("body")[:2200])
    w("--- 全部按钮/输入 ---")
    w(mf.evaluate("""(function(){var o=[];
        document.querySelectorAll('input,button,a').forEach(function(e){
          var t=(e.value||e.innerText||'').trim();
          o.push(e.tagName+' type='+(e.type||'')+' id='+(e.id||'')+' name='+(e.name||'')+' txt='+t.slice(0,20)+' oc='+(e.getAttribute('onclick')||'').slice(0,80));});
        return o.join('\\n');})()"""))
    pg.screenshot(path=".temp/usb_backup_page.png")

    # 尝试点 USB 备份相关按钮
    clicked = False
    for sel in ("input[value*='备份']", "input[value*='备 份']", "a:has-text('备份')",
                "button:has-text('备份')", "text=USB备份配置", "text=备份配置"):
        try:
            loc = mf.locator(sel).first
            if loc.count() == 0:
                continue
            w("[click] " + sel)
            loc.click()
            pg.wait_for_timeout(4000)
            clicked = True
            pg.screenshot(path=".temp/usb_backup_clicked.png")
            w(mf.inner_text("body")[:800])
            break
        except Exception as e:
            w("[click %s 失败] %s" % (sel, str(e)[:100]))

    if not clicked:
        w("!! 未找到备份按钮，仅完成页面 dump")
    else:
        w("已触发备份，请稍后拔下 U 盘前确认文件出现（通常 10-30 秒写入）")

    br.close()

os.makedirs(os.path.dirname(OUT) or ".", exist_ok=True)
open(OUT, "w", encoding="utf-8").write("\n".join(log))
print("saved", OUT)
