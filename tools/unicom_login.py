# -*- coding: utf-8 -*-
"""联通版 ZXHN G7615AV5 web 登录器（协议按实机页面复刻）。

修正点（相对早期 modem_login.py）：
  1. 密码字段名是 Password（不是 UserPW，后者只是 input 的 id）；
  2. Frm_Loginchecktoken 每次请求都会变，必须与同一 Cookie 会话一起取；
  3. 主动限速：失败 1 次后默认等 65s，避免触发 3 次锁定。
用法:
  python tools/unicom_login.py --acct adm --pass CUAdmin
  python tools/unicom_login.py --acct oth --pass 123456 --tries 2
"""
import argparse, hashlib, http.cookiejar, random, re, sys, time, urllib.parse, urllib.request

BASE = "http://192.168.1.1"


def make_opener():
    cj = http.cookiejar.CookieJar()
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    op.addheaders = [
        ("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"),
        ("Accept", "text/html,application/xhtml+xml,*/*"),
    ]
    return op, cj


def fetch_login_page(op):
    r = op.open(BASE + "/", timeout=10)
    html = r.read().decode("gb2312", "replace")
    tok = re.search(r'Frm_Loginchecktoken"\)\.value\s*=\s*"([^"]+)"', html)
    code = re.search(r'var Code\s*=\s*"(\d+)"', html)
    status = re.search(r'var Status\s*=\s*"(\d+)"', html)
    result = re.search(r'var Result\s*=\s*"(\d+)"', html)
    return {
        "token": tok.group(1) if tok else "",
        "code": code.group(1) if code else "?",
        "status": status.group(1) if status else "?",
        "result": result.group(1) if result else "?",
        "html": html,
    }


def login(op, acct, password):
    page = fetch_login_page(op)
    num = random.randint(10000000, 99999999)
    pw = hashlib.sha256((password + str(num)).encode()).hexdigest()
    fields = {
        "Frm_Logintoken": "0",
        "Frm_Loginchecktoken": page["token"],
        "_cu_url": "1" if acct == "adm" else "0",
        "Right": "1" if acct == "adm" else "2",
        "Username": "",
        "UserRandomNum": str(num),
        "Password": pw,
        "action": "login",
        "accountType": acct,
    }
    data = urllib.parse.urlencode(fields).encode()
    req = urllib.request.Request(BASE + "/", data=data, headers={"Referer": BASE + "/"})
    try:
        resp = op.open(req, timeout=15)
        body = resp.read().decode("gb2312", "replace")
        url = resp.url
    except urllib.error.HTTPError as e:
        body = e.read().decode("gb2312", "replace")
        url = BASE + "/"
    except Exception as e:
        return False, "网络异常: %s" % e, page

    # 判定：返回登录页（含登录表单 token）= 失败；否则视为进入管理页
    if "Frm_Loginchecktoken" in body:
        # 服务器把失败次数放在分页脚本里：var Lognumber = N;（N>=3 会锁 60s）
        ln = re.search(r"var\s+Lognumber\s*=\s*(\d+)", body)
        err = re.search(r'account-errinfomsg">([^<]{2,60})', body)
        detail = "失败次数 Lognumber=%s" % (ln.group(1) if ln else "?")
        if err and err.group(1).strip():
            detail += " | 提示: " + err.group(1).strip()
        if ln and int(ln.group(1)) >= 3:
            detail += "（已达 3 次，需等 60s 解锁）"
        return False, detail, page
    where = re.search(r'(?:location\.href|location\.replace)\s*[=(]\s*["\']?([^"\');]+)', body)
    return True, "跳转 → %s (HTTP %s, %d 字节) %s" % (url, getattr(resp, "status", "?"), len(body), where.group(1) if where else ""), page


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="192.168.1.1")
    ap.add_argument("--acct", default="adm", choices=["adm", "oth"])
    ap.add_argument("--pass", dest="password", required=True)
    ap.add_argument("--tries", type=int, default=1)
    ap.add_argument("--gap", type=int, default=65, help="失败后的冷却秒数")
    a = ap.parse_args()
    global BASE
    BASE = "http://" + a.host

    ok = False
    for i in range(1, a.tries + 1):
        op, cj = make_opener()
        page = fetch_login_page(op)
        print("[i] 页面: Code=%s Status=%s Result=%s token=%s" % (page["code"], page["status"], page["result"], page["token"]))
        good, msg, _ = login(op, a.acct, a.password)
        print("[%d/%d] acct=%s pass=%r → %s | %s" % (i, a.tries, a.acct, a.password, "成功" if good else "失败", msg))
        ok = ok or good
        if good:
            break
        if i < a.tries:
            print("   冷却 %ds（防 3 次锁定）..." % a.gap)
            time.sleep(a.gap)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
