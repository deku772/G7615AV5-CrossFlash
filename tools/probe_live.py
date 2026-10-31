#!/usr/bin/env python3
"""实机取证：把用户关心的几处配置逐个 dump 出来（只读）。"""
import os
import sys
import time
import json

os.environ.setdefault("NO_PROXY", "127.0.0.1,localhost")
os.environ.setdefault("no_proxy", "127.0.0.1,localhost")

from playwright.sync_api import sync_playwright

BASE = "http://192.168.1.1"
PWD = os.environ.get("ZTE_ADMIN_PASS", "CUAdmin")  # 管理账号密码，可用环境变量覆盖
OUT = sys.argv[1] if len(sys.argv) > 1 else ".temp/probe1.txt"

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

DUMP_FIELDS_JS = """(function(){
  var out=[];
  document.querySelectorAll('input,select,textarea').forEach(function(e){
    out.push({id:e.id,name:e.name,tag:e.tagName,type:e.type,
      val:(e.value||'').slice(0,40),checked:e.checked,disabled:e.disabled,
      opts:e.tagName==='SELECT'?Array.from(e.options).map(o=>o.value+'|'+o.text):null});
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
            log.append("[login] Frm_Password 仍在 = " +
                       str(page.evaluate("!!document.getElementById('Frm_Password')")))
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

        def sec(title):
            log.append("\n" + "=" * 78)
            log.append("== " + title)
            log.append("=" * 78)

        def sub_click(text, wait=2400):
            mf.locator("text=" + text).first.click()
            page.wait_for_timeout(wait)

        def dump(title):
            sec(title)
            log.append("URL: " + mf.evaluate("location.href"))
            log.append(clean(mf.inner_text("body")))
            log.append("--- fields ---")
            for x in mf.evaluate(FIELDS_JS):
                log.append(x)

        # ===== 1. 上行线路配置：逐个连接选中看真实 VLAN =====
        top.click("#mmNet")
        page.wait_for_timeout(2500)
        sub_click("上行线路配置")
        page.wait_for_timeout(1500)
        sec("上行线路配置 - 连接下拉框全部选项")
        opts = mf.evaluate("""(function(){
            var s=document.querySelector('select');
            if(!s) return [];
            return Array.from(s.options).map(o=>o.value+' | '+o.text);})()""")
        log.append(json.dumps(opts, ensure_ascii=False, indent=1))

        log.append("\n>>> 连接下拉框当前选中项:")
        log.append(json.dumps(mf.evaluate("""(function(){
            var s=document.querySelector('select');
            if(!s) return null;
            return {value:s.value, text:s.options[s.selectedIndex]?s.options[s.selectedIndex].text:''};})()"""),
                                ensure_ascii=False))

        # 逐个连接选中 -> dump 表单
        for sel_val in [o for o in opts if o.strip()]:
            val = sel_val.split(" | ")[0].strip()
            try:
                mf.locator("select").first.select_option(val)
                page.wait_for_timeout(2600)
                sec("上行线路配置 - 选中 %s" % sel_val)
                log.append(clean(mf.inner_text("body")))
                log.append("--- fields (含 disabled 标记) ---")
                for x in mf.evaluate(FIELDS_JS):
                    log.append(x)
            except Exception as e:
                log.append("[选中 %s 失败] %s" % (sel_val, str(e)[:120]))

        # ===== 2. 绑定设置 =====
        top.click("#mmNet")
        page.wait_for_timeout(2000)
        try:
            sub_click("绑定设置")
            dump("基本配置 > 绑定设置")
        except Exception as e:
            log.append("\n[绑定设置 失败] " + str(e)[:150])

        # ===== 3. LAN配置 下的 RA / DHCPv6 / 前缀管理 =====
        top.click("#mmNet")
        page.wait_for_timeout(2000)
        for sub in ("RA配置", "DHCPv6配置", "IPv6前缀管理"):
            try:
                sub_click(sub)
                dump("基本配置 > LAN配置 > " + sub)
            except Exception as e:
                log.append("\n[%s 失败] %s" % (sub, str(e)[:150]))

        # ===== 4. 设备管理 > 上行方式 (GPON/XGPON) =====
        top.click("#mmManager")
        page.wait_for_timeout(2200)
        try:
            sub_click("上行方式")
            dump("设备管理 > 上行方式")
            log.append("--- raw fields ---")
            log.append(json.dumps(mf.evaluate(DUMP_FIELDS_JS), ensure_ascii=False, indent=1))
        except Exception as e:
            log.append("\n[上行方式 失败] " + str(e)[:150])

        # ===== 5. 状态 > 网络侧信息 各标签页 =====
        top.click("#mmStatu")
        page.wait_for_timeout(2200)
        for tab in ("IPv4 WAN连接信息", "IPv6 WAN连接信息", "上行接口信息", "下行光接口信息"):
            try:
                top.click("#mmStatu")
                page.wait_for_timeout(1500)
                sub_click("网络侧信息")
                sub_click(tab)
                sec("状态 > 网络侧信息 > " + tab)
                log.append(clean(mf.inner_text("body")))
            except Exception as e:
                log.append("\n[%s 失败] %s" % (tab, str(e)[:150]))

        # ===== 6. 设备信息 =====
        top.click("#mmStatu")
        page.wait_for_timeout(2200)
        try:
            sub_click("设备信息")
            sec("状态 > 设备信息")
            log.append(clean(mf.inner_text("body")))
        except Exception as e:
            log.append("\n[设备信息 失败] " + str(e)[:150])

        # ===== 7. WLAN 5G =====
        top.click("#mmNet")
        page.wait_for_timeout(2200)
        try:
            sub_click("WLAN配置")
            for sub in ("无线基本配置(5G)",):
                try:
                    sub_click(sub)
                    dump("基本配置 > WLAN配置 > " + sub)
                except Exception as e:
                    log.append("\n[%s 失败] %s" % (sub, str(e)[:150]))
        except Exception as e:
            log.append("\n[WLAN 失败] " + str(e)[:150])

        browser.close()

    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(log))
    print("saved:", OUT, os.path.getsize(OUT))


if __name__ == "__main__":
    main()
