#!/usr/bin/env python3
"""只补填用户名下拉框：优先在列表中选 factorymode，否则键盘输入。"""
import time

from pywinauto import Application, Desktop

USER = "factorymode"

win = None
for w in Desktop(backend="uia").windows():
    if "ZTE Telnet" in (w.window_text() or ""):
        win = w
        break
if win is None:
    print("!! 未找到 ZteTelnet 窗口")
    sys_exit = 1
    raise SystemExit(sys_exit)

win.set_focus()
try:
    win.click_input(coords=(50, 40))  # 确保在基本配置标签
    time.sleep(0.8)
except Exception:
    pass

combos = win.descendants(control_type="ComboBox")
print("ComboBox 数量:", len(combos))
for i, c in enumerate(combos):
    try:
        r = c.rectangle()
        print("  [%d] y=%d texts=%s" % (i, r.top, (c.texts() or [])[:2]))
    except Exception:
        continue

# 直接按标签文本定位用户名框
target = None
for c in combos:
    try:
        t = "".join(c.texts() or [])
        if "用户名" in t:
            target = c
            print("定位到: %s" % t)
            break
    except Exception:
        continue

if target is None:
    print("!! 未定位到用户名框")
    raise SystemExit(1)

# 先尝试 select 列表项
try:
    items = target.item_count() if hasattr(target, "item_count") else None
    print("下拉项数:", items)
except Exception:
    pass
try:
    target.select(USER)
    print("✔ select('%s') 成功" % USER)
except Exception as e:
    print("select 失败:", str(e)[:100])
    # 退化为键盘输入
    try:
        target.click_input(double=True)
        time.sleep(0.3)
        target.type_keys(USER, with_spaces=True)
        time.sleep(0.3)
        target.type_keys("{ENTER}")
        print("✔ 键盘输入成功")
    except Exception as e2:
        print("键盘输入也失败:", str(e2)[:100])

time.sleep(0.5)
try:
    print("当前值:", target.texts())
except Exception:
    pass
print("DONE")
