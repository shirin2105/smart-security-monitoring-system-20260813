# Camera 1 ABODA full-frame demo

## Outcome

Camera 1 plays the reviewed ABODA abandoned-object clip in the dashboard grid and detail modal without cropping.

## Constraints

- Keep cameras 2–6, backend contracts, CV logic, and alert behavior unchanged.
- Transcode the existing MP4 asset to browser-compatible H.264/yuv420p.
- Preserve the existing 16:9 camera tile; letterboxing is acceptable.

## Implementation

1. Publish the ABODA MP4 under the frontend static assets.
2. Re-render the same source window with real DEIMv2 + ByteTrack overlays and no fixed annotation.
3. Point mock Camera 1 at that asset.
4. Render Camera 1 video with `object-contain` in the grid and modal.
5. Verify frontend tests and production build.
6. In mock demo mode, emit the Phase7C abandoned event at 13.75 s and show a toast.

## Acceptance

- Camera 1 autoplays and loops the ABODA clip.
- The complete source frame is visible in both views.
- Other camera previews retain their current crop behavior.
- Frontend verification commands pass.
