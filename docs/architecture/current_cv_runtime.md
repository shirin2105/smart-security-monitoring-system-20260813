# Current CV runtime

```text
Camera / video / webcam
  -> DEIMv2 (person + generic luggage)
  -> ByteTrack
  -> shared TrackStore snapshot
  -> intrusion / crowd / Phase7C abandoned adapters
  -> CVEventManager
  -> cv-event-v1
  -> CVEventPublisher / JsonlPublisher
```

The three emitted event types are `ZONE_INTRUSION`, `CROWD_THRESHOLD`, and
`ABANDONED_OBJECT`. The canonical output is local schema-valid CVEvent v1 JSONL;
the backend `EventCandidate` path is compatibility-only and outside the CV boundary.

## Legacy material

YOLO/Ultralytics, StrongSORT, static-region abandoned-object detection, and VLM/Gemma
validation are historical experiments. They are not dependencies of the production
worker and remain only where legacy tests or demos still import them.
