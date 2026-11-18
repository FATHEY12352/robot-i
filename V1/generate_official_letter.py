# -*- coding: utf-8 -*-
"""
Generate Official Proposal Letter to the Institute Director / Rector
Generates:
1. Official_Proposal_to_Institute_Director.html (Formal Administrative Document)
2. Official_Proposal_to_Institute_Director.pdf (A4 Portrait Official Letter)
"""

import os
import subprocess

WORKSPACE = r"d:\projekt\ARM"
HTML_PATH = os.path.join(WORKSPACE, "Official_Proposal_to_Institute_Director.html")
PDF_PATH = os.path.join(WORKSPACE, "Official_Proposal_to_Institute_Director.pdf")

html_content = """<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<title>Официальное предложение: Лаборатория Physical AI ROBOI</title>
<style>
  @page {
    size: A4 portrait;
    margin: 18mm 20mm 18mm 20mm;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: "Times New Roman", Times, serif;
    color: #111827;
    line-height: 1.45;
    font-size: 11pt;
    background: #fff;
  }
  .page {
    page-break-after: always;
    position: relative;
  }
  .page:last-child {
    page-break-after: avoid;
  }
  
  /* Official Russian Institutional Header */
  .doc-header {
    border-bottom: 2px solid #1e3a8a;
    padding-bottom: 12px;
    margin-bottom: 18px;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
  .org-title {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    font-size: 13pt;
    font-weight: 800;
    color: #1e3a8a;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }
  .org-sub {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    font-size: 8.5pt;
    color: #4b5563;
    margin-top: 2px;
  }
  .doc-meta {
    text-align: right;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    font-size: 8.5pt;
    color: #374151;
  }

  /* Addressee block (Right-aligned in Russian standard) */
  .addressee-block {
    margin-left: 50%;
    margin-bottom: 24px;
    font-size: 11pt;
    line-height: 1.35;
  }
  .addressee-title {
    font-weight: bold;
  }

  .doc-subject {
    font-weight: bold;
    font-size: 12pt;
    margin-bottom: 16px;
    color: #1e3a8a;
    text-align: center;
    text-transform: uppercase;
    letter-spacing: 0.3px;
    border-top: 1px solid #e5e7eb;
    border-bottom: 1px solid #e5e7eb;
    padding: 6px 0;
  }

  .salutation {
    font-weight: bold;
    margin-bottom: 14px;
    font-size: 12pt;
    text-align: center;
  }

  p {
    text-align: justify;
    text-indent: 1.25cm; /* Russian standard paragraph indent */
    margin-bottom: 8px;
  }

  h2 {
    font-size: 12pt;
    font-weight: bold;
    color: #1e3a8a;
    margin-top: 16px;
    margin-bottom: 8px;
    text-indent: 0;
    border-bottom: 1px solid #cbd5e1;
    padding-bottom: 2px;
  }

  ul, ol {
    margin-left: 1.5cm;
    margin-bottom: 10px;
    text-align: justify;
  }
  li {
    margin-bottom: 4px;
  }

  table.doc-table {
    width: 100%;
    border-collapse: collapse;
    margin: 12px 0;
    font-size: 9.5pt;
  }
  table.doc-table th, table.doc-table td {
    border: 1px solid #4b5563;
    padding: 5px 8px;
    text-align: left;
  }
  table.doc-table th {
    background: #f1f5f9;
    font-weight: bold;
    color: #0f172a;
    text-align: center;
  }
  table.doc-table td.num {
    text-align: right;
  }
  table.doc-table td.center {
    text-align: center;
  }

  .callout-box {
    border-left: 4px solid #1e3a8a;
    background: #f8fafc;
    padding: 10px 14px;
    margin: 12px 0;
    font-size: 10pt;
  }
  .callout-title {
    font-weight: bold;
    color: #1e3a8a;
    margin-bottom: 4px;
  }

  /* Signature Block */
  .sign-block {
    margin-top: 30px;
    display: flex;
    justify-content: space-between;
    align-items: flex-end;
  }
  .sign-person {
    width: 48%;
  }
  .sign-line {
    border-bottom: 1px solid #000;
    margin-top: 35px;
    margin-bottom: 4px;
  }
  .sign-caption {
    font-size: 8pt;
    color: #6b7280;
    text-align: center;
  }

  .stamp-place {
    width: 100px;
    height: 100px;
    border: 1px dashed #9ca3af;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 8pt;
    color: #9ca3af;
    margin: 10px auto;
  }
</style>
</head>
<body>

<!-- PAGE 1: ОФИЦИАЛЬНОЕ ОБРАЩЕНИЕ -->
<div class="page">
  <div class="doc-header">
    <div>
      <div class="org-title">Проектная группа «ROBOI: Physical AI»</div>
      <div class="org-sub">Разработка суверенных платформ открытой манипуляционной робототехники</div>
      <div class="org-sub">Россия, Москва / Санкт-Петербург • Тел.: +7 (999) 000-00-00 • E-mail: info@roboi.ru</div>
    </div>
    <div class="doc-meta">
      <div>Исх. № <strong>04/2026-ПИШ</strong></div>
      <div>Дата: <strong>«02» ноября 2026 г.</strong></div>
    </div>
  </div>

  <div class="addressee-block">
    <div class="addressee-title">Директору Института робототехники, искусственного интеллекта и мехатроники / Декану инженерного факультета</div>
    <div>Университета _______________________</div>
    <div>г. _______________________________</div>
  </div>

  <div class="doc-subject">
    О создании учебно-исследовательской лаборатории открытой робототехники и Physical AI нового поколения
  </div>

  <div class="salutation">
    Глубокоуважаемый Руководитель института!
  </div>

  <p>
    Обращаемся к Вам с предложением о развертывании на базе Вашего института передовой учебно-исследовательской лаборатории манипуляционной робототехники и физического искусственного интеллекта (<strong>Physical AI / Embodied Intelligence</strong>). В условиях беспрецедентного санкционного давления, запрета на поставку европейского оборудования (Franka Emika, Universal Robots, Niryo) и критического удорожания китайских платформ с закрытым исходным кодом (Unitree Z1, Elephant Robotics, Dobot), российская высшая школа остро нуждается в суверенной материально-технической базе.
  </p>
  <p>
    Наша проектная группа разработала и довела до стадии действующего лабораторного прототипа (<strong>TRL-4</strong>) отечественную модульную платформу роботов-манипуляторов <strong>ROBOI</strong>. В ее основе лежит собственная схемотехника платы управления V3 на микроконтроллере ESP32-S3 (трассировка и поверхностный монтаж SMT выполняются на мощностях ООО «Резонит» в РФ), открытый протокол низкоуровневого управления, интеллектуальные шинные приводы с 12-битными магнитными энкодерами и полная программная интеграция с мировыми стандартами искусственного интеллекта: <strong>Hugging Face LeRobot</strong>, <strong>ROS 2 (Humble/Jazzy)</strong>, а также алгоритмами имитационного обучения <strong>ACT (Action Chunking with Transformers)</strong> и <strong>Diffusion Policy</strong>.
  </p>
  <p>
    В отличие от зарубежных аналогов, стоимость которых на российском рынке достигает <strong>700 000 – 1 500 000 рублей за единицу</strong>, аппаратно-программный комплекс ROBOI обеспечивает себестоимость базового модуля от <strong>19 800 рублей</strong> и расчетную стоимость готового двухрукого рабочего поста (Leader + Follower с системой машинного зрения и оснасткой) <strong>120 000 – 159 000 рублей</strong>. Это позволяет переоснастить учебную лабораторию института на 20 студентов (10 рабочих станций) за <strong>1,2 млн рублей ВСЕГО</strong>, что эквивалентно цене ОДНОГО импортного китайского кобота.
  </p>

  <h2>Ключевые преимущества сотрудничества для Института и Кафедры:</h2>
  <ul>
    <li><strong>100% Практический охват студентов:</strong> Переход от пассивной демонстрации одного робота на всю группу к персональной работе каждого студента за собственным рабочим постом.</li>
    <li><strong>Готовый учебно-методический комплекс (УМК):** Семестровый курс на 72 академических часа (2 зачетные единицы) по ФГОС ВО (15.03.06 «Мехатроника и робототехника», 09.03.01 «Информатика и ВТ»), включающий 10 готовых лабораторных работ, РПД, критерии оценивания и Docker-контейнеры.</li>
    <li><strong>Выполнение наукометрических показателей (KPI):</strong> Открытый доступ ко всем кинематическим и динамическим переменным обеспечивает базу для подготовки <strong>от 4 до 8 публикаций ВАК и Scopus/RSCI ежегодно</strong>.</li>
    <li><strong>Совместная интеллектуальная собственность (РИД):** Совместная регистрация патентов на полезные модели и программ для ЭВМ в Роспатенте с закреплением прав за Университетом.</li>
    <li><strong>Эксплуатационная надежность:</strong> Безопасное питание 12V (ТР ТС 004/2011), защита моторов от перегрева спаренным приводом (Dual-Servo) и гарантийная поставка ЗИП-комплектующих со склада в РФ в течение 24–48 часов.</li>
  </ul>
</div>

<!-- PAGE 2: ЭКОНОМИКА, НОРМАТИВ И ПРЕДЛОЖЕНИЕ -->
<div class="page">
  <h2>Финансово-экономическое и нормативное обоснование</h2>
  <p>
    С 2025 года Федеральный закон от 08.08.2024 <strong>№ 318-ФЗ</strong> и Постановление Правительства РФ от 23.12.2024 <strong>№ 1875</strong> унифицировали национальный режим для законов 44-ФЗ и 223-ФЗ. Согласно защитному правилу <strong>«Второй лишний»</strong>, при наличии в реестре Минпромторга РФ отечественной заявки (ОКПД 2: <strong>32.99.53.000</strong> «Приборы, аппаратура и модели учебные демонстрационные») заказчик законодательно обязан отклонить все иностранные предложения. Кроме того, по <strong>п. 4 и 5 ч. 1 ст. 93 44-ФЗ</strong> университет вправе приобретать комплексы ROBOI по процедуре малых закупок (до 600 000 ₽ за контракт) напрямую через электронный магазин ЕАТ «Березка» в срок до 5 рабочих дней.
  </p>

  <table class="doc-table">
    <thead>
      <tr>
        <th>Показатель сравнения</th>
        <th>Китайские коботы (Unitree / Dobot / Elephant)</th>
        <th>Отечественная платформа ROBOI (Bimanual Lab)</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td><strong>Бюджет оснащения 10 станций (20 студентов)</strong></td>
        <td class="num" style="color: #b91c1c; font-weight: bold;">12 000 000 – 14 000 000 ₽</td>
        <td class="num" style="color: #15803d; font-weight: bold;">1 200 000 ₽ (Экономия 90%)</td>
      </tr>
      <tr>
        <td><strong>Доступность исходного кода и драйверов</strong></td>
        <td>Закрытый код (DLL-библиотеки, черный ящик)</td>
        <td>100% Открытый код (ROS 2, LeRobot, PyTorch, C++)</td>
      </tr>
      <tr>
        <td><strong>Сроки ремонта и поставки комплектующих</strong></td>
        <td>2–3 месяца через трансграничный импорт</td>
        <td>24–48 часов с регионального склада в РФ (СДЭК)</td>
      </tr>
      <tr>
        <td><strong>Интеграция с моделями Physical AI (ACT, Diffusion)</strong></td>
        <td>Требует кустарной адаптации сторонним ПО</td>
        <td>Штатная поддержка «из коробки», парные манипуляторы</td>
      </tr>
    </tbody>
  </table>

  <h2>Источники целевого софинансирования:</h2>
  <p>
    Финансирование развертывания лаборатории может быть осуществлено без расходования собственных внебюджетных средств института через привлечение федеральных грантов:
  </p>
  <ol>
    <li><strong>Грант «Студенческий стартап» Фонда содействия инновациям (ФСИ):</strong> 1 000 000 рублей (100% безвозмездный грант, без софинансирования) по направлению Н4 («Новые приборы») или Н1 («Цифровые технологии»). Проектная группа готова подать заявку от студентов/аспирантов кафедры.</li>
    <li><strong>Программа «Старт-1» (ФСИ):</strong> до 5 000 000 рублей на выполнение совместных НИОКР и сертификацию.</li>
    <li><strong>Целевые программы ПИШ и «Приоритет 2030»:</strong> статьи расходов на модернизацию лабораторной базы.</li>
  </ol>

  <div class="callout-box">
    <div class="callout-title">Предложение о пилотном сотрудничестве (без финансовых обязательств):</div>
    Мы предлагаем руководству Института подписать рамочное двустороннее <strong>Соглашение о научно-методическом сотрудничестве (Letter of Intent)</strong>. В рамках соглашения мы готовы:
    <br>1. Провести очную 15-минутную демонстрацию действующего прототипа манипулятора в институте в удобное для Вас время.
    <br>2. <strong>Безвозмездно передать институту 2 пилотных стенда ROBOI сроком на 30–60 дней</strong> для апробации УМК преподавателями профильной кафедры.
  </div>

  <p>
    Будем признательны за возможность личной встречи или проведения рабочего совещания с участием заведующих профильными кафедрами для демонстрации платформы и обсуждения деталей партнерства.
  </p>

  <div class="sign-block">
    <div class="sign-person">
      <div><strong>С уважением,</strong></div>
      <div style="margin-top: 4px;">Руководитель проектной группы ROBOI</div>
      <div class="sign-line"></div>
      <div class="sign-caption">(подпись / Ф.И.О.)</div>
    </div>
    <div class="sign-person" style="text-align: right;">
      <div><strong>СОГЛАСОВАНО:</strong></div>
      <div style="margin-top: 4px;">Директор института / Декан факультета</div>
      <div class="sign-line"></div>
      <div class="sign-caption">(подпись / Ф.И.О. / М.П.)</div>
    </div>
  </div>
</div>

</body>
</html>
"""

with open(HTML_PATH, "w", encoding="utf-8") as f:
    f.write(html_content)
print(f"Saved Official Proposal HTML to: {HTML_PATH}")

# Compile HTML to PDF via Headless Edge
msedge_path = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
if not os.path.exists(msedge_path):
    msedge_path = r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"

if os.path.exists(msedge_path):
    cmd = [
        msedge_path,
        "--headless",
        "--disable-gpu",
        "--no-pdf-header-footer",
        f"--print-to-pdf={PDF_PATH}",
        f"file:///{HTML_PATH.replace(os.sep, '/')}"
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if os.path.exists(PDF_PATH):
        size_kb = os.path.getsize(PDF_PATH) / 1024
        print(f"Compiled Official Proposal PDF: {PDF_PATH} ({size_kb:.1f} KB)")
    else:
        print("Edge PDF conversion failed:", res.stderr)

