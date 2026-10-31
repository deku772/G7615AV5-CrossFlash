#!/usr/bin/env python3
"""实机取证(2)：定位"逻辑ID注册信息"与"远程管理状态"两个状态页的真实内容。

做法：遍历状态页所有二级标签，点击后把 innerText 全量导出。
只读探测，不修改任何配置。
"""
import os
import sys

os.environ.setdefault("NO_PROXY", "127.0.0.1,localhost")
os.environ.setdefault("no_proxy", "127.0.0.1,localhost")

from playwright.sync_api import sync_playwright

BASE = "http://192.168.1.1"
PWD = os.environ.get("ZTE_ADMIN_PASS", "CUAdmin")
OUT = sys.argv[1] if len(sys.argv) > 1 else ".temp/probe_loid2.txt"

TABS = ["设备信息", "网络侧信息", "用户侧信息", "统计数据",
        "远程管理状态", "语音信息", "逻辑ID注册信息", "MESH 拓扑图", "插件状态"]


def main():
    log = []
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=False,
                                    args=["--no-first-run", "--no-default-browser-check"])
        ctx = browser.new_context(viewport={"width": 1600, "height": 1100})
        page = ctx.new_page()
        page.goto(BASE + "/", wait_until="domcontentloaded", timeout=40000)
        page.wait_for_timeout(1500)
        if page.evaluate("!!document.getElementById('Frm_Password')"):
            page.evaluate("GetAccessAccount('adm')")
            page.fill("#Frm_Password", PWD)
            page.click("#LoginId")
            page.wait_for_timeout(5000)

        page.goto(BASE + "/unicom.html", wait_until="domcontentloaded", timeout=25000)
        page.wait_for_timeout(1500)
        # 打开"状态"菜单
        try:
            page.click("#menu0")
        except Exception:
            pass
        page.wait_for_timeout(2500)
        mf = page.frame(name="mainFrame")
        if mf is None:
            log.append("[!] 没有 mainFrame")
        else:
            for tab in TABS:
                try:
                    ok = mf.evaluate("""(function(t){
                        var el=Array.from(document.querySelectorAll('a,span,li,td,div'))
                          .find(e=>e.innerText && e.innerText.trim()===t);
                        if(el){ el.click(); return true; } return false;
                    })(""", )
                except Exception:
                    pass
                # 上面的 evaluate 需要传参，改用 locator
                try:
                    mf.get_by_text(tab, exact=True).first.click(timeout=6000)
                except Exception as e:
                    log.append(f"[tab:{tab}] 点击失败 {e}")
                    continue
                page.wait_for_timeout(3000)
                txt = mf.evaluate("document.body ? document.body.innerText : ''")
                log.append("\n" + "=" * 74)
                log.append("== 状态 > " + tab)
                log.append("=" * 74)
                # 去掉重复的菜单行
                lines = [l.strip() for l in txt.split("\n") if l.strip()]
                # 找到第一条"网上营业厅"作为结束
                out = []
                for l in lines:
                    if l.startswith("网上营业厅"):
                        break
                    if l.startswith("状态") and len(l) < 300:
                        out.append(l)
                        continue
                    out.append(l)
                log.append("\n".join(out[-60:]))

    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(log))
    print("written", OUT)


if __name__ == "__main__":
    main()
