#!/usr/bin/env python3
"""精确取证：VLAN 模式 select 的真实 value / 生效 WiFi 口令。"""
import os
import sys
import json

os.environ.setdefault("NO_PROXY", "127.0.0.1,localhost")
os.environ.setdefault("no_proxy", "127.0.0.1,localhost")

from playwright.sync_api import sync_playwright

BASE = "http://192.168.1.1"
PWD = os.environ.get("ZTE_ADMIN_PASS", "CUAdmin")  # 管理账号密码，可用环境变量覆盖
OUT = sys.argv[1] if len(sys.argv) > 1 else ".temp/probe3.txt"

RAW_JS = """(function(){
  var out=[];
  document.querySelectorAll('input,select,textarea').forEach(function(e){
    if(e.type==='hidden') return;
    var tr=e.closest('tr'); var lab='';
    if(tr){var tds=tr.querySelectorAll('td'); if(tds.length>1) lab=(tds[0].innerText||'').trim();}
    var sel = (e.tagName==='SELECT' && e.options[e.selectedIndex]) ? e.options[e.selectedIndex].text : '';
    out.push({row:lab, id:e.id, name:e.name, tag:e.tagName, type:e.type,
      value:(e.value||'').slice(0,40), selectedText:sel, disabled:e.disabled,
      opts:(e.tagName==='SELECT')?Array.from(e.options).map(function(o){return o.value+'='+o.text;}) : null});
  });
  return out;})()"""


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

        top.click("#mmNet")
        page.wait_for_timeout(2500)
        mf.locator("text=上行线路配置").first.click()
        page.wait_for_timeout(2200)

        for label, val in (("INTERNET", "IGD.WD1.WCD3.WCPPP1"),
                           ("IPTV", "IGD.WD1.WCD4.WCIP1"),
                           ("TR069", "IGD.WD1.WCD1.WCIP1")):
            try:
                mf.locator("select").first.select_option(val)
                page.wait_for_timeout(2600)
                log.append("\n" + "=" * 78)
                log.append("== %s (%s) 全字段 raw" % (label, val))
                log.append("=" * 78)
                for f in mf.evaluate(RAW_JS):
                    if not f.get("row"):
                        continue
                    if any(k in f["row"] for k in ("VLAN", "IP协议", "封装", "连接模式", "业务类型",
                                                  "MTU", "用户名", "密码", "端口绑定", "地址获取",
                                                  "全局地址", "网关获取", "前缀", "DNS获取", "使能",
                                                  "802.1p", "DHCP服务", "NAT")):
                        log.append("%-14s id=%-18s name=%-18s %-6s value=%-12r sel=%-14r dis=%s opts=%s"
                                   % (f["row"][:14], f["id"], f["name"], f["tag"],
                                      f["value"], f["selectedText"], f["disabled"],
                                      json.dumps(f["opts"], ensure_ascii=False) if f["opts"] else ""))
            except Exception as e:
                log.append("[%s 失败] %s" % (label, str(e)[:120]))

        # WLAN: 逐个 SSID 看密钥
        top.click("#mmNet")
        page.wait_for_timeout(2200)
        mf.locator("text=WLAN配置").first.click()
        page.wait_for_timeout(2500)
        for band in ("无线基本配置(2.4G)", "无线基本配置(5G)"):
            try:
                mf.locator("text=" + band).first.click()
                page.wait_for_timeout(2500)
                log.append("\n" + "=" * 78 + "\n== WLAN %s 全字段" % band + "\n" + "=" * 78)
                for f in mf.evaluate(RAW_JS):
                    if any(k in (f.get("row") or "") for k in ("SSID", "密钥", "认证", "加密", "双频")):
                        log.append("%-16s id=%-20s name=%-20s %-6s value=%-16r sel=%-14r dis=%s"
                                   % (f["row"][:16], f["id"], f["name"], f["tag"],
                                      f["value"], f["selectedText"], f["disabled"]))
            except Exception as e:
                log.append("[%s 失败] %s" % (band, str(e)[:120]))

        browser.close()

    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(log))
    print("saved:", OUT, os.path.getsize(OUT))


if __name__ == "__main__":
    main()
