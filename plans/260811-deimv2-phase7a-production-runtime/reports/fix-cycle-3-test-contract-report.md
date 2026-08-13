# Fix cycle 3: worker test and backbone override contracts

## Diagnosis

- Five legacy integration-test executions called `CVWorker.run()` without detector assets.
- These tests cover event-engine composition or EOS cleanup, not DEIMv2 loading.
- Strict run-start asset validation correctly failed before source reads; production fail-fast remains unchanged.

## Changes

- Added one deterministic empty-detector fixture and injected it through `CVWorker(detector=...)` in the four affected test modules.
- Preserved all prior assertions and production worker behavior.
- Extracted the existing YAML/backbone equality check into a directly testable validator.
- Documented that `DEIMV2_CONFIG_PATH` and `DEIMV2_BACKBONE_PATH` must be updated as a pair.

## Verification

- `git diff --check`: passed.
- Static compilation: unavailable because this Windows environment has no installed Python (`py` reports no installed Python).
- Targeted/full pytest: pending local pytest-enabled interpreter availability.
- No backend or frontend files changed.

## Unresolved Questions

- None in scope.
