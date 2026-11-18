"""
Cloud Training Packager and Policy Model Importer for SO-101 Robotics Studio V4.
Prepares datasets for cloud GPU training (Colab, RunPod, Kaggle) and validates imported policy checkpoints.
"""

from __future__ import annotations

import json
import os
import shutil
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .logger import get_logger


class CloudPackager:
    """Manages dataset packaging for cloud training and imported model verification."""

    def __init__(self, root_dir: Optional[Path | str] = None):
        self.logger = get_logger("CloudPackager")
        if root_dir is None:
            self.root_dir = Path(__file__).resolve().parents[1]
        else:
            self.root_dir = Path(root_dir)

        self.exports_dir = self.root_dir / "exports"
        self.models_dir = self.root_dir / "models"
        self.datasets_dir = self.root_dir / "datasets"

        self.exports_dir.mkdir(parents=True, exist_ok=True)
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self.datasets_dir.mkdir(parents=True, exist_ok=True)

    # -------------------------------------------------------------------------
    # 1. Dataset Packaging for Cloud GPUs
    # -------------------------------------------------------------------------

    def package_dataset_to_zip(
        self,
        dataset_path: Path | str,
        output_zip_name: Optional[str] = None
    ) -> Path:
        """
        Zips a recorded dataset folder into V4/exports/<name>.zip excluding temp files.
        Also generates a ready-to-run train_cloud.sh script next to the zip.
        """
        src_path = Path(dataset_path)
        if not src_path.exists():
            raise FileNotFoundError(f"Dataset path does not exist: {src_path}")

        dataset_name = src_path.name
        if output_zip_name is None:
            output_zip_name = f"{dataset_name}.zip"
        elif not output_zip_name.endswith(".zip"):
            output_zip_name = f"{output_zip_name}.zip"

        target_zip = self.exports_dir / output_zip_name
        self.logger.info(f"Packaging dataset {src_path} into {target_zip}...")

        # Ignore patterns
        ignored_extensions = {".tmp", ".pyc", ".git"}
        ignored_dirs = {"__pycache__", ".git", ".pytest_cache"}

        with zipfile.ZipFile(target_zip, "w", zipfile.ZIP_DEFLATED) as zf:
            for root, dirs, files in os.walk(src_path):
                dirs[:] = [d for d in dirs if d not in ignored_dirs]
                for file in files:
                    if any(file.endswith(ext) for ext in ignored_extensions):
                        continue
                    full_file_path = Path(root) / file
                    rel_path = full_file_path.relative_to(src_path.parent)
                    zf.write(full_file_path, arcname=rel_path.as_posix())

        self.logger.info(f"Dataset package created successfully: {target_zip} ({target_zip.stat().st_size / (1024*1024):.2f} MB)")

        # Generate accompanying cloud training script
        self._generate_cloud_train_script(dataset_name)

        return target_zip

    def _generate_cloud_train_script(self, dataset_name: str) -> Path:
        """Generates train_cloud.sh in exports/ with TF32 enabled and AMP disabled for ACT."""
        script_path = self.exports_dir / f"train_{dataset_name}_colab.sh"
        content = f"""#!/usr/bin/env bash
# ==============================================================================
# SO-101 Robotics Studio V4 - Cloud GPU Training Script (Google Colab / RunPod)
# ==============================================================================
set -e

echo "[1/4] Installing LeRobot and dependencies..."
pip install --upgrade pip
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu124
pip install "lerobot>=0.7.0"

echo "[2/4] Unpacking dataset..."
unzip -q {dataset_name}.zip -d datasets/

echo "[3/4] Enabling TF32 and Training LeRobot ACT Policy..."
# Note: --policy.use_amp=false is mandatory to prevent NaN loss on ACT!
python3 -c "import torch; torch.set_float32_matmul_precision('high'); import os; os.system('''
lerobot-train \\
  --dataset.repo_id=voidstore/{dataset_name} \\
  --dataset.root=datasets/{dataset_name} \\
  --policy.type=act \\
  --policy.use_amp=false \\
  --policy.push_to_hub=false \\
  --output_dir=outputs/train/act_{dataset_name} \\
  --job_name=act_{dataset_name} \\
  --batch_size=8 \\
  --steps=20000 \\
  --save_freq=5000 \\
  --log_freq=100 \\
  --save_checkpoint=true \\
  --save_checkpoint_to_hub=false \\
  --trackio.enable=false
''')"

echo "[4/4] Training finished! Checkpoints stored in outputs/train/act_{dataset_name}/checkpoints/last/pretrained_model"
(cd outputs/train/act_{dataset_name}/checkpoints/last/pretrained_model && zip -r ../../../../../trained_model_{dataset_name}.zip .) || zip -r trained_model_{dataset_name}.zip outputs/train/act_{dataset_name}/checkpoints/last/pretrained_model
echo "[OK] Ready for download: trained_model_{dataset_name}.zip"
"""
        script_path.write_text(content, encoding="utf-8")
        return script_path

    # -------------------------------------------------------------------------
    # 2. Policy Model Importer & Validator
    # -------------------------------------------------------------------------

    def validate_policy_directory(self, dir_path: Path | str) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Validates if directory contains a functional LeRobot policy checkpoint.
        Checks for config.json (or pretrained_model/config.json) and weight files,
        searching recursively if nested inside arbitrary subfolders.
        """
        p = Path(dir_path)
        if not p.exists() or not p.is_dir():
            return False, f"Directory does not exist: {p}", {}

        target_dir = p
        # If immediate directory does not have config.json, search subdirectories
        if not (target_dir / "config.json").exists():
            candidates = [
                target_dir / "pretrained_model",
                target_dir / "checkpoints" / "last" / "pretrained_model",
            ]
            found = False
            for cand in candidates:
                if cand.is_dir() and (cand / "config.json").exists():
                    target_dir = cand
                    found = True
                    break

            # If not in standard subdirectories, recursively search for config.json with weights
            if not found:
                for cand_file in target_dir.rglob("config.json"):
                    cand_dir = cand_file.parent
                    has_weights = (
                        (cand_dir / "model.safetensors").exists()
                        or (cand_dir / "pytorch_model.bin").exists()
                        or any(cand_dir.glob("*.safetensors"))
                        or any(cand_dir.glob("*.bin"))
                    )
                    if has_weights:
                        target_dir = cand_dir
                        found = True
                        break

        config_file = target_dir / "config.json"
        if not config_file.exists():
            return False, f"Missing config.json in {target_dir}", {}

        try:
            config_data = json.loads(config_file.read_text(encoding="utf-8"))
        except Exception as e:
            return False, f"Malformed config.json in {target_dir}: {e}", {}

        # Look for weights (safetensors or pytorch_model.bin)
        weights_found = (
            (target_dir / "model.safetensors").exists()
            or (target_dir / "pytorch_model.bin").exists()
            or any(target_dir.glob("*.safetensors"))
            or any(target_dir.glob("*.bin"))
        )

        if not weights_found:
            return False, f"No model weights found (expected model.safetensors or .bin) in {target_dir}", config_data

        return True, "Valid LeRobot policy checkpoint", {
            "resolved_path": str(target_dir),
            "config": config_data,
            "policy_type": config_data.get("type", config_data.get("policy", {}).get("type", "act")),
        }

    def import_policy(
        self,
        source_path: Path | str,
        dest_name: Optional[str] = None
    ) -> Tuple[bool, str, Optional[Path]]:
        """
        Imports a policy checkpoint folder or zip file into V4/models/<dest_name>.
        Validates integrity before completing import.
        """
        src = Path(source_path)
        if not src.exists():
            return False, f"Source path does not exist: {src}", None

        # Handle zip file input
        if src.is_file() and src.suffix.lower() == ".zip":
            if dest_name is None:
                dest_name = src.stem

            extract_target = self.models_dir / dest_name
            if extract_target.exists():
                shutil.rmtree(extract_target)
            extract_target.mkdir(parents=True, exist_ok=True)

            try:
                with zipfile.ZipFile(src, "r") as zf:
                    zf.extractall(extract_target)
            except Exception as e:
                return False, f"Failed to unzip model archive: {e}", None

            valid, msg, meta = self.validate_policy_directory(extract_target)
            if not valid:
                return False, f"Imported archive is not a valid policy: {msg}", None

            resolved = Path(meta.get("resolved_path", extract_target))
            # If resolved path is nested inside extract_target, flatten it into extract_target root
            if resolved != extract_target and resolved.is_relative_to(extract_target):
                temp_stage = self.models_dir / f"__stage_{dest_name}"
                if temp_stage.exists():
                    shutil.rmtree(temp_stage)
                shutil.copytree(resolved, temp_stage)
                shutil.rmtree(extract_target)
                temp_stage.rename(extract_target)
                resolved = extract_target

            self.logger.info(f"Imported policy archive into {resolved}")
            return True, "Policy successfully imported and validated", resolved

        # Handle directory input
        elif src.is_dir():
            valid, msg, meta = self.validate_policy_directory(src)
            if not valid:
                return False, f"Directory is not a valid policy checkpoint: {msg}", None

            resolved_src = Path(meta.get("resolved_path", src))
            if dest_name is None:
                dest_name = resolved_src.name if resolved_src.name != "pretrained_model" else src.name

            target_dir = self.models_dir / dest_name
            if target_dir.exists():
                shutil.rmtree(target_dir)

            shutil.copytree(resolved_src, target_dir)
            self.logger.info(f"Copied policy checkpoint to {target_dir}")
            return True, "Policy successfully copied and validated", target_dir

        return False, f"Unsupported source type: {src}", None

    def list_available_models(self) -> List[Dict[str, Any]]:
        """Scans V4/models and V4/outputs/train for valid policy checkpoints."""
        models: List[Dict[str, Any]] = []

        scan_dirs = [self.models_dir, self.root_dir / "outputs" / "train"]
        for sdir in scan_dirs:
            if not sdir.exists():
                continue
            for item in sdir.iterdir():
                if item.is_dir():
                    valid, _, meta = self.validate_policy_directory(item)
                    if valid:
                        models.append({
                            "name": item.name,
                            "path": meta.get("resolved_path", str(item)),
                            "type": meta.get("policy_type", "act"),
                        })

        return models
