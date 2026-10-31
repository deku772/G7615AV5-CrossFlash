#!/usr/bin/env python3
"""第四轮：dump 关键页面原始 HTML，用于确认字段语义（WLAN 密码映射 / 协议开关 / 前缀管理）。"""
import os
import sys
import re

os.environ.setdefault("NO_PROXY", "127.0.0.1,localhost")
os.environ.setdefault("no_proxy", "127.0.0.1,localhost")

from playwright.sync_api import sync_playwright

BASE = "http://192.168.1.1"
PWD = os.environ.get("ZTE_ADMIN_PASS", "CUAdmin")  # 管理账号密码，可用环境变量覆盖
OUTDIR = ".temp/html"


def main():
    os.makedirs(OUTDIR, exist_ok=True)
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

        def save(name):
            html = mf.content()
            with open(os.path.join(OUTDIR, name + ".html"), "w", encoding="utf-8") as f:
                f.write(html)
            print("saved", name, len(html))

        # WLAN 2.4G
        top.click("#mmNet")
        page.wait_for_timeout(2200)
        mf.locator("text=WLAN配置").first.click()
        page.wait_for_timeout(2400)
        mf.locator("text=无线基本配置(2.4G)").first.click()
        page.wait_for_timeout(2500)
        save("wlan_24g")

        # 协议开关
        top.click("#mmManager")
        page.wait_for_timeout(2200)
        for sub in ("协议开关", "系统日志"):
            try:
                mf.locator("text=" + sub).first.click()
                page.wait_for_timeout(2400)
                save("dev_" + sub)
            except Exception as e:
                print("fail", sub, str(e)[:100])

        # 前缀管理 (顶部菜单)
        top.click("#mmNet")
        page.wait_for_timeout(2000)
        try:
            mf.locator("text=前缀管理").first.click()
            page.wait_for_timeout(2500)
            save("prefix_mgr")
        except Exception as e:
            print("fail prefix", str(e)[:100])

        # 上行线路配置 HTML（含 VLAN 联动 JS）
        top.click("#mmNet")
        page.wait_for_timeout(2000)
        mf.locator("text=上行线路配置").first.click()
        page.wait_for_timeout(2400)
        save("wan_conf")

        browser.close()


if __name__ == "__main__":
    main()
