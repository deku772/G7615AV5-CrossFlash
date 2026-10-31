#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""深入探查 WAN 配置页：选中连接后读取真实字段值，并捕获页面报错"""
import os
import sys
import json
import time

from playwright.sync_api import sync_playwright

HOST = "http://192.168.1.1"
SHOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".temp")
os.makedirs(SHOT, exist_ok=True)

USER = sys.argv[1] if len(sys.argv) > 1 else "user"
PWD = sys.argv[2] if len(sys.argv) > 2 else "FcT2t#xD"


def dump_frame(fr, tag):
    js = """
    () => {
      const out = {selects: [], inputs: [], texts: []};
      document.querySelectorAll('select').forEach(s => {
        out.selects.push({
          id: s.id, name: s.name,
          value: s.value,
          options: Array.from(s.options).map(o => ({v: o.value, t: o.text}))
        });
      });
      document.querySelectorAll('input,textarea').forEach(i => {
        out.inputs.push({tag: i.tagName, type: i.type, id: i.id, name: i.name, value: i.value});
      });
      return out;
    }
    """
    try:
        return fr.evaluate(js)
    except Exception as e:
        print("dump fail", tag, str(e)[:80])
        return None


def main():
    with sync_playwright() as p:
        b = p.chromium.launch(headless=False, channel="chrome")
        ctx = b.new_context(viewport={"width": 1400, "height": 950})
        pg = ctx.new_page()

        # 登录
        pg.goto(HOST, timeout=30000)
        pg.wait_for_timeout(2500)
        pg.fill("#Frm_Password", PWD)
        pg.click("#LoginId")
        pg.wait_for_timeout(4000)

        # 进网络模块
        pg.click("a.menu1")
        pg.wait_for_timeout(4000)
        pg.screenshot(path=os.path.join(SHOT, "wan_a_initial.png"), full_page=True)

        # 找到内容 frame
        main = None
        for fr in pg.frames:
            if "template.gch" in fr.url:
                main = fr
                break
        if main is None:
            print("!! 未找到 template.gch frame")
            for fr in pg.frames:
                print("  frame:", fr.url)
            b.close()
            return

        print("=" * 30, "初始状态", "=" * 30)
        d0 = dump_frame(main, "init")
        print(json.dumps(d0, ensure_ascii=False, indent=1)[:2500])

        # 选中每个 option 并观察
        selects = d0["selects"] if d0 else []
        if not selects:
            print("!! 页面没有 select")
            b.close()
            return

        sel = selects[0]
        for idx, opt in enumerate(sel["options"]):
            if not opt["v"] or opt["v"] in ("-1", "0", ""):
                continue
            print("=" * 25, "选中 option:", opt["v"], opt["t"], "=" * 25)
            try:
                main.select_option("select#" + sel["id"] if sel["id"] else "select", opt["v"])
            except Exception:
                try:
                    main.evaluate(
                        """([sid, v]) => {
                            const s = document.getElementById(sid);
                            s.value = v;
                            s.dispatchEvent(new Event('change', {bubbles:true}));
                            if (typeof s.onchange === 'function') s.onchange();
                        }""", [sel["id"], opt["v"]])
                except Exception as e:
                    print("select fail:", str(e)[:100])
            pg.wait_for_timeout(3500)
            safe = opt["v"].replace("/", "_").replace(" ", "_")
            pg.screenshot(path=os.path.join(SHOT, f"wan_b_{safe}.png"), full_page=True)
            dd = dump_frame(main, opt["v"])
            print(json.dumps(dd, ensure_ascii=False, indent=1)[:3000])
            # 找报错提示
            try:
                alerts = main.evaluate("""() => {
                    const r=[]; document.querySelectorAll('body *').forEach(e=>{
                      const t=(e.innerText||'').trim();
                      if(t && t.length<120 && /错误|失败|无效|非法|不支持|异常|超时/.test(t)) r.push(t);
                    }); return Array.from(new Set(r)).slice(0,20);
                }""")
                if alerts:
                    print(">>> 页面提示:", alerts)
            except Exception:
                pass
            break  # 只测第一个有效 WAN（INTERNET）

        b.close()


if __name__ == "__main__":
    main()
