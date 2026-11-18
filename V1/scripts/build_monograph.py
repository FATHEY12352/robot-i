#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ROBOI Scientific Monograph & Techno-Economic Feasibility Dossier
Automated PDF Compilation Pipeline

This script discovers, concatenates, and renders modular Arabic Markdown
chapters into a publication-grade, peer-reviewed-level PDF document via
Headless Microsoft Edge, with complete KaTeX mathematical typesetting,
Arabic RTL typography, and CSS Paged Media.

Output:
  - d:\\projekt\\ARM\\output\\ROBOI_Scientific_Monograph_Dossier.html
  - d:\\projekt\\ARM\\output\\ROBOI_Scientific_Monograph_Dossier.pdf
"""

import sys
import os
import re
import html
import shutil
import subprocess
import time
from pathlib import Path

# Force UTF-8 encoding for standard streams
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

import markdown
import pymupdf  # fitz

# Workspace Directories
ROOT_DIR = Path(__file__).resolve().parent.parent
CHAPTERS_DIR = ROOT_DIR / "chapters"
TEMPLATES_DIR = ROOT_DIR / "templates"
OUTPUT_DIR = ROOT_DIR / "output"
PREVIEWS_DIR = OUTPUT_DIR / "previews"
KATEX_LOCAL_DIR = TEMPLATES_DIR / "katex"

HTML_OUTPUT_PATH = OUTPUT_DIR / "ROBOI_Scientific_Monograph_Dossier.html"
PDF_OUTPUT_PATH = OUTPUT_DIR / "ROBOI_Scientific_Monograph_Dossier.pdf"

# The 9 Modular Chapters in strict pedagogical sequence
EXPECTED_CHAPTERS = [
    "00_front_matter.md",
    "01_section_i_executive_summary.md",
    "02_section_ii_actuator_kinematics.md",
    "03_section_iii_opensource_taxonomy.md",
    "04_section_iv_pedagogical_framework.md",
    "05_section_v_competitive_benchmarking.md",
    "06_section_vi_russian_regulatory.md",
    "07_section_vii_financial_engineering.md",
    "08_appendices.md"
]


def find_browser_executable():
    """Locate Microsoft Edge or Google Chrome executable."""
    candidates = [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    
    # Try PATH
    for name in ["msedge", "edge", "chrome", "google-chrome"]:
        found = shutil.which(name)
        if found:
            return found
            
    raise FileNotFoundError("Could not locate Microsoft Edge or Google Chrome for headless compilation.")


def preprocess_markdown(raw_md: str):
    """
    Safely isolate LaTeX math formulas, fenced code blocks, and inline code
    to prevent Markdown parsers from corrupting mathematical symbols,
    underscores, asterisks, matrix ampersands, or backslashes.
    """
    fenced_blocks = []
    def save_fenced(match):
        fenced_blocks.append(match.group(0))
        return f"<!--FENCED_CODE_BLOCK_{len(fenced_blocks)-1}-->"

    # 0. Unwrap raw <div align="center"> to ensure inner markdown headings/bold are parsed
    text_clean = re.sub(r'<\s*div[^>]*align=["\']?center["\']?[^>]*>', '', raw_md, flags=re.IGNORECASE)
    text_clean = re.sub(r'<\s*/\s*div\s*>', '', text_clean, flags=re.IGNORECASE)

    # 1. Protect fenced code blocks ``` ... ```
    text = re.sub(r'```[\s\S]*?```', save_fenced, text_clean)

    # 2. Protect inline code `...`
    inline_code_blocks = []
    def save_inline_code(match):
        inline_code_blocks.append(match.group(0))
        return f"<!--INLINE_CODE_SPAN_{len(inline_code_blocks)-1}-->"

    text = re.sub(r'`[^`\n]+`', save_inline_code, text)

    # 3. Protect display math $$ ... $$
    display_math = []
    def save_display_math(match):
        display_math.append(match.group(1).strip())
        return f"\n\n<!--KATEX_DISPLAY_{len(display_math)-1}-->\n\n"

    text = re.sub(r'\$\$([\s\S]*?)\$\$', save_display_math, text)

    # 4. Protect inline math $ ... $
    inline_math = []
    def save_inline_math(match):
        content = match.group(1).strip()
        inline_math.append(content)
        return f"<!--KATEX_INLINE_{len(inline_math)-1}-->"

    # Match $...$ on single line, avoiding escaped \$
    text = re.sub(r'(?<!\\)\$(?!\$)([^\$\n]+?)(?<!\\)\$', save_inline_math, text)

    # 5. Restore inline code and fenced code before markdown parsing
    for i, code in enumerate(inline_code_blocks):
        text = text.replace(f"<!--INLINE_CODE_SPAN_{i}-->", code)

    for i, block in enumerate(fenced_blocks):
        text = text.replace(f"<!--FENCED_CODE_BLOCK_{i}-->", block)

    return text, display_math, inline_math


def convert_markdown_to_html(md_text: str, display_math: list, inline_math: list) -> str:
    """Convert preprocessed Markdown to HTML and inject LTR math containers."""
    extensions = [
        'tables',
        'fenced_code',
        'toc',
        'attr_list',
        'def_list',
        'admonition'
    ]
    
    html_content = markdown.markdown(md_text, extensions=extensions)

    # Restore display math blocks inside strict LTR isolation containers
    for i, formula in enumerate(display_math):
        # Escape HTML entities so <, >, & don't break HTML parsing while KaTeX renders them cleanly
        safe_formula = html.escape(formula)
        replacement = (
            f'<div class="math-display-container" dir="ltr">'
            f'<div class="katex-display">$${safe_formula}$$</div>'
            f'</div>'
        )
        # Handle cases where markdown wrapped the comment in a paragraph <p>...</p>
        html_content = re.sub(
            rf'<p>\s*<!--KATEX_DISPLAY_{i}-->\s*</p>',
            lambda m, rep=replacement: rep,
            html_content
        )
        html_content = html_content.replace(f"<!--KATEX_DISPLAY_{i}-->", replacement)

    # Restore inline math spans inside strict LTR isolation containers
    for i, formula in enumerate(inline_math):
        safe_formula = html.escape(formula)
        replacement = (
            f'<span class="katex-inline-container" dir="ltr">'
            f'${safe_formula}$'
            f'</span>'
        )
        html_content = html_content.replace(f"<!--KATEX_INLINE_{i}-->", replacement)

    return html_content


def assemble_monograph_html(chapters_html: list) -> str:
    """Read template and stylesheet, then assemble full monograph HTML document."""
    css_path = TEMPLATES_DIR / "monograph_style.css"
    if css_path.exists():
        with open(css_path, "r", encoding="utf-8") as f:
            custom_css = f.read()
    else:
        custom_css = "body { direction: rtl; font-family: 'Dubai', sans-serif; }"

    template_path = TEMPLATES_DIR / "monograph_template.html"
    if template_path.exists():
        with open(template_path, "r", encoding="utf-8") as f:
            template = f.read()
    else:
        template = """<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8">
<title>ROBOI Monograph</title>
<link rel="stylesheet" href="../templates/katex/katex.min.css">
<style>__MONOGRAPH_STYLES__</style>
<script src="../templates/katex/katex.min.js"></script>
<script src="../templates/katex/auto-render.min.js"></script>
<script>
window.onload = function() {
    if (typeof renderMathInElement !== 'undefined') {
        renderMathInElement(document.body, {
            delimiters: [
                {left: '$$', right: '$$', display: true},
                {left: '$', right: '$', display: false}
            ],
            throwOnError: false
        });
    }
};
</script>
</head>
<body dir="rtl">
__MONOGRAPH_BODY__
</body>
</html>"""

    body_content = "\n\n".join(chapters_html)
    full_html = template.replace("__MONOGRAPH_STYLES__", custom_css)
    full_html = full_html.replace("__MONOGRAPH_BODY__", body_content)

    return full_html


def compile_pdf(html_path: Path, pdf_path: Path) -> bool:
    """Execute Headless Microsoft Edge to generate vector publication PDF."""
    browser_exe = find_browser_executable()
    print(f"[*] Using headless browser engine: {browser_exe}")

    html_url = f"file:///{html_path.resolve().as_posix()}"
    pdf_dest = str(pdf_path.resolve())

    cmd = [
        browser_exe,
        "--headless",
        "--disable-gpu",
        "--no-pdf-header-footer",
        "--run-all-compositor-stages-before-draw",
        "--virtual-time-budget=8000",
        f"--print-to-pdf={pdf_dest}",
        html_url
    ]

    print(f"[*] Executing PDF compilation command...")
    t0 = time.time()
    result = subprocess.run(cmd, capture_output=True, text=True)
    duration = time.time() - t0

    if result.returncode != 0:
        print(f"[!] Browser execution failed with code {result.returncode}")
        print(f"[!] Stderr: {result.stderr}")
        return False

    print(f"[+] Compilation finished in {duration:.2f} seconds.")
    return pdf_path.exists() and pdf_path.stat().st_size > 0


def generate_previews(pdf_path: Path, output_preview_dir: Path, sample_count=8):
    """Generate high-resolution PNG previews for key pages."""
    output_preview_dir.mkdir(parents=True, exist_ok=True)
    doc = pymupdf.open(str(pdf_path))
    total_pages = len(doc)
    print(f"[*] Generating visual page previews for verification (Total pages: {total_pages})...")

    # Select representative pages: first 3, middle, and end
    indices = set([0, 1, 2, 3, total_pages // 4, total_pages // 2, (3 * total_pages) // 4, total_pages - 1])
    sorted_indices = sorted([i for i in indices if 0 <= i < total_pages])

    for idx in sorted_indices:
        page = doc[idx]
        pix = page.get_pixmap(dpi=150)
        preview_file = output_preview_dir / f"page_{idx+1:03d}.png"
        pix.save(str(preview_file))
        print(f"    - Rendered preview: page_{idx+1:03d}.png (Page {idx+1}/{total_pages})")

    doc.close()


def main():
    print("=" * 78)
    print("ROBOI MONOGRAPH AUTOMATED COMPILATION PIPELINE")
    print("Academic Arabic RTL Monograph & Feasibility Dossier")
    print("=" * 78)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Inspect Chapters
    available_chapters = []
    missing_chapters = []
    total_raw_chars = 0
    total_raw_words = 0

    print(f"\n[*] Scanning chapters in: {CHAPTERS_DIR}")
    for ch_name in EXPECTED_CHAPTERS:
        ch_path = CHAPTERS_DIR / ch_name
        if ch_path.exists() and ch_path.stat().st_size > 0:
            with open(ch_path, "r", encoding="utf-8") as f:
                content = f.read()
            chars = len(content)
            words = len(content.split())
            total_raw_chars += chars
            total_raw_words += words
            available_chapters.append((ch_name, ch_path, content))
            print(f"  [✓] {ch_name:<42} | {chars:>6} chars | {words:>5} words")
        else:
            missing_chapters.append(ch_name)
            print(f"  [✗] {ch_name:<42} | MISSING OR EMPTY")

    print(f"\n[*] Chapter Summary: {len(available_chapters)}/{len(EXPECTED_CHAPTERS)} present.")
    print(f"[*] Total Raw Corpus: {total_raw_chars:,} characters | {total_raw_words:,} words.")

    if not available_chapters:
        print("[!] Fatal: No chapter files found to compile.")
        sys.exit(1)

    # 2. Process Chapters and Render HTML
    print("\n[*] Processing chapters: protecting formulas and converting Markdown to HTML...")
    chapters_html = []
    total_display_math = 0
    total_inline_math = 0

    for i, (ch_name, ch_path, raw_md) in enumerate(available_chapters):
        preprocessed, d_math, i_math = preprocess_markdown(raw_md)
        total_display_math += len(d_math)
        total_inline_math += len(i_math)
        ch_html = convert_markdown_to_html(preprocessed, d_math, i_math)
        
        # Wrap chapter in section container with page-break class
        wrapper = (
            f'<section class="chapter-container" id="chapter_{i:02d}">\n'
            f'{ch_html}\n'
            f'</section>'
        )
        chapters_html.append(wrapper)

    print(f"[*] Extracted and isolated {total_display_math} display formulas and {total_inline_math} inline formulas.")

    # 3. Assemble Full HTML Document
    print("\n[*] Assembling complete publication HTML document...")
    full_html = assemble_monograph_html(chapters_html)

    with open(HTML_OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(full_html)

    html_size = HTML_OUTPUT_PATH.stat().st_size
    print(f"[+] Saved publication HTML to: {HTML_OUTPUT_PATH} ({html_size / 1024:.1f} KB)")

    # 4. Compile to PDF via Headless Edge
    print(f"\n[*] Compiling PDF to: {PDF_OUTPUT_PATH}")
    success = compile_pdf(HTML_OUTPUT_PATH, PDF_OUTPUT_PATH)

    if not success:
        print("[!] Error: PDF compilation failed.")
        sys.exit(1)

    pdf_size = PDF_OUTPUT_PATH.stat().st_size
    doc = pymupdf.open(str(PDF_OUTPUT_PATH))
    page_count = len(doc)
    doc.close()

    print("\n" + "=" * 78)
    print("COMPILATION REPORT & VERIFICATION METRICS")
    print("=" * 78)
    print(f"  - Target PDF:        {PDF_OUTPUT_PATH}")
    print(f"  - File Size:         {pdf_size:,} bytes ({pdf_size / (1024*1024):.2f} MB)")
    print(f"  - Page Count:        {page_count} pages")
    print(f"  - Raw Words:         {total_raw_words:,} words")
    print(f"  - LaTeX Equations:   {total_display_math + total_inline_math} equations")
    print(f"  - Chapters Built:    {len(available_chapters)}/9")
    print("=" * 78)

    # 5. Generate Visual Previews
    generate_previews(PDF_OUTPUT_PATH, PREVIEWS_DIR)

    print("\n[+] Monograph compilation completed successfully!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
