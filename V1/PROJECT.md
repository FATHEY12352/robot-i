# Project: Open-Source Physical AI Manipulators & Desktop Cobots Monograph & Feasibility Dossier

## Architecture
The deliverable is an exhaustive, peer-reviewed-level Scientific Monograph and Techno-Economic Feasibility Dossier (80–100 page equivalent) in formal academic Arabic, integrating English engineering terms and Russian regulatory nomenclature, alongside an automated PDF compilation script and a programmatic verification suite.

### Document Layout & Chapter Breakdown
- `chapters/00_front_matter.md`: الغلاف الرسمي، صفحة العنوان، بيانات الجامعة، الفهرس التفصيلي والمصطلحات.
- `chapters/01_section_i_executive_summary.md`: Section I: الملخص التنفيذي والأهمية الاستراتيجية (Executive Summary & Strategic Rationale).
- `chapters/02_section_ii_actuator_kinematics.md`: Section II: التحليل الهندسي للمحركات والكينماتيكا (Actuator & Kinematic Analysis).
- `chapters/03_section_iii_opensource_taxonomy.md`: Section III: المسح الشامل للأذرع مفتوحة المصدر مع الصور والأسعار (Multi-Tier Open-Source Landscape & Taxonomy).
- `chapters/04_section_iv_pedagogical_framework.md`: Section IV: المصفوفة التعليمية ودليل التجارب المعملية (Pedagogical Blueprint & 10-Laboratory Syllabus).
- `chapters/05_section_v_competitive_benchmarking.md`: Section V: المقارنة المعيارية العالمية مع الصين وأوروبا (Global Competitive Benchmarking).
- `chapters/06_section_vi_russian_regulatory.md`: Section VI: البيئة التشريعية والمنح الروسية (Russian Legislative, Grant & Procurement Blueprint).
- `chapters/07_section_vii_financial_engineering.md`: Section VII: دراسة الجدوى المالية ومذكرة الاستثمار (Financial Engineering & Rector Investment Memorandum).
- `chapters/08_appendices.md`: الملاحق الفنية، جداول الحسابات البرمجية، كود التحكم، والمراجع العلمية.

### Scripts & Verification Tools
- `scripts/build_monograph.py`: Python compilation pipeline rendering modular Markdown -> HTML5 with KaTeX -> Headless Edge PDF.
- `scripts/verify_monograph.py`: Programmatic verification suite validating chapters, tier tables, BOM math, LaTeX equations, and image links.

---

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | Section I: Executive Summary | Strategic rationale, sovereign physical AI, NUST MISIS/university startup context | M1 | R7 |
| 2 | Section II: Actuator Analysis | Feetech STS3215/3032/3046 specs, continuous vs stall torque, thermal degradation, I²R heating, 12-bit magnetic encoder, backlash | M1 | R1 |
| 3 | Section II: Kinematics & Dynamics | Base-relocated actuation (pantograph/parallelogram vs SCARA), DH parameters, Jacobian, Euler-Lagrange, quintic polynomials, minimum jerk, impedance control | M1 | R1, R3 |
| 4 | Section III: Multi-Tier Taxonomy | Tiers A, B, C, D complete taxonomy with Min, Avg, Max BOM in RUB (EEZYbotARM, SO-100, Koch, RoArm, PAROL6, AR4, Mini-ALOHA) | M2 | R1 |
| 5 | Section III: Mechanical & Gearbox Analysis | Deflection, structural flutter, cycloidal vs compound planetary vs harmonic drives, wear & fatigue | M2 | R1 |
| 6 | Section III: Visual Figures & CAD Renders | High-resolution images, CAD renders, kinematic diagrams with working URLs and captions | M2 | R2 |
| 7 | Section IV: Pedagogical Framework | University competencies in kinematics, dynamics, physical AI, ROS 2 / micro-ROS | M3 | R3 |
| 8 | Section IV: 10-Laboratory Syllabus | Structured 10-lab semester curriculum with equipment, procedures, and learning outcomes | M3 | R3 |
| 9 | Section IV: Physical AI & Middleware | Imitation learning (ACT, Diffusion Policy), VLA models, LeRobot, ROS 2 Humble/Jazzy, FreeRTOS determinism | M3 | R3 |
| 10 | Section V: Global Benchmarking Matrix | Comparison of domestic ROBOI vs 9 platforms (Elephant, Unitree, Dobot, Franka, UR, Niryo) | M4 | R4 |
| 11 | Section V: Strategic Sovereignty Analysis | Retail price in Russia vs domestic BOM, payload, reach, repeatability, open vs closed ecosystem, sanctions immunity | M4 | R4 |
| 12 | Section VI: Russian Procurement Framework | 44-FZ & 223-FZ, PP 878 «второй лишний», Order 126n (15%/20%), PP 2013/2014 quotas | M5 | R5 |
| 13 | Section VI: Minpromtorg Registry | Decrees 719 & 878, OKPD 2 classifications, 65-75 points scoring breakdown, TPP RF & GISP inclusion | M5 | R5 |
| 14 | Section VI: Grants & Academic Capital | FASIE Student Startup (1M RUB), Start-1 (5M RUB), Priority 2030, PISH, evaluation criteria | M5 | R5 |
| 15 | Section VII: Granular BOM Ledger | BOM breakdown by Raw Materials, Fasteners, Actuators, Electronics, Labor across 10, 50, 200 units (Min, Avg, Max) | M5 | R6 |
| 16 | Section VII: 10-Station Lab Capital Efficiency | Turnkey 1.2M RUB 10-station lab vs 1 imported cobot, 10.0× student hands-on time | M5 | R6 |
| 17 | Section VII: University KPIs & Risk Matrix | VAK/RSCI/Scopus projections, patents, student recruitment, 5 supply chain risks & engineering mitigations | M5 | R6 |
| 18 | Automated PDF Compilation Pipeline | Python script rendering modular Arabic Markdown + KaTeX + CSS Paged Media to styled PDF | M6 | R7 |
| 19 | Programmatic Verification Suite | Automated script verifying chapter existence, tier BOMs, arithmetic consistency, LaTeX math, image links | M7 | Acceptance Criteria |
| 20 | Dual Track: E2E Testing Suite | Requirements-driven verification test suite covering Tiers 1-4 publishing TEST_READY.md | E2E | Project Pattern |

---

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Section I & Section II Authoring | Chapters 00, 01, 02 (Front Matter, Executive Summary, Actuator & Kinematics) | Survey | PLANNED |
| M2 | Section III Authoring | Chapter 03 (Multi-Tier Taxonomy, Mechanical/Gearbox analysis, Figures/CAD renders) | Survey | PLANNED |
| M3 | Section IV Authoring | Chapter 04 (Pedagogical Framework, 10-Lab Syllabus, Physical AI & Middleware) | Survey | PLANNED |
| M4 | Section V Authoring | Chapter 05 (Global Competitive Benchmarking Matrix & Strategic Analysis) | Survey | PLANNED |
| M5 | Section VI & Section VII Authoring | Chapters 06, 07, 08 (Regulatory, Grants, BOM Ledger, 10-Station Lab, Rector Pitch, Appendices) | Survey | PLANNED |
| M6 | Automated PDF Compilation Pipeline | `scripts/build_monograph.py`, HTML5/KaTeX template, Arabic RTL styling, Headless Edge PDF | Survey | PLANNED |
| E2E | E2E Testing & Verification Track | `scripts/verify_monograph.py`, test runners, arithmetic validator, `TEST_READY.md` | Survey | PLANNED |
| M7 | Final Integration, E2E Pass & Audit | Full publication build (80-100+ pages), 100% test pass, Reviewer, Challenger, Forensic Audit | M1-M6, E2E | PLANNED |

---

## Interface Contracts
### Chapters ↔ PDF Compilation Script (`scripts/build_monograph.py`)
- Chapters must be saved in `d:\projekt\ARM\chapters/` named `00_front_matter.md` through `08_appendices.md`.
- File encoding must be UTF-8 without BOM.
- Math expressions must use `$inline$` and `$$display$$` LaTeX syntax.
- Visual figures must use standard Markdown: `![Caption](URL)` followed by `*الشكل X: توضيح...*`.
- Tables must use standard Markdown grid syntax.

### Verification Script (`scripts/verify_monograph.py`) ↔ Monograph Chapters
- Must verify:
  1. All 9 chapter files exist and are non-empty (>15,000 characters each).
  2. Four distinct tiers (A, B, C, D) are explicitly present with numeric cost tables in RUB.
  3. All BOM arithmetic tables (Min, Avg, Max for batches 10, 50, 200) match calculated sums exactly.
  4. LaTeX formulas have matching delimiters ($ and $$).
  5. 10 distinct laboratory experiments are enumerated with objectives.
  6. Exit code 0 indicates complete verification pass.

---

## Code Layout
```
d:\projekt\ARM\
├── chapters\
│   ├── 00_front_matter.md
│   ├── 01_section_i_executive_summary.md
│   ├── 02_section_ii_actuator_kinematics.md
│   ├── 03_section_iii_opensource_taxonomy.md
│   ├── 04_section_iv_pedagogical_framework.md
│   ├── 05_section_v_competitive_benchmarking.md
│   ├── 06_section_vi_russian_regulatory.md
│   ├── 07_section_vii_financial_engineering.md
│   └── 08_appendices.md
├── scripts\
│   ├── build_monograph.py
│   └── verify_monograph.py
├── output\
│   └── ROBOI_Scientific_Monograph_Dossier.pdf
└── .agents\teamwork\
    └── ...
```
