#!/usr/bin/env python3
"""诊断「连 WiFi 跳 LOID 认证页」问题。

排查项：
  1. 状态 > 逻辑ID注册信息  —— LOID/TR-069 注册是否完成
  2. 状态 > 远程管理状态    —— ACS 会话状态
  3. 高级配置 > LOID配置     —— LOID 值与「认证注册」按钮
  4. 基本配置 > LAN配置      —— DHCP 下发的 DNS
  5. 基本配置 > 远程管理    —— TR-069 ACS 参数
  6. 全站搜索「认证/跳转/Portal」相关开关

用法: python tools/probe_portal.py
"""
import os
import sys

for k in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy", "ALL_PROXY", "all_proxy"):
    os.environ.pop(k, None)
os.environ["NO_PROXY"] = "192.168.1.1,127.0.0.1,localhost"
os.environ["no_proxy"] = os.environ["NO_PROXY"]

from playwright.sync_api import sync_playwright  # noqa: E402

BASE = "http://192.168.1.1"
CDP = "http://127.0.0.1:9222"
PWD = os.environ.get("ZTE_ADMIN_PASS", "CUAdmin")
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".temp", "portal.txt")

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
    out.push('  - '+(lab||e.id)+' : '+v+(e.disabled?' [DISABLED]':''));
  });
  return out;})()"""

ALL_OPTS_JS = """(function(){
  var out=[];
  document.querySelectorAll('select').forEach(function(s){
    out.push('  [select#'+s.id+'] '+Array.from(s.options).map(o=>o.value+' | '+o.text).join('  ||  '));
  });
  return out;})()"""

TEXT_JS = """(function(){
  var t=document.body.innerText||'';
  var hits=[];
  t.split('\\n').forEach(function(l){
    l=l.trim(); if(!l) return;
    if(/认证|跳转|注册|门户|portal|强制|重定向|登录页|上网认证|强制上网/i.test(l)) hits.push(l);
  });
  return hits.slice(0,80);})()"""


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
        log.append("[login] 密码框仍在 = " + str(page.evaluate("!!document.getElementById('Frm_Password')")))
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
        top = page.frame(name="topFrame")
        mf = page.frame(name="mainFrame")
        if top is None or mf is None:
            log.append("!! 未进入框架页")
            print("\n".join(log))
            return

        def sec(t):
            log.append("")
            log.append("=" * 78)
            log.append("== " + t)
            log.append("=" * 78)

        def dump(title, opts=True):
            sec(title)
            log.append("URL: " + mf.evaluate("location.href"))
            log.append(clean(mf.inner_text("body"))[:2500])
            fs = mf.evaluate(FIELDS_JS)
            if fs:
                log.append("--- fields ---")
                log.extend(fs)
            if opts:
                o = mf.evaluate(ALL_OPTS_JS)
                if o:
                    log.append("--- selects ---")
                    log.extend(o)
            hits = mf.evaluate(TEXT_JS)
            if hits:
                log.append("--- 认证/跳转相关文本 ---")
                log.extend(hits)

        def go(menu, sub, wait=2600):
            top.click("#%s" % MENU_ID[menu])
            page.wait_for_timeout(2000)
            mf.locator("text=" + sub).first.click()
            page.wait_for_timeout(wait)

        for menu, sub in [
            ("状态", "逻辑ID注册信息"),
            ("状态", "远程管理状态"),
            ("状态", "设备信息"),
            ("高级配置", "LOID配置"),
            ("基本配置", "LAN配置"),
            ("基本配置", "远程管理"),
        ]:
            try:
                go(menu, sub)
                dump("%s > %s" % (menu, sub))
            except Exception as e:
                log.append("[%s > %s 失败] %s" % (menu, sub, str(e)[:160]))

        # ---- 安全设置（找强制跳转/认证开关）----
        try:
            go("高级配置", "安全设置")
            dump("高级配置 > 安全设置")
        except Exception as e:
            log.append("[安全设置 失败] %s" % str(e)[:160])

        # ---- 防火墙设置 ----
        try:
            go("高级配置", "防火墙设置")
            dump("高级配置 > 防火墙设置")
        except Exception as e:
            log.append("[防火墙设置 失败] %s" % str(e)[:160])

        try:
            browser.close()
        except Exception:
            pass

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(log))
    print("saved:", OUT, os.path.getsize(OUT), "bytes")


if __name__ == "__main__":
    main()
