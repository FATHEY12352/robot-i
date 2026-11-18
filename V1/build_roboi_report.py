# -*- coding: utf-8 -*-
import sys
import os
import subprocess
import shutil

WORKSPACE_DIR = r"d:\ARM"
HTML_PATH = os.path.join(WORKSPACE_DIR, "ROBOI_Market_Analysis_Report.html")
PDF_OUTPUT_PATH = os.path.join(WORKSPACE_DIR, "ROBOI_Market_Analysis_and_Financial_Report.pdf")
PDF_MEMORANDUM_PATH = os.path.join(WORKSPACE_DIR, "ROBOI_Investment_Memorandum_2026.pdf")

html_content = """<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<title>ROBOI: Инвестиционный меморандум, анализ рынка и финансовый отчет</title>
<style>
  @page {
    size: A4;
    margin: 11mm 13mm 11mm 13mm;
  }

  * {
    box-sizing: border-box;
  }

  body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    color: #1e293b;
    line-height: 1.38;
    font-size: 8.4pt;
    background: #fff;
    margin: 0;
    padding: 0;
  }

  .cover-header {
    border-bottom: 3px solid #2563eb;
    padding-bottom: 6px;
    margin-bottom: 9px;
    display: flex;
    justify-content: space-between;
    align-items: flex-end;
  }

  .logo-title {
    font-size: 19pt;
    font-weight: 800;
    color: #0f172a;
    letter-spacing: -0.5px;
    margin: 0;
    line-height: 1.1;
  }

  .logo-sub {
    font-size: 9.8pt;
    color: #2563eb;
    font-weight: 600;
    margin-top: 2px;
  }

  .doc-meta {
    text-align: right;
    font-size: 8pt;
    color: #64748b;
    line-height: 1.28;
  }

  .status-badge {
    display: inline-block;
    background: #dbeafe;
    color: #1e40af;
    font-weight: 700;
    font-size: 7.2pt;
    padding: 2px 7px;
    border-radius: 4px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 3px;
  }

  h2 {
    font-size: 10.5pt;
    color: #0f172a;
    border-left: 4px solid #2563eb;
    padding-left: 8px;
    margin-top: 10px;
    margin-bottom: 6px;
    text-transform: uppercase;
    letter-spacing: 0.3px;
    page-break-after: avoid;
  }

  h3 {
    font-size: 8.6pt;
    color: #0f172a;
    margin-top: 8px;
    margin-bottom: 2px;
    font-weight: 700;
    page-break-after: avoid;
  }

  p {
    margin-top: 0;
    margin-bottom: 5px;
    text-align: justify;
  }

  /* Grid & KPI Cards */
  .kpi-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 7px;
    margin: 7px 0 9px 0;
    page-break-inside: avoid;
  }

  .kpi-card {
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 6px;
    padding: 6px 6px;
    text-align: center;
    border-top: 3px solid #2563eb;
  }

  .kpi-label {
    font-size: 6.5pt;
    color: #64748b;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.3px;
  }

  .kpi-value {
    font-size: 11.5pt;
    font-weight: 800;
    color: #0f172a;
    margin: 2px 0;
    white-space: nowrap;
  }

  .kpi-desc {
    font-size: 6.6pt;
    color: #475569;
    line-height: 1.18;
  }

  /* Tables */
  table {
    width: 100%;
    border-collapse: collapse;
    margin: 4px 0 7px 0;
    font-size: 7.4pt;
    page-break-inside: avoid;
  }

  th {
    background: #0f172a;
    color: #ffffff;
    font-weight: 600;
    text-align: left;
    padding: 3.5px 5px;
    border: 1px solid #0f172a;
  }

  td {
    padding: 2.5px 5px;
    border: 1px solid #e2e8f0;
    vertical-align: middle;
  }

  td.nowrap, th.nowrap {
    white-space: nowrap;
  }

  td.num, th.num {
    text-align: right;
    white-space: nowrap;
  }

  td.center, th.center {
    text-align: center;
    white-space: nowrap;
  }

  tr:nth-child(even) {
    background: #f8fafc;
  }

  .highlight-row {
    background: #eff6ff !important;
    font-weight: 700;
  }

  .total-row {
    background: #e2e8f0 !important;
    font-weight: 800;
    border-top: 2px solid #0f172a;
  }

  /* Callout Boxes */
  .callout {
    background: #eff6ff;
    border-left: 4px solid #2563eb;
    padding: 6px 9px;
    border-radius: 0 6px 6px 0;
    margin: 6px 0;
    font-size: 7.7pt;
    page-break-inside: avoid;
  }

  .callout-title {
    font-weight: 700;
    color: #1e40af;
    margin-bottom: 2px;
    font-size: 8.3pt;
  }

  .callout-success {
    background: #f0fdf4;
    border-left-color: #16a34a;
  }
  .callout-success .callout-title {
    color: #15803d;
  }

  .callout-warning {
    background: #fffbeb;
    border-left-color: #f59e0b;
  }
  .callout-warning .callout-title {
    color: #b45309;
  }

  /* Lists */
  ul {
    margin: 2px 0 4px 0;
    padding-left: 14px;
  }

  li {
    margin-bottom: 1.5px;
  }

  .source-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 4px;
    margin: 4px 0 6px 0;
    page-break-inside: avoid;
  }

  .link-item {
    padding: 3.5px 6px;
    background: #f8fafc;
    border-radius: 4px;
    border: 1px solid #e2e8f0;
    font-size: 7pt;
    line-height: 1.2;
  }

  .link-item strong {
    color: #1e40af;
  }

  .page-break {
    page-break-before: always;
  }

  .badge {
    display: inline-block;
    font-size: 6.4pt;
    font-weight: 700;
    padding: 1px 4px;
    border-radius: 3px;
    white-space: nowrap;
  }

  .badge-blue { background: #dbeafe; color: #1e40af; }
  .badge-green { background: #dcfce7; color: #166534; }
  .badge-amber { background: #fef3c7; color: #92400e; }

  .summary-card {
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 6px;
    padding: 5px 9px;
    margin-bottom: 8px;
    font-size: 7.9pt;
    line-height: 1.32;
  }
</style>
</head>
<body>

<!-- ================= PAGE 1 ================= -->
<div class="cover-header">
  <div>
    <div class="status-badge">Инвестиционный меморандум & Рыночный отчет</div>
    <div class="logo-title">ПРОЕКТ ROBOI (РОБОАЙ)</div>
    <div class="logo-sub">Расчет емкости целевого рынка (34 000 учреждений / 14,8 млрд руб.)</div>
  </div>
  <div class="doc-meta">
    <strong>НИТУ МИСИС / Акселератор</strong><br>
    Стадия: <strong>TRL-4 (Действующий прототип V2)</strong><br>
    Грант: <strong>ФСИ «Студенческий стартап» (1 млн ₽)</strong><br>
    Дата актуализации: Сентябрь 2026 г.
  </div>
</div>

<div class="summary-card">
  <strong>О продукте:</strong> <strong>ROBOI</strong> — это отечественная образовательная платформа робототехнических манипуляторов (Dual-Arm / 5–6 DOF) с замкнутой обратной связью (Closed-Loop) по положению и нагрузке. Основана на специализированной плате управления V2/V3 (модуль ESP32-S3 / RP2040, силовой DC-DC преобразователь TPS54560BDDA 5A, 16-канальный АЦП-мультиплексор CD74HC4067 для считывания потенциометров, USB-C), облегченной 3D-печатной кинематике и кроссплатформенном софте на Python с поддержкой компьютерного зрения (MediaPipe Pose), голосового интерфейса и генерации датасетов для обучения ИИ (Imitation Learning / LeRobot).
</div>

<!-- SECTION 1 -->
<h2>1. Структура и емкость целевого рынка в РФ (34 000 учреждений / 14,8 млрд руб.)</h2>
<p>
  На основе утвержденных нормативов Минпросвещения РФ (ФГОС «Труд (Технология)» 2024–2026 гг.), федерального проекта «Успех каждого ребенка» нацпроекта «Образование», реестров Минобрнауки РФ и данных НАУРР совокупная целевая аудитория платформы ROBOI составляет <strong>34 000 образовательных организаций</strong> с общей емкостью рынка <strong>14,8 млрд рублей</strong> (при стоимости комплектования класса от 12 000 ₽ за базовый манипулятор до 28 000 – 45 000 ₽ за двухманипуляторный комплекс Dual-Arm с компьютерным зрением).
</p>

<table>
  <thead>
    <tr>
      <th style="width: 30%;">Сегмент / Категория потребителей</th>
      <th style="width: 34%;">Специфика применения и профиль образовательного процесса</th>
      <th class="center" style="width: 8%;">Доля</th>
      <th class="num" style="width: 14%;">Аудитория (учр.)</th>
      <th class="num" style="width: 14%;">Емкость рынка (₽)</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><strong>1. Школьные технопарки и центры допобразования («Точки роста», Кванториумы, IT-кубы)</strong></td>
      <td>Проектная и соревновательная робототехника (РобоФест, WRO), прототипирование прикладных манипуляционных ячеек.<br><span class="badge badge-blue">Ключевое ядро</span></td>
      <td class="center" style="font-weight: 700;">35%</td>
      <td class="num" style="font-weight: 700;">11 900 учр.</td>
      <td class="num" style="font-weight: 700;">5,18 млрд ₽</td>
    </tr>
    <tr>
      <td><strong>2. Общеобразовательные школы и лицеи (модуль «Робототехника» ФГОС Труд)</strong></td>
      <td>Обязательный модуль для 5–9 классов: базовая сборка, кинематика звеньев, блочное и текстовое программирование.<br><span class="badge badge-green">Массовый спрос</span></td>
      <td class="center" style="font-weight: 700;">30%</td>
      <td class="num" style="font-weight: 700;">10 200 школ</td>
      <td class="num" style="font-weight: 700;">4,44 млрд ₽</td>
    </tr>
    <tr>
      <td><strong>3. Высшие учебные заведения и колледжи (ИТ, Мехатроника, Робототехника, ИИ)</strong></td>
      <td>Лабораторные практикумы: алгоритмы Computer Vision, телеуправление Master-Slave, Imitation Learning, ROS2/Python.<br><span class="badge badge-amber">Высокий чек</span></td>
      <td class="center" style="font-weight: 700;">20%</td>
      <td class="num" style="font-weight: 700;">6 800 лаб.</td>
      <td class="num" style="font-weight: 700;">2,96 млрд ₽</td>
    </tr>
    <tr>
      <td><strong>4. Коммерческие кружки робототехники, B2C и мейкеры (Частное STEM-образование)</strong></td>
      <td>Сетевые франшизные клубы, инженерные кружки, энтузиасты и студенты для индивидуальной исследовательской работы.<br><span class="badge badge-blue">Быстрый цикл сделки</span></td>
      <td class="center" style="font-weight: 700;">15%</td>
      <td class="num" style="font-weight: 700;">5 100 клубов</td>
      <td class="num" style="font-weight: 700;">2,22 млрд ₽</td>
    </tr>
    <tr class="total-row">
      <td colspan="2">ИТОГО ЦЕЛЕВОЙ РЫНОК В РОССИИ:</td>
      <td class="center">100%</td>
      <td class="num">34 000 учр.</td>
      <td class="num">14,80 млрд ₽</td>
    </tr>
  </tbody>
</table>

<div class="callout callout-success">
  <div class="callout-title">Ключевой рыночный вывод:</div>
  Емкость целевого рынка в <strong>14,8 млрд ₽ (34 000 учреждений)</strong> подкреплена законодательными нормативами РФ по обязательному оснащению школ модулями робототехники с 2024 года и острым дефицитом доступного оборудования. Импортные аналоги либо чрезмерно дороги (Dobot Magician — от 600 000 ₽, SO-ARM101 — 55 000–65 000 ₽), либо конструктивно закрыты, в то время как отечественный комплекс ROBOI обеспечивает полноценное обучение сквозным технологиям (мехатроника, схемотехника, ИИ) при розничной цене <strong>от 12 000 ₽</strong>.
</div>

<div class="page-break"></div>

<!-- ================= PAGE 2 ================= -->
<h2>2. Иерархия объемов рынка (PAM / TAM / SAM / SOM)</h2>

<div class="callout callout-warning">
  <div class="callout-title">Методологическое определение показателя SOM:</div>
  Показатель выручки за каждый год отражает <strong>ежегодный объем SOM</strong> для проекта ROBOI. К <strong>2030 году целевая выручка за ОДИН год составит 52,80 млн руб.</strong> (при ежегодном объеме выпуска 2 200 комплектов оборудования + сервисный доход от подписок на ПО, методические модули и библиотеку датасетов, ~2,32% от доступного рынка SAM). В <strong>2026 году</strong> коммерческие продажи минимальны <strong>(0,30 млн ₽ / 15 комплектов)</strong> — проект находится на стадии НИОКР, доводки прототипа V2/V3 до серийного образца TRL-6 и валидации на базе лабораторий НИТУ МИСИС в рамках гранта ФСИ «Студенческий стартап» (1 млн ₽). Масштабный вывод на рынок начинается с 2027 года.
</div>

<div class="kpi-grid">
  <div class="kpi-card">
    <div class="kpi-label">PAM (Мир / РФ)</div>
    <div class="kpi-value">210 млрд ₽</div>
    <div class="kpi-desc">Мировой рынок EdTech роботов ($2,8B). Рынок РФ расширенный: 18,5 млрд ₽.</div>
  </div>
  <div class="kpi-card">
    <div class="kpi-label">TAM (РФ Целевой)</div>
    <div class="kpi-value">14,8 млрд ₽</div>
    <div class="kpi-desc">34 000 целевых организаций РФ × средний чек комплектования 43 500 ₽.</div>
  </div>
  <div class="kpi-card">
    <div class="kpi-label">SAM (Доступный)</div>
    <div class="kpi-value">2,28 млрд ₽</div>
    <div class="kpi-desc">5 200 профильных учреждений с IT-инфраструктурой и активным бюджетом.</div>
  </div>
  <div class="kpi-card" style="border-top-color: #16a34a;">
    <div class="kpi-label">SOM (к 2030 г. / Годовой)</div>
    <div class="kpi-value">52,8 млн ₽</div>
    <div class="kpi-desc">Выручка за ОДИН год: 46,20M железо (2 200 шт.) + 6,60M сервис/ПО/датасеты.</div>
  </div>
</div>

<h3>1. PAM (Potential Available Market — Потенциальный рынок)</h3>
<ul>
  <li><strong>Мировой рынок: 210 млрд ₽ ($2,8 млрд в 2026 г., прогноз $6,5 млрд к 2030 г., CAGR 23%)</strong> — мировой сектор образовательных манипуляторов, наборов для изучения робототехники и тренировочных стендов физического ИИ.</li>
  <li><strong>Рынок РФ (расширенный): 18,5 млрд ₽</strong> — включает общее среднее и высшее образование, кванториумы, центры переподготовки кадров и корпоративные учебные центры промышленных предприятий.</li>
</ul>

<h3>2. TAM (Total Addressable Market — Общий объем целевого рынка в РФ)</h3>
<ul>
  <li><strong>Объем: 14,8 млрд ₽ (14 800 000 000 ₽)</strong></li>
  <li><strong>Формула расчета:</strong> <code>34 000 организаций × 43 500 ₽ (средневзвешенная стоимость поставки учебного набора с методиками)</code>.</li>
  <li><strong>Обоснование:</strong> Потребность образовательных учреждений РФ в практических манипуляторах:
    <strong>Школьные технопарки и «Точки роста»</strong> (11 900 учр. / 5,18 млрд ₽); <strong>Школы с углубленным изучением</strong> (10 200 школ / 4,44 млрд ₽); <strong>Вузы и колледжи</strong> (6 800 лаб. / 2,96 млрд ₽); <strong>Частные центры и B2C</strong> (5 100 клубов / 2,22 млрд ₽).
  </li>
</ul>

<h3>3. SAM (Serviceable Addressable Market — Доступный объем рынка)</h3>
<ul>
  <li><strong>Объем: 2,28 млрд ₽ (2 280 000 000 ₽)</strong> — приоритетная аудитория <strong>5 200 учреждений</strong> (~15,4% от общего TAM).</li>
  <li><strong>Критерии фильтрации:</strong>
    1) Наличие компьютерных классов с возможностью подключения манипуляторов по USB и установки Python/OpenCV;
    2) Регулярное участие в научно-технических соревнованиях и олимпиадах (РобоФест, НТО, Профессионалы);
    3) Наличие преподавателей информатики/технологии, готовых внедрять модули машинного обучения и компьютерного зрения.
  </li>
</ul>

<h3>4. SOM (Serviceable Obtainable Market — Ежегодный объем продаж и цель к 2030 году)</h3>
<ul>
  <li><strong>Целевой ежегодный SOM к 2030 году: 52,80 млн ₽ за ОДИН год</strong> (46,20 млн ₽ оборудование [2 200 комплектов] + 6,60 млн ₽ регулярный сервис ARR, ~2,32% от доступного SAM).</li>
  <li><strong>Динамика ежегодного SOM по этапам развития:</strong>
    <ul>
      <li><strong>2026 г. (НИОКР / Грант ФСИ 1 млн ₽): 0,30 млн ₽</strong> (15 установочных комплектов для пилотирования в МИСИС; фокус на доводке платы V3 и софта).</li>
      <li><strong>2027 г. (Выход на рынок): 5,25 млн ₽</strong> (250 комплектов: 150 B2C + 100 B2B/B2G; сервис: 0,15 млн ₽).</li>
      <li><strong>2028 г. (Масштабирование): 16,20 млн ₽</strong> (750 комплектов: 15,30 млн ₽ железо + 0,90 млн ₽ сервис с базы предыдущего года).</li>
      <li><strong>2029 г. (Серийное производство): 32,40 млн ₽</strong> (1 400 комплектов: 29,40 млн ₽ железо + 3,00 млн ₽ сервис).</li>
      <li><strong>2030 г. (Федеральный охват): 52,80 млн ₽ за ОДИН год</strong> (2 200 комплектов: 46,20 млн ₽ железо + 6,60 млн ₽ сервис с базы 2 200+ устройств).</li>
    </ul>
  </li>
  <li><strong>Совокупная выручка за 5 лет (2026–2030 гг.): 106,95 млн ₽</strong> (4 615 манипуляторов суммарно + 10,65 млн ₽ регулярный сервис).</li>
  <li><strong>Модель регулярной выручки (ARR / LTV):</strong> Подписка на лицензию Python SDK Pro, библиотека готовых датасетов траекторий для роботов (3 000 ₽/год на прибор) формируют высокомаржинальный денежный поток (>90% маржинальность).</li>
</ul>

<div class="page-break"></div>

<!-- ================= PAGE 3 ================= -->
<h2>3. Пятилетний план продаж и динамика SOM (2026–2030 гг.)</h2>
<p>
  План продаж ориентирован на завершение НИОКР в 2026 году с изготовлением пилотной партии, запуск прямых и партнерских поставок в 2027 году и достижение целевого объема выручки <strong>52,80 млн руб.</strong> за 2030 год:
</p>

<table>
  <thead>
    <tr>
      <th style="width: 28%;">Финансовый показатель</th>
      <th class="center" style="width: 12%;">2026 (НИОКР)</th>
      <th class="center" style="width: 12%;">2027 (Выход)</th>
      <th class="center" style="width: 12%;">2028 (Масштаб)</th>
      <th class="center" style="width: 12%;">2029 (Серия)</th>
      <th class="center" style="width: 12%;">2030 (Цель SOM)</th>
      <th class="num" style="width: 12%;">ИТОГО (5 лет)</th>
    </tr>
  </thead>
  <tbody>
    <tr class="highlight-row">
      <td><strong>Объем продаж оборудования</strong></td>
      <td class="center"><strong>15 шт.</strong></td>
      <td class="center"><strong>250 шт.</strong></td>
      <td class="center"><strong>750 шт.</strong></td>
      <td class="center"><strong>1 400 шт.</strong></td>
      <td class="center"><strong>2 200 шт.</strong></td>
      <td class="num"><strong>4 615 шт.</strong></td>
    </tr>
    <tr>
      <td>— Доля B2C (базовый кит, 12 000 ₽)</td>
      <td class="center">10 шт.</td>
      <td class="center">150 шт.</td>
      <td class="center">400 шт.</td>
      <td class="center">700 шт.</td>
      <td class="center">1 100 шт.</td>
      <td class="num">2 360 шт.</td>
    </tr>
    <tr>
      <td>— Доля B2B / B2G (Dual-Arm / Edu Pro)</td>
      <td class="center">5 шт.</td>
      <td class="center">100 шт.</td>
      <td class="center">350 шт.</td>
      <td class="center">700 шт.</td>
      <td class="center">1 100 шт.</td>
      <td class="num">2 255 шт.</td>
    </tr>
    <tr>
      <td>Выручка от оборудования, млн ₽</td>
      <td class="center">0,30 млн ₽</td>
      <td class="center">5,10 млн ₽</td>
      <td class="center">15,30 млн ₽</td>
      <td class="center">29,40 млн ₽</td>
      <td class="center">46,20 млн ₽</td>
      <td class="num">96,30 млн ₽</td>
    </tr>
    <tr>
      <td>Регулярный сервис, ПО и датасеты (3 000 ₽/год)</td>
      <td class="center">0,00 млн ₽</td>
      <td class="center">0,15 млн ₽</td>
      <td class="center">0,90 млн ₽</td>
      <td class="center">3,00 млн ₽</td>
      <td class="center">6,60 млн ₽</td>
      <td class="num">10,65 млн ₽</td>
    </tr>
    <tr class="highlight-row" style="background: #e0f2fe !important;">
      <td><strong>СОВОКУПНАЯ ВЫРУЧКА / Годовой SOM</strong></td>
      <td class="center"><strong>0,30 млн ₽</strong></td>
      <td class="center"><strong>5,25 млн ₽</strong></td>
      <td class="center"><strong>16,20 млн ₽</strong></td>
      <td class="center"><strong>32,40 млн ₽</strong></td>
      <td class="center"><strong>52,80 млн ₽</strong></td>
      <td class="num"><strong>106,95 млн ₽</strong></td>
    </tr>
    <tr>
      <td>Себестоимость COGS (приборы + материалы)</td>
      <td class="center">0,10 млн ₽</td>
      <td class="center">1,85 млн ₽</td>
      <td class="center">5,40 млн ₽</td>
      <td class="center">10,20 млн ₽</td>
      <td class="center">15,84 млн ₽</td>
      <td class="num">33,39 млн ₽</td>
    </tr>
    <tr class="highlight-row">
      <td><strong>Валовая прибыль (Gross Profit)</strong></td>
      <td class="center"><strong>0,20 млн ₽</strong></td>
      <td class="center"><strong>3,40 млн ₽</strong></td>
      <td class="center"><strong>10,80 млн ₽</strong></td>
      <td class="center"><strong>22,20 млн ₽</strong></td>
      <td class="center"><strong>36,96 млн ₽</strong></td>
      <td class="num"><strong>73,56 млн ₽</strong></td>
    </tr>
    <tr>
      <td>Валовая маржинальность (%)</td>
      <td class="center">66,7%</td>
      <td class="center">64,8%</td>
      <td class="center">66,7%</td>
      <td class="center">68,5%</td>
      <td class="center">70,0%</td>
      <td class="num">68,8%</td>
    </tr>
    <tr>
      <td>Операционные расходы (OPEX)</td>
      <td class="center">1,00 млн ₽ (грант)</td>
      <td class="center">1,60 млн ₽</td>
      <td class="center">3,80 млн ₽</td>
      <td class="center">6,20 млн ₽</td>
      <td class="center">8,50 млн ₽</td>
      <td class="num">21,10 млн ₽</td>
    </tr>
    <tr class="highlight-row">
      <td><strong>EBITDA (Операционная прибыль)</strong></td>
      <td class="center"><strong>0,00 млн ₽</strong></td>
      <td class="center"><strong>1,80 млн ₽</strong></td>
      <td class="center"><strong>7,00 млн ₽</strong></td>
      <td class="center"><strong>16,00 млн ₽</strong></td>
      <td class="center"><strong>28,46 млн ₽</strong></td>
      <td class="num"><strong>52,46 млн ₽</strong></td>
    </tr>
    <tr>
      <td>Налог по УСН (6% от выручки)</td>
      <td class="center">0,02 млн ₽</td>
      <td class="center">0,32 млн ₽</td>
      <td class="center">0,97 млн ₽</td>
      <td class="center">1,94 млн ₽</td>
      <td class="center">3,17 млн ₽</td>
      <td class="num">6,42 млн ₽</td>
    </tr>
    <tr class="total-row">
      <td><strong>ЧИСТАЯ ПРИБЫЛЬ (после УСН 6%)</strong></td>
      <td class="center"><strong>0,00 ₽</strong></td>
      <td class="center"><strong>1,48 млн ₽</strong></td>
      <td class="center"><strong>6,03 млн ₽</strong></td>
      <td class="center"><strong>14,06 млн ₽</strong></td>
      <td class="center"><strong>25,29 млн ₽</strong></td>
      <td class="num" style="color: #1e40af;"><strong>46,86 млн ₽</strong></td>
    </tr>
  </tbody>
</table>

<div class="callout callout-success" style="margin-top: 4px;">
  <div class="callout-title">Структура монетизации и динамика SOM:</div>
  <ul>
    <li><strong>Выручка за один год к 2030 году:</strong> Составляет <strong>52,80 млн ₽</strong> (46,20 млн ₽ от поставок 2 200 комплектов + 6,60 млн ₽ регулярный сервис), EBITDA достигает <strong>28,46 млн ₽</strong>, а чистая прибыль — <strong>25,29 млн ₽/год</strong>.</li>
    <li><strong>Стадия 2026 г.:</strong> В 2026 году коммерческая выручка символическая (0,30 млн ₽). Расходы в 1,00 млн ₽ полностью покрываются грантом ФСИ «Студенческий стартап» на проведение НИОКР, заказ тестовых плат и сборку 15 пилотных систем.</li>
    <li><strong>B2C (Розничные комплекты):</strong> Розничная цена <strong>12 000 ₽</strong> за манипулятор (себестоимость 5 450 ₽, маржа 54,6%).</li>
    <li><strong>B2B / B2G (Комплекты для вузов и школ):</strong> Цена <strong>28 000 – 45 000 ₽</strong> за двухручный комплекс Dual-Arm со стойкой камеры и методическим курсом (маржа 68–74%).</li>
    <li><strong>Регулярный доход ARR:</strong> Подписка на облачный репозиторий траекторий ИИ, библиотеку LeRobot и обновления SDK = <strong>3 000 ₽/год</strong> на прибор.</li>
    <li><strong>Точка безубыточности:</strong> При плановом OPEX 130 000 ₽/мес. полная окупаемость достигается при реализации всего <strong>15–18 базовых манипуляторов в месяц</strong> (~180–200 шт. в год).</li>
  </ul>
</div>

<div class="page-break"></div>

<!-- ================= PAGE 4 ================= -->
<h2>4. Экономика продукта (Unit Economics & спецификация BOM)</h2>
<p>
  Прямая производственная себестоимость базового манипулятора ROBOI на этапе мелкосерийного производства составляет <strong>5 450 ₽</strong> с оптимизацией до <strong>4 200 ₽</strong> в крупной серии. Это гарантирует здоровую маржинальность 54,6% в рознице и свыше 70% в сегменте B2B:
</p>

<div class="kpi-grid" style="margin-bottom: 6px;">
  <div class="kpi-card">
    <div class="kpi-label">Себестоимость (COGS)</div>
    <div class="kpi-value">5 450 ₽</div>
    <div class="kpi-desc">Базовая (снижение до 4 200 ₽ в серии от 500 шт.)</div>
  </div>
  <div class="kpi-card">
    <div class="kpi-label">Розница B2C (School Kit)</div>
    <div class="kpi-value">12 000 ₽</div>
    <div class="kpi-desc">1 манипулятор, плата V3, БП, софт (маржа 54,6%)</div>
  </div>
  <div class="kpi-card">
    <div class="kpi-label">Вузы / B2B (Dual-Arm)</div>
    <div class="kpi-value">35 000 ₽</div>
    <div class="kpi-desc">2 манипулятора, камера, методики (маржа 72,5%)</div>
  </div>
  <div class="kpi-card" style="border-top-color: #16a34a;">
    <div class="kpi-label">Сервис и ПО (ARR)</div>
    <div class="kpi-value">3 000 ₽ / год</div>
    <div class="kpi-desc">Обновления ПО, датасеты ИИ, уроки (маржа > 90%)</div>
  </div>
</div>

<table style="margin-bottom: 5px;">
  <thead>
    <tr>
      <th style="width: 50%;">Наименование компонента / технологической операции</th>
      <th style="width: 26%;">Поставщик / Спецификация</th>
      <th class="center" style="width: 10%;">Кол-во</th>
      <th class="num" style="width: 14%;">Сумма (₽)</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><strong>Модуль микроконтроллера ESP32-S3-WROOM-1</strong> (2 ядра 240 МГц, Wi-Fi/BLE, 8MB Flash)</td>
      <td>Официальный дистрибьютор</td>
      <td class="center">1 шт.</td>
      <td class="num">650 ₽</td>
    </tr>
    <tr>
      <td><strong>Импульсный понижающий регулятор TPS54560BDDA 5A</strong> (высокий КПД, вход до 60V)</td>
      <td>Texas Instruments / Компэл</td>
      <td class="center">1 шт.</td>
      <td class="num">450 ₽</td>
    </tr>
    <tr>
      <td><strong>16-канальный АЦП-мультиплексор CD74HC4067SM</strong> (опрос потенциометров обратной связи)</td>
      <td>TI / Чип и Дип</td>
      <td class="center">1 шт.</td>
      <td class="num">180 ₽</td>
    </tr>
    <tr>
      <td><strong>Стабилизатор ME6211C33 (3.3V) + ESD защита USBLC6 + силовые фильтры LC/SMD</strong></td>
      <td>COTS SMD (Резонит)</td>
      <td class="center">1 компл.</td>
      <td class="num">370 ₽</td>
    </tr>
    <tr>
      <td><strong>Разъемы и коммутация</strong> (8× servo connectors 4-pin с feedback, клеммник питания, USB-C)</td>
      <td>Промэлектроника</td>
      <td class="center">1 компл.</td>
      <td class="num">220 ₽</td>
    </tr>
    <tr>
      <td><strong>Печатная плата (Custom 2-Layer PCB) + монтаж SMD компонентов</strong></td>
      <td>Контрактное пр-во (Резонит)</td>
      <td class="center">1 шт.</td>
      <td class="num">580 ₽</td>
    </tr>
    <tr>
      <td><strong>Силовые металлические сервоприводы MG996R</strong> (основание, плечо, локоть, 11 кг·см)</td>
      <td>Заводская поставка</td>
      <td class="center">3 шт.</td>
      <td class="num">1 500 ₽</td>
    </tr>
    <tr>
      <td><strong>Компактные микросервоприводы MG90S</strong> (поворот кисти, наклон, схват, металл-редуктор)</td>
      <td>Заводская поставка</td>
      <td class="center">3 шт.</td>
      <td class="num">600 ₽</td>
    </tr>
    <tr>
      <td><strong>3D-печатный каркас корпуса</strong> (PETG/PLA пластик, 350 г) + резьбовые втулки М3 и крепеж</td>
      <td>Собственная 3D-ферма / Метизы</td>
      <td class="center">1 компл.</td>
      <td class="num">600 ₽</td>
    </tr>
    <tr>
      <td><strong>Блок питания 12V 5A (60W) + фирменная упаковка, ложемент и калибровка ОТК</strong></td>
      <td>Сертифицированный поставщик + типография</td>
      <td class="center">1 компл.</td>
      <td class="num">800 ₽</td>
    </tr>
    <tr class="total-row">
      <td colspan="3">ИТОГО БАЗОВАЯ СЕБЕСТОИМОСТЬ (COGS манипулятора с платой V3):</td>
      <td class="num" style="color: #1e40af;">5 450 ₽</td>
    </tr>
  </tbody>
</table>

<!-- SECTION 5 & 6 -->
<h2 style="margin-top: 6px; margin-bottom: 4px;">5. Верифицированные источники данных</h2>
<div class="source-grid">
  <div class="link-item">
    1. <strong>Минпросвещения РФ:</strong> Приказ № 171 об обязательном модуле «Робототехника» в 40 000+ школ РФ.
  </div>
  <div class="link-item">
    2. <strong>Нацпроект «Образование»:</strong> 17 000+ «Точек роста», 350+ «Кванториумов» и 260 «IT-кубов».
  </div>
  <div class="link-item">
    3. <strong>НАУРР / IFR:</strong> Рост рынка робототехники РФ до 7,3 млрд ₽ к 2033 г. (CAGR 14,1%).
  </div>
  <div class="link-item">
    4. <strong>НИТУ МИСИС:</strong> Лаборатория робототехники и ИИ — апробация методик и сбор датасетов.
  </div>
</div>

<div class="callout callout-warning" style="margin-top: 4px; padding: 5px 8px;">
  <div class="callout-title" style="font-size: 7.9pt; margin-bottom: 2px;">6. Стадия зрелости, оценка и запрашиваемое финансирование (Funding Ask):</div>
  <div style="font-size: 7.2pt; line-height: 1.25;">
    • <strong>Стадия TRL-4 (Действующий лабораторный прототип V2/V3):</strong> Разработан и напечатан 3D-каркас манипулятора, спроектирована плата V3 в KiCad (ESP32-S3 + TPS54560 5A + CD74HC4067 + разъемы с feedback), написан Python SDK с MediaPipe Pose, голосовым управлением и модулем записи датасетов.<br>
    • <strong>Оценка компании (Pre-money Valuation): 18 000 000 ₽</strong> (рассчитана методом DCF при ставке 28% на базе 5-летнего финплана).<br>
    • <strong>Запрашиваемое финансирование: 1 000 000 ₽</strong> (Грант <strong>ФСИ «Студенческий стартап»</strong> без размытия долей), либо Pre-seed раунд 1,5–2,0 млн ₽ за 8–10% доли.<br>
    • <strong>Смета гранта (1,0 млн ₽):</strong> 1) Опытная серия плат V3 и монтаж (Резонит, 20 шт.) — <strong>320 тыс. ₽</strong>; 2) Приводы и компоненты на 15 наборов — <strong>280 тыс. ₽</strong>; 3) Доработка ПО, библиотек и облачного банка датасетов — <strong>200 тыс. ₽</strong>; 4) Патентование РИД (ПО + полезная модель) — <strong>100 тыс. ₽</strong>; 5) Пилоты в НИТУ МИСИС и кружках — <strong>100 тыс. ₽</strong>.
  </div>
</div>

</body>
</html>
"""

with open(HTML_PATH, "w", encoding="utf-8") as f:
    f.write(html_content)

print(f"Saved HTML to: {HTML_PATH}")

msedge_path = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
if not os.path.exists(msedge_path):
    msedge_path = r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"

cmd = [
    msedge_path,
    "--headless",
    "--disable-gpu",
    "--no-pdf-header-footer",
    f"--print-to-pdf={PDF_OUTPUT_PATH}",
    f"file:///{HTML_PATH.replace(os.sep, '/')}"
]

res = subprocess.run(cmd, capture_output=True, text=True)
print("Return code:", res.returncode)

if os.path.exists(PDF_OUTPUT_PATH):
    size = os.path.getsize(PDF_OUTPUT_PATH)
    print(f"Generated PDF: {PDF_OUTPUT_PATH} ({size / 1024:.1f} KB)")
    shutil.copy2(PDF_OUTPUT_PATH, PDF_MEMORANDUM_PATH)

    import pypdfium2 as pdfium
    pdf = pdfium.PdfDocument(PDF_OUTPUT_PATH)
    print(f"Total pages in generated PDF: {len(pdf)}")
    preview_dir = os.path.join(WORKSPACE_DIR, "preview_report")
    os.makedirs(preview_dir, exist_ok=True)
    for i, page in enumerate(pdf):
        img = page.render(scale=2).to_pil()
        img_path = os.path.join(preview_dir, f"page_{i+1}.png")
        img.save(img_path)
    print("Previews regenerated.")
