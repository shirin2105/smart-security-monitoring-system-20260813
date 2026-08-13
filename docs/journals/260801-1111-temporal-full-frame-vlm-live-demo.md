# Temporal Full-Frame VLM Stopped a Bad Alert

**Date**: 2026-08-01 11:11
**Severity**: High
**Component**: Static-region abandoned-object validation and multi-camera worker
**Status**: Resolved with production-scale limitations

## What Happened

The validator originally understood one cropped region, not temporal full-scene evidence. That was insufficient: a crop could show *what* occupied a box, but not whether someone moved through it or left an object. We implemented ordered full-frame validation over `[T-8s, T+8s]`, sampled at 1 FPS with at most 17 frames. Candidate time remains `T`; the decision deliberately waits for future post-roll.

## The Brutal Truth

Our first live attempt failed because we ran a short clip with `owner_absent_seconds=10`. The region matured too late to collect eight seconds of future video, so EOS correctly discarded it without a VLM call. This was not model failure; it was a careless mismatch between rule latency and clip length. It was maddening because the pipeline worked exactly as designed while the demo setup made success impossible.

## Technical Details

The live PETS run used `owner_absent_seconds=0` because this demo has no person tracker. Candidate `T=14.666667s` was evaluated at `22.666667s` using 16 ordered full frames. `google/gemma-3-4b-it` rejected the detector's moving-person false static region with confidence `0.99`; `event_count` stayed `0`, so no alert escaped. The detector-only comparison later emitted three likely bag-region alerts at `45.5s`, `46.866667s`, and `47.1s`.

Review exposed ugly scale risks. Six cameras could otherwise retain oversized raw frames and construct bloated requests. Fixes added proportional resizing to 480 px, a 12 MB buffer ceiling, a 500 KB serialized-request budget, per-region call isolation, and no-network rejection for oversize payloads. EOS and stream errors now finalize once, discard incomplete pending windows, clear frames/state, and release the source.

## What We Tried

- Rejected crop-only validation: compatible, but blind to before/after motion.
- Rejected immediate validation at `T`: it cannot contain future evidence.
- Kept temporal mode opt-in so the legacy crop path remains supported.
- Used `owner_absent=0` only for the trackerless demo; production remains `10`.

## Root Cause Analysis

We designed around a still-image API before admitting abandonment is a temporal claim. The demo failure came from forgetting that owner absence plus post-roll consumes real clip duration.

## Lessons Learned

Calculate the full latency budget before choosing a demo clip. Never treat EOS silence as mysterious. Full-frame CCTV must remain memory-only; credentials stay environment-only, and tokens, authorization headers, raw payloads, and raw provider responses must never enter summaries, logs, or artifacts.

## Next Steps

- Runtime owner, before production trial: benchmark six real cameras and record FPS, latency, memory, dropped frames, and detector-lock contention.
- ML owner, before accuracy claims: run labeled PETS positives and negatives; report false-alert suppression and missed bags.
- CV owner, next iteration: integrate person tracking so `owner_absent_seconds=10` has real semantic meaning.
