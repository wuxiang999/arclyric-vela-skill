#!/usr/bin/env python3
"""Vela 快应用 .ux 静态检查。

只查「编译能过、真机上必炸」的那几类问题：

  - 不支持的 CSS：@media / @keyframes / @import、复合选择器、border-*-style
  - text 上误用 lines 属性（lines 是 style）
  - text 类设置 height
  - line-height / font-size < 1.3
  - 根容器有多个子节点却没有 flex-direction
  - src/config-watch.json 残留

用法：
  python3 lint_ux.py <src 目录或项目根目录> [--strict]

退出码：0 通过；1 有 error（--strict 时 warning 也算）。
"""
import os
import re
import sys

ERROR = 'error'
WARN = 'warn'

TAG_RE = re.compile(r'<(/?)([a-zA-Z][\w-]*)((?:"[^"]*"|\'[^\']*\'|[^>"\'])*)>')
STYLE_RE = re.compile(r'<style[^>]*>(.*?)</style>', re.S)
TEMPLATE_RE = re.compile(r'<template[^>]*>(.*?)</template>', re.S)
RULE_RE = re.compile(r'([^{}]+)\{([^{}]*)\}')

UNSUPPORTED_SELECTOR_CHARS = (' ', '>', ':', '#', '*', '[', ']')
UNSUPPORTED_AT = ('@media', '@keyframes', '@import', '@supports', '@font-face')
UNSUPPORTED_PROPS = ('border-left-style', 'border-right-style', 'border-top-style',
                     'border-bottom-style', 'box-shadow')


def decls(body):
    out = {}
    for chunk in body.split(';'):
        if ':' not in chunk:
            continue
        key, value = chunk.split(':', 1)
        out[key.strip()] = value.strip()
    return out


def to_number(value):
    m = re.match(r'^(-?[\d.]+)', value or '')
    if not m:
        return None
    try:
        return float(m.group(1))
    except ValueError:
        return None


def class_attr(attrs):
    m = re.search(r'class\s*=\s*"([^"]*)"', attrs or '')
    return m.group(1).strip() if m else None


def root_info(tpl):
    """返回 (根节点 class 列表, 直接子节点数量)。"""
    depth = 0
    root_classes = []
    children = 0
    for m in TAG_RE.finditer(tpl):
        closing, name, attrs = m.group(1), m.group(2), m.group(3)
        self_closing = attrs.rstrip().endswith('/')
        if closing:
            depth -= 1
            if depth < 0:
                depth = 0
            continue
        if depth == 0:
            cls = class_attr(attrs)
            if cls:
                root_classes = cls.split()
        elif depth == 1:
            children += 1
        if not self_closing:
            depth += 1
    return root_classes, children


def lint_file(path):
    issues = []
    src = open(path, encoding='utf-8').read()
    lines = src.splitlines()

    def add(level, msg, pos=0):
        line_no = src.count('\n', 0, pos) + 1
        issues.append((level, line_no, msg))

    # ---------- style ----------
    rules = []  # (selector, props, pos)
    for block in STYLE_RE.finditer(src):
        for m in RULE_RE.finditer(block.group(1)):
            sel = m.group(1).strip()
            if not sel or sel.startswith('/*'):
                continue
            rules.append((sel, decls(m.group(2)), block.start() + m.start()))

    for sel, props, pos in rules:
        if sel.startswith('@'):
            if any(sel.startswith(at) for at in UNSUPPORTED_AT):
                add(ERROR, '不支持的 at 规则：%s（该版本无 @media/@keyframes）' % sel.split()[0], pos)
            continue

        for part in sel.split(','):
            p = part.strip()
            if not p:
                continue
            if any(ch in p for ch in UNSUPPORTED_SELECTOR_CHARS):
                add(ERROR, '不支持的选择器：%s（只允许 class 选择器）' % p, pos)
                break

        for prop in UNSUPPORTED_PROPS:
            if prop in props:
                add(ERROR, '不支持的样式：%s' % prop, pos)

        font = to_number(props.get('font-size', ''))
        line_h = to_number(props.get('line-height', ''))
        height = to_number(props.get('height', ''))

        if font and height:
            add(WARN, 'text 类同时设了 font-size 和 height：%s（高度交给 line-height）' % sel, pos)

        if font and line_h and font > 0 and line_h / font < 1.3:
            add(WARN, '行高过紧：%s line-height/font-size = %.2f（建议 >= 1.35）'
                % (sel, line_h / font), pos)

    # ---------- template ----------
    tpl_m = TEMPLATE_RE.search(src)
    tpl = tpl_m.group(1) if tpl_m else ''
    tpl_pos = tpl_m.start() if tpl_m else 0

    for m in TAG_RE.finditer(tpl):
        closing, name, attrs = m.group(1), m.group(2), m.group(3)
        if closing or name != 'text':
            continue
        if re.search(r'\blines\s*=', attrs or ''):
            add(ERROR, 'text 不支持 lines 属性，请写进 CSS：.cls { lines: 1; }',
                tpl_pos + m.start())

    root_classes, children = root_info(tpl)
    if children >= 2:
        for cls in root_classes:
            rule = next((p for s, p, _ in rules if cls in [x.strip() for x in s.split(',')]), None)
            if rule is None:
                continue
            if 'flex-direction' not in rule:
                add(WARN, '根容器 .%s 有 %d 个直接子节点但没有 flex-direction（默认是 row）'
                    % (cls, children), tpl_pos)

    return issues


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('-')]
    strict = '--strict' in sys.argv[1:]
    if not args:
        print(__doc__)
        return 2

    target = args[0]
    if os.path.isdir(os.path.join(target, 'src')):
        target = os.path.join(target, 'src')

    files = sorted(
        os.path.join(base, name)
        for base, _, names in os.walk(target)
        for name in names
        if name.endswith('.ux')
    )
    if not files:
        print('没有找到 .ux 文件：%s' % target)
        return 2

    total_error = 0
    total_warn = 0
    for path in files:
        issues = lint_file(path)
        if not issues:
            continue
        rel = os.path.relpath(path, target)
        for level, line_no, msg in issues:
            print('%s:%s: %s: %s' % (rel, line_no, level, msg))
            if level == ERROR:
                total_error += 1
            else:
                total_warn += 1

    if os.path.exists(os.path.join(target, 'config-watch.json')):
        print('config-watch.json: %s: 该文件在部分机型会导致启动白屏，确认无必要就删除'
              % WARN)
        total_warn += 1

    print('检查完成：%d 个 .ux，%d 个 error，%d 个 warning'
          % (len(files), total_error, total_warn))
    if total_error or (strict and total_warn):
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
