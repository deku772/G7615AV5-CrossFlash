#!/usr/bin/env python3
"""联通光猫 G7615AV5 网页操作助手。

通过 Playwright 接管本机 Edge（--remote-debugging-port=9222），
用真实页面交互完成登录、状态查看、WAN 配置等操作。

用法示例：
    python tools/zte_ui.py status          # 查看 ONU 注册状态 + WAN 连接
    python tools/zte_ui.py wanlist         # 列出 WAN 连接
    python tools/zte_ui.py setpppoe <账号> <密码> [vlan] [mtu]
"""
import os
import sys
import time

os.environ.setdefault("NO_PROXY", "127.0.0.1,localhost")
os.environ.setdefault("no_proxy", "127.0.0.1,localhost")

from playwright.sync_api import sync_playwright  # noqa: E402

BASE = "http://192.168.1.1"
CDP = "http://127.0.0.1:9222"
SHOT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".temp")


class Modem:
    def __init__(self, page):
        self.page = page

    # ---------- 基础 ----------
    def login(self, user="CUAdmin", pwd="CUAdmin", acct="adm"):
        pg = self.page
        pg.goto(BASE + "/", wait_until="domcontentloaded", timeout=30000)
        pg.wait_for_timeout(1200)
        if not pg.evaluate("!!document.getElementById('Frm_Password')"):
            return False  # 已在管理界面
        pg.evaluate("GetAccessAccount('%s')" % acct)
        pg.fill("#Frm_Password", pwd)
        pg.click("#LoginId")
        pg.wait_for_timeout(4000)
        return pg.evaluate("!document.getElementById('Frm_Password')")

    def top(self):
        return self.page.frame(name="topFrame")

    def main(self):
        return self.page.frame(name="mainFrame")

    def click_top(self, menu_id):
        """点击顶部主菜单图标：0 状态 / 1 基本配置 / 2 高级配置 / 3 设备管理 / 4 快速配置"""
        self.page.click("#menu%s" % menu_id)
        for _ in range(20):
            if self.page.frame(name="topFrame"):
                break
            self.page.wait_for_timeout(300)
        self.page.wait_for_timeout(1500)

    def click_sub(self, text, wait=2200):
        """点击内容区左侧二级菜单文字"""
        self.main().locator("text=" + text).first.click()
        self.page.wait_for_timeout(wait)

    def main_text(self, limit=2000):
        return self.main().inner_text("body")[:limit].replace("\n", " | ")

    def main_url(self):
        return self.main().evaluate("location.href")

    def shot(self, name):
        path = os.path.join(SHOT_DIR, name)
        self.page.screenshot(path=path, full_page=True)
        return path


def run(fn):
    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(CDP)
        ctx = browser.contexts[0]
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.set_viewport_size({"width": 1400, "height": 950})
        m = Modem(page)
        if not m.login():
            # 已登录但停留在别的页面
            if not page.evaluate("!document.getElementById('Frm_Password')"):
                pass
        return fn(m)


# ---------------- 命令实现 ----------------
def cmd_status(m):
    m.click_top("0")
    print("== 设备信息 ==")
    print(m.main_text(900))
    m.click_sub("网络侧信息")
    print("\n== 网络侧信息 ==", m.main_url())
    print(m.main_text(1500))


def cmd_wanlist(m):
    m.click_top("1")
    print("== WAN 页面 ==", m.main_url())
    print(m.main_text(900))


def cmd_setpppoe(m, user, pwd, vlan="48", mtu="1492"):
    m.click_top("1")
    # 选中已有的 INTERNET WAN
    sel = m.main().locator("select").first
    sel.select_option("IGD.WD1.WCD3.WCPPP1")
    m.page.wait_for_timeout(2500)
    print("== 选中后表单 ==")
    print(m.main_text(1200))
    fields = m.main().evaluate(
        """(function(){var out=[];document.querySelectorAll('input,select').forEach(function(e){
            if(e.type==='hidden') return;
            out.push({id:e.id,name:e.name,tag:e.tagName,type:e.type,val:(e.value||'').slice(0,30),checked:e.checked});});
            return out;})()"""
    )
    import json

    print(json.dumps(fields, ensure_ascii=False, indent=1))


def cmd_dumpfields(m):
    m.click_top("1")
    sel = m.main().locator("select").first
    sel.select_option("IGD.WD1.WCD3.WCPPP1")
    m.page.wait_for_timeout(2500)
    import json

    print(json.dumps(m.main().evaluate(
        """(function(){var out=[];document.querySelectorAll('input,select').forEach(function(e){
            out.push({id:e.id,name:e.name,tag:e.tagName,type:e.type,val:(e.value||'').slice(0,30),
                      opts:e.tagName==='SELECT'?Array.from(e.options).map(o=>o.value+'|'+o.text):null});});
            return out;})()"""), ensure_ascii=False, indent=1))


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    if cmd == "status":
        run(cmd_status)
    elif cmd == "wanlist":
        run(cmd_wanlist)
    elif cmd == "dumpfields":
        run(cmd_dumpfields)
    elif cmd == "setpppoe":
        u = sys.argv[2]
        pw = sys.argv[3]
        vlan = sys.argv[4] if len(sys.argv) > 4 else "48"
        mtu = sys.argv[5] if len(sys.argv) > 5 else "1492"
        run(lambda m: cmd_setpppoe(m, u, pw, vlan, mtu))
    else:
        print(__doc__)
