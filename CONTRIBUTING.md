<div dir="rtl">

# مشارکت

ممنون که وقت می‌گذارید. این پروژه کوچک است و هر اصلاح، هر مثال و هر گزارش خطا ارزش دارد.

## پیش از ارسال تغییر

۱. مسئله را در یک ایشو توضیح بدهید. اگر تغییر کوچک است، همان پول‌ریکوئست کافی است.
۲. فایل‌های مارک‌داونی که انسان می‌خواند باید در بستهٔ `<div dir="rtl">` باشند:

```bash
python tools/rtl_wrap.py docs/your-file.md --in-place
python tools/rtl_wrap.py docs/your-file.md --check
```

۳. هر فایل متنی را با بازرس بررسی کنید:

```bash
python tools/rtl_lint.py README.md docs/*.md
```

۴. آزمون‌ها را اجرا کنید:

```bash
python tests/test_rtl_presentation.py
```

## قواعد محتوایی

- کد، نام فایل، فرمان و آدرس هگز در بلوک کد یا کد درون‌خطی؛ نه وسط جملهٔ فارسی.
- ارقام لاتین برای عددهای فنی، تا جست‌وجو و مقایسه ممکن بماند.
- جمله‌های کوتاه، بدون تعارف و مقدمه‌چینی.
- اگر رفتار یک محیط را ادعا می‌کنید، نسخه و منبع را بنویسید.

## پیام کامیت

از قالب متعارف استفاده کنید:

```
docs: add troubleshooting entry for mirrored parentheses
fix: keep nested lists inside their parent item
feat: strip invisible bidi marks before wrapping
```

## مجوز مشارکت

با ارسال پول‌ریکوئست می‌پذیرید که مشارکت شما تحت مجوز MIT همین مخزن منتشر شود.

</div>
