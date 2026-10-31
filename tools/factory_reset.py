#!/usr/bin/env python3
"""执行 设备管理 > 恢复出厂配置，并监控光猫重启回到在线状态。

自动接受 confirm 弹窗；复位期间轮询 192.168.1.1 直到恢复（最长 8 分钟）。
"""
import os
import sys
import time
import socket

for k in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy", "ALL_PROXY", "all_proxy"):
    os.environ.pop(k, None)
os.environ["NO_PROXY"] = "192.168.1.1,127.0.0.1,localhost"
os.environ["no_proxy"] = os.environ["NO_PROXY"]

from playwright.sync_api import sync_playwright  # noqa: E402

BASE = "http://192.168.1.1"
PWD = os.environ.get("ZTE_ADMIN_PASS", "CUAdmin")
OUT = sys.argv[1] if len(sys.argv) > 1 else ".temp/factory_reset.txt"
log = []


def w(s=""):
    log.append(str(s))
    print(s, flush=True)


def ping_host(host="192.168.1.1", timeout=1.0):
    try:
        s = socket.create_connection((host, 80), timeout=timeout)
        s.close()
        return True
    except Exception:
        return False


w("复位前在线检测: " + str(ping_host()))

with sync_playwright() as p:
    br = p.chromium.launch(channel="msedge", headless=False,
                           args=["--no-first-run", "--no-default-browser-check"])
    ctx = br.new_context(viewport={"width": 1500, "height": 1000})
    pg = ctx.new_page()

    # 自动接受 confirm/alert
    pg.on("dialog", lambda d: (w("[dialog:%s] %s" % (d.type, d.message[:120])), d.accept()))

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
        w("!! 未进入框架页，中止（不做任何复位操作）")
        br.close()
        open(OUT, "w", encoding="utf-8").write("\n".join(log))
        sys.exit(1)

    # 进入 恢复出厂配置 页
    top.click("#mmManager")
    pg.wait_for_timeout(2200)
    r = mf.evaluate("""(function(){
      var a=document.querySelector('#smReturnFactory');
      if(a){a.click();return 'clicked #smReturnFactory';}
      return 'not found';})()""")
    w("[进入恢复出厂页] " + r)
    pg.wait_for_timeout(3000)
    try:
        mf = pg.frame(name="mainFrame")
    except Exception:
        pass
    w("URL: " + mf.evaluate("location.href"))
    w(mf.inner_text("body")[:1500])
    w("--- 按钮 ---")
    w(mf.evaluate("""(function(){var o=[];
        document.querySelectorAll('input[type=button],button').forEach(function(e){
          o.push('id='+(e.id||'')+' name='+(e.name||'')+' value='+(e.value||e.innerText||'')+' oc='+(e.getAttribute('onclick')||'').slice(0,80));});
        return o.join('\\n');})()"""))
    pg.screenshot(path=".temp/reset_page.png")

    # 找恢复出厂按钮并点击
    r = mf.evaluate("""(function(){
      var cands=[...document.querySelectorAll('input[type=button],button')];
      for(var e of cands){
        var v=(e.value||e.innerText||'');
        if(v.indexOf('恢复出厂')>=0 || /ReturnFactory/i.test(e.id) || /ReturnFactory/i.test(e.getAttribute('onclick')||'')){
          e.click(); return 'clicked id='+e.id+' value='+v;
        }
      }
      return 'button not found';})()""")
    w("[点击恢复出厂] " + r)
    pg.wait_for_timeout(3000)
    pg.screenshot(path=".temp/reset_clicked.png")
    try:
        w("点击后页面: " + mf.inner_text("body")[:600])
    except Exception as e:
        w("[读页面失败-可能正在重启] " + str(e)[:100])

    # 第二段确认：找出确认区里的确定按钮再点一次
    r2 = mf.evaluate("""(function(){
      var cands=[...document.querySelectorAll('input[type=button],button,a')];
      var hits=[];
      for(var e of cands){
        var v=(e.value||e.innerText||'').trim();
        if(v==='确定'||v==='确 定'||v==='OK'||v==='是'){hits.push(e);}
      }
      // 优先点"确定"
      for(var e of hits){ e.click(); return 'confirmed via value='+(e.value||e.innerText); }
      return 'confirm button not found; buttons=' + cands.map(function(e){return (e.value||e.innerText||'').trim();}).filter(Boolean).join(',');
    })()""")
    w("[二次确认] " + r2)
    pg.wait_for_timeout(3000)
    pg.screenshot(path=".temp/reset_confirmed.png")
    try:
        w("确认后页面: " + mf.inner_text("body")[:500])
    except Exception as e:
        w("[页面已跳转/重启中] " + str(e)[:100])
    br.close()

# 监控重启
w("")
w("=== 监控光猫重启（最长 8 分钟）===")
down_at = None
start = time.time()
came_back = False
was_down = False
while time.time() - start < 480:
    online = ping_host()
    if not online:
        if not was_down:
            was_down = True
            down_at = time.time()
            w("[%02d:%02d] 光猫已下线（复位执行中）" % ((time.time() - start) // 60, (time.time() - start) % 60))
    else:
        if was_down:
            w("[%02d:%02d] 光猫已恢复在线 ✔" % ((time.time() - start) // 60, (time.time() - start) % 60))
            came_back = True
            break
        elif time.time() - start > 20:
            w("!! 光猫一直在线，复位可能未触发，请人工检查")
            break
    time.sleep(3)

if not came_back:
    w("!! 8 分钟内未恢复在线，请检查电源/网线，手动确认")

w("")
w("最终状态: online=" + str(ping_host()))
open(OUT, "w", encoding="utf-8").write("\n".join(log))
print("saved", OUT)
