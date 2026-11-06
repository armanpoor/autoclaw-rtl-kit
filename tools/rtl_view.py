#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
rtl_view.py — پیش‌نمایش راست‌چین و قابل‌اعتماد متن‌های فارسی
============================================================

مشکل: بسیاری از محيط‌ها (ترمینال ویندوز، پیش‌نمایش خام فایل، پنجره‌های
متن ساده) پایهٔ جهت پاراگراف را LTR می‌گذارند. نتیجه: حروف فارسی درست
رندر می‌شوند ولی علائم نگارشی، پرانتزها، بولت فهرست و ستون‌های جدول
جابه‌جا می‌شوند (نقص پیاده‌سازی الگوریتم دوجهته یونیکد، UAX #9).

راه‌حل قطعی: رندر متن با یک موتور واقعی که پایهٔ جهت را RTL می‌کند.
این اسکریپت هر فایل .md/.txt (و در صورت نصب python-docx هر .docx) را به
یک HTML مستقل و آفلاین تبدیل می‌کند و در مرورگر باز می‌کند.

نکات پیاده‌سازی:
  * direction: rtl  +  unicode-bidi: isolate  برای بلوک‌های متن
  * pre / code / hex / اعداد  →  direction: ltr  +  unicode-bidi: isolate
  * پاک‌سازی کاراکترهای کنترلی مطابق قانون ۱.۴ سند حاکمیتی پروژه
  * بدون هیچ وابستگی خارجی (بدون markdown/pygments) تا در هر ماشینی اجرا شود

استفاده:
    python tools/rtl_view.py <file>            # ساخت HTML و باز کردن آن
    python tools/rtl_view.py <file> --no-open  # فقط ساخت HTML
    python tools/rtl_view.py <file> --out out.html
    python tools/rtl_view.py <file> --no-toc --normalize
    python tools/rtl_view.py <file> --normalize  # ي/ك عربی → ی/ک فارسی
"""

from __future__ import annotations

import argparse
import html
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

# ---------------------------------------------------------------- قانون ۱.۴
CTRL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x84\x86-\x9f]")

PERSIAN_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")
NUMERIC_RE = re.compile(r"^[\s\d.,+\-–—%<>×/()\[\]:‏‎]*$")


# ------------------------------------------------------------------- کمکی‌ها
def clean(text: str, normalize: bool = False) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\t", "    ")
    text = CTRL_RE.sub("", text)
    if normalize:
        text = (text.replace("ي", "ی").replace("ك", "ک")
                    .replace("ۀ", "هٔ").replace("أ", "ا").replace("إ", "ا"))
    return text


def esc(text: str) -> str:
    return html.escape(text, quote=False)


def is_numeric_cell(text: str) -> bool:
    candidate = text.translate(PERSIAN_DIGITS)
    return bool(candidate.strip()) and bool(NUMERIC_RE.match(candidate)) and any(
        ch.isdigit() for ch in candidate
    )


def inline(text: str) -> str:
    """مارک‌داون درون‌خطی → HTML (امن و بدون وابستگی)."""
    stash: list[str] = []

    def keep(fragment: str) -> str:
        stash.append(fragment)
        return f"\x00{len(stash) - 1}\x00"

    text = esc(text)

    # کد درون‌خطی: همیشه LTR و ایزوله
    text = re.sub(r"`([^`]+)`", lambda m: keep(f'<code class="ltr">{m.group(1)}</code>'), text)
    # پیوندها
    text = re.sub(
        r"\[([^\]]+)\]\((https?://[^\s)]+)\)",
        lambda m: keep(f'<a href="{m.group(2)}">{m.group(1)}</a>'),
        text,
    )
    # پررنگ / کج
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<![\w*])\*([^*\n]+)\*(?![\w*])", r"<em>\1</em>", text)
    # پرانتزهای حاوی واژه/عدد لاتین: ایزوله‌سازی دوجهته با span (بدون کاراکتر نامرئی)
    text = re.sub(
        r"\(([^()\n]{0,80})\)",
        lambda m: f'<span class="iso">({m.group(1)})</span>'
        if re.search(r"[A-Za-z0-9%°×+\-]+", m.group(1)) else f"({m.group(1)})",
        text,
    )

    for index, fragment in enumerate(stash):
        text = text.replace(f"\x00{index}\x00", fragment)
    return text


# ------------------------------------------------------------------ بلوک‌ها
def render_table(rows: list[str]) -> str:
    def cells(line: str) -> list[str]:
        return [c.strip() for c in line.strip().strip("|").split("|")]

    header, separator = cells(rows[0]), cells(rows[1])
    aligns: list[str] = []
    for col in separator:
        left, right = col.startswith(":"), col.endswith(":")
        aligns.append("center" if left and right else "left" if right else
                      "right" if left else "center")

    out = ['<table class="grid">', "<thead><tr>"]
    for i, cell in enumerate(header):
        out.append(f'<th style="text-align:{aligns[i] if i < len(aligns) else "center"}">{inline(cell)}</th>')
    out.append("</tr></thead><tbody>")
    for row in rows[2:]:
        out.append("<tr>")
        for i, cell in enumerate(cells(row)):
            numeric = is_numeric_cell(cell)
            cls = ' class="num ltr"' if numeric else ""
            alignment = "center" if numeric else (aligns[i] if i < len(aligns) else "right")
            out.append(f'<td{cls} style="text-align:{alignment}">{inline(cell)}</td>')
        out.append("</tr>")
    out.append("</tbody></table>")
    return "".join(out)


def render_list(items: list[tuple[int, str, bool]]) -> str:
    """items: (سطح تورفتگی، متن، آیا شماره‌دار) — ساخت درخت و رندر بازگشتی"""
    root: list[dict] = []
    stack: list[tuple[int, list[dict]]] = [(-1, root)]
    for level, text, ordered in items:
        level = min(level, 3)
        while len(stack) > 1 and stack[-1][0] >= level:
            stack.pop()
        node = {"text": text, "ordered": ordered, "children": []}
        stack[-1][1].append(node)
        stack.append((level, node["children"]))

    def render(nodes: list[dict]) -> str:
        chunks: list[str] = []
        index = 0
        while index < len(nodes):
            ordered = nodes[index]["ordered"]
            tag = "ol" if ordered else "ul"
            chunks.append(f"<{tag}>")
            while index < len(nodes) and nodes[index]["ordered"] == ordered:
                node = nodes[index]
                chunks.append(f"<li>{inline(node['text'])}")
                if node["children"]:
                    chunks.append(render(node["children"]))
                chunks.append("</li>")
                index += 1
            chunks.append(f"</{tag}>")
        return "".join(chunks)

    return render(root)


def md_to_html(source: str, toc: bool = True) -> tuple[str, str]:
    lines, out, titles = source.split("\n"), [], []
    i, n = 0, len(lines)
    paragraph: list[str] = []

    def flush() -> None:
        if paragraph:
            out.append(f"<p>{inline(' '.join(paragraph))}</p>")
            paragraph.clear()

    while i < n:
        line = lines[i]
        stripped = line.strip()

        # بلوک کد
        fence = re.match(r"^\s*(```+|~~~+)\s*([\w+#-]*)", line)
        if fence:
            flush()
            marker, lang = fence.group(1), fence.group(2)
            body: list[str] = []
            i += 1
            while i < n and not lines[i].strip().startswith(marker):
                body.append(lines[i])
                i += 1
            i += 1
            cls = f' class="ltr language-{lang}"' if lang else ' class="ltr"'
            out.append(f"<pre><code{cls}>{esc(chr(10).join(body))}</code></pre>")
            continue

        # عنوان‌ها
        heading = re.match(r"^\s{0,3}(#{1,6})\s+(.*?)\s*#*\s*$", line)
        if heading:
            flush()
            level = len(heading.group(1))
            text = heading.group(2)
            anchor = f"h{len(titles)}"
            titles.append((level, text, anchor))
            out.append(f'<h{level} id="{anchor}">{inline(text)}</h{level}>')
            i += 1
            continue

        # جدول
        if stripped.startswith("|") and i + 1 < n and re.match(r"^\s*\|?[\s:|-]+\|[\s:|-]*$", lines[i + 1]):
            flush()
            block: list[str] = []
            while i < n and lines[i].strip().startswith("|"):
                block.append(lines[i])
                i += 1
            out.append(render_table(block))
            continue

        # فهرست‌ها
        bullet = re.match(r"^(\s*)([-*+]|\d+[.)])\s+(.*)$", line)
        if bullet:
            flush()
            items: list[tuple[int, str, bool]] = []
            while i < n:
                match = re.match(r"^(\s*)([-*+]|\d+[.)])\s+(.*)$", lines[i])
                if not match:
                    if lines[i].strip() == "":
                        i += 1
                        continue
                    break
                indent = len(match.group(1).replace("\t", "  "))
                items.append((indent // 2, match.group(3), match.group(2)[0].isdigit()))
                i += 1
            out.append(render_list(items))
            continue

        # نقل‌قول
        if stripped.startswith(">"):
            flush()
            quote: list[str] = []
            while i < n and lines[i].strip().startswith(">"):
                quote.append(lines[i].strip()[1:].strip())
                i += 1
            out.append(f"<blockquote>{inline(' '.join(quote))}</blockquote>")
            continue

        # جداکننده
        if re.match(r"^\s*([-*_])\1{2,}\s*$", line):
            flush()
            out.append("<hr/>")
            i += 1
            continue

        if not stripped:
            flush()
            i += 1
            continue

        paragraph.append(stripped)
        i += 1

    flush()

    if toc and len(titles) >= 3:
        entries = "".join(
            f'<li class="toc-l{min(level, 3)}"><a href="#{anchor}">{inline(text)}</a></li>'
            for level, text, anchor in titles if level <= 3
        )
        nav = ('<nav class="toc"><div class="toc-title">فهرست مطالب</div>'
               f"<ul>{entries}</ul></nav>")
        out.insert(0, nav)

    return "\n".join(out), source


CSS = """
:root{--bg:#fbfbf9;--paper:#ffffff;--fg:#1c1c1e;--muted:#5b6470;--line:#d7dce2;--accent:#0f5c8c}
*{box-sizing:border-box}
html{background:var(--bg)}
body{margin:0 auto;max-width:52rem;padding:2.2rem 2.4rem 4rem;background:var(--paper);
     border:1px solid var(--line);border-radius:10px;margin-top:1.6rem;margin-bottom:2.4rem;
     font-family:"Vazirmatn","Vazir","IRANSansX","IRANSans","Sahel","Segoe UI","Tahoma",system-ui,sans-serif;
     font-size:12.5pt;line-height:1.95;color:var(--fg);direction:rtl;text-align:justify;
     font-feature-settings:"ss02","kern";}
h1,h2,h3,h4,h5,h6{direction:rtl;unicode-bidi:isolate;text-align:right;line-height:1.5;
     margin:1.8em 0 .6em;color:#10222e;page-break-after:avoid}
h1{font-size:1.75em;border-bottom:3px solid var(--accent);padding-bottom:.35em}
h2{font-size:1.38em;border-bottom:1px solid var(--line);padding-bottom:.25em}
h3{font-size:1.16em;color:var(--accent)}
p,li,dd,dt,blockquote,td,th{direction:rtl;unicode-bidi:isolate}
p{margin:0 0 1em}
a{color:var(--accent);text-decoration:none;border-bottom:1px dotted var(--accent)}
blockquote{margin:1.2em 0;padding:.7em 1em;border-right:4px solid var(--accent);
     background:#f4f8fb;border-radius:0 6px 6px 0;color:#243b4a}
ul,ol{padding-right:1.6em;padding-left:0;margin:0 0 1em}
li{margin:.25em 0}
code{direction:ltr;unicode-bidi:isolate;font-family:"Cascadia Mono","Consolas","Courier New",monospace;
     font-size:.9em;background:#eef2f6;padding:.08em .35em;border-radius:4px;display:inline-block}
pre{direction:ltr;text-align:left;unicode-bidi:isolate;background:#0f1b24;color:#e6edf3;
     padding:1em 1.1em;border-radius:8px;overflow-x:auto;line-height:1.6;margin:1.2em 0}
pre code{background:none;color:inherit;padding:0;display:block;font-size:.88em;white-space:pre}
table.grid{direction:rtl;width:100%;border-collapse:collapse;margin:1.2em 0;font-size:.95em;line-height:1.5}
table.grid th,table.grid td{border:1px solid var(--line);padding:.45em .6em;vertical-align:top}
table.grid th{background:#eaf1f7;font-weight:700}
table.grid tr:nth-child(even) td{background:#fafcfd}
td.num{direction:ltr;unicode-bidi:isolate;font-family:"Cascadia Mono","Consolas",monospace;text-align:center}
span.iso{unicode-bidi:isolate}
hr{border:0;border-top:1px solid var(--line);margin:2em 0}
nav.toc{background:#f6f9fb;border:1px solid var(--line);border-radius:8px;padding:1em 1.2em;margin:0 0 2em}
nav.toc .toc-title{font-weight:700;margin-bottom:.5em;color:var(--accent)}
nav.toc ul{list-style:none;padding:0;margin:0}
nav.toc li{margin:.2em 0}
nav.toc li.toc-l2{padding-right:1.4em;font-size:.95em}
nav.toc li.toc-l3{padding-right:2.8em;font-size:.92em;color:var(--muted)}
nav.toc a{border:0}
@media print{
  @page{size:A4;margin:20mm 18mm}
  html{background:#fff}
  body{max-width:none;border:0;border-radius:0;margin:0;padding:0;font-size:11.5pt;line-height:1.8}
  nav.toc{page-break-after:always}
  pre,table,blockquote{page-break-inside:avoid}
  a{color:#000;border:0}
}
"""

SCRIPT = """
(function(){
  var size = 12.5;
  function apply(){ document.body.style.fontSize = size + 'pt'; }
  document.addEventListener('keydown', function(e){
    if (!e.ctrlKey && !e.metaKey) return;
    if (e.key === '=' || e.key === '+') { size = Math.min(size + 0.5, 20); apply(); e.preventDefault(); }
    if (e.key === '-') { size = Math.max(size - 0.5, 9); apply(); e.preventDefault(); }
  });
})();
"""


def strip_wrapper(text: str) -> str:
    """حذف بستهٔ <div dir="rtl"> از سر و ته متن (اگر وجود داشته باشد)."""
    cleaned = text.lstrip("\ufeff").strip()
    if cleaned.startswith('<div dir="rtl">'):
        cleaned = cleaned[len('<div dir="rtl">'):].lstrip()
        if cleaned.endswith("</div>"):
            cleaned = cleaned[: -len("</div>")]
    return cleaned


def build_html(body: str, title: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>{esc(title)}</title>
<link rel="preconnect" href="https://cdn.jsdelivr.net"/>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/rastikerdar/vazirmatn@v33.003/Vazirmatn-font-face.css"/>
<style>{CSS}</style>
</head>
<body>
{body}
<script>{SCRIPT}</script>
</body>
</html>
"""


def docx_to_markdown(path: Path) -> str:
    """تبدیل سادهٔ داکس به مارک‌داون (در صورت نصب python-docx)."""
    from docx import Document
    from docx.table import Table
    from docx.text.paragraph import Paragraph

    document = Document(str(path))
    chunks: list[str] = []
    for child in document.element.body.iterchildren():
        if child.tag.endswith("}p"):
            paragraph = Paragraph(child, document)
            text = paragraph.text.strip()
            if not text:
                continue
            style = (paragraph.style.name or "").lower()
            if style.startswith("heading"):
                digits = re.findall(r"\d+", style)
                level = int(digits[0]) if digits else 2
                chunks.append("#" * min(max(level, 1), 6) + " " + text)
            else:
                chunks.append(text)
        elif child.tag.endswith("}tbl"):
            table = Table(child, document)
            rows: list[list[str]] = []
            for row in table.rows:
                cells = [c.text.strip().replace("\n", " ") for c in row.cells]
                if any(cells):
                    rows.append(cells)
            if rows:
                cols = max(len(r) for r in rows)
                rendered = ["| " + " | ".join(r + [""] * (cols - len(r))) + " |" for r in rows]
                separator = "| " + " | ".join(["---"] * cols) + " |"
                chunks.append("\n".join([rendered[0], separator] + rendered[1:]))
    return "\n\n".join(chunks)


def read_clipboard() -> str:
    """متن کلیپ‌بورد ویندوز (برای متن کپی‌شده از پنجره‌هایی که فارسی را بهم می‌ریزند)."""
    command = "[Console]::OutputEncoding=[Text.Encoding]::UTF8; Get-Clipboard -Raw"
    result = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", command],
        capture_output=True,
    )
    if result.returncode != 0 or not result.stdout.strip():
        raise RuntimeError("کلیپ‌بورد خالی است یا خواندنش ممکن نشد")
    for encoding in ("utf-8", "utf-16", "cp1256"):
        try:
            return result.stdout.decode(encoding).strip()
        except UnicodeDecodeError:
            continue
    return result.stdout.decode("utf-8", errors="replace").strip()


def main() -> int:
    parser = argparse.ArgumentParser(description="پیش‌نمایش راست‌چین فایل متنی در مرورگر")
    parser.add_argument("source", nargs="?", help="مسیر فایل .md / .txt / .docx")
    parser.add_argument("--clipboard", action="store_true", help="خواندن متن از کلیپ‌بورد به‌جای فایل")
    parser.add_argument("--out", help="مسیر فایل HTML خروجی")
    parser.add_argument("--title", help="عنوان صفحه")
    parser.add_argument("--no-toc", action="store_true", help="بدون فهرست مطالب")
    parser.add_argument("--no-open", action="store_true", help="مرورگر را باز نکن")
    parser.add_argument("--normalize", action="store_true", help="تبدیل ي/ك عربی به ی/ک فارسی")
    args = parser.parse_args()

    if args.clipboard:
        try:
            source = clean(read_clipboard(), args.normalize)
        except RuntimeError as error:
            print(error, file=sys.stderr)
            return 3
        body, _ = md_to_html(strip_wrapper(source), toc=False)
        out_path = Path(args.out) if args.out else Path(tempfile.gettempdir()) / "clipboard.rtl.html"
        out_path.write_text(build_html(body, args.title or "متن کلیپ‌بورد"), encoding="utf-8")
        print(f"HTML ساخته شد: {out_path}")
        if not args.no_open:
            open_in_browser(out_path)
        return 0

    if not args.source:
        print("مسیر فایل لازم است یا از --clipboard استفاده کنید.", file=sys.stderr)
        return 2

    path = Path(args.source)
    if not path.is_file():
        print(f"فایل پیدا نشد: {path}", file=sys.stderr)
        return 2

    if path.suffix.lower() in {".docx", ".docm"}:
        source = clean(docx_to_markdown(path), args.normalize)
    else:
        source = clean(path.read_text(encoding="utf-8", errors="replace"), args.normalize)

    source = strip_wrapper(source)

    body, _ = md_to_html(source, toc=not args.no_toc)
    out_path = Path(args.out) if args.out else path.with_suffix(".rtl.html")
    out_path.write_text(build_html(body, args.title or path.stem), encoding="utf-8")

    print(f"HTML ساخته شد: {out_path}")
    if not args.no_open:
        open_in_browser(out_path)
    return 0


def open_in_browser(path: Path) -> None:
    try:
        os.startfile(str(path))  # type: ignore[attr-defined]
    except (AttributeError, OSError):
        import webbrowser
        webbrowser.open(path.as_uri())


if __name__ == "__main__":
    raise SystemExit(main())
