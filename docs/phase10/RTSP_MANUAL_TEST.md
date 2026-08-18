# Phase 10 RTSP manual verification

Hardware status: **NOT HARDWARE VERIFIED** in this environment.

1. Set the RTSP URL outside source control and enable only the RTSP camera.
2. Verify DEIMv2, ByteTrack, shared TrackStore and `cv-event-v1` JSONL output.
3. Run for 5–10 minutes, then disconnect the camera/network.
4. Verify degraded/reconnect health, wait beyond `reset_after_s`, and reconnect.
5. Confirm recovery without detector reload, no stale tracks/temporal state, and no false abandoned event.
6. Stop with Ctrl+C and confirm capture/retry loops release cleanly.

Record camera/backend, OpenCV build, timestamps, reconnect/reset health snapshots, detector construction count, and emitted CVEvent v1 records. Do not include the RTSP URI or credentials.

OpenCV open/read timeout properties are backend/build dependent. A clean stop during reconnect backoff does not prove that every native `VideoCapture.read()` can be forcibly interrupted. Record any stop delay or blocked native read as a portability failure, not PASS.
