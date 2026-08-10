import logging

import pytest

from app.agents.handoff import AssessmentHandoff
from tests.unit.test_assessment_record import _outcome
from tests.unit.test_assessment_runtime import _candidate


class _StubRunner:
    def __init__(self, *, outcome=None, error=None):
        self.outcome = outcome
        self.error = error
        self.calls = []

    async def assess(self, candidate):
        self.calls.append(candidate.candidateId)
        if self.error is not None:
            raise self.error
        return self.outcome


@pytest.mark.asyncio
async def test_handoff_logs_terminal_outcome(caplog):
    runner = _StubRunner(outcome=_outcome())
    handoff = AssessmentHandoff(runner)

    with caplog.at_level(logging.INFO):
        result = await handoff.run(_candidate())

    assert result is not None
    assert "agent_assessment_completed" in caplog.text
    assert runner.calls == ["candidate-ZONE_INTRUSION"]


@pytest.mark.asyncio
async def test_handoff_logs_unexpected_failure(caplog):
    runner = _StubRunner(error=RuntimeError("boom"))
    handoff = AssessmentHandoff(runner)

    with caplog.at_level(logging.ERROR):
        result = await handoff.run(_candidate())

    assert result is None
    assert "agent_assessment_failed" in caplog.text
    record = caplog.records[-1]
    assert record.candidate_id == "candidate-ZONE_INTRUSION"
    assert record.event_type == "ZONE_INTRUSION"
    assert record.assessment_status == "failed"
    assert record.exception_class == "RuntimeError"
