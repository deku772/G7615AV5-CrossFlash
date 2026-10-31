#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
G7615AV5 Web UI 自动化（Playwright + 系统 Chrome）

用法:
    python tools/web_ui.py probe            # 打开登录页，抓表单结构与截图
    python tools/web_ui.py login <user> <pwd>
    python tools/web_ui.py wan              # 进 WAN 配置页截图并抓文本
    python tools/web_ui.py shot <url> <out.png>
"""
import sys
import os
import json
import time

from playwright.sync_api import sync_playwright

HOST = "http://192.168.1.1"
SHOT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".temp")
os.makedirs(SHOT_DIR, exist_ok=True)

STATE_FILE = os.path.join(SHOT_DIR, "web_state.json")


def shot_dir(name):
    return os.path.join(SHOT_DIR, name)


def dump_inputs(page):
    out = []
    for el in page.query_selector_all("input"):
        out.append({
            "type": el.get_attribute("type"),
            "id": el.get_attribute("id"),
            "name": el.get_attribute("name"),
            "placeholder": el.get_attribute("placeholder"),
            "value": el.get_attribute("value"),
            "visible": el.is_visible(),
        })
    return out


def do_login(page, user, pwd):
    page.goto(HOST, timeout=30000)
    page.wait_for_timeout(2500)
    page.screenshot(path=shot_dir("web_00_login.png"), full_page=True)

    # 依据之前逆向：账号框 id=Frm_Username 之类，先按可见文本框顺序填
    inputs = page.query_selector_all("input")
    text_inputs = [i for i in inputs if i.is_visible()
                   and (i.get_attribute("type") in (None, "text", "password"))]
    print("可见输入框数量:", len(text_inputs))
    for i in text_inputs:
        print("   ", i.get_attribute("type"), i.get_attribute("id"),
              i.get_attribute("name"), i.get_attribute("placeholder"))

    if len(text_inputs) >= 2:
        # 有账号框 + 密码框
        text_inputs[0].fill(user)
        text_inputs[1].fill(pwd)
    elif len(text_inputs) == 1:
        # 只有密码框：账号靠页面切换决定，直接把密码填进去
        text_inputs[0].fill(pwd)
        print("单密码框模式，已填密码（账号由页面当前模式决定）")
    else:
        raise RuntimeError("找不到账号/密码输入框")

    page.screenshot(path=shot_dir("web_01_filled.png"), full_page=True)

    # 找登录按钮
    btn = None
    for sel in ("input[type=submit]", "button[type=submit]", "#Frm_Login", "input[value*='登录']",
                "button:has-text('登录')", "a:has-text('登录')", "[onclick*='login']", "[onclick*='Login']"):
        try:
            b = page.query_selector(sel)
            if b and b.is_visible():
                btn = b
                print("登录按钮 selector:", sel)
                break
        except Exception:
            pass
    if btn is None:
        page.keyboard.press("Enter")
    else:
        btn.click()

    page.wait_for_timeout(4000)
    print("登录后 URL:", page.url)
    print("登录后 TITLE:", page.title())
    page.screenshot(path=shot_dir("web_02_after_login.png"), full_page=True)

    body = page.inner_text("body")[:600]
    print("---- 页面文本 ----")
    print(body)

    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump({"url": page.url, "title": page.title()}, f, ensure_ascii=False)


def extract_wan(page):
    """抓取 WAN 配置页的可见文本、表格与所有包含错误关键词的节点"""
    texts = []
    try:
        texts.append(page.inner_text("body")[:3000])
    except Exception:
        pass
    errs = []
    for kw in ("错误", "失败", "无效", "不支持", "异常", "error", "Error", "alert"):
        try:
            for el in page.query_selector_all(f"text={kw}"):
                t = el.inner_text().strip()
                if t and t not in errs:
                    errs.append(t[:200])
        except Exception:
            pass
    return texts, errs


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "probe"
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, channel="chrome",
                                    args=["--start-maximized"])
        ctx = browser.new_context(viewport={"width": 1400, "height": 950},
                                  ignore_https_errors=True)
        page = ctx.new_page()

        if cmd == "probe":
            page.goto(HOST, timeout=30000)
            page.wait_for_timeout(2500)
            print("URL:", page.url)
            print("TITLE:", page.title())
            page.screenshot(path=shot_dir("web_00_login.png"), full_page=True)
            print(json.dumps(dump_inputs(page), ensure_ascii=False, indent=1))
            print("---- 可见文本 ----")
            print(page.inner_text("body")[:800])

        elif cmd == "login":
            do_login(page, sys.argv[2], sys.argv[3])
            page.wait_for_timeout(1500)

        elif cmd == "wan":
            # 账号密码必须从命令行传入，不在代码里留默认凭据
            if len(sys.argv) <= 3:
                sys.exit("用法: python web_ui.py wan <用户名> <密码>")
            do_login(page, sys.argv[2], sys.argv[3])
            # 先抓首页所有可点菜单
            links = []
            for a in page.query_selector_all("a, li, div[onclick]"):
                try:
                    if not a.is_visible():
                        continue
                    t = (a.inner_text() or "").strip()
                    if t and len(t) < 20:
                        links.append(t)
                except Exception:
                    pass
            print("---- 可见菜单/链接 ----")
            print(sorted(set(links)))

        elif cmd == "shot":
            page.goto(sys.argv[2], timeout=30000)
            page.wait_for_timeout(2500)
            page.screenshot(path=sys.argv[3], full_page=True)
            print("saved", sys.argv[3])

        elif cmd == "nav":
            # nav <user> <pwd> <menu1> [menu2] [menu3]
            # menu 支持模块名(status/network/security/manager/Register/help)
            # 或 CSS selector(以 # . [ 开头)，或页面上的文字
            do_login(page, sys.argv[2], sys.argv[3])
            MENU_IDX = {"status": 0, "network": 1, "security": 2,
                        "manager": 3, "Register": 4, "help": 5}
            menus = sys.argv[4:]
            for idx, m in enumerate(menus):
                page.wait_for_timeout(1500)
                ok = False
                if m in MENU_IDX:
                    try:
                        page.click(f"a.menu{MENU_IDX[m]}", timeout=8000)
                        ok = True
                        print(f"点击菜单[{idx}] {m} via a.menu{MENU_IDX[m]}")
                    except Exception as e:
                        print("click menuN fail:", str(e)[:100])
                if not ok and m[:1] in ".[#":
                    try:
                        page.click(m, timeout=8000)
                        ok = True
                        print(f"点击菜单[{idx}] {m} via selector")
                    except Exception as e:
                        print("click selector fail:", str(e)[:100])
                if not ok:
                    for sel in (f"text={m}", f"a:has-text('{m}')"):
                        try:
                            page.click(sel, timeout=5000)
                            ok = True
                            print(f"点击菜单[{idx}] {m} via {sel}")
                            break
                        except Exception:
                            pass
                if not ok:
                    print(f"!! 未找到菜单 {m}")
                    break
                page.wait_for_timeout(3500)
                page.screenshot(path=shot_dir(f"web_nav_{idx}_{m}.png"), full_page=True)
                print("URL:", page.url)
                try:
                    print("---- 页面文本 ----")
                    print(page.inner_text("body")[:1800])
                except Exception:
                    pass
            print("最终 URL:", page.url)

        elif cmd == "dumpall":
            # dumpall <user> <pwd> <menu>  保存该模块下所有 frame 的 HTML
            do_login(page, sys.argv[2], sys.argv[3])
            MENU_IDX = {"status": 0, "network": 1, "security": 2,
                        "manager": 3, "Register": 4, "help": 5}
            m = sys.argv[4]
            page.click(f"a.menu{MENU_IDX[m]}")
            page.wait_for_timeout(4000)
            for i, fr in enumerate(page.frames):
                try:
                    h = fr.content()
                except Exception:
                    continue
                fn = shot_dir(f"frame_{m}_{i}.html")
                with open(fn, "w", encoding="utf-8") as f:
                    f.write(h)
                print("frame", i, fr.url, "len", len(h), "->", fn)
            page.screenshot(path=shot_dir(f"web_dumpall_{m}.png"), full_page=True)

        elif cmd == "click":
            # click <user> <pwd> <module> <href子串|文字> [out.png]
            do_login(page, sys.argv[2], sys.argv[3])
            MENU_IDX = {"status": 0, "network": 1, "security": 2,
                        "manager": 3, "Register": 4, "help": 5}
            mod = sys.argv[4]
            target = sys.argv[5]
            out = sys.argv[6] if len(sys.argv) > 6 else shot_dir("web_click.png")
            page.click(f"a.menu{MENU_IDX[mod]}")
            page.wait_for_timeout(3500)
            hit = None
            for fi, fr in enumerate(page.frames):
                try:
                    for a in fr.query_selector_all("a"):
                        href = a.get_attribute("href") or ""
                        txt = (a.inner_text() or "").strip()
                        if target in href or (target and target in txt):
                            hit = (fi, a, href, txt)
                            break
                except Exception:
                    continue
                if hit:
                    break
            if not hit:
                print("!! 未找到目标链接:", target)
            else:
                fi, a, href, txt = hit
                print(f"点击 frame{fi} href={href[:110]} text={txt!r}")
                try:
                    a.click()
                except Exception as e:
                    print("click fail, 尝试 JS:", str(e)[:80])
                    href2 = href.split("nextpage=")[-1].split("&")[0]
                    page.frames[fi].evaluate(
                        "h => { if (h && h.indexOf('nextpage=') < 0) { window.location.href = 'getpage.gch?pid=1002&nextpage=' + h; } }",
                        href2)
                page.wait_for_timeout(4000)
            page.screenshot(path=out, full_page=True)
            print("saved", out, "url", page.url)
            for fi, fr in enumerate(page.frames):
                try:
                    t = fr.inner_text("body")
                except Exception:
                    continue
                if t and len(t.strip()) > 20:
                    print(f"==== frame{fi} {fr.url} ====")
                    print(t[:2500])

        elif cmd == "page":
            # page <user> <pwd> <url> [out.png]
            do_login(page, sys.argv[2], sys.argv[3])
            url = sys.argv[4]
            out = sys.argv[5] if len(sys.argv) > 5 else shot_dir("web_page.png")
            page.goto(url if url.startswith("http") else HOST + url, timeout=30000)
            page.wait_for_timeout(4000)
            page.screenshot(path=out, full_page=True)
            print("URL:", page.url, "->", out)
            print("---- 页面文本 ----")
            try:
                print(page.inner_text("body")[:3000])
            except Exception:
                pass
            # 抓表单控件
            print("---- 表单控件 ----")
            for el in page.query_selector_all("input, select, textarea, button"):
                try:
                    print("  ", el.evaluate("e => e.tagName"), el.get_attribute("type"),
                          "id=", el.get_attribute("id"), "name=", el.get_attribute("name"),
                          "value=", (el.get_attribute("value") or "")[:40],
                          "vis=", el.is_visible())
                except Exception:
                    pass
            html = page.content()
            with open(shot_dir("web_page_src.html"), "w", encoding="utf-8") as f:
                f.write(html)
            print("html saved len", len(html))

        elif cmd == "dump":
            do_login(page, sys.argv[2], sys.argv[3])
            page.wait_for_timeout(2000)
            html = page.content()
            out = shot_dir("web_index.html")
            with open(out, "w", encoding="utf-8") as f:
                f.write(html)
            print("html saved:", out, "len", len(html))
            import re
            urls = sorted(set(re.findall(r'[A-Za-z0-9_./?=&%-]*\.gch[A-Za-z0-9_./?=&%-]*', html)))
            print("---- .gch 链接 (%d) ----" % len(urls))
            for u in urls:
                print("  ", u)
            funcs = sorted(set(re.findall(r'on(?:click|mouseover)\s*=\s*["\']([^"\']{1,90})', html)))
            print("---- onclick/onmouseover (%d) ----" % len(funcs))
            for f in funcs[:80]:
                print("  ", f)

        elif cmd == "fetch":
            # fetch <user> <pwd> <url> <outfile>
            do_login(page, sys.argv[2], sys.argv[3])
            url = sys.argv[4]
            out = sys.argv[5] if len(sys.argv) > 5 else shot_dir("web_fetch.txt")
            txt = page.evaluate("u => fetch(u, {credentials:'include'}).then(r => r.text())", url)
            with open(out, "w", encoding="utf-8") as f:
                f.write(txt)
            print("fetched", url, "len", len(txt), "->", out)
            print(txt[:2000])

        browser.close()


if __name__ == "__main__":
    main()
