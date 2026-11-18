# -*- coding: utf-8 -*-
"""
ROBOI Director Pitch Deck Generator
Generates:
1. ROBOI_Pitch_Deck_Director.html (Interactive 16:9 Web Presentation)
2. ROBOI_Pitch_Deck_Director.pdf (16:9 Landscape PDF via Headless Edge)
3. ROBOI_Pitch_Deck_Director.pptx (16:9 Microsoft PowerPoint Presentation)
"""

import os
import sys
import subprocess
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE

WORKSPACE = r"d:\projekt\ARM"
HTML_PATH = os.path.join(WORKSPACE, "ROBOI_Pitch_Deck_Director.html")
PDF_PATH = os.path.join(WORKSPACE, "ROBOI_Pitch_Deck_Director.pdf")
PPTX_PATH = os.path.join(WORKSPACE, "ROBOI_Pitch_Deck_Director.pptx")

# -------------------------------------------------------------
# 1. HTML SLIDE DECK (16:9 Modern Academic Presentation)
# -------------------------------------------------------------
html_content = """<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<title>ROBOI: Презентация для Директора института</title>
<style>
  @page {
    size: 297mm 167mm; /* 16:9 landscape presentation */
    margin: 0;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    background: #0f172a;
    color: #f8fafc;
    overflow-x: hidden;
  }
  .slide {
    width: 297mm;
    height: 167mm;
    page-break-after: always;
    padding: 14mm 18mm;
    position: relative;
    background: linear-gradient(135deg, #0b1329 0%, #111d38 100%);
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    overflow: hidden;
  }
  .slide::before {
    content: "";
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 4px;
    background: linear-gradient(90deg, #3b82f6, #06b6d4, #10b981);
  }
  .slide-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    border-bottom: 1px solid rgba(255, 255, 255, 0.1);
    padding-bottom: 8px;
    margin-bottom: 12px;
  }
  .slide-category {
    font-size: 9pt;
    text-transform: uppercase;
    letter-spacing: 1.5px;
    color: #38bdf8;
    font-weight: 700;
  }
  .slide-title {
    font-size: 20pt;
    font-weight: 800;
    color: #ffffff;
    line-height: 1.2;
    margin-top: 2px;
  }
  .slide-subtitle {
    font-size: 10.5pt;
    color: #94a3b8;
    margin-top: 3px;
  }
  .slide-number {
    font-size: 11pt;
    font-weight: 700;
    color: #64748b;
    background: rgba(255,255,255,0.05);
    padding: 4px 10px;
    border-radius: 6px;
  }
  .slide-body {
    flex: 1;
    display: flex;
    flex-direction: column;
    justify-content: center;
  }
  .grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
  .grid-3 { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 14px; }
  .grid-4 { display: grid; grid-template-columns: 1fr 1fr 1fr 1fr; gap: 12px; }

  .card {
    background: rgba(30, 41, 59, 0.7);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 10px;
    padding: 12px 14px;
  }
  .card-highlight {
    background: rgba(37, 99, 235, 0.15);
    border-color: #3b82f6;
  }
  .card-success {
    background: rgba(16, 185, 129, 0.12);
    border-color: #10b981;
  }
  .card-warning {
    background: rgba(245, 158, 11, 0.12);
    border-color: #f59e0b;
  }
  .card-title {
    font-size: 11.5pt;
    font-weight: 700;
    margin-bottom: 6px;
    color: #f1f5f9;
    display: flex;
    align-items: center;
    gap: 6px;
  }
  .card-title .badge {
    font-size: 7.5pt;
    padding: 2px 6px;
    border-radius: 4px;
    background: #0284c7;
    color: white;
  }
  .card p, .card li {
    font-size: 9pt;
    line-height: 1.4;
    color: #cbd5e1;
  }
  .card ul { margin-left: 16px; margin-top: 4px; }
  .card li { margin-bottom: 3px; }

  .metric-box {
    text-align: center;
    padding: 12px;
    border-radius: 8px;
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.08);
  }
  .metric-value {
    font-size: 24pt;
    font-weight: 900;
    color: #38bdf8;
    line-height: 1;
  }
  .metric-label {
    font-size: 8pt;
    color: #94a3b8;
    margin-top: 4px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }

  table.pres-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 8.5pt;
    margin-top: 6px;
  }
  table.pres-table th {
    background: #1e293b;
    color: #38bdf8;
    text-align: left;
    padding: 6px 10px;
    border-bottom: 2px solid #334155;
    font-weight: 700;
  }
  table.pres-table td {
    padding: 6px 10px;
    border-bottom: 1px solid #334155;
    color: #e2e8f0;
  }
  table.pres-table tr:nth-child(even) { background: rgba(255,255,255,0.02); }

  .slide-footer {
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-top: 1px solid rgba(255,255,255,0.08);
    padding-top: 6px;
    font-size: 8pt;
    color: #64748b;
  }
  .tag {
    display: inline-block;
    padding: 2px 7px;
    border-radius: 4px;
    font-size: 7.5pt;
    font-weight: 700;
    margin-right: 4px;
  }
  .tag-blue { background: rgba(59, 130, 246, 0.2); color: #60a5fa; border: 1px solid #3b82f6; }
  .tag-green { background: rgba(16, 185, 129, 0.2); color: #34d399; border: 1px solid #10b981; }
  .tag-purple { background: rgba(168, 85, 247, 0.2); color: #c084fc; border: 1px solid #a855f7; }

  /* Title Slide Styling */
  .title-slide {
    background: radial-gradient(circle at 80% 20%, rgba(37, 99, 235, 0.25) 0%, transparent 60%),
                linear-gradient(135deg, #070d1e 0%, #0f172a 100%);
    justify-content: center;
    padding: 24mm 24mm;
  }
  .title-hero {
    font-size: 32pt;
    font-weight: 900;
    color: #ffffff;
    letter-spacing: -0.5px;
    line-height: 1.15;
    margin-bottom: 10px;
  }
  .title-hero span {
    background: linear-gradient(90deg, #38bdf8, #818cf8);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
  }
  .title-desc {
    font-size: 13pt;
    color: #94a3b8;
    line-height: 1.4;
    max-width: 85%;
    margin-bottom: 24px;
  }
  .title-meta {
    display: flex;
    gap: 20px;
    margin-top: 15px;
    font-size: 9pt;
    color: #cbd5e1;
  }
</style>
</head>
<body>

<!-- SLIDE 1: ТИТУЛЬНЫЙ СЛАЙД -->
<div class="slide title-slide">
  <div style="margin-bottom: 12px;">
    <span class="tag tag-blue">ИНВЕСТИЦИОННОЕ И НАУЧНО-ОБРАЗОВАТЕЛЬНОЕ ПРЕДЛОЖЕНИЕ</span>
    <span class="tag tag-green">TRL-4 ДЕЙСТВУЮЩИЙ ПРОТОТИП</span>
    <span class="tag tag-purple">ИМПОРТОЗАМЕЩЕНИЕ</span>
  </div>
  <div class="title-hero">
    Проект <span>ROBOI</span>: Суверенная платформа робототехники и Physical AI
  </div>
  <div class="title-desc">
    Оснащение образовательно-исследовательских лабораторий российских вузов отечественными открытыми манипуляторами нового поколения (LeRobot / ROS 2 / ACT) по цене в 5–10 раз ниже зарубежных аналогов.
  </div>
  <div class="grid-3" style="max-width: 90%; margin-top: 10px;">
    <div class="card card-highlight">
      <div style="font-size: 8pt; color: #93c5fd; text-transform: uppercase;">Инициатива кафедры и стартапа</div>
      <div style="font-weight: 700; font-size: 10pt; margin-top: 2px;">Для Руководства Института и Ученого совета</div>
    </div>
    <div class="card">
      <div style="font-size: 8pt; color: #94a3b8; text-transform: uppercase;">Базовый УМК по ФГОС ВО</div>
      <div style="font-weight: 700; font-size: 10pt; margin-top: 2px;">72 академических часа (10 лабораторных)</div>
    </div>
    <div class="card card-success">
      <div style="font-size: 8pt; color: #86efac; text-transform: uppercase;">Бюджет оснащения 10 постов</div>
      <div style="font-weight: 700; font-size: 10pt; margin-top: 2px;">1,2 млн ₽ вместо 12–14 млн ₽ коботов</div>
    </div>
  </div>
  <div class="slide-footer" style="position: absolute; bottom: 10mm; left: 18mm; right: 18mm;">
    <div>Россия • Москва / Санкт-Петербург • 2026 год</div>
    <div>Конфиденциально • Для служебного пользования</div>
  </div>
</div>

<!-- SLIDE 2: ПРОБЛЕМА И ВЫЗОВ -->
<div class="slide">
  <div class="slide-header">
    <div>
      <div class="slide-category">Вызовы и рыночный контекст</div>
      <div class="slide-title">Кризис материально-технической базы в робототехнике РФ</div>
      <div class="slide-subtitle">Почему классический подход к закупке импортных манипуляторов зашел в тупик</div>
    </div>
    <div class="slide-number">02 / 12</div>
  </div>
  <div class="slide-body">
    <div class="grid-3">
      <div class="card card-warning">
        <div class="card-title">1. Санкционная блокада</div>
        <p>Полный запрет на поставку европейских исследовательских коботов (<strong>Franka Emika, Universal Robots, Niryo</strong>). Прекращение обновлений ПО, отключение облачных сервисов и невозможность поставки запчастей.</p>
        <div style="margin-top: 10px; font-size: 8pt; color: #f59e0b; font-weight: 700;">Риск простоя лабораторий: 100%</div>
      </div>
      <div class="card card-warning">
        <div class="card-title">2. Китайский «Черный ящик»</div>
        <p>Импортные китайские платформы (<strong>Elephant Robotics, Unitree Z1, Dobot</strong>) стоят от <strong>700 тыс. до 1,5 млн ₽</strong>. Закрытый исходный код драйверов не позволяет изучать фундаментальное управление и обучать современные нейросети.</p>
        <div style="margin-top: 10px; font-size: 8pt; color: #f59e0b; font-weight: 700;">Цена завышена в 5–8 раз</div>
      </div>
      <div class="card card-warning">
        <div class="card-title">3. Оторванность от практики</div>
        <p>Из-за дороговизны оборудования 90% студентов изучают робототехнику только в симуляторах (Gazebo/MATLAB). Студенты не имеют навыков работы с реальными датчиками, люфтами, задержками и шумами в Physical AI.</p>
        <div style="margin-top: 10px; font-size: 8pt; color: #f59e0b; font-weight: 700;">Дефицит практических навыков</div>
      </div>
    </div>
    <div class="card card-highlight" style="margin-top: 12px; padding: 10px 14px;">
      <div style="font-weight: 700; color: #93c5fd; font-size: 9.5pt;">Парадокс современного образования:</div>
      <p style="font-size: 8.5pt;">Вуз тратит годовой бюджет на покупку 1–2 китайских роботов, которые стоят под стеклом в демонстрационном режиме, пока студенты пишут теоретические отчеты. Необходим переход к модели: <strong>персональный робототехнический стенд каждому студенту</strong>.</p>
    </div>
  </div>
  <div class="slide-footer">
    <div>ROBOI: Анализ академической потребности</div>
    <div>Конфиденциально</div>
  </div>
</div>

<!-- SLIDE 3: НАШЕ РЕШЕНИЕ -->
<div class="slide">
  <div class="slide-header">
    <div>
      <div class="slide-category">Концепция продукта</div>
      <div class="slide-title">Экосистема ROBOI: Суверенный Physical AI «из коробки»</div>
      <div class="slide-subtitle">Аппаратно-программный комплекс для высшего инженерного образования</div>
    </div>
    <div class="slide-number">03 / 12</div>
  </div>
  <div class="slide-body">
    <div class="grid-2">
      <div>
        <div class="card card-highlight" style="margin-bottom: 10px;">
          <div class="card-title">Аппаратная часть (Hardware Platform)</div>
          <ul>
            <li><strong>Модульная кинематика 4–6 DoF:</strong> шасси из композитного углеволокна (PETG-CF / PA-CF), устойчивое к нагрузкам.</li>
            <li><strong>Отечественная плата управления V3:</strong> микроконтроллер ESP32-S3, силовой DC-DC преобразователь 12V 5A, аппаратная защита шины, производство и монтаж в РФ (Резонит).</li>
            <li><strong>Шинные интеллектуальные сервоприводы:</strong> 12-битные магнитные энкодеры, телеметрия тока, напряжения и температуры в реальном времени.</li>
            <li><strong>Система машинного зрения:</strong> стерео-комплект камер 1080p 60fps (Eye-to-Hand + Eye-in-Hand) по цене до 5 000 ₽ взамен заблокированных Intel RealSense.</li>
          </ul>
        </div>
      </div>
      <div>
        <div class="card card-success" style="margin-bottom: 10px;">
          <div class="card-title">Программный стек (Physical AI & ROS 2)</div>
          <ul>
            <li><strong>Hugging Face LeRobot & ACT:</strong> нативная поддержка передовых алгоритмов имитационного обучения (Action Chunking with Transformers, Diffusion Policy).</li>
            <li><strong>ROS 2 Humble / Jazzy:</strong> готовые пакеты URDF, безаварийное планирование траекторий в MoveIt 2.</li>
            <li><strong>Двусторонняя телеоперация (Leader-Follower):** мгновенный сбор демонстрационных датасетов студентами без написания сложного кода.</li>
            <li><strong>100% Открытый исходный код:</strong> полный доступ ко всем регистрам, ПИД-регуляторам и кинематическим матрицам.</li>
          </ul>
        </div>
      </div>
    </div>
    <div class="grid-4" style="margin-top: 6px;">
      <div class="metric-box"><div class="metric-value">12V</div><div class="metric-label">Безопасное питание ТР ТС</div></div>
      <div class="metric-box"><div class="metric-value">69 тыс. ₽</div><div class="metric-label">Базовая цена рабочего поста</div></div>
      <div class="metric-box"><div class="metric-value">24-48 ч</div><div class="metric-label">Срок поставки запчастей по РФ</div></div>
      <div class="metric-box"><div class="metric-value">100%</div><div class="metric-label">Открытый код и схемы</div></div>
    </div>
  </div>
  <div class="slide-footer">
    <div>ROBOI: Архитектура суверенной платформы</div>
    <div>TRL-4 Действующий лабораторный образец</div>
  </div>
</div>

<!-- SLIDE 4: ТЕХНИЧЕСКИЕ ИННОВАЦИИ -->
<div class="slide">
  <div class="slide-header">
    <div>
      <div class="slide-category">Инженерные преимущества</div>
      <div class="slide-title">Преодоление тепловых и механических лимитов</div>
      <div class="slide-subtitle">Почему платформа ROBOI надежнее любительских open-source проектов (SO-100)</div>
    </div>
    <div class="slide-number">04 / 12</div>
  </div>
  <div class="slide-body">
    <div class="grid-3">
      <div class="card">
        <div class="card-title"><span class="badge">Инновация 1</span> Спаренный сустав плеча</div>
        <p><strong>Проблема:</strong> В стандартном SO-100 сервопривод плеча STS3215 перегревается до 70°C за 10 мин из-за превышения длительного момента (10 кг·см).</p>
        <p style="margin-top: 6px;"><strong>Решение ROBOI:</strong> Синхронный тандемный привод <strong>Dual-Servo</strong> удваивает номинальный момент до <strong>20 кг·см</strong> (пик 60 кг·см), полностью устраняя тепловую деградацию при непрерывном удержании груза.</p>
      </div>
      <div class="card">
        <div class="card-title"><span class="badge">Инновация 2</span> Электронный антилюфт</div>
        <p><strong>Проблема:</strong> Механический зазор прямозубых редукторов (Backlash ~1°) дает погрешность позиционирования конца руки до ±7 мм на вылете 400 мм.</p>
        <p style="margin-top: 6px;"><strong>Решение ROBOI:</strong> Программный встречный преднатяг тандемных моторов (микросмещение ±0.15°) выбирает механический зазор, повышая повторяемость до <strong>±0.3 мм</strong>.</p>
      </div>
      <div class="card">
        <div class="card-title"><span class="badge">Инновация 3</span> Кинематика Пантографа</div>
        <p><strong>Проблема:</strong> Размещение тяжелых двигателей на плечевых звеньях увеличивает инерцию и требует массивных конструкций.</p>
        <p style="margin-top: 6px;"><strong>Решение ROBOI:</strong> Перенос моторов локтя и плеча в базовую плиту через параллелограммные углепластиковые тяги снижает динамическую инерцию на <strong>60%</strong> и позволяет балансировать руку пружинами.</p>
      </div>
    </div>
    <div class="card card-success" style="margin-top: 12px; padding: 10px 14px;">
      <div style="font-weight: 700; color: #86efac; font-size: 9.5pt;">Математическая независимость от геометрии:</div>
      <p style="font-size: 8.5pt;">Современные нейросетевые модели (ACT, Diffusion Policy) агностичны к типу манипулятора. Они обучаются отображению $O_t \to A_t$ в абстрактных пространствах состояний. ROBOI предоставляет точные URDF-модели и солверы обратной кинематики (Pink / Pinocchio), обеспечивая 100% совместимость со всеми мировыми бенчмарками.</p>
    </div>
  </div>
  <div class="slide-footer">
    <div>ROBOI: Инженерный аудит и математическая строгость</div>
    <div>Сравнение с мировыми SOTA решениями</div>
  </div>
</div>

<!-- SLIDE 5: 4 ЦЕНОВЫХ УРОВНЯ -->
<div class="slide">
  <div class="slide-header">
    <div>
      <div class="slide-category">Продуктовая линейка</div>
      <div class="slide-title">Четырехуровневая линейка оборудования ROBOI</div>
      <div class="slide-subtitle">От начальных практикумов до передовых исследовательских комплексов</div>
    </div>
    <div class="slide-number">05 / 12</div>
  </div>
  <div class="slide-body">
    <table class="pres-table">
      <thead>
        <tr>
          <th>Уровень платформы</th>
          <th>Аппаратная архитектура</th>
          <th>Полезная нагрузка / Повторяемость</th>
          <th>Себестоимость (BOM)</th>
          <th>Рекомендованная цена вузу</th>
          <th>Целевое назначение</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td><strong>Tier A: Mini-Edu</strong></td>
          <td>4-DoF, микроприводы металл, плата ESP32, шасси PETG</td>
          <td>100 г / ±5.0 мм</td>
          <td>5 450 – 8 200 ₽</td>
          <td><span style="color:#38bdf8; font-weight:700;">18 500 – 24 000 ₽</span></td>
          <td>1 курс бакалавриата, вводная кинематика, школьные кванториумы</td>
        </tr>
        <tr style="background: rgba(37,99,235,0.15);">
          <td><strong>Tier B: Physical AI Starter</strong></td>
          <td>6-DoF, сервоприводы Feetech STS3215, USB-C контроллер V3, Carbon-PETG</td>
          <td>350–500 г / ±1.5 мм</td>
          <td>19 800 – 34 800 ₽</td>
          <td><span style="color:#60a5fa; font-weight:700;">69 000 – 85 000 ₽</span></td>
          <td>Флагманский практикум по ИИ, LeRobot, телеоперация, сбор датасетов</td>
        </tr>
        <tr>
          <td><strong>Tier B: Bimanual Lab</strong></td>
          <td>Две руки (Leader + Follower) + двойные камеры + алюминиевая плита D16T</td>
          <td>500 г / ±1.5 мм</td>
          <td>51 400 – 78 000 ₽</td>
          <td><span style="color:#34d399; font-weight:700;">159 000 – 175 000 ₽</span></td>
          <td>Двуручные манипуляции, захват сложных предметов, обучение ACT</td>
        </tr>
        <tr>
          <td><strong>Tier C: Semi-Industrial</strong></td>
          <td>6-DoF, шаговые моторы NEMA 17/23 Closed-Loop + циклоидные редукторы 3D</td>
          <td>1.0–1.5 кг / ±0.2 мм</td>
          <td>42 000 – 65 000 ₽</td>
          <td><span style="color:#f59e0b; font-weight:700;">145 000 – 185 000 ₽</span></td>
          <td>Магистратура, планирование MoveIt 2, траекторный контроль без перегрева</td>
        </tr>
        <tr>
          <td><strong>Tier D: Pro Research</strong></td>
          <td>Алюминий ЧПУ, волновые/планетарные редукторы, CAN-шина, BLDC приводы</td>
          <td>2.0 кг / ±0.05 мм</td>
          <td>98 000 – 165 000 ₽</td>
          <td><span style="color:#c084fc; font-weight:700;">245 000 – 380 000 ₽</span></td>
          <td>Аспирантура, прецизионные НИОКР, замена коботов Universal Robots</td>
        </tr>
      </tbody>
    </table>
    <div style="margin-top: 10px; font-size: 8pt; color: #94a3b8; text-align: right;">
      *Все цены включают НДС, полную заводскую калибровку, фирменную тару и гарантию 12 месяцев.
    </div>
  </div>
  <div class="slide-footer">
    <div>ROBOI: Параметры серийных модификаций</div>
    <div>Масштабируемость от 10 до 200 единиц</div>
  </div>
</div>

<!-- SLIDE 6: УЧЕБНО-МЕТОДИЧЕСКИЙ КОМПЛЕКС (УМК) -->
<div class="slide">
  <div class="slide-header">
    <div>
      <div class="slide-category">Образовательная ценность</div>
      <div class="slide-title">Учебно-методический комплекс (УМК): 10 лабораторных работ</div>
      <div class="slide-subtitle">Готовый семестровый курс на 72 академических часа по ФГОС ВО (15.03.06 / 09.03.01)</div>
    </div>
    <div class="slide-number">06 / 12</div>
  </div>
  <div class="slide-body">
    <div class="grid-2">
      <div class="card">
        <div class="card-title" style="color: #38bdf8;">Блок 1: Фундаментальная мехатроника и ROS 2</div>
        <ul style="font-size: 8.5pt;">
          <li><strong>Лаб 1:</strong> Протоколы шинных актуаторов, телеметрия UART, чтение токов и термопрофиль.</li>
          <li><strong>Лаб 2:</strong> Прямая кинематика (FK), матрицы преобразования Денавита-Хартенберга (DH).</li>
          <li><strong>Лаб 3:</strong> Обратная кинематика (IK), квазиобращение Якобиана и солверы Pink/Pinocchio.</li>
          <li><strong>Лаб 4:</strong> Моделирование в ROS 2: URDF, коллизии и планирование MoveIt 2.</li>
          <li><strong>Лаб 5:</strong> Калибровка технического зрения: Eye-in-Hand и Eye-to-Hand матрицы.</li>
        </ul>
      </div>
      <div class="card card-highlight">
        <div class="card-title" style="color: #818cf8;">Блок 2: Physical AI и имитационное обучение</div>
        <ul style="font-size: 8.5pt;">
          <li><strong>Лаб 6:</strong> Компьютерное зрение: сегментация YOLOv11 и 6D-оценка положения объектов.</li>
          <li><strong>Лаб 7:</strong> Двусторонняя телеоперация (Leader-Follower) и запись датасетов в LeRobot.</li>
          <li><strong>Лаб 8:</strong> Обучение трансформерных моделей: Action Chunking with Transformers (ACT).</li>
          <li><strong>Лаб 9:</strong> Вероятностные диффузионные модели: Diffusion Policy в недетерминированных средах.</li>
          <li><strong>Лаб 10:</strong> Физический тест обобщения: устойчивость к помехам освещения и Sim-to-Real.</li>
        </ul>
      </div>
    </div>
    <div class="card card-success" style="margin-top: 10px; padding: 8px 12px;">
      <div style="font-weight: 700; color: #86efac; font-size: 9pt;">Ключевой фактор для преподавателей:</div>
      <p style="font-size: 8pt;">Комплект включает Рабочую программу дисциплины (РПД), методические указания студенту, критерии оценивания, код решений и настроенные Docker-контейнеры. Курс запускается кафедрой <strong>за 1 неделю без необходимости подготовки новых материалов</strong>.</p>
    </div>
  </div>
  <div class="slide-footer">
    <div>ROBOI: Методическое сопровождение учебного процесса</div>
    <div>Соответствие ФГОС ВО РФ</div>
  </div>
</div>

<!-- SLIDE 7: ЭКОНОМИКА ЛАБОРАТОРИИ -->
<div class="slide">
  <div class="slide-header">
    <div>
      <div class="slide-category">Экономическая эффективность</div>
      <div class="slide-title">Сравнение бюджетов: В 10 раз больше практики за те же деньги</div>
      <div class="slide-subtitle">Расчет комплексного оснащения лаборатории на 20 учебных мест (10 рабочих постов)</div>
    </div>
    <div class="slide-number">07 / 12</div>
  </div>
  <div class="slide-body">
    <div class="grid-2">
      <div class="card card-warning">
        <div class="card-title" style="color: #f59e0b;">Вариант А: Закупка китайских коботов (Unitree / Dobot)</div>
        <table style="width: 100%; font-size: 8.5pt; margin-top: 6px; line-height: 1.5;">
          <tr><td>Стоимость 1 промышленного манипулятора:</td><td style="text-align:right; font-weight:700;">1 200 000 ₽</td></tr>
          <tr><td>Количество постов на класс 20 чел.:</td><td style="text-align:right; font-weight:700;">10 постов</td></tr>
          <tr><td>Итого затраты на манипуляторы:</td><td style="text-align:right; font-weight:700; color:#f87171;">12 000 000 ₽</td></tr>
          <tr><td>Стереокамеры, софт и оснастка:</td><td style="text-align:right; font-weight:700;">1 500 000 ₽</td></tr>
          <tr style="border-top: 1px solid #475569;"><td><strong>ИТОГО БЮДЖЕТ ЛАБОРАТОРИИ:</strong></td><td style="text-align:right; font-weight:900; color:#f87171; font-size:11pt;">13 500 000 ₽</td></tr>
        </table>
        <div style="margin-top: 8px; font-size: 7.5pt; color: #cbd5e1; background: rgba(0,0,0,0.2); padding: 6px; border-radius: 4px;">
          Реальный результат вуза: из-за нехватки средств покупается 1 робот за 1,2 млн ₽. 19 студентов смотрят со стороны.
        </div>
      </div>
      <div class="card card-success">
        <div class="card-title" style="color: #34d399;">Вариант Б: Оснащение лабораторией ROBOI Physical AI</div>
        <table style="width: 100%; font-size: 8.5pt; margin-top: 6px; line-height: 1.5;">
          <tr><td>Стоимость двухрукого поста ROBOI Bimanual:</td><td style="text-align:right; font-weight:700;">120 000 ₽</td></tr>
          <tr><td>Количество постов (по 2 студента на пост):</td><td style="text-align:right; font-weight:700;">10 постов</td></tr>
          <tr><td>Итого затраты на 20 манипуляторов (10 пар):</td><td style="text-align:right; font-weight:700; color:#34d399;">1 200 000 ₽</td></tr>
          <tr><td>Камеры, калибровочные стенды, УМК:</td><td style="text-align:right; font-weight:700; color:#34d399;">ВКЛЮЧЕНО</td></tr>
          <tr style="border-top: 1px solid #475569;"><td><strong>ИТОГО БЮДЖЕТ ЛАБОРАТОРИИ:</strong></td><td style="text-align:right; font-weight:900; color:#34d399; font-size:11pt;">1 200 000 ₽</td></tr>
        </table>
        <div style="margin-top: 8px; font-size: 7.5pt; color: #cbd5e1; background: rgba(0,0,0,0.2); padding: 6px; border-radius: 4px;">
          Реальный результат вуза: <strong>полноценный класс на 20 рабочих мест</strong> по цене ОДНОГО китайского робота! 100% охват практикой.
        </div>
      </div>
    </div>
    <div class="grid-3" style="margin-top: 10px;">
      <div class="metric-box"><div class="metric-value">91%</div><div class="metric-label">Прямая экономия бюджета</div></div>
      <div class="metric-box"><div class="metric-value">10.0x</div><div class="metric-label">Рост практических часов на студента</div></div>
      <div class="metric-box"><div class="metric-value">0 ₽</div><div class="metric-label">Затраты на покупку закрытых лицензий</div></div>
    </div>
  </div>
  <div class="slide-footer">
    <div>ROBOI: Финансово-экономическое обоснование</div>
    <div>Бюджетная оптимизация государственных средств</div>
  </div>
</div>

<!-- SLIDE 8: НОРМАТИВНОЕ ОКНО И ГОСЗАКУПКИ -->
<div class="slide">
  <div class="slide-header">
    <div>
      <div class="slide-category">Законодательство РФ</div>
      <div class="slide-title">Регуляторная защита и механизмы госзакупок</div>
      <div class="slide-subtitle">Как законодательство 2025–2026 годов защищает и отдает приоритет продукции ROBOI</div>
    </div>
    <div class="slide-number">08 / 12</div>
  </div>
  <div class="slide-body">
    <div class="grid-3">
      <div class="card card-highlight">
        <div class="card-title">1. Реформа нацрежима (318-ФЗ)</div>
        <p>Федеральный закон от 08.08.2024 <strong>№ 318-ФЗ</strong> и Постановление Правительства <strong>№ 1875</strong> унифицировали национальный режим для 44-ФЗ и 223-ФЗ. Введено единое жесткое правило допуска отечественной продукции.</p>
        <div style="margin-top: 8px; font-size: 8pt; color: #60a5fa; font-weight: 700;">Единые правила для всех вузов</div>
      </div>
      <div class="card card-highlight">
        <div class="card-title">2. Правило «Второй лишний»</div>
        <p>При наличии хотя бы одной заявки с продукцией из Реестра Минпромторга (ПП РФ № 719), заказчик <strong>обязан отклонить все иностранные заявки</strong>. Китайские коботы законодательно блокируются при участии ROBOI.</p>
        <div style="margin-top: 8px; font-size: 8pt; color: #34d399; font-weight: 700;">100% защита от демпинга КНР</div>
      </div>
      <div class="card card-highlight">
        <div class="card-title">3. Малые закупки (без торгов)</div>
        <p>По <strong>п. 4 и 5 ч. 1 ст. 93 44-ФЗ</strong> государственные вузы вправе заключать прямые договоры <strong>до 600 000 ₽</strong> через электронные магазины (ЕАТ «Березка», РТС-маркет). Поставка оформляется за 5 рабочих дней!</p>
        <div style="margin-top: 8px; font-size: 8pt; color: #f59e0b; font-weight: 700;">Быстрый запуск без бюрократии</div>
      </div>
    </div>
    <div class="card" style="margin-top: 10px; padding: 10px 14px;">
      <div style="font-weight: 700; color: #f1f5f9; font-size: 9pt;">Включение в Реестр Минпромторга РФ (Постановление Правительства № 719):</div>
      <div class="grid-3" style="margin-top: 4px; font-size: 8pt;">
        <div>• <strong>Код ОКПД 2: 32.99.53.000</strong> («Приборы, аппаратура и модели учебные»)</div>
        <div>• <strong>Собственные права на РИД</strong> по ГОСТ ЕСКД у юрлица РФ</div>
        <div>• <strong>Локализация плат:</strong> трассировка и пайка SMT в РФ (Резонит)</div>
      </div>
    </div>
  </div>
  <div class="slide-footer">
    <div>ROBOI: Юридическая чистота и государственные реестры</div>
    <div>Соответствие 44-ФЗ, 223-ФЗ и ПП № 1875</div>
  </div>
</div>

<!-- SLIDE 9: ИСТОЧНИКИ ФИНАНСИРОВАНИЯ -->
<div class="slide">
  <div class="slide-header">
    <div>
      <div class="slide-category">Гранты и финансирование</div>
      <div class="slide-title">Финансирование лаборатории: Вузу не нужно тратить свои средства</div>
      <div class="slide-subtitle">Привлечение целевого неразводняющего государственного капитала через федеральные программы</div>
    </div>
    <div class="slide-number">09 / 12</div>
  </div>
  <div class="slide-body">
    <div class="grid-3">
      <div class="card card-success">
        <div class="card-title">«Студенческий стартап» (ФСИ)</div>
        <div style="font-size: 18pt; font-weight: 900; color: #34d399; margin: 4px 0;">1 000 000 ₽</div>
        <p>100% безвозмездный грант студентам или аспирантам института по направлению <strong>Н4 (Новые приборы)</strong> или <strong>Н1 (Цифровые технологии)</strong>. Средства полностью покрывают закупку оснастки, компонентов и плат опытной серии.</p>
        <div style="margin-top: 8px; font-size: 7.5pt; color: #86efac;">Внебюджетное софинансирование: 0%</div>
      </div>
      <div class="card card-success">
        <div class="card-title">Программа «Старт-1» (ФСИ)</div>
        <div style="font-size: 18pt; font-weight: 900; color: #38bdf8; margin: 4px 0;">до 5 000 000 ₽</div>
        <p>Грант на выполнение НИОКР юридическим лицом (стартапом с участием вуза). Финансирование зарплат инженеров (до 60%), покупки лабораторного оборудования и патентования в Роспатенте.</p>
        <div style="margin-top: 8px; font-size: 7.5pt; color: #93c5fd;">Софинансирование на 1 этапе: 0%</div>
      </div>
      <div class="card card-success">
        <div class="card-title">Субсидии ПИШ и Приоритет 2030</div>
        <div style="font-size: 18pt; font-weight: 900; color: #c084fc; margin: 4px 0;">от 300 млн ₽/год</div>
        <p>Федеральные средства программ «Передовые инженерные школы» и «Приоритет 2030» имеют обязательные целевые статьи на переоснащение лабораторий робототехники и ИИ отечественными комплексами.</p>
        <div style="margin-top: 8px; font-size: 7.5pt; color: #d8b4fe;">Готовые строки в сметах кафедр</div>
      </div>
    </div>
    <div class="card card-highlight" style="margin-top: 10px; padding: 10px 14px;">
      <div style="font-weight: 700; color: #93c5fd; font-size: 9pt;">Готовая модель партнерства «Вуз — Стартап»:</div>
      <p style="font-size: 8.5pt;">Команда проекта под научным кураторством кафедры подает заявку на грант ФСИ «Студенческий стартап» (1 млн ₽), регистрирует малое инновационное предприятие (МИП) с долей университета, и за счет средств гранта безвозмездно передает в институт первые 5–10 рабочих постов!</p>
    </div>
  </div>
  <div class="slide-footer">
    <div>ROBOI: Государственные институты развития</div>
    <div>Фонд содействия инновациям (ФСИ / Фонд Бортника)</div>
  </div>
</div>

<!-- SLIDE 10: ВЫГОДА ДЛЯ ДИРЕКТОРА И КАФЕДРЫ -->
<div class="slide">
  <div class="slide-header">
    <div>
      <div class="slide-category">Ценностное предложение</div>
      <div class="slide-title">Прямая академическая выгода для Директора института</div>
      <div class="slide-subtitle">Выполнение ключевых показателей эффективности (KPI) Министерства науки и высшего образования</div>
    </div>
    <div class="slide-number">10 / 12</div>
  </div>
  <div class="slide-body">
    <div class="grid-2">
      <div class="card">
        <div class="card-title" style="color: #38bdf8;">1. Наукометрические показатели (Публикации ВАК/RSCI)</div>
        <p>Благодаря открытому доступу к низкоуровневой динамике и кинематике, студенты, магистранты и аспиранты получают базу для проведения оригинальных экспериментов по Physical AI. Это гарантирует <strong>от 4 до 8 публикаций ежегодно</strong> в журналах ВАК и изданиях, индексируемых в Scopus / RSCI.</p>
      </div>
      <div class="card">
        <div class="card-title" style="color: #34d399;">2. Интеллектуальная собственность (РИД)</div>
        <p>Совместная регистрация в Роспатенте патентов на полезные модели (кинематические схемы манипулятора) и свидетельств на программы для ЭВМ (драйверы, алгоритмы компенсации люфтов) <strong>с указанием Университета в качестве правообладателя</strong>.</p>
      </div>
      <div class="card">
        <div class="card-title" style="color: #f59e0b;">3. Престиж и победы в студенческих чемпионатах</div>
        <p>Подготовка студенческих команд к соревнованиям по робототехнике и ИИ (Хакатоны, «Битва роботов», «Я — профессионал»). Команды тренируются на реальном оборудовании, а не на симуляторах, что кратно повышает шансы на призовые места.</p>
      </div>
      <div class="card">
        <div class="card-title" style="color: #c084fc;">4. Полное снятие рисков поломок и прокурорских проверок</div>
        <p>Безопасное питание 12V снимает вопросы охраны труда (ТР ТС 004/2011). В комплект каждого класса входит <strong>«ЗИП-набор»</strong> (запасные сервоприводы, шестерни, напечатанные звенья). Любой ремонт выполняется студентами за 15 минут прямо в аудитории.</p>
      </div>
    </div>
  </div>
  <div class="slide-footer">
    <div>ROBOI: Академические KPI кафедры и института</div>
    <div>Выполнение показателей Минобрнауки РФ</div>
  </div>
</div>

<!-- SLIDE 11: ДОРОЖНАЯ КАРТА СОТРУДНИЧЕСТВА -->
<div class="slide">
  <div class="slide-header">
    <div>
      <div class="slide-category">План реализации</div>
      <div class="slide-title">Дорожная карта партнерства: Без финансовых рисков</div>
      <div class="slide-subtitle">Поэтапный переход от пилотной апробации к созданию флагманского центра компетенций</div>
    </div>
    <div class="slide-number">11 / 12</div>
  </div>
  <div class="slide-body">
    <div class="grid-4" style="margin-bottom: 12px;">
      <div class="card card-highlight">
        <div style="font-size: 8pt; color: #93c5fd; font-weight: 700;">ЭТАП 1 (СЕЙЧАС)</div>
        <div style="font-size: 11pt; font-weight: 800; color: #fff; margin: 4px 0;">Соглашение о намерениях</div>
        <p style="font-size: 8pt;">Подписание рамочного соглашения (LoI) о научно-методическом сотрудничестве. Институт не несет никаких финансовых обязательств.</p>
      </div>
      <div class="card card-success">
        <div style="font-size: 8pt; color: #86efac; font-weight: 700;">ЭТАП 2 (НЕДЕЛЯ 2–4)</div>
        <div style="font-size: 11pt; font-weight: 800; color: #fff; margin: 4px 0;">Пилотный тест-драйв</div>
        <p style="font-size: 8pt;">Бесплатная передача в лабораторию 2 действующих манипуляторов ROBOI для проведения пилотных занятий и сбора отзывов преподавателей.</p>
      </div>
      <div class="card">
        <div style="font-size: 8pt; color: #f59e0b; font-weight: 700;">ЭТАП 3 (МЕСЯЦ 2–3)</div>
        <div style="font-size: 11pt; font-weight: 800; color: #fff; margin: 4px 0;">Грант ФСИ 1 000 000 ₽</div>
        <p style="font-size: 8pt;">Подача совместной заявки на конкурс «Студенческий стартап» с поддержкой института. Привлечение грантовых средств на расширение лаборатории.</p>
      </div>
      <div class="card card-highlight">
        <div style="font-size: 8pt; color: #c084fc; font-weight: 700;">ЭТАП 4 (МЕСЯЦ 4–6)</div>
        <div style="font-size: 11pt; font-weight: 800; color: #fff; margin: 4px 0;">Флагманский класс</div>
        <p style="font-size: 8pt;">Развертывание полноценного класса на 10 рабочих станций ROBOI Bimanual по программе ПИШ / Приоритет 2030 / малым закупкам 44-ФЗ.</p>
      </div>
    </div>
    <div class="card" style="padding: 10px 14px;">
      <div style="font-weight: 700; color: #f1f5f9; font-size: 9.5pt;">Предложение на первую встречу с Руководством института:</div>
      <p style="font-size: 8.5pt;">Мы готовы провести <strong>живую 15-минутную демонстрацию действующего прототипа TRL-4</strong> непосредственно в кабинете Директора института или в лаборатории кафедры: показать зеркальную телеоперацию, автономную сортировку предметов по техническому зрению и предоставить полный комплект методических указаний для экспертизы ведущими доцентами кафедры.</p>
    </div>
  </div>
  <div class="slide-footer">
    <div>ROBOI: План совместных действий</div>
    <div>Готовность к немедленному пилотированию</div>
  </div>
</div>

<!-- SLIDE 12: КОНТАКТЫ И ПРИЗЫВ К ДЕЙСТВИЮ -->
<div class="slide title-slide" style="justify-content: space-between;">
  <div style="margin-top: 10mm;">
    <span class="tag tag-green">ДАВАЙТЕ СОЗДАВАТЬ РОБОТОТЕХНИКУ БУДУЩЕГО ВМЕСТЕ</span>
    <div class="title-hero" style="font-size: 28pt; margin-top: 8px;">
      Готовы к запуску лаборатории <span>ROBOI Physical AI</span>
    </div>
    <div class="title-desc" style="font-size: 11pt; max-width: 90%;">
      Мы предлагаем Институту стать опорной площадкой и лидером внедрения суверенного Physical AI в России. Мы берем на себя конструкторскую разработку, поставку «железа», методическое сопровождение и гарантийное обслуживание.
    </div>
  </div>
  <div class="grid-3" style="max-width: 95%;">
    <div class="card card-highlight">
      <div style="font-size: 8pt; color: #93c5fd; text-transform: uppercase;">Демонстрация стенда</div>
      <div style="font-weight: 700; font-size: 9.5pt; margin-top: 2px;">Выездная презентация прототипа в удобное время</div>
    </div>
    <div class="card card-success">
      <div style="font-size: 8pt; color: #86efac; text-transform: uppercase;">Тестовый комплект</div>
      <div style="font-weight: 700; font-size: 9.5pt; margin-top: 2px;">Бесплатная апробация на кафедре на 30 дней</div>
    </div>
    <div class="card">
      <div style="font-size: 8pt; color: #cbd5e1; text-transform: uppercase;">Контакты проектной группы</div>
      <div style="font-weight: 700; font-size: 9.5pt; margin-top: 2px;">Команда разработки платформы ROBOI</div>
    </div>
  </div>
  <div class="slide-footer" style="margin-top: 10px;">
    <div>Проект отечественной открытой робототехники ROBOI • 2026</div>
    <div>Благодарим за внимание! Будем рады ответить на ваши вопросы.</div>
  </div>
</div>

</body>
</html>
"""

with open(HTML_PATH, "w", encoding="utf-8") as f:
    f.write(html_content)
print(f"Saved HTML Presentation to: {HTML_PATH}")

# -------------------------------------------------------------
# 2. COMPILE HTML TO 16:9 PDF VIA HEADLESS EDGE
# -------------------------------------------------------------
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
        print(f"Compiled PDF Presentation: {PDF_PATH} ({size_kb:.1f} KB)")
    else:
        print("Edge PDF conversion failed:", res.stderr)
else:
    print("Edge not found, skipping PDF generation.")


# -------------------------------------------------------------
# 3. GENERATE POWERPOINT PRESENTATION (.PPTX) VIA python-pptx
# -------------------------------------------------------------
prs = Presentation()
# Set 16:9 widescreen dimensions (13.333 x 7.5 inches)
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)

# Color constants
C_NAVY = RGBColor(11, 19, 41)
C_DARK_BLUE = RGBColor(15, 23, 42)
C_CARD_BG = RGBColor(30, 41, 59)
C_WHITE = RGBColor(255, 255, 255)
C_CYAN = RGBColor(56, 189, 248)
C_BLUE = RGBColor(59, 130, 246)
C_GREEN = RGBColor(16, 185, 129)
C_AMBER = RGBColor(245, 158, 11)
C_GRAY_TEXT = RGBColor(148, 163, 184)
C_LIGHT_GRAY = RGBColor(203, 213, 225)

blank_slide_layout = prs.slide_layouts[6]

slides_data = [
    {
        "cat": "ИНВЕСТИЦИОННОЕ И НАУЧНО-ОБРАЗОВАТЕЛЬНОЕ ПРЕДЛОЖЕНИЕ",
        "title": "Проект ROBOI: Суверенная платформа робототехники и Physical AI",
        "sub": "Оснащение университетских лабораторий отечественными манипуляторами нового поколения по цене в 5–10 раз ниже зарубежных аналогов",
        "cards": [
            ("Для Руководства Института", "Инициатива кафедры и университетского стартапа в рамках импортозамещения и технологического суверенитета"),
            ("Базовый УМК по ФГОС ВО", "Семестровый курс на 72 академических часа (10 практических лабораторных работ)"),
            ("Экономия бюджета 90%", "Оснащение 10 рабочих станций (20 манипуляторов) за 1,2 млн ₽ вместо 12–14 млн ₽ на коботах")
        ]
    },
    {
        "cat": "ВЫЗОВЫ И АНАЛИЗ РЫНКА",
        "title": "Кризис материально-технической базы в робототехнике РФ",
        "sub": "Почему классический подход к закупке импортных манипуляторов больше не работает",
        "cards": [
            ("1. Санкционная блокада", "Полный запрет поставок европейских манипуляторов (Franka Emika, Universal Robots, Niryo). Отключение облачных сервисов и блокировка импорта оригинальных запчастей."),
            ("2. Китайский «Черный ящик»", "Китайские манипуляторы (Unitree, Elephant Robotics, Dobot) стоят от 700 тыс. до 1,5 млн ₽. Закрытые драйверы и библиотеки не позволяют исследовать алгоритмы управления."),
            ("3. Оторванность от практики", "Из-за дефицита «железа» 90% студентов обучаются только в симуляторах. Индустрия получает выпускников без навыков работы с реальными датчиками и Physical AI.")
        ]
    },
    {
        "cat": "КОНЦЕПЦИЯ ПРОДУКТА",
        "title": "Экосистема ROBOI: Суверенный Physical AI «из коробки»",
        "sub": "Аппаратно-программный комплекс манипуляционной робототехники для университетов",
        "cards": [
            ("Аппаратная часть (Hardware)", "• Модульные звенья из композитного углеволокна (PETG-CF / PA-CF)\n• Отечественная плата управления V3 (ESP32-S3 + TPS54560, производство в РФ)\n• Интеллектуальные сервоприводы с 12-битными магнитными энкодерами\n• Стерео-комплект камер 1080p 60fps (Eye-to-Hand + Eye-in-Hand) за 5 000 ₽"),
            ("Программный стек (Software & AI)", "• Полная интеграция с Hugging Face LeRobot, ACT и Diffusion Policy\n• Нативная поддержка ROS 2 Humble/Jazzy и планировщика MoveIt 2\n• Зеркальная двусторонняя телеоперация (Leader-Follower) для записи датасетов\n• 100% открытый код: доступ ко всем регистрам, токам и матрицам"),
            ("Ключевые метрики", "• Безопасное питание 12V (ТР ТС 004/2011)\n• Базовая цена: от 69 000 ₽ за рабочий пост\n• Доставка запчастей по РФ: 24–48 часов\n• Действующий лабораторный образец TRL-4")
        ]
    },
    {
        "cat": "ИНЖЕНЕРНЫЕ ИННОВАЦИИ",
        "title": "Преодоление тепловых и механических лимитов",
        "sub": "Почему архитектура ROBOI превосходит типовые любительские проекты (SO-100)",
        "cards": [
            ("Инновация 1: Спаренный сустав", "Тандемный привод Dual-Servo на плечевом шарнире удваивает номинальный длительный момент до 20 кг·см (пик 60 кг·см), полностью устраняя перегрев и аварийное отключение моторов."),
            ("Инновация 2: Антилюфтовый натяг", "Программный встречный преднатяг тандемных моторов (микросмещение ±0.15°) выбирает механический зазор шестерен редуктора, повышая повторяемость руки до ±0.3 мм."),
            ("Инновация 3: Кинематика Пантографа", "Перенос сервоприводов локтя и плеча в неподвижную базу снижает момент инерции звеньев на 60% и позволяет уравновесить собственный вес руки механическими пружинами.")
        ]
    },
    {
        "cat": "МЕТОДИЧЕСКОЕ ОБЕСПЕЧЕНИЕ",
        "title": "Учебно-методический комплекс (УМК): 10 лабораторных работ",
        "sub": "Готовый семестровый курс на 72 академических часа по стандартам ФГОС ВО (15.03.06 / 09.03.01)",
        "cards": [
            ("Блок 1: Мехатроника и ROS 2", "Лаб 1: Шинные актуаторы, протокол UART, чтение токов и термопрофиль\nЛаб 2: Прямая кинематика (FK) и DH-параметры Денавита-Хартенберга\nЛаб 3: Обратная кинематика (IK) и численные солверы Pink/Pinocchio\nЛаб 4: Моделирование в ROS 2: URDF, коллизии и планирование MoveIt 2\nЛаб 5: Калибровка камер: матрицы Eye-in-Hand и Eye-to-Hand"),
            ("Блок 2: Physical AI и трансформеры", "Лаб 6: Сегментация YOLOv11 и 6D-оценка положения объектов захвата\nЛаб 7: Двусторонняя телеоперация (Leader-Follower) и датасеты LeRobot\nЛаб 8: Обучение модели Action Chunking with Transformers (ACT)\nЛаб 9: Диффузионные вероятностные модели (Diffusion Policy)\nЛаб 10: Физический тест обобщающей способности (Sim-to-Real)"),
            ("Готовность «Под ключ»", "Включает РПД, методические указания студенту, типовые решения задач преподавателю и готовые Docker-образы. Курс запускается кафедрой за 1 неделю.")
        ]
    },
    {
        "cat": "ЭКОНОМИЧЕСКАЯ ЭФФЕКТИВНОСТЬ",
        "title": "Сравнение бюджетов: 10 постов за цену ОДНОГО китайского робота",
        "sub": "Расчет оснащения лабораторного класса на 20 студентов (10 рабочих постов)",
        "cards": [
            ("Вариант А: Китайские роботы", "• 10 коботов (Unitree Z1 / Dobot CR): 12 000 000 ₽\n• Дополнительные камеры и оснастка: 1 500 000 ₽\n• ИТОГО: 13 500 000 ₽\n\nРеальность: Вуз покупает 1 робота за 1,2 млн ₽, 19 студентов стоят в очереди."),
            ("Вариант Б: Лаборатория ROBOI", "• 10 двухруких постов ROBOI Bimanual: 1 200 000 ₽\n• Камеры, плиты, оснастка, УМК: ВКЛЮЧЕНО\n• ИТОГО: 1 200 000 ₽\n\nРеальность: Полноценный класс на 20 студентов по цене ОДНОГО китайского робота!"),
            ("Финансовые показатели", "• Экономия бюджета: 91%\n• Рост практических часов на студента: 10.0x\n• Стоимость лицензий ПО: 0 ₽ (Open Source)\n• Запчасти и ремонт: в течение 24–48 часов в РФ")
        ]
    },
    {
        "cat": "НОРМАТИВНАЯ ЗАЩИТА",
        "title": "Регуляторная защита и механизмы госзакупок",
        "sub": "Законодательство РФ 2025–2026 годов отдает безусловный приоритет отечественному комплексу",
        "cards": [
            ("1. Реформа 318-ФЗ и ПП № 1875", "Унифицированный нацрежим для 44-ФЗ и 223-ФЗ. Правило «Второй лишний»: при наличии отечественной реестровой заявки иностранные роботы законодательно отклоняются."),
            ("2. Реестр Минпромторга (ПП 719)", "Регистрация по коду ОКПД 2: 32.99.53.000 («Приборы и модели учебные демонстрационные»). 78 баллов локализации (при норме 65): разводка плат, пайка и сборка в РФ."),
            ("3. Малые закупки без конкурса", "По п. 4 и 5 ч. 1 ст. 93 44-ФЗ вузы могут приобретать стенды до 600 000 ₽ напрямую через электронные магазины (ЕАТ «Березка», РТС-маркет) за 5 рабочих дней.")
        ]
    },
    {
        "cat": "ФИНАНСИРОВАНИЕ И ГРАНТЫ",
        "title": "Вузу не требуется тратить собственные средства",
        "sub": "Привлечение целевого государственного финансирования через федеральные программы",
        "cards": [
            ("«Студенческий стартап» (ФСИ)", "1 000 000 ₽ безвозмездный грант на команду студентов/аспирантов кафедры. 0% софинансирования. Средства покрывают закупку компонентов и производство первой партии для вуза."),
            ("Программа «Старт-1» (ФСИ)", "До 5 000 000 ₽ на выполнение НИОКР юридическим лицом с участием университета. Финансирование зарплат разработчиков и регистрация патентов в Роспатенте."),
            ("ПИШ и Приоритет 2030", "Федеральные субсидии от 300 млн до 1 млрд ₽/год на оснащение передовых инженерных школ и лабораторий суверенными отечественными разработками.")
        ]
    },
    {
        "cat": "ЦЕННОСТЬ ДЛЯ ДИРЕКТОРА",
        "title": "Прямая выгода для Руководства института и Кафедры",
        "sub": "Выполнение ключевых показателей эффективности (KPI) Минобрнауки РФ",
        "cards": [
            ("Публикации ВАК / Scopus / RSCI", "Открытый доступ к кинематике и динамике обеспечивает 4–8 научных публикаций ежегодно на базе реальных экспериментов с Physical AI."),
            ("Патенты и права на РИД", "Совместная регистрация патентов на полезные модели и свидетельств на программы для ЭВМ с указанием Университета в качестве правообладателя."),
            ("Безопасность и эксплуатация", "Питание 12V (ТР ТС 004/2011). Наличие складского ЗИП-набора (моторы, звенья). Любой ремонт выполняется студентами за 15 минут в аудитории.")
        ]
    },
    {
        "cat": "ПЛАН РЕАЛИЗАЦИИ",
        "title": "Дорожная карта партнерства без финансовых рисков",
        "sub": "Поэтапный переход от пилотной апробации к развертыванию опорного центра",
        "cards": [
            ("Этап 1 (Сейчас)", "Подписание рамочного Соглашения о намерениях (Letter of Intent — LoI). Институт не несет никаких финансовых обязательств."),
            ("Этап 2 (Неделя 2–4)", "Бесплатная передача в лабораторию 2 манипуляторов ROBOI для проведения пилотных занятий и сбора отзывов преподавателей кафедры."),
            ("Этап 3 (Месяц 2–4)", "Подача совместной заявки на грант «Студенческий стартап» (1 млн ₽) и развертывание класса на 10 постов ROBOI Bimanual по программам ПИШ.")
        ]
    },
    {
        "cat": "ПРИЗЫВ К ДЕЙСТВИЮ",
        "title": "Готовы к запуску лаборатории ROBOI Physical AI",
        "sub": "Предлагаем Институту стать опорной площадкой суверенной робототехники в России",
        "cards": [
            ("Живая демонстрация стенда", "Готовы привезти действующий прототип TRL-4 и провести 15-минутный показ работы в кабинете Директора или на заседании кафедры."),
            ("Бесплатный пилот на 30 дней", "Предоставим 2 манипулятора с УМК преподавателям кафедры для тестирования в реальном учебном процессе."),
            ("Контакты проектной группы", "Команда проекта ROBOI • Россия, 2026\nГотовы ответить на любые вопросы и согласовать дату демонстрации!")
        ]
    }
]

for idx, sdata in enumerate(slides_data):
    slide = prs.slides.add_slide(blank_slide_layout)
    
    # Background rectangle (Dark Navy)
    bg = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, Inches(13.333), Inches(7.5))
    bg.fill.solid()
    bg.fill.fore_color.rgb = C_NAVY
    bg.line.color.rgb = C_NAVY
    
    # Accent top border
    top_bar = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, Inches(13.333), Inches(0.1))
    top_bar.fill.solid()
    top_bar.fill.fore_color.rgb = C_BLUE
    top_bar.line.fill.background()
    
    # Header block
    header_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.4), Inches(11.7), Inches(1.3))
    tf = header_box.text_frame
    tf.word_wrap = True
    
    p0 = tf.paragraphs[0]
    p0.text = sdata["cat"]
    p0.font.size = Pt(10)
    p0.font.bold = True
    p0.font.color.rgb = C_CYAN
    
    p1 = tf.add_paragraph()
    p1.text = sdata["title"]
    p1.font.size = Pt(20)
    p1.font.bold = True
    p1.font.color.rgb = C_WHITE
    p1.space_after = Pt(2)
    
    p2 = tf.add_paragraph()
    p2.text = sdata["sub"]
    p2.font.size = Pt(11)
    p2.font.color.rgb = C_GRAY_TEXT

    # Slide number
    num_box = slide.shapes.add_textbox(Inches(11.5), Inches(0.4), Inches(1.2), Inches(0.5))
    ntf = num_box.text_frame
    np = ntf.paragraphs[0]
    np.text = f"{idx+1:02d} / 12"
    np.font.size = Pt(11)
    np.font.bold = True
    np.font.color.rgb = C_GRAY_TEXT
    np.alignment = PP_ALIGN.RIGHT

    # Content cards (3 cards horizontal layout)
    num_cards = len(sdata["cards"])
    card_width = (11.733 - (num_cards - 1) * 0.35) / num_cards
    
    for c_idx, (ctitle, cdesc) in enumerate(sdata["cards"]):
        left = 0.8 + c_idx * (card_width + 0.35)
        top = 2.0
        height = 4.7
        
        card_shape = slide.shapes.add_shape(
            MSO_SHAPE.ROUNDED_RECTANGLE,
            Inches(left), Inches(top), Inches(card_width), Inches(height)
        )
        card_shape.fill.solid()
        card_shape.fill.fore_color.rgb = C_CARD_BG
        card_shape.line.color.rgb = C_BLUE if c_idx == 0 else RGBColor(51, 65, 85)
        card_shape.line.width = Pt(1.5 if c_idx == 0 else 1)
        
        ctf = card_shape.text_frame
        ctf.word_wrap = True
        ctf.margin_left = Inches(0.2)
        ctf.margin_right = Inches(0.2)
        ctf.margin_top = Inches(0.2)
        
        cp0 = ctf.paragraphs[0]
        cp0.text = ctitle
        cp0.font.size = Pt(13)
        cp0.font.bold = True
        cp0.font.color.rgb = C_CYAN if c_idx == 0 else C_WHITE
        cp0.space_after = Pt(8)
        
        for line in cdesc.split("\n"):
            cp_line = ctf.add_paragraph()
            cp_line.text = line
            cp_line.font.size = Pt(10)
            cp_line.font.color.rgb = C_LIGHT_GRAY
            cp_line.space_after = Pt(4)

    # Footer
    footer_box = slide.shapes.add_textbox(Inches(0.8), Inches(6.9), Inches(11.7), Inches(0.4))
    ftf = footer_box.text_frame
    fp = ftf.paragraphs[0]
    fp.text = "ROBOI: Платформа открытой робототехники и Physical AI • Россия, 2026 • Для служебного пользования"
    fp.font.size = Pt(8.5)
    fp.font.color.rgb = C_GRAY_TEXT

prs.save(PPTX_PATH)
print(f"Saved PowerPoint Presentation to: {PPTX_PATH}")
print("ALL PRESENTATION ASSETS GENERATED SUCCESSFULLY.")

