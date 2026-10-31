#!/usr/bin/env python3
"""刷机前全量配置快照（只读）。

自行拉起本机 Edge，登录后逐页抓取：
  设备信息 / 逻辑ID注册信息 / 上行线路配置(逐连接) / LAN配置 / WLAN(2G+5G) /
  绑定设置 / 远程管理 / LOID配置 / 上行方式 / 网络侧信息

用法: python tools/snapshot_now.py [输出路径]
环境变量: ZTE_ADMIN_PASS 覆盖超密（默认 CUAdmin）
"""
import os
import sys
import time
import json

for k in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy", "ALL_PROXY", "all_proxy"):
    os.environ.pop(k, None)
os.environ["NO_PROXY"] = "192.168.1.1,127.0.0.1,localhost"
os.environ["no_proxy"] = os.environ["NO_PROXY"]

from playwright.sync_api import sync_playwright  # noqa: E402

BASE = "http://192.168.1.1"
PWD = os.environ.get("ZTE_ADMIN_PASS", "CUAdmin")
OUT = sys.argv[1] if len(sys.argv) > 1 else ".temp/snapshot_preflash.txt"

MENU_ID = {"状态": "mmStatu", "基本配置": "mmNet", "高级配置": "mmAdv", "设备管理": "mmManager"}

FIELDS_JS = """(function(){
  var out=[];
  document.querySelectorAll('input,select,textarea').forEach(function(e){
    if(e.type==='hidden') return;
    var lab=''; var tr=e.closest('tr');
    if(tr){var tds=tr.querySelectorAll('td');
      if(tds.length>1) lab=(tds[0].innerText||'').trim()+' >> '+(tds[1].innerText||'').trim();}
    var v = e.tagName==='SELECT' ? (e.options[e.selectedIndex]?e.options[e.selectedIndex].text:'')
         : (e.type==='checkbox' ? (e.checked?'是':'否') : (e.value||''));
    if(v==='' && e.type!=='text') return;
    out.push('  - '+(lab||e.id)+' : '+v+(e.disabled?' [DISABLED]':''));
  });
  return out;})()"""

SELECT_OPTS_JS = """(function(){
  var s=document.querySelector('select');
  if(!s) return [];
  return Array.from(s.options).map(function(o){return o.value+' | '+o.text;});})()"""


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
            log.append("[login] 密码框仍在 = " +
                       str(page.evaluate("!!document.getElementById('Frm_Password')")))
        page.wait_for_timeout(2000)
        for attempt in range(30):
            if page.frame(name="topFrame") and page.frame(name="mainFrame"):
                break
            try:
                page.click("#menu0", timeout=2000)
            except Exception:
                pass
            page.wait_for_timeout(600)
            if attempt == 8:
                try:
                    page.goto(BASE + "/unicom.html", wait_until="domcontentloaded", timeout=15000)
                except Exception:
                    pass
        page.wait_for_timeout(2000)
        log.append("[frame] url=%s frames=%s" % (page.url, [f.name for f in page.frames]))
        top = page.frame(name="topFrame")
        mf = page.frame(name="mainFrame")
        if top is None or mf is None:
            log.append("!! 未进入框架页，登录可能失败")
            os.makedirs(os.path.dirname(OUT) or ".", exist_ok=True)
            open(OUT, "w", encoding="utf-8").write("\n".join(log))
            browser.close()
            return

        def sec(t):
            log.append("")
            log.append("=" * 78)
            log.append("== " + t)
            log.append("=" * 78)

        def dump(title, fields=True, opts=False):
            sec(title)
            log.append("URL: " + mf.evaluate("location.href"))
            log.append(clean(mf.inner_text("body")))
            if opts:
                o = mf.evaluate(SELECT_OPTS_JS)
                if o:
                    log.append("--- select options ---")
                    log.append(json.dumps(o, ensure_ascii=False, indent=1))
            if fields:
                fs = mf.evaluate(FIELDS_JS)
                if fs:
                    log.append("--- fields ---")
                    log.extend(fs)

        def go(menu, sub, wait=2400):
            top.click("#%s" % MENU_ID[menu])
            page.wait_for_timeout(2000)
            mf.locator("text=" + sub).first.click()
            page.wait_for_timeout(wait)

        # ---------- 1. 设备信息 ----------
        try:
            go("状态", "设备信息")
            dump("状态 > 设备信息")
        except Exception as e:
            log.append("[设备信息 失败] " + str(e)[:150])

        # ---------- 2. 逻辑ID注册信息 ----------
        try:
            go("状态", "逻辑ID注册信息")
            dump("状态 > 逻辑ID注册信息")
        except Exception as e:
            log.append("[逻辑ID注册信息 失败] " + str(e)[:150])

        # ---------- 3. 上行线路配置：逐连接 ----------
        try:
            go("基本配置", "上行线路配置")
            dump("基本配置 > 上行线路配置（默认视图）", opts=True)
            opts = mf.evaluate(SELECT_OPTS_JS)
            for o in opts:
                val = o.split(" | ")[0].strip()
                if not val:
                    continue
                try:
                    mf.locator("select").first.select_option(val)
                    page.wait_for_timeout(2600)
                except Exception as e:
                    log.append("[选中 %s 失败] %s" % (o, str(e)[:120]))
                    continue
                # 每个连接下的所有 tab（IPv4/IPv6/VLAN/组播等）挨个点
                dump("上行线路配置 > 选中 [%s]" % o)
        except Exception as e:
            log.append("[上行线路配置 失败] " + str(e)[:150])

        # ---------- 4. LAN配置 + IPv6 子页 ----------
        for sub in ("LAN配置", "RA配置", "DHCPv6配置", "IPv6前缀管理"):
            try:
                go("基本配置", sub)
                dump("基本配置 > " + sub)
            except Exception as e:
                log.append("[%s 失败] %s" % (sub, str(e)[:150]))

        # ---------- 5. WLAN 2G / 5G ----------
        try:
            go("基本配置", "WLAN配置")
            for sub in ("无线基本配置(2.4G)", "无线基本配置(5G)", "无线安全配置(2.4G)", "无线安全配置(5G)"):
                try:
                    top.click("#mmNet")
                    page.wait_for_timeout(1800)
                    mf.locator("text=WLAN配置").first.click()
                    page.wait_for_timeout(1600)
                    mf.locator("text=" + sub).first.click()
                    page.wait_for_timeout(2400)
                    dump("基本配置 > WLAN配置 > " + sub)
                except Exception as e:
                    log.append("[%s 失败] %s" % (sub, str(e)[:150]))
        except Exception as e:
            log.append("[WLAN 失败] " + str(e)[:150])

        # ---------- 6. 绑定设置 ----------
        try:
            go("基本配置", "绑定设置")
            dump("基本配置 > 绑定设置")
        except Exception as e:
            log.append("[绑定设置 失败] " + str(e)[:150])

        # ---------- 7. 远程管理 ----------
        try:
            go("基本配置", "远程管理")
            dump("基本配置 > 远程管理")
        except Exception as e:
            log.append("[远程管理 失败] " + str(e)[:150])

        # ---------- 8. LOID配置 ----------
        try:
            go("高级配置", "LOID配置")
            dump("高级配置 > LOID配置")
        except Exception as e:
            log.append("[LOID配置 失败] " + str(e)[:150])

        # ---------- 9. 上行方式 ----------
        try:
            go("设备管理", "上行方式")
            dump("设备管理 > 上行方式")
        except Exception as e:
            log.append("[上行方式 失败] " + str(e)[:150])

        # ---------- 10. 网络侧信息 各 tab ----------
        for tab in ("IPv4 WAN连接信息", "IPv6 WAN连接信息", "上行接口信息", "下行光接口信息"):
            try:
                top.click("#mmStatu")
                page.wait_for_timeout(1800)
                mf.locator("text=网络侧信息").first.click()
                page.wait_for_timeout(1800)
                mf.locator("text=" + tab).first.click()
                page.wait_for_timeout(2200)
                sec("状态 > 网络侧信息 > " + tab)
                log.append(clean(mf.inner_text("body")))
            except Exception as e:
                log.append("[%s 失败] %s" % (tab, str(e)[:150]))

        # ---------- 11. 用户侧信息 / 远程管理状态 ----------
        for sub in ("用户侧信息", "远程管理状态"):
            try:
                go("状态", sub)
                sec("状态 > " + sub)
                log.append(clean(mf.inner_text("body")))
            except Exception as e:
                log.append("[%s 失败] %s" % (sub, str(e)[:150]))

        browser.close()

    os.makedirs(os.path.dirname(OUT) or ".", exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(log))
    print("saved:", OUT, os.path.getsize(OUT), "bytes")


if __name__ == "__main__":
    main()
