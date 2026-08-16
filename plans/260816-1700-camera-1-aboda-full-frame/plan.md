# Camera 1 ABODA full-frame demo

## Outcome

Camera 1 plays the reviewed ABODA abandoned-object clip in the dashboard grid and detail modal without cropping.

## Constraints

- Keep cameras 2–6, backend contracts, CV logic, and alert behavior unchanged.
- Transcode the existing MP4 asset to browser-compatible H.264/yuv420p.
- Preserve the existing 16:9 camera tile; letterboxing is acceptable.

## Implementation

1. Publish the ABODA MP4 under the frontend static assets.
2. Encode the clean full source as browser-compatible H.264 without overlays.
3. Point mock Camera 1 at the clean source starting at 40 s.
4. Render Camera 1 video with `object-contain` in the grid and modal.
5. Verify frontend tests and production build.
6. In mock demo mode, emit the Phase7C abandoned event at source time 53.75 s.
7. Build the evidence view at runtime from the full source using a ±6 s window.

## Acceptance

- Camera 1 autoplays and loops the ABODA clip.
- The complete source frame is visible in both views.
- Other camera previews retain their current crop behavior.
- Frontend verification commands pass.
