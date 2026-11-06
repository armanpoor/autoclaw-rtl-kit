#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
rtl_guard.py — نگهبان بستهٔ راست‌چین برای فایل‌های مارک‌داون
============================================================

هر ابزاری که مارک‌داون را به اچ‌تی‌ام‌ال تبدیل می‌کند (پیش‌نمایش AutoClaw،
پیش‌نمایش VS Code، گیت‌هاب، آبسیدین)، تگ `<div dir="rtl">` را که داخل خود
فایل باشد محترم می‌شمارد. پس کافی است فایل‌های فارسی یک‌بار بسته‌بندی شوند؛
از آن پس هر جا باز شوند درست دیده می‌شوند.

این ابزار سه کار می‌کند:

    python tools/rtl_guard.py .              # گزارش: کدام فایل بسته ندارد
    python tools/rtl_guard.py . --write      # بسته‌بندی خودکار همان فایل‌ها
    python tools/rtl_guard.py . --watch      # پایش پیوسته و بسته‌بندی خودکار
    python tools/rtl_guard.py . --check      # فقط بررسی؛ کد خروج ۱ در صورت نقص

قواعد رد کردن:

  * فایل‌هایی که در `.rtlignore` فهرست شده‌اند دست‌نخورده می‌مانند
    (پیش‌فرض: فایل‌های دستور عامل مثل `CLAUDE.md` و `AGENTS.md`).
  * فایل بدون حرف فارسی بسته نمی‌شود.
  * پوشه‌های ابزاری مثل `.git`، `node_modules` و `build` پیمایش نمی‌شوند.

کد خروج: ۰ سالم، ۱ فایل بسته‌نشده، ۲ خطای ورودی.
"""

from __future__ import annotations

import argparse
import fnmatch
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from rtl_wrap import is_wrapped, unwrap, wrap  # noqa: E402

PERSIAN_RE = re.compile(r"[\u0600-\u06FF]")
SKIP_DIRS = {
    ".git", ".hg", ".svn", "node_modules", ".venv", "venv", "__pycache__",
    "build", "dist", ".idea", ".vscode", ".mypy_cache", ".pytest_cache",
    ".zwork", ".claude", "build_logs", "site-packages",
}
DEFAULT_IGNORES = ["CLAUDE.md", "AGENTS.md", "GEMINI.md", "README.en.md"]
MIN_PERSIAN_CHARS = 24


def load_ignores(root: Path) -> list[str]:
    patterns = list(DEFAULT_IGNORES)
    ignore_file = root / ".rtlignore"
    if ignore_file.is_file():
        for line in ignore_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                patterns.append(line)
    return patterns


def matches(path: Path, patterns: list[str], root: Path) -> bool:
    relative = path.relative_to(root).as_posix() if path.is_relative_to(root) else path.name
    for pattern in patterns:
        if fnmatch.fnmatch(path.name, pattern) or fnmatch.fnmatch(relative, pattern):
            return True
    return False


def iter_markdown(root: Path, ignores: list[str]):
    for path in sorted(root.rglob("*.md")):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if matches(path, ignores, root):
            continue
        yield path


def is_candidate(path: Path) -> bool:
    try:
        text = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return False
    if is_wrapped(text):
        return False
    return len(PERSIAN_RE.findall(text)) >= MIN_PERSIAN_CHARS


def scan(root: Path) -> tuple[list[Path], list[Path]]:
    ignores = load_ignores(root)
    pending: list[Path] = []
    ready: list[Path] = []
    for path in iter_markdown(root, ignores):
        if is_candidate(path):
            pending.append(path)
        elif is_wrapped(path.read_text(encoding="utf-8", errors="replace")):
            ready.append(path)
    return pending, ready


def apply(root: Path, paths: list[Path]) -> None:
    for path in paths:
        text = path.read_text(encoding="utf-8")
        path.write_text(wrap(unwrap(text)), encoding="utf-8", newline="\n")
        print(f"  ✓ بسته شد: {path.relative_to(root).as_posix()}")


def one_pass(root: Path, write: bool, quiet: bool = False) -> int:
    pending, ready = scan(root)
    if not quiet:
        print(f"{root}")
        print(f"  بسته‌بندی‌شده: {len(ready)}")
        print(f"  بدون بسته: {len(pending)}")
    if write and pending:
        apply(root, pending)
        pending = []
    elif pending and not quiet:
        for path in pending:
            print(f"  ✗ {path.relative_to(root).as_posix()}")
    return 0 if not pending else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="نگهبان بستهٔ راست‌چین برای فایل‌های مارک‌داون")
    parser.add_argument("root", nargs="?", default=".", help="پوشه یا فایل مورد بررسی")
    parser.add_argument("--write", action="store_true", help="بسته‌بندی خودکار فایل‌های بدون بسته")
    parser.add_argument("--check", action="store_true", help="فقط بررسی؛ کد خروج ۱ در صورت نقص")
    parser.add_argument("--watch", action="store_true", help="پایش پیوسته")
    parser.add_argument("--interval", type=float, default=3.0, help="فاصلهٔ پایش به ثانیه")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    if not root.exists():
        print(f"مسیر پیدا نشد: {root}", file=sys.stderr)
        return 2

    if args.watch:
        print(f"پایش {root} هر {args.interval} ثانیه. توقف با Ctrl+C.")
        try:
            while True:
                one_pass(root, write=True)
                time.sleep(args.interval)
        except KeyboardInterrupt:
            print("\nپایش پایان یافت.")
        return 0

    return one_pass(root, write=args.write and not args.check)


if __name__ == "__main__":
    raise SystemExit(main())
