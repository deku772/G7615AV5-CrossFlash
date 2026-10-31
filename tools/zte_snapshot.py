#!/usr/bin/env python3
"""抓取联通光猫 G7615AV5 的完整配置快照（只读）。

通过 Playwright 接管本机 Edge，逐页读取状态/基本配置/高级配置/设备管理，
输出 Markdown 快照，用于配置留档与重建参考。

用法: python tools/zte_snapshot.py [输出路径]
"""
import os
import sys
import time

os.environ.setdefault("NO_PROXY", "127.0.0.1,localhost")
os.environ.setdefault("no_proxy", "127.0.0.1,localhost")

from playwright.sync_api import sync_playwright  # noqa: E402

CDP = "http://127.0.0.1:9222"
BASE = "http://192.168.1.1"
OUT = sys.argv[1] if len(sys.argv) > 1 else "docs/config-snapshot.md"

# (顶部菜单, 二级菜单或 None)
PAGES = [
    ("状态", "设备信息"),
    ("状态", "网络侧信息"),
    ("状态", "用户侧信息"),
    ("状态", "远程管理状态"),
    ("状态", "逻辑ID注册信息"),
    ("基本配置", "上行线路配置"),
    ("基本配置", "LAN配置"),
    ("基本配置", "WLAN配置"),
    ("基本配置", "绑定设置"),
    ("基本配置", "远程管理"),
    ("高级配置", "LOID配置"),
    ("设备管理", "用户管理"),
]

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
    out.push('  - '+(lab||e.id)+' : '+v);
  });
  return out;})()"""


def clean(text):
    lines = [l.strip() for l in text.split("\n")]
    return "\n".join(l for l in lines if l)


def main():
    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(CDP)
        ctx = browser.contexts[0]
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.set_viewport_size({"width": 1400, "height": 950})
        page.goto(BASE + "/", wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(1500)
        if page.evaluate("!!document.getElementById('Frm_Password')"):
            page.evaluate("GetAccessAccount('adm')")
            page.fill("#Frm_Password", "CUAdmin")
            page.click("#LoginId")
            page.wait_for_timeout(4000)
        # 首次进入：若当前是单页菜单，点 #menu0 进入框架页；已在框架页则直接用
        if not page.frame(name="topFrame"):
            page.click("#menu0")
            for _ in range(20):
                if page.frame(name="topFrame"):
                    break
                page.wait_for_timeout(300)
        page.wait_for_timeout(1200)

        top = page.frame(name="topFrame")
        mf = page.frame(name="mainFrame")
        cur_menu = None
        chunks = ["# G7615AV5 配置快照", "", "生成时间: " + time.strftime("%Y-%m-%d %H:%M:%S"), ""]

        for menu, sub in PAGES:
            if menu != cur_menu:
                top.click("#%s" % MENU_ID[menu])
                page.wait_for_timeout(2200)
                cur_menu = menu
            try:
                mf.locator("text=" + sub).first.click()
                page.wait_for_timeout(2400)
            except Exception as e:
                chunks.append("## %s > %s" % (menu, sub))
                chunks.append("")
                chunks.append("!! 无法打开: %s" % str(e)[:80])
                chunks.append("")
                continue
            url = mf.evaluate("location.href")
            body = mf.inner_text("body")
            # 去掉左侧二级菜单行
            tail = body
            chunks.append("## %s > %s" % (menu, sub))
            chunks.append("")
            chunks.append("页面: `%s`" % url)
            chunks.append("")
            chunks.append("```")
            chunks.append(clean(tail))
            chunks.append("```")
            chunks.append("")
            fields = mf.evaluate(FIELDS_JS)
            if fields:
                chunks.append("可填写项当前值：")
                chunks.extend(fields)
                chunks.append("")

        # 网络侧信息页内的标签页：上行/下行光接口
        for tab in ("上行接口信息", "下行光接口信息", "IPv6 WAN连接信息"):
            try:
                top.click("#mmStatu")
                page.wait_for_timeout(1800)
                mf.locator("text=网络侧信息").first.click()
                page.wait_for_timeout(2000)
                mf.locator("text=" + tab).first.click()
                page.wait_for_timeout(2200)
                chunks.append("## 状态 > 网络侧信息 > %s" % tab)
                chunks.append("")
                chunks.append("```")
                chunks.append(clean(mf.inner_text("body")))
                chunks.append("```")
                chunks.append("")
            except Exception as e:
                chunks.append("## 状态 > 网络侧信息 > %s" % tab)
                chunks.append("")
                chunks.append("!! 无法打开: %s" % str(e)[:80])
                chunks.append("")

        os.makedirs(os.path.dirname(OUT) or ".", exist_ok=True)
        with open(OUT, "w", encoding="utf-8") as f:
            f.write("\n".join(chunks))
        print("快照已保存:", OUT, os.path.getsize(OUT), "bytes")


if __name__ == "__main__":
    main()
