# SO-101 LeRobot ACT Training Launch Script
# PowerShell wrapper with pre-validated arguments for LeRobot on Windows & RTX 4050

param (
    [int]$Steps = 30000,
    [int]$BatchSize = 8,
    [int]$SaveFreq = 5000,
    [int]$LogFreq = 100,
    [switch]$Resume
)

$V3Dir = (Resolve-Path "$PSScriptRoot/..").Path.Replace("\", "/")
$DatasetDir = "$V3Dir/datasets/so101_pick_place"
if (-not (Test-Path $DatasetDir)) {
    $DatasetDir = "$V3Dir/../datasets/so101_pick_place"
}
$OutputDir = "$V3Dir/outputs/train/act_so101_pick_place"

Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host "      SO-101 LE ROBOT ACT POLICY TRAINING (GPU / CUDA)" -ForegroundColor Cyan
Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host "[*] Dataset:    $DatasetDir"
Write-Host "[*] Output Dir: $OutputDir"
Write-Host "[*] Batch Size: $BatchSize"
Write-Host "[*] Steps:      $Steps"
Write-Host "[*] Precision:  fp16"
Write-Host "================================================================="

$argsList = @(
    "--dataset.repo_id=voidstore/so101_pick_place",
    "--dataset.root=$DatasetDir",
    "--policy.type=act",
    "--policy.push_to_hub=false",
    "--output_dir=$OutputDir",
    "--job_name=act_so101_pick_place",
    "--batch_size=$BatchSize",
    "--steps=$Steps",
    "--save_freq=$SaveFreq",
    "--log_freq=$LogFreq",
    "--save_checkpoint=true",
    "--save_checkpoint_to_hub=false",
    "--trackio.enable=false",
    "--num_workers=0",
    "--accelerator.mixed_precision=fp16"
)

if ($Resume) {
    $argsList += "--resume=true"
}

lerobot-train @argsList
