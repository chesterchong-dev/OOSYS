"""Transaction-local PostgreSQL row-level-security context."""
from sqlalchemy import text
from sqlalchemy.orm import Session


def set_tenant_context(session: Session, organization_id: str | None, user_id: str | None = None,
                       user_email: str | None = None, reset_token_hash: str | None = None, session_token_hash: str | None = None) -> None:
    """Set fail-closed transaction-local context; SQLite tests intentionally no-op."""
    if session.get_bind().dialect.name != "postgresql":
        return
    session.execute(text(
        "SELECT set_config('app.tenant_id', :tenant, true), "
        "set_config('app.user_id', :user_id, true), "
        "set_config('app.user_email', :email, true), "
        "set_config('app.reset_token_hash', :reset_hash, true), "
        "set_config('app.session_token_hash', :session_hash, true)"
    ), {"tenant": organization_id or "", "user_id": user_id or "",
        "email": user_email or "", "reset_hash": reset_token_hash or "", "session_hash": session_token_hash or ""})
