from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import AuditEvent


def record(db: Session, event_type: str, *, actor: str = "system", run_id: str | None = None,
           assessment_id: str | None = None, **detail) -> None:
    db.add(AuditEvent(event_type=event_type, actor=actor, run_id=run_id, assessment_id=assessment_id,
                      detail=detail))
