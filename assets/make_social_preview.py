#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
make_social_preview.py — ساخت تصویر پیش‌نمایش اجتماعی مخزن (۱۲۸۰×۶۴۰)
=====================================================================

گیت‌هاب برای لینک مخزن، تصویری ۱۲۸۰ در ۶۴۰ پیکسل و کوچک‌تر از یک مگابایت
می‌پذیرد. این اسکریپت همان تصویر را بازتولیدپذیر می‌سازد.

نیازمندی‌ها (فقط برای تولید تصویر، نه برای استفاده از کیت):

    pip install pillow arabic-reshaper python-bidi

اجرا:

    python assets/make_social_preview.py

خروجی: assets/social-preview.png

بارگذاری: Settings → General → Social preview → Upload an image
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

try:
    import arabic_reshaper
    from bidi.algorithm import get_display
except ImportError:  # pragma: no cover
    raise SystemExit("نصب لازم: pip install arabic-reshaper python-bidi")

HERE = Path(__file__).resolve().parent
WIDTH, HEIGHT = 1280, 640

INK = (232, 238, 242)
MUTED = (150, 168, 180)
ACCENT = (76, 176, 240)
BG_TOP = (10, 17, 26)
BG_BOTTOM = (18, 31, 44)


def shape(text: str) -> str:
    """متن فارسی را برای موتور چپ‌به‌راست Pillow به ترتیب نمایش تبدیل می‌کند."""
    return get_display(arabic_reshaper.reshape(text))


def font(name: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(HERE / name), size)


def gradient() -> Image.Image:
    image = Image.new("RGB", (WIDTH, HEIGHT), BG_TOP)
    draw = ImageDraw.Draw(image)
    for y in range(HEIGHT):
        ratio = y / (HEIGHT - 1)
        color = tuple(int(BG_TOP[i] + (BG_BOTTOM[i] - BG_TOP[i]) * ratio) for i in range(3))
        draw.line([(0, y), (WIDTH, y)], fill=color)
    return image


def rtl_text(draw: ImageDraw.ImageDraw, right: int, y: int, text: str, fnt, fill) -> None:
    """متن راست‌چین نسبت به مختصات افقی داده‌شده می‌نویسد."""
    rendered = shape(text)
    width = draw.textlength(rendered, font=fnt)
    draw.text((right - width, y), rendered, font=fnt, fill=fill)


def main() -> int:
    image = gradient()
    draw = ImageDraw.Draw(image)

    # نوار تزئینی سمت راست
    draw.rectangle([WIDTH - 8, 0, WIDTH, HEIGHT], fill=ACCENT)

    bold_56 = font("Vazirmatn-Bold.ttf", 56)
    bold_34 = font("Vazirmatn-Bold.ttf", 34)
    regular_26 = font("Vazirmatn-Regular.ttf", 26)
    regular_22 = font("Vazirmatn-Regular.ttf", 22)

    right = WIDTH - 72

    rtl_text(draw, right, 92, "کیت راست‌چین AutoClaw", bold_56, INK)
    rtl_text(draw, right, 180, "نمایش درست فارسی در پیام‌ها،", regular_26, MUTED)
    rtl_text(draw, right, 222, "مارک‌داون و ترمینال", regular_26, MUTED)

    # دو نمونهٔ پیش و پس
    box_top, box_height = 320, 88
    box_right = right
    box_left = right - 720

    def panel(top: int, outline: tuple, fill: tuple, dot: tuple, label: str) -> None:
        draw.rounded_rectangle([box_left, top, box_right, top + box_height], 14,
                               fill=fill, outline=outline, width=2)
        draw.ellipse([box_left + 22, top + box_height // 2 - 6,
                      box_left + 34, top + box_height // 2 + 6], fill=dot)
        rendered = shape(label)
        width = draw.textlength(rendered, font=regular_22)
        draw.text((box_right - 28 - width, top + (box_height - 30) // 2), rendered,
                  font=regular_22, fill=INK)

    panel(box_top, (120, 60, 60), (38, 24, 26), (232, 120, 120),
          "پیش: پرانتز برعکس، ترتیب به‌هم‌ریخته")
    panel(box_top + box_height + 20, (60, 130, 100), (20, 38, 32), (120, 220, 160),
          "پس: پایهٔ جهت راست، جمله یکدست")

    # پانویس
    rtl_text(draw, right, HEIGHT - 96, "github.com/armanpoor/autoclaw-rtl-kit", regular_22, ACCENT)
    rtl_text(draw, right, HEIGHT - 58, "پرامپت‌های آماده • سه ابزار بدون وابستگی • مجوز MIT", regular_22, MUTED)

    out = HERE / "social-preview.png"
    image.save(out, "PNG", optimize=True)
    print(f"ساخته شد: {out} ({out.stat().st_size // 1024} کیلوبایت)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
