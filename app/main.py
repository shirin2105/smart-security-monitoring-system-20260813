from fastapi import FastAPI

from app.agents import AssessmentRunner, create_assessment_runner
from app.agents.handoff import AssessmentHandoff
from app.api.debug import router as debug_router
from app.api.events import router as events_router
from app.api.health import router as health_router
from app.services.intake import PersistedIntake

BACKEND_EVENT_DIR = "artifacts/backend_events"


def create_app(
    *,
    intake: PersistedIntake | None = None,
    assessment_runner: AssessmentRunner | None = None,
) -> FastAPI:
    application = FastAPI(
        title="CV/VLM Security Event Detection System",
        description="Computer Vision CCTV Security Event Candidate Producer & Backend Ingestion",
        version="1.0.0",
    )
    resolved_intake = intake or PersistedIntake(storage_dir=BACKEND_EVENT_DIR)
    resolved_runner = assessment_runner or create_assessment_runner(
        output_dir=BACKEND_EVENT_DIR
    )
    application.state.intake = resolved_intake
    application.state.assessment_handoff = AssessmentHandoff(resolved_runner)
    application.include_router(health_router)
    application.include_router(debug_router)
    application.include_router(events_router)

    @application.get("/")
    def root():
        return {
            "system": "CV/VLM Security Event Detection System",
            "phase": "Phase 2 - Privacy Redaction Gate & Backend Integration",
            "status": "OPERATIONAL",
        }

    return application


app = create_app()
