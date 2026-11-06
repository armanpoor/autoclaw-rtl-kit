#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
rtl_wrap.py — پیچیدن خروجی‌های متنی در بستهٔ جهت‌دار راست‌به‌چپ
===============================================================

هر متنی که انسان در کانال‌های گفت‌وگو یا پیش‌نمایش می‌خواند باید داخل
بستهٔ زیر باشد تا پایهٔ جهت پاراگراف راست‌به‌چپ شود:

    <div dir="rtl">

    ... بدنهٔ مارک‌داون ...

    </div>

سطر تگ آغاز، یک سطر خالی، بدنه، یک سطر خالی، تگ پایانی. در CommonMark
شروع بلوک HTML تا خط خالی ادامه دارد؛ با این آرایش بدنه مارک‌داون پارس
می‌شود و تگ باز همچنان بر کل بدنه اثر می‌گذارد.

استفاده:
    python tools/rtl_wrap.py file.md              # چاپ نتیجه در خروجی استاندارد
    python tools/rtl_wrap.py file.md --in-place    # نوشتن روی همان فایل
    python tools/rtl_wrap.py file.md --check       # ۰ اگر بسته‌بندی‌شده باشد، ۱ اگر نه
    python tools/rtl_wrap.py file.md --unwrap --in-place
    python tools/rtl_wrap.py file.md --strip-marks # حذف RLM/LRM/RLI/PDI
    python tools/rtl_wrap.py --check docs/*.md      # بررسی گروهی
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

OPEN_TAG = '<div dir="rtl">'
OPEN_RE = re.compile(r'<div\s+dir="rtl"[^>]*>')
CLOSE_TAG = "</div>"
BOM = "\ufeff"
MARKS_RE = re.compile("[\u200e\u200f\u2066-\u2069]")


def unwrap(text: str) -> str:
    body = text.lstrip(BOM).lstrip("\n")
    stripped = body.lstrip()
    match = OPEN_RE.match(stripped)
    if match:
        body = stripped[match.end():]
    body = body.rstrip()
    if body.endswith(CLOSE_TAG):
        body = body[: -len(CLOSE_TAG)]
    return body.strip("\n") + "\n"


def wrap(text: str) -> str:
    body = unwrap(text).strip("\n")
    return f"{OPEN_TAG}\n\n{body}\n\n{CLOSE_TAG}\n"


def is_wrapped(text: str) -> bool:
    cleaned = text.lstrip(BOM).strip()
    return bool(OPEN_RE.match(cleaned)) and cleaned.endswith(CLOSE_TAG)


def main() -> int:
    parser = argparse.ArgumentParser(description="بسته‌بندی راست‌چین متن")
    parser.add_argument("files", nargs="+", help="مسیر یک یا چند فایل متنی")
    parser.add_argument("--check", action="store_true", help="فقط بررسی؛ کد خروج ۱ در صورت نبود بسته")
    parser.add_argument("--unwrap", action="store_true", help="حذف بسته")
    parser.add_argument("--strip-marks", action="store_true", help="حذف نویسه‌های نامرئی RLM/LRM/RLI/PDI")
    parser.add_argument("--in-place", action="store_true", help="نوشتن روی همان فایل")
    args = parser.parse_args()

    failures = 0
    for name in args.files:
        path = Path(name)
        if not path.is_file():
            print(f"فایل پیدا نشد: {path}", file=sys.stderr)
            failures += 1
            continue

        original = path.read_text(encoding="utf-8")
        if args.strip_marks:
            original = MARKS_RE.sub("", original)
        if args.check:
            ok = is_wrapped(original)
            print(f"{'OK ' if ok else 'RED'} {path}")
            failures += 0 if ok else 1
            continue

        result = unwrap(original) if args.unwrap else wrap(original)
        if args.in_place:
            path.write_text(result, encoding="utf-8")
            print(f"نوشته شد: {path}")
        else:
            sys.stdout.write(result)

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
