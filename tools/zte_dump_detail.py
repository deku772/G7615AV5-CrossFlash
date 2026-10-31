#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
补抓 G7615AV5 Web 界面的关键配置页细节（宽带设置 / IPv6 / 绑定 / WLAN），
追加到 docs/web-ui-structure.md 末尾。

用法: python tools/zte_dump_detail.py [输出路径]
"""
import os
import sys
import time

os.environ.setdefault("NO_PROXY", "127.0.0.1,localhost")
os.environ.setdefault("no_proxy", "127.0.0.1,localhost")

OUT = sys.argv[1] if len(sys.argv) > 1 else "docs/web-ui-structure.md"
CDP = "http://127.0.0.1:9222"
BASE = "http://192.168.1.1"

FIELDS_JS = """(function(){
  var res=[];
  document.querySelectorAll('input,select,textarea').forEach(function(e){
    if(e.type==='hidden') return;
    var lab='';
    var tr=e.closest('tr');
    if(tr){ var tds=tr.querySelectorAll('td');
      if(tds.length>1) lab=(tds[0].innerText||'').trim(); }
    if(!lab){ var p=e.parentElement;
      for(var i=0;i<4&&p;i++,p=p.parentElement){ var pv=p.previousElementSibling;
        if(pv && !pv.querySelector('input,select,textarea')){ var t=(pv.innerText||'').trim();
          if(t&&t.length<26){lab=t;break;} } } }
    var opts=null;
    if(e.tagName==='SELECT') opts=Array.from(e.options).map(function(o){return o.value+(o.selected?'*':'');}).join(',');
    res.push({id:e.id||'(no-id)', type:e.type||e.tagName, label:lab.slice(0,34),
              val:String(e.value||'').slice(0,44),
              checked:(e.type==='checkbox'||e.type==='radio')?e.checked:null, opts:opts});
  });
  return res;})()"""

LABELS_JS = """Array.from(document.querySelectorAll('a,li,span,td')).filter(function(e){
    var t=(e.innerText||'').trim();
    return t && t.length<=18 && t.length>=2 && !e.querySelector('a,table,input,select') && (e.getAttribute('onclick')||'');
  }).map(function(e){return (e.innerText||'').trim();}).filter(function(v,i,a){return a.indexOf(v)===i;})"""


def boot(page):
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


def dump_fields(mf):
    out = []
    for f in mf.evaluate(FIELDS_JS):
        if f["id"] in ("Frm_Logintoken", "Frm_Loginchecktoken", "Frm_UserRandomNum"):
            continue
        out.append("| %s | `%s` | %s | %s | %s |" % (
            (f["label"] or "").replace("|", "\\|"),
            f["id"], f["type"],
            (f["val"] or "").replace("|", "\\|"),
            (f["opts"] or "").replace("|", "\\|")))
    return out


def main():
    from playwright.sync_api import sync_playwright

    chunks = ["", "---", "", "## 附录 · 关键配置页字段明细", ""]

    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(CDP)
        ctx = browser.contexts[0]
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        top, mf = boot(page)

        # ============ A. 宽带设置（上游线路配置） ============
        top.click("#mmNet")
        page.wait_for_timeout(3200)
        chunks.append("### A. 宽带设置（`IPv46_net_wan_conf_t.gch`）")
        chunks.append("")
        chunks.append("URL: `/getpage.gch?pid=1002&nextpage=IPv46_net_wan_conf_t.gch`")
        chunks.append("")
        opts = mf.evaluate(
            "Array.from(document.querySelectorAll('#Frm_WANCName0 option')).map(o=>o.value+'|'+o.text)")
        chunks.append("WAN 连接下拉（`#Frm_WANCName0`）：")
        chunks.append("")
        for o in opts:
            chunks.append("- `%s`" % o)
        chunks.append("")

        for value, label in [("IGD.WD1.WCD3.WCPPP1", "INTERNET (PPPoE)"),
                             ("IGD.WD1.WCD3.WCBRIDGE3", "IPTV (Bridge)")]:
            try:
                mf.locator("#Frm_WANCName0").select_option(value)
                page.wait_for_timeout(3000)
            except Exception as e:
                chunks.append("#### %s —— 选择失败 %s" % (label, str(e)[:60]))
                chunks.append("")
                continue
            chunks.append("#### %s（`%s`）" % (label, value))
            chunks.append("")
            chunks.append("| 标签 | id | 类型 | 当前值 | 选项 |")
            chunks.append("|---|---|---|---|---|")
            chunks += dump_fields(mf)
            chunks.append("")

        # 新建 WAN 表单
        try:
            mf.locator("#Frm_WANCName0").select_option("-1")
            page.wait_for_timeout(3000)
            chunks.append("#### 新建 WAN 连接（选“新建”后的空表单）")
            chunks.append("")
            chunks.append("| 标签 | id | 类型 | 当前值 | 选项 |")
            chunks.append("|---|---|---|---|---|")
            chunks += dump_fields(mf)
            chunks.append("")
        except Exception as e:
            chunks.append("> 新建表单抓取失败: %s" % str(e)[:80])
            chunks.append("")

        # ============ B. IPv6 相关 ============
        top.click("#mmNet")
        page.wait_for_timeout(2800)
        for tabname in ["RA配置", "DHCPv6配置", "IPv6前缀管理"]:
            try:
                mf.locator("text=" + tabname).first.click()
                page.wait_for_timeout(2600)
                chunks.append("### B. LAN配置 → %s" % tabname)
                chunks.append("")
                chunks.append("URL: `%s`" % mf.evaluate("location.href").replace(BASE, ""))
                chunks.append("")
                chunks.append("| 标签 | id | 类型 | 当前值 | 选项 |")
                chunks.append("|---|---|---|---|---|")
                chunks += dump_fields(mf)
                chunks.append("")
            except Exception as e:
                chunks.append("### B. LAN配置 → %s —— 打开失败 (%s)" % (tabname, str(e)[:50]))
                chunks.append("")

        # 高级配置 → IPv6控制
        try:
            top.click("#mmAdv")
            page.wait_for_timeout(2800)
            mf.locator("text=IPv6控制").first.click()
            page.wait_for_timeout(2600)
            chunks.append("### B2. 高级配置 → IPv6控制")
            chunks.append("")
            chunks.append("URL: `%s`" % mf.evaluate("location.href").replace(BASE, ""))
            chunks.append("")
            chunks.append("| 标签 | id | 类型 | 当前值 | 选项 |")
            chunks.append("|---|---|---|---|---|")
            chunks += dump_fields(mf)
            chunks.append("")
        except Exception as e:
            chunks.append("### B2. 高级配置 → IPv6控制 —— 打开失败 (%s)" % str(e)[:50])
            chunks.append("")

        # ============ C. 绑定设置 ============
        try:
            top.click("#mmNet")
            page.wait_for_timeout(2800)
            mf.locator("text=绑定设置").first.click()
            page.wait_for_timeout(2800)
            chunks.append("### C. 绑定设置")
            chunks.append("")
            chunks.append("URL: `%s`" % mf.evaluate("location.href").replace(BASE, ""))
            chunks.append("")
            chunks.append("| 标签 | id | 类型 | 当前值 | 选项 |")
            chunks.append("|---|---|---|---|---|")
            chunks += dump_fields(mf)
            chunks.append("")
            chunks.append("连接名下拉：")
            chunks.append("")
            for o in mf.evaluate(
                    "Array.from(document.querySelectorAll('select')).map(s=>s.id+' :: '+Array.from(s.options).map(o=>o.value+(o.selected?'*':'')).join(','))"):
                chunks.append("- `%s`" % o)
            chunks.append("")
        except Exception as e:
            chunks.append("### C. 绑定设置 —— 打开失败 (%s)" % str(e)[:50])
            chunks.append("")

        # ============ D. WLAN 2.4G / 5G ============
        try:
            top.click("#mmNet")
            page.wait_for_timeout(2800)
            mf.locator("text=WLAN配置").first.click()
            page.wait_for_timeout(2800)
            for tabname in ["无线基本配置(2.4G)", "无线基本配置(5G)"]:
                try:
                    mf.locator("text=" + tabname).first.click()
                    page.wait_for_timeout(2600)
                    chunks.append("### D. WLAN配置 → %s" % tabname)
                    chunks.append("")
                    chunks.append("URL: `%s`" % mf.evaluate("location.href").replace(BASE, ""))
                    chunks.append("")
                    chunks.append("| 标签 | id | 类型 | 当前值 | 选项 |")
                    chunks.append("|---|---|---|---|---|")
                    for line in dump_fields(mf):
                        if any(k in line for k in ["SSID", "ESSID", "Passphrase", "KeyPass", "SSIDEnable", "ESSIDHide"]):
                            chunks.append(line)
                    chunks.append("")
                except Exception as e:
                    chunks.append("### D. WLAN配置 → %s —— 失败 (%s)" % (tabname, str(e)[:50]))
                    chunks.append("")
        except Exception as e:
            chunks.append("### D. WLAN配置 —— 失败 (%s)" % str(e)[:50])
            chunks.append("")

        # ============ E. 上行方式 ============
        try:
            top.click("#mmManager")
            page.wait_for_timeout(2800)
            mf.locator("text=上行方式").first.click()
            page.wait_for_timeout(2600)
            body = mf.inner_text("body")
            chunks.append("### E. 设备管理 → 上行方式")
            chunks.append("")
            chunks.append("URL: `%s`" % mf.evaluate("location.href").replace(BASE, ""))
            chunks.append("")
            chunks.append("```")
            for line in body.splitlines():
                if line.strip():
                    chunks.append(line.strip())
            chunks.append("```")
            chunks.append("")
        except Exception as e:
            chunks.append("### E. 上行方式 —— 失败 (%s)" % str(e)[:50])
            chunks.append("")

    with open(OUT, "a", encoding="utf-8") as f:
        f.write("\n".join(chunks) + "\n")
    print("appended:", OUT)


if __name__ == "__main__":
    main()
