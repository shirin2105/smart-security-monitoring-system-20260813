# Phase 8.5 local webcam CV test

Disposable Computer Vision integration tool. It imports the frozen Phase 7A
DEIMv2 checkpoint, Phase 7B.1 generic-luggage ByteTrack runtime, and Phase 7C
abandoned-candidate reasoning. It does not modify production modules.

## Install and run

```powershell
third_party\deimv2\.python311\python.exe -m pip install -r devtools\webcam_cv_test\requirements_test.txt
third_party\deimv2\.python311\python.exe -m pip install torch==2.5.1 torchvision==0.20.1 --index-url https://download.pytorch.org/whl/cu124
third_party\deimv2\.python311\python.exe devtools\webcam_cv_test\app.py
```

Open <http://127.0.0.1:5000>. To select another camera:

```powershell
third_party\deimv2\.python311\python.exe devtools\webcam_cv_test\app.py --camera 1
```

For one-click startup on Windows, double-click `start-web-and-camera.bat`.
Keep its terminal window open; press `Ctrl+C` there to stop both camera and web.
Alternatively, double-click `stop-web-and-camera.bat` to release the webcam and
terminate only the server process listening on port 5000.

The tool requires the local Phase 7A `best.pth`, DINOv3 `vitt_distill.pt`, and a
webcam accessible through OpenCV. CUDA is selected automatically; CPU fallback
is supported for compatibility but is unlikely to be realtime. Model
initialization can take a while. All decisions use monotonic seconds; model
inference occurs once per captured frame and its tracks feed all three rules.

## Fixed test rules

- Intrusion: confirmed person's bbox bottom-center in the right half for 1 s.
- Crowd: at least two confirmed person tracks for 2 s; clear after 1 s below two.
- Abandoned: unchanged Phase 7C quality, stitching, stationary, owner and
  owner-away candidate logic (3 s / 5 s holds from `config.json`).

Only state transitions are appended to `outputs/events.jsonl`.

## Validation snapshot

- Unit tests: 3/3 pass; existing Phase 7C regression tests: 5/5 pass.
- Strict Phase 7A EMA checkpoint load and one black-frame inference: pass.
- RTX 3050 CUDA reference after warm-up: 84.6 ms detector, 86.0 ms
  detector-to-tracker pipeline (about 11.6 FPS, 91.3 MiB peak allocated VRAM).
- CPU reference: 407.6 ms detector, 409.0 ms pipeline (about 2.4 FPS).
- The development sandbox had no accessible camera device. The camera-open
  failure path and clean stop/release behavior pass; live `VideoCapture(0)`
  still needs verification on the target Windows machine.

## Tests

```powershell
third_party\deimv2\.python311\python.exe -m unittest discover -s devtools\webcam_cv_test\tests -v
```

## Remove completely

```powershell
Remove-Item -Recurse -Force .\devtools\webcam_cv_test
```
