# Dispatch: Milestone 6 — Automated PDF Compilation Pipeline

You are `worker_pdf`.
Working directory: `d:\projekt\ARM\.agents\teamwork\worker_pdf`

## Mandatory Directives
1. You MUST read `d:\projekt\ARM\.agents\teamwork\ORIGINAL_REQUEST.md` before starting work.
2. Read the findings from `d:\projekt\ARM\.agents\teamwork\explorer_survey_1\handoff.md`.
3. MANDATORY INTEGRITY WARNING:
   > DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## File Ownership
You EXCLUSIVELY own:
- `d:\projekt\ARM\scripts\build_monograph.py`
- `d:\projekt\ARM\PROJECT.md` (root mirror copy)
- Supporting style/template files in `d:\projekt\ARM\scripts\` or `d:\projekt\ARM\templates\` (if needed).
Do NOT modify chapter markdown files directly.

## Detailed Requirements
Create an automated Python compilation pipeline `d:\projekt\ARM\scripts\build_monograph.py` that:
1. Discovers and concatenates all chapters from `d:\projekt\ARM\chapters\`:
   - `00_front_matter.md`
   - `01_section_i_executive_summary.md`
   - `02_section_ii_actuator_kinematics.md`
   - `03_section_iii_opensource_taxonomy.md`
   - `04_section_iv_pedagogical_framework.md`
   - `05_section_v_competitive_benchmarking.md`
   - `06_section_vi_russian_regulatory.md`
   - `07_section_vii_financial_engineering.md`
   - `08_appendices.md`
2. Converts Markdown to HTML5 using Python `markdown` with extensions: `tables`, `fenced_code`, `toc`, and `markdown-katex` or KaTeX auto-render scripts.
3. Implements proper Arabic RTL layout:
   - Sets `<html dir="rtl" lang="ar">`.
   - Uses system font stack: `Dubai`, `Arabic Typesetting`, `Segoe UI`, `Arial`.
   - Critical LaTeX isolation: `.katex, .katex-display, pre, code { direction: ltr !important; unicode-bidi: isolate; }` to prevent bidirectional formula corruption.
   - Professional CSS Paged Media: `@page { size: A4 portrait; margin: 20mm 15mm 20mm 15mm; @bottom-center { content: counter(page); } }`.
   - Academic styling: Beautiful cover page, styled chapter headers, clear table formatting with alternating row colors, callout boxes for Russian legislative decrees, figure styling with centered captions.
4. Uses `msedge.exe` (or `chrome.exe`) in headless mode:
   `msedge.exe --headless --disable-gpu --no-pdf-header-footer --print-to-pdf=...`
5. Outputs the completed monograph PDF to `d:\projekt\ARM\output\ROBOI_Scientific_Monograph_Dossier.pdf`.
6. Executes the script, tests the PDF compilation, checks that the PDF is generated without fatal errors, and reports the resulting file size and page count (verifying it reaches ~80–100+ pages).

Maintain `progress.md` with your timestamp and status.
Write your final report to `handoff.md` and message the orchestrator when finished.

## 2026-11-02T10:58:26Z
**Context**: PDF Pipeline Generation
**Content**: All 9 chapters (00 through 08) in `d:\projekt\ARM\chapters` are now fully authored and verified (over 38,000 words total).
**Action**: Please implement `d:\projekt\ARM\scripts\build_monograph.py` and run it to compile the complete publication into `d:\projekt\ARM\output\ROBOI_Scientific_Monograph_Dossier.pdf`. Report back with page count, file size, and completion.

