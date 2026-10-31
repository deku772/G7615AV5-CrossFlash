#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""补抓：IPTV 连接明细 / RA+DHCPv6 标签页 / 上行方式选中项。"""
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


def rows(mf):
    out = []
    for f in mf.evaluate(FIELDS_JS):
        if f["id"] in ("Frm_Logintoken", "Frm_Loginchecktoken", "Frm_UserRandomNum"):
            continue
        out.append("| %s | `%s` | %s | %s | %s |" % (
            (f["label"] or "").replace("|", "\\|"), f["id"], f["type"],
            (f["val"] or "").replace("|", "\\|"), (f["opts"] or "").replace("|", "\\|")))
    return out


def click_text_js(mf, text):
    """用 JS 触发点击，绕过可见性/遮挡问题。返回是否点到。"""
    ok = mf.evaluate(
        """(function(t){
          var els=Array.from(document.querySelectorAll('a,span,li,td,div'));
          var hit=els.filter(function(e){
            var s=(e.innerText||'').trim();
            return s===t && !e.querySelector('a,table,input,select,div');
          });
          if(!hit.length) return false;
          hit[hit.length-1].click();
          return true;})(%s)""" % repr(text))
    return ok


def main():
    from playwright.sync_api import sync_playwright

    chunks = ["", "---", "", "## 附录二 · IPTV / IPv6 LAN 侧 / 上行方式", ""]

    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(CDP)
        ctx = browser.contexts[0]
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        top, mf = boot(page)

        # ===== A. IPTV 连接明细 =====
        top.click("#mmNet")
        page.wait_for_timeout(3200)
        try:
            mf.locator("#Frm_WANCName0").select_option("IGD.WD1.WCD4.WCIP1")
            page.wait_for_timeout(3200)
            chunks.append("### A. IPTV 桥接连接（`IGD.WD1.WCD4.WCIP1` / `3_IPTV_B_VID_3185`）")
            chunks.append("")
            chunks.append("| 标签 | id | 类型 | 当前值 | 选项 |")
            chunks.append("|---|---|---|---|---|")
            chunks += rows(mf)
            chunks.append("")
        except Exception as e:
            chunks.append("### A. IPTV —— 失败 (%s)" % str(e)[:80])
            chunks.append("")

        # ===== B. LAN配置 的 RA / DHCPv6 / IPv6前缀管理 标签页 =====
        top.click("#mmNet")
        page.wait_for_timeout(3000)
        mf.locator("text=LAN配置").first.click()
        page.wait_for_timeout(3000)
        for tab in ["RA配置", "DHCPv6配置", "IPv6前缀管理"]:
            if not click_text_js(mf, tab):
                chunks.append("### B. LAN配置 → %s —— 未找到可点击元素" % tab)
                chunks.append("")
                continue
            page.wait_for_timeout(3000)
            chunks.append("### B. LAN配置 → %s" % tab)
            chunks.append("")
            chunks.append("URL: `%s`" % mf.evaluate("location.href").replace(BASE, ""))
            chunks.append("")
            chunks.append("| 标签 | id | 类型 | 当前值 | 选项 |")
            chunks.append("|---|---|---|---|---|")
            chunks += rows(mf)
            chunks.append("")
            # 回到 DHCPv4 主页再切下一个标签
            mf.locator("text=LAN配置").first.click()
            page.wait_for_timeout(2500)

        # ===== C. 上行方式当前选中 =====
        try:
            top.click("#mmManager")
            page.wait_for_timeout(2800)
            click_text_js(mf, "上行方式")
            page.wait_for_timeout(2800)
            rad = mf.evaluate("""Array.from(document.querySelectorAll('input[type=radio],input[type=checkbox]')).map(function(e){
                var lab=''; var tr=e.closest('tr');
                if(tr){var tds=tr.querySelectorAll('td'); if(tds.length>1) lab=(tds[0].innerText||'').trim();}
                return {id:e.id, name:e.name, val:e.value, checked:e.checked, label:lab};})""")
            chunks.append("### C. 上行方式（`manager_Change_PonMode_qgw_t.gch`）")
            chunks.append("")
            chunks.append("| id | name | value | 选中 | 标签 |")
            chunks.append("|---|---|---|---|---|")
            for r in rad:
                chunks.append("| `%s` | %s | %s | %s | %s |" % (
                    r["id"], r["name"], r["val"], "YES" if r["checked"] else "-", r["label"]))
            chunks.append("")
        except Exception as e:
            chunks.append("### C. 上行方式 —— 失败 (%s)" % str(e)[:80])
            chunks.append("")

    with open(OUT, "a", encoding="utf-8") as f:
        f.write("\n".join(chunks) + "\n")
    print("appended:", OUT)


if __name__ == "__main__":
    main()
