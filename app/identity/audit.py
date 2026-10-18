"""Safe audit helpers; credential values are deliberately not accepted by this API."""
from sqlalchemy.orm import Session
from app.identity.models import AuditEvent


def record_event(session: Session, *, action: str, target_type: str,
                 organization_id: str | None = None, actor_user_id: str | None = None,
                 target_id: str | None = None, outcome: str = "success",
                 correlation_id: str | None = None, details: dict | None = None) -> None:
    session.add(AuditEvent(organization_id=organization_id, actor_user_id=actor_user_id,
        action=action, target_type=target_type, target_id=target_id, outcome=outcome,
        correlation_id=correlation_id, details_json=details or {}))
