#!/usr/bin/env python3
"""端口绑定 checkbox 真实状态取证：逐条连接读 Frm_PortETHn / Frm_PortWLANn。"""
import os
import sys
import json

os.environ.setdefault("NO_PROXY", "127.0.0.1,localhost")
os.environ.setdefault("no_proxy", "127.0.0.1,localhost")

from playwright.sync_api import sync_playwright

BASE = "http://192.168.1.1"
PWD = os.environ.get("ZTE_ADMIN_PASS", "CUAdmin")
OUT = sys.argv[1] if len(sys.argv) > 1 else ".temp/probe_ports.txt"

JS = """(function(){
  var ids=['Frm_PortETH1','Frm_PortETH2','Frm_PortETH3','Frm_PortETH4','Frm_PortETH5',
           'Frm_PortWLAN1','Frm_PortWLAN2','Frm_PortWLAN3','Frm_PortWLAN4',
           'Frm_PortWLAN5','Frm_PortWLAN6','Frm_PortWLAN7','Frm_PortWLAN8'];
  var out={};
  ids.forEach(function(i){var e=document.getElementById(i);
    out[i]= e? (e.checked?'ON':'off') : 'MISSING';});
  return out;})()"""

LABEL = {"Frm_PortETH1": "LAN1", "Frm_PortETH2": "LAN2", "Frm_PortETH3": "LAN3",
         "Frm_PortETH4": "LAN4", "Frm_PortETH5": "PON",
         "Frm_PortWLAN1": "SSID1", "Frm_PortWLAN2": "SSID2", "Frm_PortWLAN3": "SSID3",
         "Frm_PortWLAN4": "SSID4", "Frm_PortWLAN5": "SSID5", "Frm_PortWLAN6": "SSID6",
         "Frm_PortWLAN7": "SSID7", "Frm_PortWLAN8": "SSID8"}


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
        page.wait_for_timeout(2400)

        for label, val in (("新建WAN连接(默认)", "-1"),
                           ("TR069  1_TR069_R_VID_3600", "IGD.WD1.WCD1.WCIP1"),
                           ("INTERNET  2_INTERNET_R_VID_48", "IGD.WD1.WCD3.WCPPP1"),
                           ("IPTV  3_IPTV_B_VID_3185", "IGD.WD1.WCD4.WCIP1")):
            try:
                mf.locator("select").first.select_option(val)
                page.wait_for_timeout(3000)
                d = mf.evaluate(JS)
                log.append("\n== %s" % label)
                on = [LABEL.get(k, k) for k, v in d.items() if v == "ON"]
                log.append("   绑定中: %s" % (", ".join(on) if on else "(无)"))
                log.append("   全量: %s" % json.dumps(d, ensure_ascii=False))
                # 连接名与协议
                log.append("   VLAN=%s/%s  协议=%s  模式=%s" % (
                    mf.evaluate("(function(){var e=document.getElementById('Frm_WBDMode');return e?e.options[e.selectedIndex].text:'';})()"),
                    mf.evaluate("(function(){var e=document.getElementById('Frm_VLANID');return e?e.value:'';})()"),
                    mf.evaluate("(function(){var e=document.getElementById('Frm_protocol');return e?e.options[e.selectedIndex].text:'';})()"),
                    mf.evaluate("(function(){var e=document.getElementById('WanConnectMode_select');return e?e.options[e.selectedIndex].text:'';})()")))
            except Exception as e:
                log.append("[%s 失败] %s" % (label, str(e)[:120]))

        browser.close()

    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(log))
    print("\n".join(log))
    print("saved:", OUT)


if __name__ == "__main__":
    main()
