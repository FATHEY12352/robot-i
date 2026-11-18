# -*- coding: utf-8 -*-
import pymupdf
import arabic_reshaper
from bidi.algorithm import get_display

doc = pymupdf.open(r"d:\projekt\ARM\.agents\teamwork\explorer_survey_1\test_render.pdf")
page = doc[0]
rect = page.rect

font_path = r"C:\Windows\Fonts\dubai-regular.ttf"

def reshape_ar(text):
    reshaped = arabic_reshaper.reshape(text)
    return get_display(reshaped)

header_text = reshape_ar("أطروحة مشروع ROBOI — النظم الميكاترونيكية والذكاء الاصطناعي الفيزيائي")
footer_text = reshape_ar("جامعة MISIS — صفحة 1 من 100 — وثيقة سرية للاستخدام الأكاديمي")

# Header line and text
page.draw_line(pymupdf.Point(40, 42), pymupdf.Point(rect.width - 40, 42), color=(0.85, 0.85, 0.88), width=0.75)
page.insert_font(fontname="dubai", fontfile=font_path)
page.insert_textbox(pymupdf.Rect(40, 22, rect.width - 40, 40), header_text, fontname="dubai", fontsize=8.5, color=(0.35, 0.4, 0.45), align=pymupdf.TEXT_ALIGN_RIGHT)

# Footer line and text
page.draw_line(pymupdf.Point(40, rect.height - 42), pymupdf.Point(rect.width - 40, rect.height - 42), color=(0.85, 0.85, 0.88), width=0.75)
page.insert_textbox(pymupdf.Rect(40, rect.height - 38, rect.width - 40, rect.height - 20), footer_text, fontname="dubai", fontsize=8.5, color=(0.35, 0.4, 0.45), align=pymupdf.TEXT_ALIGN_CENTER)

out_pdf = r"d:\projekt\ARM\.agents\teamwork\explorer_survey_1\test_reshaped_stamped.pdf"
doc.save(out_pdf)

pix = doc[0].get_pixmap(dpi=150)
pix.save(r"d:\projekt\ARM\.agents\teamwork\explorer_survey_1\test_reshaped_stamped.png")
print("Saved test_reshaped_stamped.png!")
