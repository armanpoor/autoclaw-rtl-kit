#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
rtl_lint.py — بازرسی متن پیش از ارسال
======================================

سه چیز را بررسی می‌کند:

  ۱) بستهٔ جهت‌دار: متن با `<div dir="rtl">` آغاز و با `</div>` پایان یابد،
     با یک سطر خالی بعد از تگ آغاز و یک سطر خالی پیش از تگ پایانی.
  ۲) رشتهٔ لاتین درون‌خطی: خطی که هم فارسی دارد و هم واژهٔ لاتین، در معرض
     به‌هم‌ریختن است؛ باید به بلوک کد یا `<span dir="ltr">` منتقل شود.
  ۳) بلوک کد: شمارش زوج باشد و هر بلوک برچسب زبان داشته باشد.

استفاده:
    python tools/rtl_lint.py draft.md
    python tools/rtl_lint.py draft.md --strict   # هشدارها هم خطا شمرده شوند
    python tools/rtl_lint.py --selftest

کد خروج: ۰ سالم، ۱ خطا، ۲ فایل نبود.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

OPEN_TAG = '<div dir="rtl">'
OPEN_RE = re.compile(r'<div\s+dir="rtl"[^>]*>')
CLOSE_TAG = "</div>"

PERSIAN_RE = re.compile(r"[\u0600-\u06FF]")
LATIN_WORD_RE = re.compile(r"[A-Za-z]{2,}")
INLINE_CODE_RE = re.compile(r"`[^`]*`")
SPAN_LTR_RE = re.compile(r'<span[^>]*dir="ltr"[^>]*>.*?</span>', re.S)
TAG_RE = re.compile(r"<[^>]+>")
LINK_TARGET_RE = re.compile(r"\]\([^)]*\)")
FENCE_RE = re.compile(r"^\s*(```|~~~)")


def analyse(text: str) -> dict:
    """نتیجهٔ بازرسی یک متن را برمی‌گرداند."""
    lines = text.replace("\r\n", "\n").split("\n")
    stripped = [line.strip() for line in lines]

    errors: list[str] = []
    warnings: list[str] = []

    body_first = next((i for i, line in enumerate(stripped) if line), None)
    body_last = next((i for i, line in enumerate(reversed(stripped)) if line), None)

    if body_first is None:
        errors.append("متن خالی است")
        return {"errors": errors, "warnings": warnings, "inline": []}

    body_last = len(lines) - 1 - body_last

    if not OPEN_RE.fullmatch(stripped[body_first]):
        errors.append("با بستهٔ جهت‌دار آغاز نمی‌شود")
    elif body_first + 1 < len(lines) and stripped[body_first + 1] != "":
        errors.append("بعد از تگ آغاز سطر خالی نیست؛ مارک‌داون خام می‌ماند")

    if stripped[body_last] != CLOSE_TAG:
        errors.append("با تگ پایانی بسته نمی‌شود")
    elif body_last - 1 >= 0 and stripped[body_last - 1] != "":
        errors.append("قبل از تگ پایانی سطر خالی نیست")

    # شمارش تگ‌ها
    opened = len(OPEN_RE.findall(text))
    if opened != text.count(CLOSE_TAG):
        errors.append(
            f"تعداد تگ آغاز و پایان برابر نیست ({opened} در برابر {text.count(CLOSE_TAG)})"
        )

    inline_hits: list[tuple[int, str]] = []
    fences: list[tuple[int, str]] = []
    in_fence = False

    for index, raw in enumerate(lines, start=1):
        fence = FENCE_RE.match(raw)
        if fence:
            marker = fence.group(1)
            if not in_fence:
                fences.append((index, raw.strip()))
            in_fence = not in_fence
            continue
        if in_fence:
            continue

        candidate = INLINE_CODE_RE.sub("", raw)
        candidate = SPAN_LTR_RE.sub("", candidate)
        candidate = LINK_TARGET_RE.sub("]", candidate)
        candidate = TAG_RE.sub("", candidate)
        if PERSIAN_RE.search(candidate) and LATIN_WORD_RE.search(candidate):
            inline_hits.append((index, raw.strip()[:70]))

    if in_fence:
        errors.append("بلوک کد بسته نشده است")

    for index, opening in fences:
        if opening in ("```", "~~~"):
            warnings.append(f"خط {index}: بلوک کد بدون برچسب زبان")

    for index, excerpt in inline_hits:
        warnings.append(f"خط {index}: رشتهٔ لاتین درون‌خطی → {excerpt}")

    return {"errors": errors, "warnings": warnings, "inline": inline_hits}


SELFTEST_CASES = [
    ('<div dir="rtl">\n\nمتن سالم.\n\n</div>\n', 0, 0),
    ("متن بدون بسته\n", 2, 0),
    ('<div dir="rtl">\nمتن چسبیده.\n</div>\n', 2, 0),
    ('<div dir="rtl">\n\nضریب `0.375` برای زیمنس.\n\n</div>\n', 0, 0),
    ('<div dir="rtl">\n\nضریب factor برای زیمنس.\n\n</div>\n', 0, 1),
]


def selftest() -> int:
    failures = 0
    for text, expected_errors, expected_warnings in SELFTEST_CASES:
        result = analyse(text)
        got = (len(result["errors"]), len(result["warnings"]))
        ok = got == (expected_errors, expected_warnings)
        print(f"{'OK ' if ok else 'BAD'} خطا={got[0]} هشدار={got[1]} ← {text!r}"[:110])
        failures += 0 if ok else 1
    print("همهٔ آزمون‌ها گذشت" if not failures else f"{failures} آزمون شکست خورد")
    return 1 if failures else 0


def main() -> int:
    parser = argparse.ArgumentParser(description="بازرسی انطباق متن با قانون راست‌چین")
    parser.add_argument("files", nargs="*", help="مسیر فایل‌های متنی")
    parser.add_argument("--strict", action="store_true", help="هشدارها هم خطا شمرده شوند")
    parser.add_argument("--selftest", action="store_true", help="آزمون خودکار ابزار")
    args = parser.parse_args()

    if args.selftest:
        return selftest()

    if not args.files:
        parser.print_help()
        return 2

    status = 0
    for name in args.files:
        path = Path(name)
        if not path.is_file():
            print(f"فایل پیدا نشد: {path}", file=sys.stderr)
            status = max(status, 2)
            continue

        result = analyse(path.read_text(encoding="utf-8"))
        print(f"\n{path}")

        for message in result["errors"]:
            print(f"  ✗ {message}")
        for message in result["warnings"]:
            print(f"  ! {message}")

        if not result["errors"] and not result["warnings"]:
            print("  ✓ سالم")

        if result["errors"]:
            status = max(status, 1)
        elif result["warnings"] and args.strict:
            status = max(status, 1)

    return status


if __name__ == "__main__":
    raise SystemExit(main())
