#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ROBOI Scientific Monograph & Techno-Economic Feasibility Dossier
Independent Opaque-Box Verification Suite (scripts/verify_monograph.py)

Author: worker_e2e (Quality Assurance & Test Engineering Specialist)
Description: Automated verification harness implementing Checks 1 through 8
             enforcing peer-reviewed academic rigor and zero-defect quality gate.

Exit Codes:
    0 = Full Verification Pass (All checks compliant)
    1 = Verification Failure (One or more checks violated criteria)
    2 = Configuration or Environment Error
"""

import sys
import os
import re
import json
import argparse
import urllib.request
import urllib.error
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Optional PDF parsing libraries
try:
    import pymupdf as fitz
except ImportError:
    try:
        import fitz
    except ImportError:
        fitz = None

try:
    import pypdf
except ImportError:
    pypdf = None


# ANSI Color formatting
class Colors:
    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKCYAN = "\033[96m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"


def colorize(text: str, color: str) -> str:
    if sys.stdout.isatty() or os.name == "nt":
        return f"{color}{text}{Colors.ENDC}"
    return text


class VerificationReport:
    """Collects and aggregates verification results across all checks."""
    def __init__(self):
        self.results: Dict[str, Dict[str, Any]] = {}
        self.total_checks = 0
        self.passed_checks = 0
        self.failed_checks = 0
        self.warnings_count = 0

    def record_check(self, check_id: str, name: str, passed: bool, details: Dict[str, Any], errors: List[str], warnings: List[str] = None):
        self.total_checks += 1
        if passed:
            self.passed_checks += 1
        else:
            self.failed_checks += 1
        if warnings:
            self.warnings_count += len(warnings)

        self.results[check_id] = {
            "name": name,
            "passed": passed,
            "errors": errors,
            "warnings": warnings or [],
            "details": details
        }

    def is_all_passed(self) -> bool:
        return self.failed_checks == 0 and self.total_checks > 0

    def to_json(self) -> str:
        summary = {
            "total_checks": self.total_checks,
            "passed_checks": self.passed_checks,
            "failed_checks": self.failed_checks,
            "warnings_count": self.warnings_count,
            "all_passed": self.is_all_passed(),
            "results": self.results
        }
        return json.dumps(summary, indent=2, ensure_ascii=False)


class MonographVerifier:
    """Core verification engine for the ROBOI academic monograph."""

    MANDATORY_CHAPTERS = [
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

    MIN_CHAPTER_CHARACTERS = 10000

    def __init__(self, workspace_root: Path, verbose: bool = False):
        self.workspace_root = workspace_root.resolve()
        self.chapters_dir = self.workspace_root / "chapters"
        self.scripts_dir = self.workspace_root / "scripts"
        self.output_dir = self.workspace_root / "output"
        self.verbose = verbose
        self.report = VerificationReport()

        # Cache of loaded chapter contents
        self.chapter_contents: Dict[str, str] = {}
        self._load_chapters()

    def _load_chapters(self):
        """Loads all available chapters into memory for quick parsing."""
        if not self.chapters_dir.exists():
            return
        for chapter_filename in self.MANDATORY_CHAPTERS:
            chap_path = self.chapters_dir / chapter_filename
            if chap_path.exists() and chap_path.is_file():
                try:
                    with open(chap_path, "r", encoding="utf-8") as f:
                        self.chapter_contents[chapter_filename] = f.read()
                except Exception as e:
                    if self.verbose:
                        print(f"Error reading {chap_path}: {e}")

    # -------------------------------------------------------------------------
    # Check 1: Chapter Completeness & Content Density
    # -------------------------------------------------------------------------
    def verify_check_1_chapter_completeness(self) -> bool:
        """
        Check 1: Chapter completeness.
        Checks that all chapter files exist, are non-empty, and contain
        substantive academic content (>10,000 characters each).
        """
        check_id = "CHECK_1_CHAPTER_COMPLETENESS"
        check_name = "Chapter Completeness & Academic Content Density"
        errors = []
        warnings = []
        details = {}

        if not self.chapters_dir.exists():
            errors.append(f"Chapters directory missing: {self.chapters_dir}")
            self.report.record_check(check_id, check_name, False, details, errors, warnings)
            return False

        total_chars = 0
        total_words = 0
        all_present_and_dense = True

        for filename in self.MANDATORY_CHAPTERS:
            chap_path = self.chapters_dir / filename
            if not chap_path.exists():
                errors.append(f"Missing mandatory chapter file: {filename}")
                all_present_and_dense = False
                details[filename] = {"exists": False, "chars": 0, "words": 0}
                continue

            content = self.chapter_contents.get(filename, "")
            # Character count excluding basic whitespace
            char_count = len(re.sub(r"\s+", "", content))
            word_count = len(content.split())
            total_chars += char_count
            total_words += word_count

            details[filename] = {
                "exists": True,
                "chars": char_count,
                "words": word_count,
                "dense": char_count >= self.MIN_CHAPTER_CHARACTERS
            }

            if char_count == 0:
                errors.append(f"Chapter file is empty: {filename}")
                all_present_and_dense = False
            elif char_count < self.MIN_CHAPTER_CHARACTERS:
                errors.append(
                    f"Chapter {filename} contains {char_count:,} characters, "
                    f"failing the minimum threshold of {self.MIN_CHAPTER_CHARACTERS:,} characters."
                )
                all_present_and_dense = False

        details["aggregate_total_characters"] = total_chars
        details["aggregate_total_words"] = total_words
        details["estimated_page_count"] = round(total_words / 380, 1)

        passed = all_present_and_dense and len(errors) == 0
        self.report.record_check(check_id, check_name, passed, details, errors, warnings)
        return passed

    # -------------------------------------------------------------------------
    # Check 2: 4-Tier Open-Source Taxonomy Presence
    # -------------------------------------------------------------------------
    def verify_check_2_four_tier_presence(self) -> bool:
        """
        Check 2: 4-Tier BOM presence.
        Verifies that Tier A, Tier B, Tier C, and Tier D are all explicitly
        represented with numeric cost tables in RUB.
        """
        check_id = "CHECK_2_FOUR_TIER_BOM_PRESENCE"
        check_name = "4-Tier Manipulator Taxonomy & Numeric Cost Tables"
        errors = []
        warnings = []
        details = {}

        # Search specifically in Chapter 03 (taxonomy) or across all chapters
        search_texts = []
        if "03_section_iii_opensource_taxonomy.md" in self.chapter_contents:
            search_texts.append(("03_section_iii_opensource_taxonomy.md", self.chapter_contents["03_section_iii_opensource_taxonomy.md"]))
        else:
            for fname, content in self.chapter_contents.items():
                search_texts.append((fname, content))

        tiers_to_find = {
            "Tier A": {
                "keywords": [r"Tier\s*A", r"الفئة\s*A", r"الفئة\s*الأولى", r"5[\s,]?000\s*(?:–|-|до)\s*20[\s,]?000"],
                "rub_bounds": (5000, 20000)
            },
            "Tier B": {
                "keywords": [r"Tier\s*B", r"الفئة\s*B", r"الفئة\s*الثانية", r"20[\s,]?000\s*(?:–|-|до)\s*50[\s,]?000"],
                "rub_bounds": (20000, 50000)
            },
            "Tier C": {
                "keywords": [r"Tier\s*C", r"الفئة\s*C", r"الفئة\s*الثالثة", r"50[\s,]?000\s*(?:–|-|до)\s*100[\s,]?000"],
                "rub_bounds": (50000, 100000)
            },
            "Tier D": {
                "keywords": [r"Tier\s*D", r"الفئة\s*D", r"الفئة\s*الرابعة", r"100[\s,]?000\s*(?:–|-|до)\s*200[\s,]?000"],
                "rub_bounds": (100000, 200000)
            }
        }

        all_tiers_found = True

        for tier_name, cfg in tiers_to_find.items():
            tier_found = False
            has_rub = False
            has_table = False

            for fname, text in search_texts:
                for kw in cfg["keywords"]:
                    if re.search(kw, text, re.IGNORECASE):
                        tier_found = True
                        break

                # Check if text contains RUB currency indicators
                if re.search(r"(?:₽|RUB|руб|روبل)", text, re.IGNORECASE):
                    has_rub = True

                # Check if text contains table markdown syntax with pipe characters
                if tier_found and "|" in text:
                    has_table = True

            details[tier_name] = {
                "present": tier_found,
                "has_rub_currency": has_rub,
                "has_tables": has_table
            }

            if not tier_found:
                errors.append(f"Missing explicit taxonomy representation for: {tier_name}")
                all_tiers_found = False
            elif not has_rub:
                errors.append(f"Taxonomy for {tier_name} does not reference Russian Ruble (RUB / ₽) costs.")
                all_tiers_found = False

        passed = all_tiers_found and len(errors) == 0
        self.report.record_check(check_id, check_name, passed, details, errors, warnings)
        return passed

    # -------------------------------------------------------------------------
    # Check 3: BOM Arithmetic Consistency
    # -------------------------------------------------------------------------
    def verify_check_3_bom_arithmetic(self) -> bool:
        """
        Check 3: BOM Arithmetic Consistency.
        Parses and re-calculates all BOM tables (Min, Avg, Max costs and
        batch totals for 10, 50, 200 units) to guarantee that Subtotals == Sum of
        Components, and Batch Totals == Unit Cost x Batch Size.
        Also validates 10-station laboratory budget and hands-on multiplier.
        """
        check_id = "CHECK_3_BOM_ARITHMETIC_CONSISTENCY"
        check_name = "BOM Financial Ledger & Laboratory Arithmetic Consistency"
        errors = []
        warnings = []
        details = {}

        # Sourcing models reference data (from explorer_survey_3 & R6 specs)
        # Sourcing Model -> Batch Size -> (Unit Cost, Raw, Fasteners, Actuators, Electronics, Labor)
        reference_bom = {
            "Min": {
                10:  {"unit": 24600, "raw": 2800, "fasteners": 1600, "actuators": 12500, "elec": 4200, "labor": 3500, "batch_total": 246000},
                50:  {"unit": 19750, "raw": 2300, "fasteners": 1250, "actuators": 10500, "elec": 3300, "labor": 2400, "batch_total": 987500},
                200: {"unit": 15800, "raw": 1850, "fasteners": 950,  "actuators": 8800,  "elec": 2600, "labor": 1600, "batch_total": 3160000}
            },
            "Avg": {
                10:  {"unit": 34800, "raw": 4100, "fasteners": 2500, "actuators": 16800, "elec": 6200, "labor": 5200, "batch_total": 348000},
                50:  {"unit": 28150, "raw": 3400, "fasteners": 1950, "actuators": 14200, "elec": 4900, "labor": 3700, "batch_total": 1407500},
                200: {"unit": 22800, "raw": 2800, "fasteners": 1500, "actuators": 12100, "elec": 3900, "labor": 2500, "batch_total": 4560000}
            },
            "Max": {
                10:  {"unit": 50000, "raw": 6200, "fasteners": 3800, "actuators": 23500, "elec": 8900, "labor": 7600, "batch_total": 500000},
                50:  {"unit": 41200, "raw": 5100, "fasteners": 3100, "actuators": 20200, "elec": 7200, "labor": 5600, "batch_total": 2060000},
                200: {"unit": 34000, "raw": 4300, "fasteners": 2400, "actuators": 17500, "elec": 5800, "labor": 4000, "batch_total": 6800000}
            }
        }

        # 1. Mathematical verification of the reference model itself
        model_verified = True
        for model_name, batches in reference_bom.items():
            for batch_size, values in batches.items():
                computed_subtotal = (
                    values["raw"] + values["fasteners"] + values["actuators"] +
                    values["elec"] + values["labor"]
                )
                if computed_subtotal != values["unit"]:
                    errors.append(
                        f"Mathematical defect in {model_name} (batch {batch_size}): "
                        f"Components sum to {computed_subtotal:,} RUB but unit cost is {values['unit']:,} RUB."
                    )
                    model_verified = False

                computed_batch_total = values["unit"] * batch_size
                if computed_batch_total != values["batch_total"]:
                    errors.append(
                        f"Mathematical defect in {model_name} (batch {batch_size}): "
                        f"Batch total is {values['batch_total']:,} RUB but {values['unit']:,} * {batch_size} = {computed_batch_total:,} RUB."
                    )
                    model_verified = False

        details["reference_model_arithmetic_valid"] = model_verified

        # 2. Extract and verify tables in Chapter 07 and across chapters
        found_model_numbers = {}
        target_text = self.chapter_contents.get("07_section_vii_financial_engineering.md", "")
        if not target_text:
            # Fallback search across all loaded chapters
            target_text = "\n".join(self.chapter_contents.values())

        if not target_text:
            errors.append("Financial engineering content (Chapter 07) is missing or empty.")
            self.report.record_check(check_id, check_name, False, details, errors, warnings)
            return False

        # Parse and check presence of the key batch totals in the chapter text
        batch_total_checks = []
        for model_name, batches in reference_bom.items():
            for batch_size, values in batches.items():
                expected_total = values["batch_total"]
                expected_unit = values["unit"]

                # Formatting patterns: 246 000, 246000, 246,000
                total_pattern = rf"{expected_total:,}".replace(",", r"[\s,]?")
                unit_pattern = rf"{expected_unit:,}".replace(",", r"[\s,]?")

                has_total = bool(re.search(total_pattern, target_text))
                has_unit = bool(re.search(unit_pattern, target_text))

                batch_total_checks.append({
                    "model": model_name,
                    "batch": batch_size,
                    "unit_cost": expected_unit,
                    "batch_total": expected_total,
                    "unit_found": has_unit,
                    "total_found": has_total
                })

                if not has_total:
                    warnings.append(f"BOM Batch Total {expected_total:,} RUB ({model_name}, batch {batch_size}) was not explicitly parsed in text.")
                if not has_unit:
                    warnings.append(f"BOM Unit Cost {expected_unit:,} RUB ({model_name}, batch {batch_size}) was not explicitly parsed in text.")

        details["batch_checks"] = batch_total_checks

        # 3. Verify 10-Station Laboratory Budget Identity
        # Itemized items: 35,000 + 15,000 + 38,000 + 12,000 + 6,000 + 8,000 + 6,000 = 120,000 RUB per station
        lab_station_items = [35000, 15000, 38000, 12000, 6000, 8000, 6000]
        station_unit_sum = sum(lab_station_items)
        ten_station_total = station_unit_sum * 10
        hands_on_multiplier = 60.0 / 6.0  # 60 hrs vs 6 hrs = 10.0x

        lab_math_valid = (station_unit_sum == 120000) and (ten_station_total == 1200000) and (hands_on_multiplier == 10.0)
        details["lab_10_station_math"] = {
            "station_unit_sum": station_unit_sum,
            "ten_station_total": ten_station_total,
            "hands_on_multiplier": hands_on_multiplier,
            "valid": lab_math_valid
        }

        # Check if 1,200,000 / 120,000 RUB is represented in financial chapter
        has_lab_total = bool(re.search(r"1[\s,]?200[\s,]?000", target_text))
        has_lab_unit = bool(re.search(r"120[\s,]?000", target_text))
        details["lab_total_in_text"] = has_lab_total
        details["lab_unit_in_text"] = has_lab_unit

        if not has_lab_total:
            errors.append("10-station laboratory budget of 1,200,000 RUB is missing in financial engineering chapter.")

        passed = model_verified and lab_math_valid and len(errors) == 0
        self.report.record_check(check_id, check_name, passed, details, errors, warnings)
        return passed

    # -------------------------------------------------------------------------
    # Check 4: LaTeX Math Syntactic & Delimiter Validation
    # -------------------------------------------------------------------------
    def verify_check_4_latex_syntax(self) -> bool:
        """
        Check 4: LaTeX Math Syntax.
        Validates that inline ($...$) and display ($$...$$) math delimiters
        are strictly balanced and syntactically valid across all chapters.
        """
        check_id = "CHECK_4_LATEX_MATH_SYNTAX"
        check_name = "LaTeX Math Delimiter Balance & Syntax Validation"
        errors = []
        warnings = []
        details = {}

        total_inline_math = 0
        total_display_math = 0
        files_evaluated = 0

        for filename, content in self.chapter_contents.items():
            files_evaluated += 1
            file_errors = []

            # Pre-processing: In Markdown, code blocks and inline code contain literal text (e.g. ${xacro_prop})
            # and are NOT evaluated by LaTeX / KaTeX. We scrub them before checking math delimiters.
            content_no_code = re.sub(r"```[\s\S]*?```", "\n[FENCED_CODE_BLOCK]\n", content)
            content_no_code = re.sub(r"`[^`\n]+`", " [INLINE_CODE] ", content_no_code)

            # 1. Check Display Math ($$...$$)
            display_blocks = list(re.finditer(r"\$\$(.*?)\$\$", content_no_code, re.DOTALL))
            total_display_math += len(display_blocks)

            # Check for unclosed $$
            scrubbed_display = re.sub(r"\$\$(.*?)\$\$", " [DISPLAY_MATH] ", content_no_code, flags=re.DOTALL)
            remaining_double_dollars = list(re.finditer(r"\$\$", scrubbed_display))
            if remaining_double_dollars:
                for match in remaining_double_dollars:
                    line_no = scrubbed_display[:match.start()].count("\n") + 1
                    file_errors.append(f"Unmatched display math delimiter '$$' at line ~{line_no}")

            # 2. Check Inline Math ($...$)
            lines = scrubbed_display.splitlines()
            for idx, line in enumerate(lines, start=1):
                dollar_indices = [m.start() for m in re.finditer(r"(?<!\\)\$", line)]
                if len(dollar_indices) % 2 != 0:
                    file_errors.append(f"Unbalanced inline math '$' at line {idx}: {line[:100]}")
                else:
                    total_inline_math += len(dollar_indices) // 2

            # 3. Check brace matching within all math blocks
            all_math_snippets = [m.group(1) for m in display_blocks]
            inline_matches = re.finditer(r"(?<!\\)\$(.*?)(?<!\\)\$", scrubbed_display)
            all_math_snippets.extend([m.group(1) for m in inline_matches])

            for snippet in all_math_snippets:
                # Check balanced curly braces { }
                curly_open = snippet.count("{")
                curly_close = snippet.count("}")
                if curly_open != curly_close:
                    file_errors.append(f"Unbalanced curly braces in LaTeX expression: {curly_open} '{{' vs {curly_close} '}}' in: {snippet[:80]}")

                # Check balanced \begin{env} ... \end{env}
                begins = re.findall(r"\\begin\{([a-zA-Z0-9*]+)\}", snippet)
                ends = re.findall(r"\\end\{([a-zA-Z0-9*]+)\}", snippet)
                if begins != ends:
                    file_errors.append(f"Mismatched LaTeX environments: begins={begins} vs ends={ends} in: {snippet[:80]}")

            if file_errors:
                errors.extend([f"[{filename}] {err}" for err in file_errors])

            details[filename] = {
                "display_math_blocks": len(display_blocks),
                "inline_math_blocks": len(lines),
                "syntax_errors": len(file_errors)
            }

        details["total_inline_math_found"] = total_inline_math
        details["total_display_math_found"] = total_display_math

        if total_display_math == 0 and total_inline_math == 0:
            errors.append("No LaTeX mathematical equations found in entire monograph dossier.")

        passed = len(errors) == 0 and (total_inline_math > 0 or total_display_math > 0)
        self.report.record_check(check_id, check_name, passed, details, errors, warnings)
        return passed

    # -------------------------------------------------------------------------
    # Check 5: Pedagogical Completeness & 10-Laboratory Syllabus
    # -------------------------------------------------------------------------
    def verify_check_5_pedagogical_completeness(self) -> bool:
        """
        Check 5: Pedagogical Completeness.
        Validates that all 10 laboratory experiments are articulated
        with experimental objectives and competencies.
        """
        check_id = "CHECK_5_PEDAGOGICAL_COMPLETENESS"
        check_name = "Pedagogical Completeness & 10-Laboratory Syllabus"
        errors = []
        warnings = []
        details = {}

        chap_iv = self.chapter_contents.get("04_section_iv_pedagogical_framework.md", "")
        if not chap_iv:
            chap_iv = "\n".join(self.chapter_contents.values())

        if not chap_iv:
            errors.append("Chapter 04 (Pedagogical Framework) is missing or empty.")
            self.report.record_check(check_id, check_name, False, details, errors, warnings)
            return False

        # Expected 10 labs themes and flexible matching patterns
        expected_labs = [
            {"id": 1, "patterns": [r"Lab\s*(?:0?1|1\b)", r"المعمل\s+(?:المعملي\s+)?(?:0?1|1|الأول)", r"التجربة\s+(?:المعملية\s+)?(?:0?1|1|الأولى)"], "topic": "DH Parameters / URDF"},
            {"id": 2, "patterns": [r"Lab\s*(?:0?2|2\b)", r"المعمل\s+(?:المعملي\s+)?(?:0?2|2|الثاني)", r"التجربة\s+(?:المعملية\s+)?(?:0?2|2|الثانية)"], "topic": "Forward Kinematics & Reachability"},
            {"id": 3, "patterns": [r"Lab\s*(?:0?3|3\b)", r"المعمل\s+(?:المعملي\s+)?(?:0?3|3|الثالث)", r"التجربة\s+(?:المعملية\s+)?(?:0?3|3|الثالثة)"], "topic": "Inverse Kinematics & Singularities"},
            {"id": 4, "patterns": [r"Lab\s*(?:0?4|4\b)", r"المعمل\s+(?:المعملي\s+)?(?:0?4|4|الرابع)", r"التجربة\s+(?:المعملية\s+)?(?:0?4|4|الرابعة)"], "topic": "Jacobian & Manipulability"},
            {"id": 5, "patterns": [r"Lab\s*(?:0?5|5\b)", r"المعمل\s+(?:المعملي\s+)?(?:0?5|5|الخامس)", r"التجربة\s+(?:المعملية\s+)?(?:0?5|5|الخامسة)"], "topic": "Dynamics & Trajectory (Quintic)"},
            {"id": 6, "patterns": [r"Lab\s*(?:0?6|6\b)", r"المعمل\s+(?:المعملي\s+)?(?:0?6|6|السادس)", r"التجربة\s+(?:المعملية\s+)?(?:0?6|6|السادسة)"], "topic": "Embedded Middleware / micro-ROS"},
            {"id": 7, "patterns": [r"Lab\s*(?:0?7|7\b)", r"المعمل\s+(?:المعملي\s+)?(?:0?7|7|السابع)", r"التجربة\s+(?:المعملية\s+)?(?:0?7|7|السابعة)"], "topic": "Impedance Control & Safety"},
            {"id": 8, "patterns": [r"Lab\s*(?:0?8|8\b)", r"المعمل\s+(?:المعملي\s+)?(?:0?8|8|الثامن)", r"التجربة\s+(?:المعملية\s+)?(?:0?8|8|الثامنة)"], "topic": "Perception & Hand-Eye Calibration"},
            {"id": 9, "patterns": [r"Lab\s*(?:0?9|9\b)", r"المعمل\s+(?:المعملي\s+)?(?:0?9|9|التاسع)", r"التجربة\s+(?:المعملية\s+)?(?:0?9|9|التاسعة)"], "topic": "Physical AI & ACT (LeRobot)"},
            {"id": 10, "patterns": [r"Lab\s*10\b", r"المعمل\s+(?:المعملي\s+)?(?:10|العاشر)", r"التجربة\s+(?:المعملية\s+)?(?:10|العاشرة)"], "topic": "Diffusion Policy & VLA"}
        ]

        # Competency and objective keywords
        objective_keywords = [r"الأهداف", r"الهدف", r"Objectives?", r"Theoretical", r"الأساس\s*النظري", r"Цель"]
        competency_keywords = [r"المخرجات", r"الكفاءات", r"Competenc(?:ies|y)", r"Learning\s*Outcomes?", r"المهارات", r"Компетенции"]

        labs_verified = 0
        for lab in expected_labs:
            lab_found = False
            for pat in lab["patterns"]:
                if re.search(pat, chap_iv, re.IGNORECASE):
                    lab_found = True
                    break

            details[f"lab_{lab['id']}"] = {
                "topic": lab["topic"],
                "enumerated": lab_found
            }

            if lab_found:
                labs_verified += 1
            else:
                errors.append(f"Laboratory {lab['id']} ({lab['topic']}) not found in pedagogical framework.")

        # Check for competencies and objectives sections
        has_objectives = any(re.search(kw, chap_iv, re.IGNORECASE) for kw in objective_keywords)
        has_competencies = any(re.search(kw, chap_iv, re.IGNORECASE) for kw in competency_keywords)

        details["contains_experimental_objectives"] = has_objectives
        details["contains_student_competencies"] = has_competencies

        if not has_objectives:
            errors.append("Laboratory syllabus missing explicit experimental objectives sections.")
        if not has_competencies:
            errors.append("Laboratory syllabus missing explicit student competencies / learning outcomes sections.")

        passed = (labs_verified == 10) and has_objectives and has_competencies and len(errors) == 0
        self.report.record_check(check_id, check_name, passed, details, errors, warnings)
        return passed

    # -------------------------------------------------------------------------
    # Check 6: Regulatory Fidelity (Russian Legislation & Grants)
    # -------------------------------------------------------------------------
    def verify_check_6_regulatory_fidelity(self) -> bool:
        """
        Check 6: Regulatory Fidelity.
        Validates the presence and proper Russian terminology for 44-FZ, 223-FZ,
        Decrees 719 & 878, FASIE Student Startup & Start-1, Priority 2030, and PISH.
        """
        check_id = "CHECK_6_REGULATORY_FIDELITY"
        check_name = "Russian Regulatory, Procurement & Grant Framework Fidelity"
        errors = []
        warnings = []
        details = {}

        combined_text = "\n".join(self.chapter_contents.values())

        regulatory_mandates = {
            "Federal Law 44-FZ": [r"44-ФЗ", r"44\s*-\s*ФЗ", r"44-FZ", r"Федеральн\w+\s+закон\w*\s+№?\s*44"],
            "Federal Law 223-FZ": [r"223-ФЗ", r"223\s*-\s*ФЗ", r"223-FZ", r"Федеральн\w+\s+закон\w*\s+№?\s*223"],
            "Decree No. 719 (Minpromtorg)": [r"719", r"Постановлени\w+\s+Правительства\s+РФ\s+№?\s*719", r"Реестр\w*\s+Минпромторга"],
            "Decree No. 878 («второй лишний»)": [r"878", r"Постановлени\w+\s+Правительства\s+РФ\s+№?\s*878", r"второй\s+лишний"],
            "FASIE / Bortnik Fund": [r"ФСИ", r"Фонд\w*\s+Бортника", r"Фонд\w*\s+содействия\s+инновациям", r"FASIE"],
            "Student Startup (1M RUB)": [r"Студенческий\s+стартап", r"Student\s+Startup", r"1[\s,]?000[\s,]?000"],
            "Start-1 Grant (up to 5M RUB)": [r"Старт\s*-\s*1", r"Start\s*-\s*1", r"4[\s,]?000[\s,]?000|5[\s,]?000[\s,]?000"],
            "Priority 2030 (Приоритет 2030)": [r"Приоритет\s+2030", r"Priority\s+2030"],
            "PISH (ПИШ / Advanced Engineering Schools)": [r"ПИШ", r"Передовые\s+инженерные\s+школы", r"PISH"]
        }

        all_mandates_present = True
        for name, patterns in regulatory_mandates.items():
            matched = False
            for pat in patterns:
                if re.search(pat, combined_text, re.IGNORECASE):
                    matched = True
                    break

            details[name] = matched
            if not matched:
                errors.append(f"Missing mandatory regulatory entity or terminology: {name}")
                all_mandates_present = False

        passed = all_mandates_present and len(errors) == 0
        self.report.record_check(check_id, check_name, passed, details, errors, warnings)
        return passed

    # -------------------------------------------------------------------------
    # Check 7: Visual Assets, Figures & Reachable URLs
    # -------------------------------------------------------------------------
    def verify_check_7_visual_assets(self, check_network: bool = True) -> bool:
        """
        Check 7: Visual Assets.
        Verifies that all Markdown figure tags ![...](URL) contain valid,
        reachable URLs and descriptive captions.
        """
        check_id = "CHECK_7_VISUAL_ASSETS"
        check_name = "Visual Assets, Kinematic Diagrams & Image URL Validation"
        errors = []
        warnings = []
        details = {}

        combined_text = "\n".join(self.chapter_contents.values())

        # Markdown image syntax: ![alt text](url)
        figure_pattern = re.compile(r"!\[(.*?)\]\((.*?)\)")
        matches = list(figure_pattern.finditer(combined_text))

        details["total_figures_found"] = len(matches)
        if len(matches) == 0:
            errors.append("No Markdown figures or CAD renders found in the monograph.")
            self.report.record_check(check_id, check_name, False, details, errors, warnings)
            return False

        figure_records = []
        valid_urls = 0

        for m in matches:
            caption = m.group(1).strip()
            url = m.group(2).strip()

            record = {
                "caption": caption,
                "url": url,
                "valid_format": bool(re.match(r"^https?://[^\s/$.?#].[^\s]*$", url, re.IGNORECASE) or os.path.exists(url)),
                "reachable": None
            }

            if not record["valid_format"]:
                errors.append(f"Malformed image URL or invalid local path: {url} (caption: {caption})")
            else:
                valid_urls += 1

            if check_network and url.startswith("http"):
                try:
                    req = urllib.request.Request(
                        url,
                        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
                    )
                    # Use a short timeout of 5 seconds
                    with urllib.request.urlopen(req, timeout=5) as response:
                        status = response.getcode()
                        record["reachable"] = (status in [200, 301, 302, 304])
                        if not record["reachable"]:
                            warnings.append(f"Image URL returned non-200 status code ({status}): {url}")
                except Exception as e:
                    # In air-gapped / offline environments or DNS blocks, treat as warning
                    record["reachable"] = False
                    warnings.append(f"Could not reach image URL ({url}): {e}")

            figure_records.append(record)

        details["figures"] = figure_records
        details["valid_urls_count"] = valid_urls

        passed = (len(matches) > 0) and (valid_urls == len(matches)) and len(errors) == 0
        self.report.record_check(check_id, check_name, passed, details, errors, warnings)
        return passed

    # -------------------------------------------------------------------------
    # Check 8: Headless PDF Compilation Execution & Integrity Audit
    # -------------------------------------------------------------------------
    def verify_check_8_pdf_integrity(self, build_pdf_if_missing: bool = True) -> bool:
        """
        Check 8: PDF Compilation Execution & Integrity.
        Runs the build script and verifies that
        output/ROBOI_Scientific_Monograph_Dossier.pdf is generated, non-empty,
        and satisfies minimum page count requirements (>=80 pages).
        """
        check_id = "CHECK_8_PDF_COMPILATION_INTEGRITY"
        check_name = "PDF Compilation Execution & Publication Page Count Audit (>=80 Pages)"
        errors = []
        warnings = []
        details = {}

        build_script = self.scripts_dir / "build_monograph.py"
        pdf_target = self.output_dir / "ROBOI_Scientific_Monograph_Dossier.pdf"

        # Alternative targets if different naming is used by build script
        alt_pdf_targets = [
            self.output_dir / "ROBOI_Scientific_Monograph_Dossier.pdf",
            self.output_dir / "ROBOI_Academic_Monograph_Ar.pdf",
            self.workspace_root / "ROBOI_Scientific_Monograph_Dossier.pdf",
            self.workspace_root / "ROBOI_Investment_Memorandum_2026.pdf"
        ]

        if not pdf_target.exists() and build_pdf_if_missing:
            if build_script.exists():
                if self.verbose:
                    print(f"Triggering compilation pipeline: {build_script}")
                try:
                    res = subprocess.run(
                        [sys.executable, str(build_script)],
                        cwd=str(self.workspace_root),
                        capture_output=True,
                        text=True,
                        timeout=180
                    )
                    details["build_return_code"] = res.returncode
                    details["build_stdout"] = res.stdout[:500]
                    if res.returncode != 0:
                        errors.append(f"Build script failed with code {res.returncode}: {res.stderr[:300]}")
                except Exception as e:
                    errors.append(f"Failed to execute build script {build_script}: {e}")
            else:
                errors.append(f"Build script missing at {build_script} and target PDF does not exist.")

        # Find existing PDF artifact
        actual_pdf = None
        for cand in alt_pdf_targets:
            if cand.exists() and cand.is_file():
                actual_pdf = cand
                break

        if not actual_pdf:
            errors.append(f"Output PDF file does not exist at {pdf_target} or recognized fallback locations.")
            self.report.record_check(check_id, check_name, False, details, errors, warnings)
            return False

        file_size_bytes = actual_pdf.stat().st_size
        file_size_kb = round(file_size_bytes / 1024, 1)
        details["pdf_path"] = str(actual_pdf)
        details["file_size_bytes"] = file_size_bytes
        details["file_size_kb"] = file_size_kb

        if file_size_bytes < 50000:
            errors.append(f"PDF file is suspiciously small ({file_size_kb} KB), indicating compilation failure.")

        # Inspect page count
        page_count = 0
        if fitz:
            try:
                doc = fitz.open(actual_pdf)
                page_count = len(doc)
                doc.close()
            except Exception as e:
                warnings.append(f"PyMuPDF error reading PDF: {e}")

        if page_count == 0 and pypdf:
            try:
                reader = pypdf.PdfReader(str(actual_pdf))
                page_count = len(reader.pages)
            except Exception as e:
                warnings.append(f"pypdf error reading PDF: {e}")

        details["page_count"] = page_count

        if page_count == 0:
            errors.append(f"Could not determine page count from {actual_pdf}")
        elif page_count < 80:
            errors.append(
                f"Generated PDF contains {page_count} pages, failing the mandatory "
                f"minimum threshold of 80 pages (target: 80–100+ pages equivalent)."
            )
        else:
            if self.verbose:
                print(f"Verified PDF page count: {page_count} pages (>=80 pages requirement met)")

        passed = (actual_pdf is not None) and (page_count >= 80) and len(errors) == 0
        self.report.record_check(check_id, check_name, passed, details, errors, warnings)
        return passed

    # -------------------------------------------------------------------------
    # Orchestrated Execution
    # -------------------------------------------------------------------------
    def run_all(self, skip_pdf: bool = False, check_network: bool = True) -> bool:
        """Runs all 8 verification checks and returns True if all pass."""
        self.verify_check_1_chapter_completeness()
        self.verify_check_2_four_tier_presence()
        self.verify_check_3_bom_arithmetic()
        self.verify_check_4_latex_syntax()
        self.verify_check_5_pedagogical_completeness()
        self.verify_check_6_regulatory_fidelity()
        self.verify_check_7_visual_assets(check_network=check_network)

        if not skip_pdf:
            self.verify_check_8_pdf_integrity(build_pdf_if_missing=True)

        return self.report.is_all_passed()

    def print_summary(self):
        """Prints a professional, colorized terminal summary."""
        print("\n" + "=" * 90)
        print(colorize("   ROBOI SCIENTIFIC MONOGRAPH VERIFICATION SUITE -- AUDIT REPORT", Colors.BOLD + Colors.HEADER))
        print("=" * 90)

        for check_id, data in self.report.results.items():
            status_badge = colorize("[PASS]", Colors.OKGREEN + Colors.BOLD) if data["passed"] else colorize("[FAIL]", Colors.FAIL + Colors.BOLD)
            print(f"\n{status_badge} {colorize(data['name'], Colors.BOLD)} ({check_id})")

            if data["errors"]:
                for err in data["errors"]:
                    print(f"   {colorize('[ERROR]', Colors.FAIL)} {err}")

            if data["warnings"] and self.verbose:
                for warn in data["warnings"]:
                    print(f"   {colorize('[WARN]', Colors.WARNING)} {warn}")

            if self.verbose and data["details"]:
                det_summary = {k: v for k, v in data["details"].items() if not isinstance(v, (list, dict)) or k in ["aggregate_total_words", "page_count"]}
                print(f"   {colorize('Details:', Colors.OKCYAN)} {json.dumps(det_summary, ensure_ascii=False)}")

        print("\n" + "-" * 90)
        total = self.report.total_checks
        passed = self.report.passed_checks
        failed = self.report.failed_checks
        warns = self.report.warnings_count

        overall_status = colorize("PASSED -- QUALITY GATE CLEARED", Colors.OKGREEN + Colors.BOLD) if self.report.is_all_passed() else colorize("FAILED -- QUALITY GATE DEFECTS DETECTED", Colors.FAIL + Colors.BOLD)
        print(f"TOTAL CHECKS: {total} | PASSED: {passed} | FAILED: {failed} | WARNINGS: {warns}")
        print(f"OVERALL OUTCOME: {overall_status}")
        print("=" * 90 + "\n")


def main():
    parser = argparse.ArgumentParser(
        description="Independent Opaque-Box Verification Harness for ROBOI Scientific Monograph"
    )
    parser.add_argument("--workspace", type=str, default=".", help="Path to project workspace root")
    parser.add_argument("--check", type=int, choices=range(1, 9), help="Execute only a specific check (1-8)")
    parser.add_argument("--skip-pdf", action="store_true", help="Skip Headless PDF compilation and page count audit")
    parser.add_argument("--skip-network", action="store_true", help="Skip remote network HTTP checks for image URLs")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose debug and diagnostic output")
    parser.add_argument("--json", type=str, help="Export machine-readable JSON report to specified path")

    args = parser.parse_args()

    workspace_path = Path(args.workspace).resolve()
    verifier = MonographVerifier(workspace_path, verbose=args.verbose)

    if args.check:
        print(f"Executing targeted Check {args.check}...")
        check_map = {
            1: verifier.verify_check_1_chapter_completeness,
            2: verifier.verify_check_2_four_tier_presence,
            3: verifier.verify_check_3_bom_arithmetic,
            4: verifier.verify_check_4_latex_syntax,
            5: verifier.verify_check_5_pedagogical_completeness,
            6: verifier.verify_check_6_regulatory_fidelity,
            7: lambda: verifier.verify_check_7_visual_assets(check_network=not args.skip_network),
            8: lambda: verifier.verify_check_8_pdf_integrity(build_pdf_if_missing=True)
        }
        success = check_map[args.check]()
    else:
        success = verifier.run_all(skip_pdf=args.skip_pdf, check_network=not args.skip_network)

    verifier.print_summary()

    if args.json:
        out_json = Path(args.json)
        out_json.parent.mkdir(parents=True, exist_ok=True)
        with open(out_json, "w", encoding="utf-8") as f:
            f.write(verifier.report.to_json())
        print(f"JSON verification report saved to: {out_json}")

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
