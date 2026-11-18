# -*- coding: utf-8 -*-
import subprocess
import os
import sys
import pymupdf

test_html_path = r"d:\projekt\ARM\.agents\teamwork\explorer_survey_1\test_render.html"
test_pdf_path = r"d:\projekt\ARM\.agents\teamwork\explorer_survey_1\test_edge_hf.pdf"

msedge_path = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
if not os.path.exists(msedge_path):
    msedge_path = r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"

# In Chrome/Edge headless, custom header and footer requires not passing --no-pdf-header-footer
# and passing --display-header-footer or using DevTools protocol
# Or let's test if --no-pdf-header-footer is omitted:
cmd = [
    msedge_path,
    "--headless",
    "--disable-gpu",
    f"--print-to-pdf={test_pdf_path}",
    f"file:///{test_html_path.replace(os.sep, '/')}"
]

res = subprocess.run(cmd, capture_output=True, text=True)
print("Return code:", res.returncode)
print("PDF exists:", os.path.exists(test_pdf_path))

doc = pymupdf.open(test_pdf_path)
print("Page count:", len(doc))
pix = doc[0].get_pixmap(dpi=150)
pix.save(r"d:\projekt\ARM\.agents\teamwork\explorer_survey_1\test_edge_hf.png")
print("Saved preview image.")
