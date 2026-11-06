# -*- coding: utf-8 -*-
"""
آزمون‌های کیت راست‌چین
======================

اجرای مستقیم:

    python tests/test_rtl_presentation.py

یا با پای‌تست:

    python -m pytest tests/ -q
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from rtl_lint import analyse  # noqa: E402
from rtl_wrap import CLOSE_TAG, OPEN_TAG, is_wrapped, unwrap, wrap  # noqa: E402

SAMPLE = "# عنوان آزمایشی\n\nمتن فارسی با پرانتز (AFR) و ضریب 0.375 در یک جمله.\n"


def test_wrap_produces_canonical_block() -> None:
    result = wrap(SAMPLE)
    assert result.startswith(OPEN_TAG + "\n\n"), "تگ آغاز باید سطر اول و جدا از بدنه باشد"
    assert result.rstrip().endswith(CLOSE_TAG), "تگ پایانی باید آخرین سطر باشد"
    assert is_wrapped(result)


def test_wrap_is_idempotent() -> None:
    once = wrap(SAMPLE)
    assert wrap(once) == once, "بسته‌بندی دوباره نباید لایهٔ تکراری بسازد"


def test_unwrap_restores_body() -> None:
    assert unwrap(wrap(SAMPLE)).strip() == SAMPLE.strip()


def test_bare_text_is_rejected() -> None:
    assert not is_wrapped(SAMPLE)
    assert not is_wrapped("")
    result = analyse(SAMPLE)
    assert result["errors"], "متن بدون بسته باید خطا بدهد"


def test_markdown_survives_wrapping() -> None:
    wrapped = wrap(SAMPLE)
    assert "# عنوان آزمایشی" in wrapped
    assert "(AFR)" in wrapped
    assert "0.375" in wrapped


def test_lint_accepts_clean_document() -> None:
    result = analyse('<div dir="rtl">\n\nضریب `0.375` درست است.\n\n</div>\n')
    assert not result["errors"]
    assert not result["warnings"]


def test_lint_flags_inline_latin() -> None:
    result = analyse('<div dir="rtl">\n\nضریب factor برای زیمنس است.\n\n</div>\n')
    assert not result["errors"], "بسته سالم است، پس خطای ساختاری نباید باشد"
    assert result["warnings"], "رشتهٔ لاتین درون‌خطی باید هشدار بدهد"


def test_lint_flags_missing_blank_line() -> None:
    result = analyse('<div dir="rtl">\nمتن چسبیده.\n</div>\n')
    assert len(result["errors"]) >= 2


def test_prompt_files_exist() -> None:
    for name in ("autoclaw-rtl-law.md", "system-prompt.md", "reply-template.md"):
        assert (ROOT / "prompt" / name).is_file(), f"قطعهٔ آماده نیست: {name}"


def test_human_facing_docs_are_wrapped() -> None:
    for path in sorted(ROOT.glob("docs/*.md")) + sorted(ROOT.glob("examples/*.md")):
        assert is_wrapped(path.read_text(encoding="utf-8")), f"بدون بستهٔ راست‌چین: {path}"


def main() -> int:
    tests = [value for name, value in sorted(globals().items()) if name.startswith("test_")]
    failures = 0
    for test in tests:
        try:
            test()
            print(f"OK  {test.__name__}")
        except AssertionError as error:
            failures += 1
            print(f"BAD {test.__name__}: {error}")
    print(f"\n{len(tests) - failures} از {len(tests)} آزمون گذشت")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
