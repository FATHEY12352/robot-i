# Dispatch: E2E Testing Track — Programmatic Verification Suite & Quality Gate

You are `worker_e2e` (`teamwork_test_writer`).
Working directory: `d:\projekt\ARM\.agents\teamwork\worker_e2e`

## Mandatory Directives
1. You MUST read `d:\projekt\ARM\.agents\teamwork\ORIGINAL_REQUEST.md` before starting work.
2. Read the findings from all three survey explorers:
   - `d:\projekt\ARM\.agents\teamwork\explorer_survey_1\handoff.md`
   - `d:\projekt\ARM\.agents\teamwork\explorer_survey_2\handoff.md`
   - `d:\projekt\ARM\.agents\teamwork\explorer_survey_3\handoff.md`
3. MANDATORY INTEGRITY WARNING:
   > DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## File Ownership
You EXCLUSIVELY own:
- `d:\projekt\ARM\scripts\verify_monograph.py`
- `d:\projekt\ARM\TEST_INFRA.md`
- `d:\projekt\ARM\TEST_READY.md`
Do NOT edit chapter files or compilation pipeline files.

## Detailed Requirements
Create an independent, opaque-box, requirement-driven verification suite:
1. `TEST_INFRA.md`: Document test philosophy, feature inventory coverage (Tiers 1-4 methodology: Category-Partition, Boundary Value Analysis, Pairwise Combinations, Real-World Workload Scenarios), runner invocations, pass/fail semantics.
2. `scripts/verify_monograph.py`: An automated Python script that strictly verifies:
   - Check 1: Chapter completeness. Checks that all chapter files (`00_front_matter.md` to `08_appendices.md` covering Sections I through VII) exist, are non-empty, and contain substantive academic content (>10,000 characters each).
   - Check 2: 4-Tier BOM presence. Verifies that Tier A, Tier B, Tier C, and Tier D are all explicitly represented with numeric cost tables in RUB.
   - Check 3: BOM Arithmetic Consistency. Parses and re-calculates all BOM tables (Min, Avg, Max costs and batch totals for 10, 50, 200 units) to guarantee that Subtotals == Sum of Components, and Batch Totals == Unit Cost × Batch Size. Any mathematical mismatch fails the test.
   - Check 4: LaTeX Math Syntax. Validates that inline ($...$) and display ($$...$$) math delimiters are strictly balanced and syntactically valid.
   - Check 5: Pedagogical Completeness. Validates that all 10 laboratory experiments are articulated with experimental objectives and competencies.
   - Check 6: Regulatory Fidelity. Validates the presence and proper Russian terminology for 44-FZ, 223-FZ, Decrees 719 & 878, FASIE Student Startup & Start-1, Priority 2030, and PISH.
   - Check 7: Visual Assets. Verifies that all Markdown figure tags `![...](URL)` contain valid, reachable URLs.
   - Check 8: PDF Compilation Execution & Integrity. Runs the build script and verifies that `output/ROBOI_Scientific_Monograph_Dossier.pdf` is generated, non-empty, and satisfies minimum page count requirements (>=80 pages).
   - Returns exit code 0 on complete pass, non-zero on any failure.
3. Once the verification harness is implemented and passing, publish `TEST_READY.md` at project root with full coverage summary.

Maintain `progress.md` with your timestamp and status.
Write your final report to `handoff.md` and message the orchestrator when finished.

## 2026-11-02T10:49:56Z
[Message] timestamp=2026-11-02T10:49:56Z sender=d908d5d1-f1ea-4f29-b4e8-eecacd50557e priority=MESSAGE_PRIORITY_HIGH
You are `worker_e2e` (`teamwork_test_writer`).
Working directory: `d:\projekt\ARM\.agents\teamwork\worker_e2e`.
You MUST read `d:\projekt\ARM\.agents\teamwork\ORIGINAL_REQUEST.md` and `d:\projekt\ARM\.agents\teamwork\worker_e2e\DISPATCH.md` first.

MANDATORY INTEGRITY WARNING:
> DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Scope & File Ownership:
Exclusively implement and verify:
- `d:\projekt\ARM\scripts\verify_monograph.py`
- `d:\projekt\ARM\TEST_INFRA.md`
- `d:\projekt\ARM\TEST_READY.md`

Requirements:
Create an independent, opaque-box, requirement-driven verification suite:
1. `TEST_INFRA.md`: Document test philosophy, feature inventory coverage (Tiers 1-4 methodology: Category-Partition, Boundary Value Analysis, Pairwise Combinations, Real-World Workload Scenarios), runner invocations, pass/fail semantics.
2. `scripts/verify_monograph.py`: An automated Python script that strictly verifies:
   - Check 1: Chapter completeness. Checks that all chapter files (`00_front_matter.md` to `08_appendices.md` covering Sections I through VII) exist, are non-empty, and contain substantive academic content (>10,000 characters each).
   - Check 2: 4-Tier BOM presence. Verifies that Tier A, Tier B, Tier C, and Tier D are all explicitly represented with numeric cost tables in RUB.
   - Check 3: BOM Arithmetic Consistency. Parses and re-calculates all BOM tables (Min, Avg, Max costs and batch totals for 10, 50, 200 units) to guarantee that Subtotals == Sum of Components, and Batch Totals == Unit Cost × Batch Size. Any mathematical mismatch fails the test.
   - Check 4: LaTeX Math Syntax. Validates that inline ($...$) and display ($$...$$) math delimiters are strictly balanced and syntactically valid.
   - Check 5: Pedagogical Completeness. Validates that all 10 laboratory experiments are articulated with experimental objectives and competencies.
   - Check 6: Regulatory Fidelity. Validates the presence and proper Russian terminology for 44-FZ, 223-FZ, Decrees 719 & 878, FASIE Student Startup & Start-1, Priority 2030, and PISH.
   - Check 7: Visual Assets. Verifies that all Markdown figure tags `![...](URL)` contain valid, reachable URLs.
   - Check 8: PDF Compilation Execution & Integrity. Runs the build script and verifies that `output/ROBOI_Scientific_Monograph_Dossier.pdf` is generated, non-empty, and satisfies minimum page count requirements (>=80 pages).
   - Returns exit code 0 on complete pass, non-zero on any failure.
3. Once the verification harness is implemented and passing, publish `TEST_READY.md` at project root with full coverage summary.

Maintain `progress.md` with status and timestamp.
Write final report to `handoff.md` and message orchestrator (`d908d5d1-f1ea-4f29-b4e8-eecacd50557e`) when finished.
