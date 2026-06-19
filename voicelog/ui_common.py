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
from AppKit import (
    NSTextField, NSFont, NSColor, NSApp,
    NSMutableParagraphStyle, NSFontAttributeName,
    NSForegroundColorAttributeName, NSParagraphStyleAttributeName,
    NSApplicationActivationPolicyRegular, NSApplicationActivationPolicyAccessory,
)
from Foundation import NSObject, NSAttributedString, NSMutableAttributedString


# ============================================================================
#  激活策略（前台/菜单栏）引用计数：多个窗口可能同时需要前台。
#  菜单栏 App 默认 Accessory(无 Dock)下窗口拿不到键盘/不稳前台 → 开窗 push_regular(变前台)，
#  关窗 pop_regular()；只有计数归零才切回 Accessory。避免两窗各自盲切互相踩、或失败路径卡住 Dock 图标。
# ============================================================================
_regular_depth = 0


def push_regular():
    global _regular_depth
    _regular_depth += 1
    if _regular_depth == 1:
        try:
            NSApp.setActivationPolicy_(NSApplicationActivationPolicyRegular)
        except Exception:
            pass
    try:
        NSApp.activateIgnoringOtherApps_(True)
    except Exception:
        pass


def pop_regular():
    global _regular_depth
    _regular_depth = max(0, _regular_depth - 1)
    if _regular_depth == 0:
        try:
            NSApp.setActivationPolicy_(NSApplicationActivationPolicyAccessory)
        except Exception:
            pass


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


# 语义字体/颜色：用「层次」代替「一坨等宽文本」，避免廉价感。
def title_font(size=15.0):
    return NSFont.boldSystemFontOfSize_(size)


def body_font(size=12.5):
    return NSFont.systemFontOfSize_(size)


def C_PRIMARY():    return NSColor.labelColor()
def C_SECONDARY():  return NSColor.secondaryLabelColor()
def C_TERTIARY():   return NSColor.tertiaryLabelColor()


def make_rich_label(frame, segments, line_spacing=5.0, para_spacing=6.0):
    """富文本多行只读标签。segments: [(text, font, color|None), ...]，拼成带行距的层次化标题块。"""
    s = NSMutableAttributedString.alloc().init()
    for text, font, color in segments:
        attrs = {NSFontAttributeName: font}
        if color is not None:
            attrs[NSForegroundColorAttributeName] = color
        s.appendAttributedString_(
            NSAttributedString.alloc().initWithString_attributes_(text, attrs))
    ps = NSMutableParagraphStyle.alloc().init()
    ps.setLineSpacing_(line_spacing)
    ps.setParagraphSpacing_(para_spacing)
    s.addAttribute_value_range_(NSParagraphStyleAttributeName, ps, (0, s.length()))

    lbl = NSTextField.alloc().initWithFrame_(frame)
    lbl.setEditable_(False)
    lbl.setSelectable_(False)
    lbl.setBezeled_(False)
    lbl.setDrawsBackground_(False)
    lbl.setUsesSingleLineMode_(False)
    lbl.cell().setWraps_(True)
    lbl.setAttributedStringValue_(s)
    return lbl
