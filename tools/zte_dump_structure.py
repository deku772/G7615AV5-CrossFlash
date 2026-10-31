#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
抓取联通 G7615AV5 Web 管理界面的完整页面结构，输出 Markdown 交接文档。

产出:
  docs/web-ui-structure.md

用法:
  python tools/zte_dump_structure.py [输出路径]

前置:
  1. Edge 以调试端口启动（见 README Step 10）
  2. 光猫可达 192.168.1.1，账号 CUAdmin/CUAdmin
"""
import os
import sys
import time

os.environ.setdefault("NO_PROXY", "127.0.0.1,localhost")
os.environ.setdefault("no_proxy", "127.0.0.1,localhost")

OUT = sys.argv[1] if len(sys.argv) > 1 else "docs/web-ui-structure.md"

CDP = "http://127.0.0.1:9222"
BASE = "http://192.168.1.1"

# 主菜单 -> (顶部菜单元素 id, 显示名)
MENUS = [
    ("mmStatu", "状态"),
    ("mmNet", "基本配置"),
    ("mmAdv", "高级配置"),
    ("mmManager", "设备管理"),
]

# 表单里需要隐藏的公共控件
NOISE = {"Frm_Logintoken", "Frm_Loginchecktoken", "Frm_UserRandomNum"}


def clean(text):
    lines = [l.strip() for l in (text or "").splitlines()]
    return "\n".join(l for l in lines if l)


def boot(page):
    """登录并进入框架页，返回 (top_frame, main_frame)。"""
    page.set_viewport_size({"width": 1500, "height": 1000})
    page.goto(BASE + "/", wait_until="domcontentloaded", timeout=40000)
    page.wait_for_timeout(1500)
    if page.evaluate("!!document.getElementById('Frm_Password')"):
        page.evaluate("GetAccessAccount('adm')")
        page.fill("#Frm_Password", "CUAdmin")
        page.click("#LoginId")
        page.wait_for_timeout(6000)
    if not page.frame(name="topFrame"):
        page.click("#menu0")
        for _ in range(30):
            if page.frame(name="topFrame"):
                break
            page.wait_for_timeout(400)
    page.wait_for_timeout(1500)
    return page.frame(name="topFrame"), page.frame(name="mainFrame")


def menu_items(mf):
    """提取左侧菜单项：文本 + 触发方式。"""
    return mf.evaluate(
        """(function(){
          var out=[], seen={};
          document.querySelectorAll('a').forEach(function(e){
            var t=(e.innerText||'').trim();
            if(!t || t.length>18) return;
            if(seen[t]) return; seen[t]=1;
            out.push({t:t, oc:(e.getAttribute('onclick')||'').slice(0,120),
                      href:(e.getAttribute('href')||'').slice(0,120)});
          });
          return out;})()"""
    )


def page_url(mf):
    try:
        return mf.evaluate("location.href")
    except Exception:
        return "(unreachable)"


def fields(mf):
    """导出页面上所有可见/可交互控件，按行标签配对。"""
    return mf.evaluate(
        """(function(){
          var res=[];
          document.querySelectorAll('input,select,textarea').forEach(function(e){
            if(e.type==='hidden') return;
            var lab='';
            var tr=e.closest('tr');
            if(tr){
              var tds=tr.querySelectorAll('td');
              if(tds.length>1) lab=(tds[0].innerText||'').trim();
            }
            if(!lab){
              // 找左侧最近的文本单元格
              var p=e.parentElement;
              for(var i=0;i<4 && p;i++,p=p.parentElement){
                var prev=p.previousElementSibling;
                if(prev && !prev.querySelector('input,select,textarea')){
                  var t=(prev.innerText||'').trim();
                  if(t && t.length<24){ lab=t; break; }
                }
              }
            }
            var val=e.value||'';
            var opts=null;
            if(e.tagName==='SELECT'){
              opts=Array.from(e.options).map(function(o){return o.value+(o.selected?'*':'');}).join(',');
            }
            res.push({id:e.id||'(no-id)', name:e.name||'', type:e.type||e.tagName,
                      label:lab.slice(0,34), val:String(val).slice(0,42),
                      checked:e.type==='checkbox'||e.type==='radio'?e.checked:null,
                      opts:opts});
          });
          return res;})()"""
    )


def tabs(mf):
    """页面内的标签页（tab）文字。"""
    return mf.evaluate(
        """(function(){
          var out=[], seen={};
          document.querySelectorAll('a,li,span,td').forEach(function(e){
            var t=(e.innerText||'').trim();
            if(!t || t.length>16 || t.length<2) return;
            if(e.querySelector('a,table,input,select')) return;
            var oc=e.getAttribute('onclick')||'';
            if(!oc) return;
            if(seen[t]) return; seen[t]=1;
            out.push(t);
          });
          return out;})()"""
    )


def open_sub(page, mf, text):
    """点击左侧菜单文字，返回 (是否成功, 落地 URL)。"""
    try:
        loc = mf.locator("text=" + text).first
        loc.click(timeout=8000)
        page.wait_for_timeout(2600)
        return True, page_url(mf)
    except Exception:
        return False, page_url(mf)


def md_escape(s):
    return (s or "").replace("|", "\\|").replace("\n", " ")


def main():
    from playwright.sync_api import sync_playwright

    chunks = []
    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(CDP)
        ctx = browser.contexts[0]
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        top, mf = boot(page)

        chunks.append("# 联通 G7615AV5 Web 管理界面 · 页面结构交接文档")
        chunks.append("")
        chunks.append("> 本文档由 `tools/zte_dump_structure.py` 自动抓取生成。")
        chunks.append("> 抓取时间: " + time.strftime("%Y-%m-%d %H:%M:%S"))
        chunks.append("")

        # ---------- 框架层 ----------
        chunks.append("## 1. 整体框架")
        chunks.append("")
        chunks.append("```")
        chunks.append("http://192.168.1.1/            单页菜单 (#menu0 ~ #menu6)")
        chunks.append("  └─ 点击菜单 → enterFrame() → template.gch")
        chunks.append("       ├─ topFrame    主菜单栏  (#mmStatu / #mmNet / #mmAdv / #mmManager)")
        chunks.append("       └─ mainFrame   内容区    (getpage.gch?pid=1002&nextpage=<页面>.gch)")
        chunks.append("```")
        chunks.append("")
        chunks.append("| 元素 | 作用 | 说明 |")
        chunks.append("|---|---|---|")
        chunks.append("| `#Frm_Password` | 登录密码输入框 | 表单真实字段名是 `Password`，`id=UserPW` 只是元素 id |")
        chunks.append("| `#LoginId` | 登录按钮 | 需先执行 `GetAccessAccount('adm')` 选账户类型 |")
        chunks.append("| `#Frm_Loginchecktoken` | 动态令牌 | 每次会话不同，提交前必须从当前页重取 |")
        chunks.append("| `UserRandomNum` | 随机数 | 与密码一起做 `sha256(明文 + 随机数)` |")
        chunks.append("| `accountType` | `adm` / `oth` | 对应 DevAuthInfo 的 Level2 / Level1 行 |")
        chunks.append("")
        chunks.append("登录提交字段（已实测有效）：")
        chunks.append("")
        chunks.append("```")
        chunks.append("Frm_Logintoken=0")
        chunks.append("Frm_Loginchecktoken=<当前页 token>")
        chunks.append("_cu_url=1")
        chunks.append("Right=1")
        chunks.append("Username=")
        chunks.append("UserRandomNum=<8位随机数>")
        chunks.append("Password=sha256(密码明文 + UserRandomNum)")
        chunks.append("action=login")
        chunks.append("accountType=adm|oth")
        chunks.append("```")
        chunks.append("")

        # ---------- 逐主菜单 ----------
        page_no = 0
        for mid, mname in MENUS:
            try:
                top.click("#" + mid)
                page.wait_for_timeout(3000)
            except Exception as e:
                chunks.append("## %s · 无法打开 (%s)" % (mname, str(e)[:60]))
                chunks.append("")
                continue

            landing = page_url(mf)
            chunks.append("## %s  (`#%s`)" % (mname, mid))
            chunks.append("")
            chunks.append("入口页: `%s`" % landing.replace(BASE, ""))
            chunks.append("")

            items = menu_items(mf)
            if not items:
                chunks.append("_该菜单为单页，无左侧子菜单。_")
                chunks.append("")
                chunks.append("### 控件")
                chunks.append("")
                chunks.append("| 标签 | id | 类型 | 当前值 | 选项 |")
                chunks.append("|---|---|---|---|---|")
                for f in fields(mf):
                    if f["id"] in NOISE:
                        continue
                    chunks.append(
                        "| %s | `%s` | %s | %s | %s |"
                        % (
                            md_escape(f["label"]),
                            f["id"],
                            f["type"],
                            md_escape(f["val"]),
                            md_escape(f["opts"]),
                        )
                    )
                chunks.append("")
                continue

            chunks.append("| 子菜单 | 触发方式 |")
            chunks.append("|---|---|")
            for it in items:
                trig = it["oc"] or ("href=" + it["href"]) or "-"
                chunks.append("| %s | `%s` |" % (md_escape(it["t"]), md_escape(trig)))
            chunks.append("")

            for it in items:
                page_no += 1
                ok, url = open_sub(page, mf, it["t"])
                chunks.append("### %s" % it["t"])
                chunks.append("")
                if not ok:
                    chunks.append("> 打开失败或无独立内容页。")
                    chunks.append("")
                    continue
                chunks.append("URL: `%s`" % url.replace(BASE, ""))
                chunks.append("")
                tb = tabs(mf)
                if tb:
                    chunks.append("页内标签: " + "、".join(tb))
                    chunks.append("")
                fs = [f for f in fields(mf) if f["id"] not in NOISE]
                if fs:
                    chunks.append("| 标签 | id | 类型 | 当前值 | 选项 |")
                    chunks.append("|---|---|---|---|---|")
                    for f in fs:
                        chunks.append(
                            "| %s | `%s` | %s | %s | %s |"
                            % (
                                md_escape(f["label"]),
                                f["id"],
                                f["type"],
                                md_escape(f["val"]),
                                md_escape(f["opts"]),
                            )
                        )
                    chunks.append("")
                else:
                    chunks.append("_纯展示页，无表单控件。_")
                    chunks.append("")

    os.makedirs(os.path.dirname(OUT) or ".", exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(chunks) + "\n")
    print("written:", OUT, len("\n".join(chunks)), "chars")


if __name__ == "__main__":
    main()
