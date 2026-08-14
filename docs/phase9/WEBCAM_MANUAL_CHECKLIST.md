# Webcam manual verification

Hardware status: **NOT HARDWARE VERIFIED** in the agent environment.

Run `third_party\deimv2\.python311\python.exe devtools\webcam_cv_test\app.py` as a
legacy/devtool-only visual check. It does not exercise CVWorker, TrackStore,
CVEventManager, JsonlPublisher, or canonical `cv-event-v1` lifecycle output.
Verify:

- intrusion: entering the right half emits START; leaving emits END;
- crowd: one person remains normal; two people trigger then recover;
- abandoned: stationary luggage plus owner-away emits the devtool candidate indication;
- Ctrl+C releases the camera. Canonical webcam CVEvent verification remains pending a
  webcam source wired through the unified worker.
