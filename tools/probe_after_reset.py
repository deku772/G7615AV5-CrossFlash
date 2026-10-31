# -*- coding: utf-8 -*-
"""复位后基线探测：设备信息 / WAN 连接列表 / USB备份配置页（文件列表）"""
import os, sys, re

for k in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy", "ALL_PROXY", "all_proxy"):
    os.environ.pop(k, None)
os.environ["NO_PROXY"] = "192.168.1.1,127.0.0.1,localhost"

from playwright.sync_api import sync_playwright

BASE = "http://192.168.1.1"
PWD = os.environ.get("ZTE_ADMIN_PASS", "nE%jA@5b")
OUT = sys.argv[1] if len(sys.argv) > 1 else ".temp/probe_after_reset.txt"
log = []


def w(s=""):
    log.append(str(s))
    print(s, flush=True)


with sync_playwright() as p:
    br = p.chromium.launch(channel="msedge", headless=True, args=["--no-first-run"])
    ctx = br.new_context(viewport={"width": 1500, "height": 1000})
    pg = ctx.new_page()
    pg.goto(BASE + "/", wait_until="domcontentloaded", timeout=40000)
    pg.wait_for_timeout(1500)
    pg.evaluate("GetAccessAccount('adm')")
    pg.fill("#Frm_Password", PWD)
    pg.click("#LoginId")
    pg.wait_for_timeout(5000)
    if pg.evaluate("!!document.getElementById('Frm_Password')"):
        w("!! 登录失败")
        br.close()
        sys.exit(1)
    w("[登录成功] " + PWD)

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
    w("frames: top=%s main=%s" % (top is not None, mf is not None))
    if not mf:
        br.close(); sys.exit(1)

    def goto_main(url, title):
        w("")
        w("=" * 20 + " " + title + " " + "=" * 20)
        try:
            mf.evaluate("location.href='%s'" % url)
            pg.wait_for_timeout(3500)
            f = pg.frame(name="mainFrame")
            w("URL: " + f.evaluate("location.href"))
            w(f.inner_text("body")[:2500])
        except Exception as e:
            w("[失败] " + str(e)[:120])

    # 1) 设备信息
    try:
        top.click("#mmStatu"); pg.wait_for_timeout(2000)
        mf2 = pg.frame(name="mainFrame")
        mf2.evaluate("""(function(){var els=Array.from(document.querySelectorAll('a,li,td,font,span'));
            for(var i=0;i<els.length;i++){var e=els[i];
              if((e.innerText||'').trim()==='设备信息'){e.click();return 'ok';}}return 'nf';})()""")
        pg.wait_for_timeout(3000)
        f = pg.frame(name="mainFrame")
        w("")
        w("=" * 20 + " 设备信息 " + "=" * 20)
        w(f.inner_text("body")[:1200])
    except Exception as e:
        w("[设备信息失败] " + str(e)[:100])

    # 2) WAN 连接列表
    goto_main("/getpage.gch?pid=1002&nextpage=IPv46_net_wan_conf_t.gch", "WAN 连接列表")
    try:
        f = pg.frame(name="mainFrame")
        w("--- 连接名称下拉 ---")
        w(f.evaluate("""(function(){var s=document.getElementById('Frm_ConList')||document.querySelector('select');
            if(!s) return 'no select';
            return Array.from(s.options).map(function(o){return o.value+' | '+o.text;}).join('\\n');})()"""))
    except Exception as e:
        w("[下拉读取失败] " + str(e)[:100])

    # 3) USB 备份配置页
    try:
        top.click("#mmManager"); pg.wait_for_timeout(2000)
        mf3 = pg.frame(name="mainFrame")
        r = mf3.evaluate("""(function(){var els=Array.from(document.querySelectorAll('a,li,td,font,span'));
            for(var i=0;i<els.length;i++){var e=els[i];
              if((e.innerText||'').trim()==='设备管理'){e.click();return 'ok';}}return 'nf';})()""")
        w("")
        w("[二级菜单 设备管理] " + r)
        pg.wait_for_timeout(3500)
        f = pg.frame(name="mainFrame")
        w("=" * 20 + " USB备份配置页 " + "=" * 20)
        w("URL: " + f.evaluate("location.href"))
        w(f.inner_text("body")[:2000])
        w("--- 按钮 ---")
        w(f.evaluate("""(function(){var o=[];
            document.querySelectorAll('input,button').forEach(function(e){
              var t=(e.value||e.innerText||'').trim();
              if(t) o.push(e.tagName+' id='+e.id+' name='+e.name+' txt='+t+' oc='+(e.getAttribute('onclick')||'').slice(0,70));});
            return o.join('\\n');})()"""))
    except Exception as e:
        w("[USB页失败] " + str(e)[:100])

    br.close()

os.makedirs(os.path.dirname(OUT) or ".", exist_ok=True)
open(OUT, "w", encoding="utf-8").write("\n".join(log))
print("saved", OUT)
