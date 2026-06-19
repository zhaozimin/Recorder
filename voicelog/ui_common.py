#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[INPUT]: 依赖 AppKit/Foundation(PyObjC，rumps 已带入) 的 NSObject/NSTextField/NSFont
[OUTPUT]: 对外提供 BtnTarget(按钮回调桥) 与 make_label(只读标签 helper)
[POS]: voicelog 各原生窗口(enroll_ui / replace_ui)的公共底座，消除按钮桥与标签的重复代码。
[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md

所有 AppKit 操作必须在主线程调用(由 rumps 菜单回调 / rumps.Timer 保证)。
"""
import objc
from AppKit import NSTextField, NSFont
from Foundation import NSObject


# ============================================================================
#  按钮回调桥：AppKit 按钮需要一个 ObjC target，转调 Python 回调。
#  用法：t = BtnTarget.alloc().initWithCallback_(cb); btn.setTarget_(t); btn.setAction_("invoke:")
#  注意：必须用 python 变量持有 target，否则被 GC 后点击无反应。
# ============================================================================
class BtnTarget(NSObject):
    def initWithCallback_(self, cb):
        self = objc.super(BtnTarget, self).init()
        if self is None:
            return None
        self._cb = cb
        return self

    def invoke_(self, sender):
        try:
            if self._cb:
                self._cb()
        except Exception:
            pass


def make_label(frame, text: str, size: float):
    """只读、无边框、透明背景的文字标签。"""
    lbl = NSTextField.alloc().initWithFrame_(frame)
    lbl.setStringValue_(text)
    lbl.setEditable_(False)
    lbl.setSelectable_(False)
    lbl.setBezeled_(False)
    lbl.setDrawsBackground_(False)
    lbl.setFont_(NSFont.systemFontOfSize_(size))
    return lbl
