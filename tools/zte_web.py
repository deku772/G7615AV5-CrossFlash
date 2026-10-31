# -*- coding: utf-8 -*-
"""光猫 web 自动化工具（登录 + 页面操作）。

登录协议（逆向自 /js/sha256.min.js + 登录页 JS）：
  UserRandomNum = 8位随机数
  UserPW        = sha256(明文密码 + UserRandomNum)
  提交字段: Frm_Logintoken=0, Frm_Loginchecktoken=<页面内固定串>,
            _cu_url=1(admin)/0(user), Right=1(admin)/2(user),
            Username='', UserRandomNum, UserPW, action=login, accountType=adm|oth

用法:
  python zte_web.py login <密码>                 # 登录并打印顶部菜单
  python zte_web.py dump <密码> <nextpage.gch>   # 抓取某页面的控件清单
"""
import os
import re
import sys

for _k in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy",
           "ALL_PROXY", "all_proxy"):
    os.environ.pop(_k, None)
os.environ["NO_PROXY"] = "192.168.1.1,127.0.0.1,localhost"
os.environ["no_proxy"] = os.environ["NO_PROXY"]

from playwright.sync_api import sync_playwright  # noqa: E402

BASE = "http://192.168.1.1"
LOG = []


def w(s=""):
    LOG.append(str(s))
    print(s, flush=True)


def _login(pg, pwd, acct="adm"):
    """在已打开的首页完成登录。返回 True 表示进入了管理界面。"""
    pg.goto(BASE + "/", wait_until="domcontentloaded", timeout=40000)
    pg.wait_for_timeout(1500)
    if not pg.evaluate("!!document.getElementById('Frm_Password')"):
        return True
    # 关键：先切到管理员账户，密码框才 enabled
    pg.evaluate("GetAccessAccount('%s')" % acct)
    pg.wait_for_timeout(600)
    pg.fill("#Frm_Password", pwd)
    pg.click("#LoginId")
    pg.wait_for_timeout(6000)
    return not pg.evaluate("!!document.getElementById('Frm_Password')")


JS_CONTROLS = r"""(function(){
  var o=[];
  document.querySelectorAll('input,select,textarea,button,a[onclick]').forEach(function(e){
    var t=(e.value||e.innerText||'').trim();
    var oc=String(e.getAttribute('onclick')||'');
    var id=e.id||'';
    if(!t && !id && !oc) return;
    o.push(e.tagName
      +' id='+id
      +' name='+(e.name||'')
      +' type='+(e.type||'')
      +' value='+String(e.value||'').slice(0,40)
      +' checked='+(e.checked===undefined?'':e.checked)
      +' disabled='+e.disabled
      +' text='+t.slice(0,30)
      +' oc='+oc.slice(0,90));
  });
  return o.join('\n');})()"""

JS_SELECT = r"""(function(){
  var o=[];
  document.querySelectorAll('select').forEach(function(s){
    o.push('SELECT id='+s.id+' name='+s.name+' value='+s.value
      +' | '+Array.prototype.map.call(s.options,function(x){
          return x.value+'|'+(x.text||'').trim();}).join(' ;; '));
  });
  return o.join('\n')||'(no select)';})()"""


def _dump_frame(pg, label):
    """打印 mainFrame 的正文与控件。"""
    try:
        mf = pg.frame(name="mainFrame")
    except Exception:
        mf = None
    if mf is None:
        w("[%s] 无 mainFrame" % label)
        return None
    w("=" * 20, label, "=" * 20)
    w("URL: " + mf.evaluate("location.href"))
    try:
        w("--- 正文 ---")
        w(mf.inner_text("body")[:2500])
    except Exception as e:
        w("正文读取失败 " + str(e)[:80])
    w("--- select ---")
    w(mf.evaluate(JS_SELECT))
    w("--- 控件 ---")
    w(mf.evaluate(JS_CONTROLS))
    return mf


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "login"
    pwd = sys.argv[2] if len(sys.argv) > 2 else ""

    with sync_playwright() as p:
        br = p.chromium.launch(channel="msedge", headless=True,
                               args=["--no-first-run", "--no-default-browser-check"])
        ctx = br.new_context(viewport={"width": 1500, "height": 1000})
        pg = ctx.new_page()

        if not _login(pg, pwd):
            w("!! 登录失败")
            w(pg.evaluate("document.body.innerText.slice(0,400)"))
            br.close()
            sys.exit(1)
        w("[登录成功]")

        if mode == "login":
            top = pg.frame(name="topFrame")
            if top:
                w("--- 顶部菜单 ---")
                w(top.evaluate(r"""(function(){var o=[];
                  document.querySelectorAll('a,li,span,font,div').forEach(function(e){
                    var t=(e.innerText||'').trim(); var oc=e.getAttribute('onclick')||'';
                    if(t && t.length<16 && oc) o.push(t+' | '+oc.slice(0,90));});
                  return Array.from(new Set(o)).join('\n');})()"""))
        elif mode == "dump":
            page = sys.argv[3]
            pg.evaluate("location.href='/getpage.gch?pid=1002&nextpage=%s'" % page)
            pg.wait_for_timeout(5000)
            _dump_frame(pg, page)
            pg.screenshot(path=".temp/zteweb_%s.png" % page.replace(".gch", ""))

        br.close()

    out = ".temp/zte_web_%s.txt" % mode
    os.makedirs(".temp", exist_ok=True)
    open(out, "w", encoding="utf-8").write("\n".join(LOG))
    print("saved", out)


if __name__ == "__main__":
    main()
