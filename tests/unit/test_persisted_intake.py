"""PersistedIntake tests (architecture review candidate 5).

The intake module owns canonical identity, atomic dedupe, durable write, and
assessment handoff. The route stays thin and never touches idempotency or
filesystem ordering directly.
"""


from app.common.schemas import EventCandidate
from app.services.intake import PersistedIntake
from tests.integration.test_enrichment_pipeline import INTRUSION_EVENT


def _candidate(candidate_id: str = "cand-intake-1", **overrides) -> EventCandidate:
    payload = dict(INTRUSION_EVENT)
    payload["candidateId"] = candidate_id
    payload.update(overrides)
    return EventCandidate.model_validate(payload)


def test_accept_writes_candidate_and_marks_processed(tmp_path):
    intake = PersistedIntake(storage_dir=str(tmp_path))
    outcome = intake.accept(_candidate("cand-1"))

    assert outcome.status == "ACCEPTED"
    assert (tmp_path / "candidate_cand-1.json").exists()
    assert intake.store.is_processed("cand-1")


def test_duplicate_ignored_without_second_write(tmp_path):
    intake = PersistedIntake(storage_dir=str(tmp_path))
    first = intake.accept(_candidate("cand-dup"))
    second = intake.accept(_candidate("cand-dup"))

    assert first.status == "ACCEPTED"
    assert second.status == "DUPLICATE_IGNORED"
    files = list(tmp_path.glob("candidate_*.json"))
    assert len(files) == 1


def test_header_id_wins_over_body_id(tmp_path):
    intake = PersistedIntake(storage_dir=str(tmp_path))
    outcome = intake.accept(_candidate("body-id"), header_id="header-id")

    assert outcome.candidate_id == "header-id"
    assert (tmp_path / "candidate_header-id.json").exists()
    assert intake.store.is_processed("header-id")
    assert not intake.store.is_processed("body-id")


def test_accept_failure_returns_error_outcome(tmp_path):
    intake = PersistedIntake(storage_dir=str(tmp_path))
    outcome = intake.accept(_candidate('bad"id'))

    assert outcome.status == "ERROR"
    assert outcome.error is not None


def test_accept_outcome_json_shape(tmp_path):
    intake = PersistedIntake(storage_dir=str(tmp_path))
    outcome = intake.accept(_candidate("cand-shape"))

    assert outcome.as_response() == {
        "status": "ACCEPTED",
        "candidateId": "cand-shape",
        "stored_uri": "/backend/events/candidate_cand-shape.json",
    }


def test_duplicate_outcome_json_shape(tmp_path):
    intake = PersistedIntake(storage_dir=str(tmp_path))
    intake.accept(_candidate("cand-shape"))
    outcome = intake.accept(_candidate("cand-shape"))

    assert outcome.as_response()["status"] == "DUPLICATE_IGNORED"
    assert outcome.as_response()["candidateId"] == "cand-shape"
