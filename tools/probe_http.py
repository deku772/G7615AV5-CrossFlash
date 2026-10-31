#!/usr/bin/env python3
"""纯 HTTP 抓取光猫状态页（不依赖 Playwright/CDP）。

复用 unicom_login 的登录协议，登录后直接 GET 各 getpage.gch 页面，
抽取文本 + 表单字段 + select 选项。

用法: python tools/probe_http.py
"""
import hashlib
import http.cookiejar
import os
import random
import re
import sys
import urllib.parse
import urllib.request

BASE = "http://192.168.1.1"
PWD = os.environ.get("ZTE_ADMIN_PASS", "CUAdmin")
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".temp", "portal_http.txt")

# (标题, nextpage)
PAGES = [
    ("状态 > 逻辑ID注册信息", "status_registerinfo_t.gch"),
    ("状态 > 设备信息", "status_dev_info_t.gch"),
    ("基本配置 > LAN配置", "net_dhcp_dynamic_t.gch"),
    ("高级配置 > LOID配置", "pon_net_ponloid_t.gch"),
    ("基本配置 > 远程管理", "net_tr069_basic_t.gch"),
    ("高级配置 > 安全设置", "sec_secure_t.gch"),
]


def make_opener():
    cj = http.cookiejar.CookieJar()
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    op.addheaders = [
        ("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"),
        ("Accept", "text/html,application/xhtml+xml,*/*"),
    ]
    return op, cj


def fetch(op, url, data=None, timeout=12):
    req = urllib.request.Request(url, data=data, headers={"Referer": BASE + "/"})
    try:
        r = op.open(req, timeout=timeout)
        return r.read().decode("gb2312", "replace"), r.status
    except urllib.error.HTTPError as e:
        return e.read().decode("gb2312", "replace"), e.code
    except Exception as e:
        return "ERR:%s" % e, 0


def login(op):
    html, _ = fetch(op, BASE + "/")
    tok = re.search(r'Frm_Loginchecktoken"\)\.value\s*=\s*"([^"]+)"', html)
    num = random.randint(10000000, 99999999)
    pw = hashlib.sha256((PWD + str(num)).encode()).hexdigest()
    fields = {
        "Frm_Logintoken": "0",
        "Frm_Loginchecktoken": tok.group(1) if tok else "",
        "_cu_url": "1",
        "Right": "1",
        "Username": "",
        "UserRandomNum": str(num),
        "Password": pw,
        "action": "login",
        "accountType": "adm",
    }
    body, st = fetch(op, BASE + "/", urllib.parse.urlencode(fields).encode())
    if "Frm_Loginchecktoken" in body:
        ln = re.search(r"var\s+Lognumber\s*=\s*(\d+)", body)
        return False, "登录失败 Lognumber=%s" % (ln.group(1) if ln else "?")
    return True, "登录成功 HTTP=%s" % st


TAG_RE = re.compile(r"<(input|select|textarea|option)[^>]*>", re.I)
ATTR_RE = {
    "id": re.compile(r'id\s*=\s*["\']?([\w\-]+)', re.I),
    "name": re.compile(r'name\s*=\s*["\']?([\w\-]+)', re.I),
    "value": re.compile(r'value\s*=\s*["\']([^"\']*)', re.I),
    "type": re.compile(r'type\s*=\s*["\']?([\w\-]+)', re.I),
    "selected": re.compile(r'\bselected\b', re.I),
    "disabled": re.compile(r'\bdisabled\b', re.I),
}


def strip_tags(html):
    t = re.sub(r"<script.*?</script>", " ", html, flags=re.S | re.I)
    t = re.sub(r"<style.*?</style>", " ", t, flags=re.S | re.I)
    t = re.sub(r"<[^>]+>", "\n", t)
    t = re.sub(r"&nbsp;", " ", t)
    t = re.sub(r"&amp;", "&", t)
    lines = [re.sub(r"\s+", " ", l).strip() for l in t.split("\n")]
    return [l for l in lines if l]


def main():
    op, cj = make_opener()
    ok, msg = login(op)
    log = ["[login] " + msg]
    if not ok:
        print("\n".join(log))
        return
    log.append("[cookies] " + "; ".join("%s=%s" % (c.name, c.value[:20]) for c in cj))

    for title, npage in PAGES:
        url = "%s/getpage.gch?pid=1002&nextpage=%s" % (BASE, npage)
        html, st = fetch(op, url)
        log.append("")
        log.append("=" * 78)
        log.append("== %s   (HTTP %s)" % (title, st))
        log.append("== %s" % url)
        log.append("=" * 78)
        lines = strip_tags(html)
        # 去掉公共导航噪声
        nav = {"状态", "基本配置", "高级配置", "设备管理", "帮助", "上网营业厅www.10010.com 网关厂商服务电话:800-8301118 客服热线10010 充值专线10011"}
        body = [l for l in lines if l not in nav]
        log.extend(body[:120])
        log.append("--- fields ---")
        for m in TAG_RE.finditer(html):
            tag = m.group(0)
            low = tag.lower()
            if "hidden" in low:
                continue
            if tag.lower().startswith("<option"):
                continue
            idm = ATTR_RE["id"].search(tag)
            nm = ATTR_RE["name"].search(tag)
            vm = ATTR_RE["value"].search(tag)
            ty = ATTR_RE["type"].search(tag)
            sel = " [SEL]" if ATTR_RE["selected"].search(tag) else ""
            dis = " [DIS]" if ATTR_RE["disabled"].search(tag) else ""
            log.append("  - <%s> id=%-26s name=%-22s type=%-9s value=%-28s%s%s" % (
                m.group(1), idm.group(1) if idm else "-", nm.group(1) if nm else "-",
                ty.group(1) if ty else ("select" if m.group(1).lower() == "select" else ""),
                (vm.group(1) if vm else "")[:28], sel, dis))
        log.append("--- select options ---")
        for m in re.finditer(r"<select[^>]*>(.*?)</select>", html, re.S | re.I):
            sid = ATTR_RE["id"].search(m.group(0))
            opts = []
            for om in re.finditer(r"<option([^>]*)>(.*?)</option>", m.group(1), re.S | re.I):
                v = ATTR_RE["value"].search(om.group(1))
                t = strip_tags(om.group(2))
                txt = " ".join(t)
                if ATTR_RE["selected"].search(om.group(1)):
                    txt += "  <<CURRENT>>"
                opts.append("%s | %s" % (v.group(1) if v else "", txt))
            log.append("  [%s] %s" % (sid.group(1) if sid else "-", "  ||  ".join(opts)))

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(log))
    print("saved:", OUT, os.path.getsize(OUT), "bytes")


if __name__ == "__main__":
    main()
