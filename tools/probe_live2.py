#!/usr/bin/env python3
"""第二轮取证：LAN配置二级菜单(RA/DHCPv6/前缀管理) + 5G WLAN + IPTV 连接详情 + 快速配置。"""
import os
import sys
import json

os.environ.setdefault("NO_PROXY", "127.0.0.1,localhost")
os.environ.setdefault("no_proxy", "127.0.0.1,localhost")

from playwright.sync_api import sync_playwright

BASE = "http://192.168.1.1"
PWD = os.environ.get("ZTE_ADMIN_PASS", "CUAdmin")  # 管理账号密码，可用环境变量覆盖
OUT = sys.argv[1] if len(sys.argv) > 1 else ".temp/probe2.txt"

FIELDS_JS = """(function(){
  var out=[];
  document.querySelectorAll('input,select,textarea').forEach(function(e){
    if(e.type==='hidden') return;
    var lab=''; var tr=e.closest('tr');
    if(tr){var tds=tr.querySelectorAll('td');
      if(tds.length>1) lab=(tds[0].innerText||'').trim()+' >> '+(tds[1].innerText||'').trim();}
    var v = e.tagName==='SELECT' ? (e.options[e.selectedIndex]?e.options[e.selectedIndex].text:'')
         : (e.type==='checkbox' ? (e.checked?'是':'否') : (e.value||''));
    var dis = e.disabled ? ' [DISABLED]' : '';
    if(v==='' && e.type!=='text') return;
    out.push('  - '+(lab||e.id)+' : '+v+dis);
  });
  return out;})()"""


def clean(t):
    return "\n".join(l.strip() for l in t.split("\n") if l.strip())


def main():
    log = []
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=False,
                                    args=["--no-first-run", "--no-default-browser-check"])
        ctx = browser.new_context(viewport={"width": 1500, "height": 1000})
        page = ctx.new_page()
        page.goto(BASE + "/", wait_until="domcontentloaded", timeout=40000)
        page.wait_for_timeout(1500)
        if page.evaluate("!!document.getElementById('Frm_Password')"):
            page.evaluate("GetAccessAccount('adm')")
            page.fill("#Frm_Password", PWD)
            page.click("#LoginId")
            page.wait_for_timeout(4500)
        if not page.frame(name="topFrame"):
            try:
                page.click("#menu0")
            except Exception:
                pass
            for _ in range(20):
                if page.frame(name="topFrame"):
                    break
                page.wait_for_timeout(300)
        page.wait_for_timeout(1500)
        top = page.frame(name="topFrame")
        mf = page.frame(name="mainFrame")

        def sec(t):
            log.append("\n" + "=" * 78 + "\n== " + t + "\n" + "=" * 78)

        def dump(t):
            sec(t)
            log.append("URL: " + mf.evaluate("location.href"))
            log.append(clean(mf.inner_text("body")))
            log.append("--- fields ---")
            for x in mf.evaluate(FIELDS_JS):
                log.append(x)

        # ---- 基本配置 -> LAN配置 父页，列出二级菜单 ----
        top.click("#mmNet")
        page.wait_for_timeout(2500)
        mf.locator("text=LAN配置").first.click()
        page.wait_for_timeout(2500)
        sec("基本配置 > LAN配置 父页")
        log.append(clean(mf.inner_text("body")))
        # 列出左侧二级菜单链接
        links = mf.evaluate("""(function(){
            var out=[];
            document.querySelectorAll('a,li,td,span').forEach(function(e){
                var t=(e.innerText||'').trim();
                if(t && t.length<20) out.push(t);});
            return Array.from(new Set(out));})()""")
        log.append("二级菜单候选: " + json.dumps(links, ensure_ascii=False))

        for sub in ("RA配置", "DHCPv6配置", "IPv6前缀管理", "端口DHCP服务控制"):
            try:
                mf.locator("text=" + sub).first.click()
                page.wait_for_timeout(2600)
                dump("基本配置 > LAN配置 > " + sub)
            except Exception as e:
                log.append("\n[%s 失败] %s" % (sub, str(e)[:130]))

        # ---- WLAN 5G ----
        top.click("#mmNet")
        page.wait_for_timeout(2200)
        try:
            mf.locator("text=WLAN配置").first.click()
            page.wait_for_timeout(2500)
            for sub in ("无线基本配置(5G)", "无线基本配置(2.4G)"):
                try:
                    mf.locator("text=" + sub).first.click()
                    page.wait_for_timeout(2600)
                    dump("基本配置 > WLAN配置 > " + sub)
                except Exception as e:
                    log.append("\n[%s 失败] %s" % (sub, str(e)[:130]))
        except Exception as e:
            log.append("\n[WLAN 失败] " + str(e)[:130])

        # ---- IPTV 连接详情 (3_IPTV_B_VID_3185) ----
        top.click("#mmNet")
        page.wait_for_timeout(2500)
        mf.locator("text=上行线路配置").first.click()
        page.wait_for_timeout(2200)
        try:
            mf.locator("select").first.select_option("IGD.WD1.WCD4.WCIP1")
            page.wait_for_timeout(2600)
            dump("上行线路配置 - 选中 3_IPTV_B_VID_3185")
            # 再 dump 绑定设置里 LAN 端口绑定的可编辑单元格
        except Exception as e:
            log.append("\n[IPTV 失败] " + str(e)[:130])

        # ---- 绑定设置：把绑定模式切成 VLAN绑定 看可填内容 ----
        top.click("#mmNet")
        page.wait_for_timeout(2000)
        try:
            mf.locator("text=绑定设置").first.click()
            page.wait_for_timeout(2500)
            sec("绑定设置 - 表格 raw")
            rows = mf.evaluate("""(function(){
                var out=[];
                document.querySelectorAll('tr').forEach(function(tr){
                    var cells=Array.from(tr.querySelectorAll('td')).map(function(td){
                        var inp=td.querySelector('input,select');
                        return (td.innerText||'').trim()+(inp?(' <'+inp.tagName+' '+(inp.name||inp.id||'')+'='+(inp.value||'')+'>'):'');});
                    if(cells.length) out.push(cells.join(' | '));});
                return out;})()""")
            for r in rows:
                log.append(r)
        except Exception as e:
            log.append("\n[绑定表格 失败] " + str(e)[:130])

        browser.close()

    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(log))
    print("saved:", OUT, os.path.getsize(OUT))


if __name__ == "__main__":
    main()
