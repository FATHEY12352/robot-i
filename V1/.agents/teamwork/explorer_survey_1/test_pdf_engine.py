# -*- coding: utf-8 -*-
import subprocess
import os
import sys
import pymupdf

sys.stdout.reconfigure(encoding='utf-8')

test_html_path = r"d:\projekt\ARM\.agents\teamwork\explorer_survey_1\test_render.html"
test_pdf_path = r"d:\projekt\ARM\.agents\teamwork\explorer_survey_1\test_render.pdf"

html = """<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8">
<title>اختبار الطباعة العربية وتوجيه المعادلات</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.css">
<script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.js"></script>
<script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/contrib/auto-render.min.js"
    onload="renderMathInElement(document.body, {delimiters: [{left: '$$', right: '$$', display: true}, {left: '$', right: '$', display: false}]});"></script>
<style>
  @page {
    size: A4;
    margin: 15mm;
  }
  body {
    font-family: 'Dubai', 'Segoe UI', Arial, sans-serif;
    font-size: 11pt;
    line-height: 1.6;
    color: #1e293b;
    direction: rtl;
  }
  h1 { color: #1e40af; border-bottom: 2px solid #2563eb; padding-bottom: 5px; }
  .box { background: #f1f5f9; border-right: 4px solid #2563eb; padding: 10px; margin: 15px 0; border-radius: 4px; }
  
  /* Critical rule for Math and Code in RTL academic documents */
  .katex, .katex-display, .math-ltr, code, pre {
    direction: ltr !important;
    unicode-bidi: isolate !important;
    text-align: center;
  }
  .katex-inline {
    display: inline-block;
    direction: ltr !important;
    unicode-bidi: isolate !important;
  }
</style>
</head>
<body>
  <h1>أطروحة الجدوى التقنية والاقتصادية لمنظومات الذكاء الاصطناعي الفيزيائي</h1>
  <p>هذا النص تجريبي للتحقق من سلامة دعم الحروف العربية وتشكيل الكلمات (Text Shaping & BiDi) والخطوط الرسمية مثل خط دبي (Dubai Font) و Segoe UI.</p>
  <div class="box">
    <strong>معادلة التحويل الحركي الأمامي (Forward Kinematics):</strong>
    <p>مصفوفة التحويل المتجانس من القاعدة إلى النهاية الفعالة:</p>
    <div class="math-ltr">
      $$^{0}T_{6} = \\prod_{i=1}^{6} A_i(\\theta_i, d_i, a_i, \\alpha_i) = A_1 A_2 A_3 A_4 A_5 A_6$$
    </div>
    <p>حيث تمثل المصفوفة <span class="katex-inline">$A_i$</span> مصفوفة ديناميك-هارتنبرغ (Denavit-Hartenberg) للوصلة <span class="katex-inline">$i$</span>.</p>
  </div>
</body>
</html>"""

with open(test_html_path, "w", encoding="utf-8") as f:
    f.write(html)

msedge_path = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
if not os.path.exists(msedge_path):
    msedge_path = r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"

cmd = [
    msedge_path,
    "--headless",
    "--disable-gpu",
    "--no-pdf-header-footer",
    f"--print-to-pdf={test_pdf_path}",
    f"file:///{test_html_path.replace(os.sep, '/')}"
]
subprocess.run(cmd, capture_output=True, text=True)

doc = pymupdf.open(test_pdf_path)
page = doc[0]
pix = page.get_pixmap(dpi=150)
pix.save(r"d:\projekt\ARM\.agents\teamwork\explorer_survey_1\test_render.png")
print("Rendered updated test_render.png.")
