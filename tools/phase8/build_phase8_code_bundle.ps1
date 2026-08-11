$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "../..")).Path
$kernelRoot = Join-Path $repoRoot "kaggle_pipeline/phase8_kernel"
$bundlePath = Join-Path $repoRoot "kaggle_pipeline/phase8_code_dataset/phase8_code_bundle.zip"

if (Test-Path -LiteralPath $bundlePath) {
    Remove-Item -LiteralPath $bundlePath -Force
}

tar -a -c -f $bundlePath --exclude="__pycache__" -C $kernelRoot `
    app tools kaggle_pipeline phase7b1_kaggle_v4_generic_luggage.py phase8_tracker_wrapper.py
if ($LASTEXITCODE -ne 0) {
    throw "tar failed with exit code $LASTEXITCODE"
}

Add-Type -AssemblyName System.IO.Compression.FileSystem
$archive = [IO.Compression.ZipFile]::OpenRead($bundlePath)
try {
    $required = @(
        "tools/phase8/phase8_batch_runner.py",
        "tools/phase8/inference_video.py",
        "phase8_tracker_wrapper.py",
        "phase7b1_kaggle_v4_generic_luggage.py",
        "kaggle_pipeline/phase7c_kernel/phase7c_core.py"
    )
    $names = @($archive.Entries | ForEach-Object { $_.FullName.Replace("\", "/") })
    $missing = @($required | Where-Object { $_ -notin $names })
    if ($missing.Count -gt 0) {
        throw "Code bundle missing: $($missing -join ', ')"
    }
    if ($names -match "__pycache__") {
        throw "Code bundle contains __pycache__"
    }
} finally {
    $archive.Dispose()
}

Write-Host "PHASE8 CODE BUNDLE READY: $bundlePath"
