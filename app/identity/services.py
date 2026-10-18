"""Small identity provisioning helpers shared by authentication use cases."""
from datetime import datetime
from sqlalchemy.orm import Session
from app.identity.models import AuthSession, Role, RolePermission, User
from app.identity.permissions import OWNER_PERMISSIONS
from app.identity.security import issue_token, session_expiry

def _owner_role(db: Session, org_id: str) -> Role:
    role = Role(organization_id=org_id, name="Owner", description="Organisation owner", is_system=True)
    db.add(role)
    db.flush()
    db.add_all([RolePermission(organization_id=org_id, role_id=role.id, permission_key=key)
                for key in OWNER_PERMISSIONS])
    return role


def _new_session(db: Session, user: User, org_id: str, ttl_hours: int = 12) -> tuple[str, datetime]:
    raw, digest = issue_token()
    expires = session_expiry(ttl_hours)
    db.add(AuthSession(user_id=user.id, token_hash=digest, active_organization_id=org_id, expires_at=expires))
    return raw, expires
