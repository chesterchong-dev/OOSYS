"""Password recovery and email-backed organisation invitation workflows."""
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.identity.audit import record_event
from app.identity.dependencies import Principal, get_identity_session, get_principal, require_permission
from app.identity.delivery import send_invitation, send_password_reset
from app.identity.models import AuthSession, Membership, MembershipRole, Organization, OrganizationInvitation, PasswordResetToken, Role, RolePermission, User
from app.identity.schemas import InvitationAccept, InvitationCreate, PasswordResetConfirm, PasswordResetRequest
from app.identity.security import hash_password, issue_token, token_digest, utc_now
from app.identity.tenant_context import set_tenant_context

router = APIRouter()
RESET_MESSAGE = {"message": "If the account is eligible, password reset instructions will be sent."}


@router.post("/auth/password-reset/request", status_code=202)
def request_password_reset(payload: PasswordResetRequest, request: Request, db: Session = Depends(get_identity_session)):
    settings = request.app.state.settings
    if not settings.smtp_host or not settings.email_from or not settings.password_reset_url:
        raise HTTPException(503, "Password recovery delivery is not configured")
    set_tenant_context(db, None, user_email=str(payload.email).lower())
    user = db.scalar(select(User).where(User.email == str(payload.email).lower(),
        User.is_active.is_(True), User.archived_at.is_(None)))
    if user is None:
        return RESET_MESSAGE
    now = utc_now()
    set_tenant_context(db, None, user.id, user.email)
    db.query(PasswordResetToken).filter(PasswordResetToken.user_id == user.id,
        PasswordResetToken.used_at.is_(None)).update({PasswordResetToken.used_at: now}, synchronize_session=False)
    raw, digest = issue_token()
    token = PasswordResetToken(user_id=user.id, token_hash=digest, expires_at=now + timedelta(minutes=30))
    db.add(token)
    record_event(db, action="auth.password_reset.request", target_type="user",
        actor_user_id=user.id, target_id=user.id, outcome="requested")
    db.commit()
    try:
        send_password_reset(settings, user.email, raw)
    except Exception:
        token.used_at = utc_now()
        db.commit()
    return RESET_MESSAGE


@router.post("/auth/password-reset/confirm", status_code=204)
def confirm_password_reset(payload: PasswordResetConfirm, db: Session = Depends(get_identity_session)):
    now = utc_now()
    set_tenant_context(db, None, reset_token_hash=token_digest(payload.token))
    token = db.scalar(select(PasswordResetToken).where(PasswordResetToken.token_hash == token_digest(payload.token),
        PasswordResetToken.used_at.is_(None), PasswordResetToken.expires_at > now))
    if token is None:
        raise HTTPException(400, "Invalid or expired password reset token")
    set_tenant_context(db, None, token.user_id)
    user = db.get(User, token.user_id)
    if user is None or not user.is_active or user.archived_at is not None:
        raise HTTPException(400, "Invalid or expired password reset token")
    set_tenant_context(db, None, user.id, user.email)
    token.used_at = now
    user.password_hash = hash_password(payload.new_password)
    db.query(PasswordResetToken).filter(PasswordResetToken.user_id == user.id,
        PasswordResetToken.id != token.id, PasswordResetToken.used_at.is_(None)).update(
        {PasswordResetToken.used_at: now}, synchronize_session=False)
    db.query(AuthSession).filter(AuthSession.user_id == user.id, AuthSession.revoked_at.is_(None)).update(
        {AuthSession.revoked_at: now}, synchronize_session=False)
    record_event(db, action="auth.password_reset.complete", target_type="user",
        actor_user_id=user.id, target_id=user.id)
    db.commit()
    return None


@router.post("/organizations/{organization_id}/invitations", status_code=202)
def create_invitation(organization_id: str, payload: InvitationCreate, request: Request,
    principal: Principal = Depends(require_permission("members.invite")), db: Session = Depends(get_identity_session)):
    if principal.organization_id != organization_id:
        raise HTTPException(404, "Organisation not found")
    settings = request.app.state.settings
    if not settings.smtp_host or not settings.email_from or not settings.invitation_accept_url:
        raise HTTPException(503, "Invitation delivery is not configured")
    email = str(payload.email).lower()
    set_tenant_context(db, organization_id, principal.user_id, email)
    user = db.scalar(select(User).where(User.email == email, User.is_active.is_(True), User.archived_at.is_(None)))
    if user is None:
        raise HTTPException(404, "Invitee must have an active OOSYS account")
    role = db.scalar(select(Role).where(Role.id == payload.role_id,
        Role.organization_id == organization_id, Role.archived_at.is_(None)))
    if role is None:
        raise HTTPException(404, "Role not found")
    assigned = set(db.scalars(select(RolePermission.permission_key).where(
        RolePermission.organization_id == organization_id, RolePermission.role_id == role.id)).all())
    if not assigned.issubset(principal.permissions):
        raise HTTPException(403, "Cannot invite a user with permissions you do not hold")
    raw, digest = issue_token()
    now = utc_now()
    db.query(OrganizationInvitation).filter(OrganizationInvitation.organization_id == organization_id,
        OrganizationInvitation.email == email, OrganizationInvitation.accepted_at.is_(None),
        OrganizationInvitation.revoked_at.is_(None)).update({OrganizationInvitation.revoked_at: now}, synchronize_session=False)
    invitation = OrganizationInvitation(organization_id=organization_id, email=email, role_id=role.id,
        invited_by_user_id=principal.user_id, token_hash=digest, expires_at=now + timedelta(days=7))
    db.add(invitation)
    db.flush()
    record_event(db, action="organization.invitation.create", target_type="invitation",
        organization_id=organization_id, actor_user_id=principal.user_id, target_id=invitation.id)
    db.commit()
    try:
        send_invitation(settings, email, raw, organization_id)
    except Exception:
        invitation.revoked_at = utc_now()
        db.commit()
        raise HTTPException(503, "Invitation delivery failed")
    return {"message": "Invitation sent."}


@router.post("/auth/invitations/accept", status_code=201)
def accept_invitation(payload: InvitationAccept, principal: Principal = Depends(get_principal),
    db: Session = Depends(get_identity_session)):
    now = utc_now()
    set_tenant_context(db, None, principal.user_id, principal.email)
    invitation = db.scalar(select(OrganizationInvitation).where(
        OrganizationInvitation.token_hash == token_digest(payload.token),
        OrganizationInvitation.accepted_at.is_(None), OrganizationInvitation.revoked_at.is_(None),
        OrganizationInvitation.expires_at > now))
    if invitation is None or invitation.email != principal.email:
        raise HTTPException(400, "Invalid, expired or ineligible invitation")
    set_tenant_context(db, invitation.organization_id, principal.user_id, principal.email)
    org = db.get(Organization, invitation.organization_id)
    role = db.scalar(select(Role).where(Role.id == invitation.role_id,
        Role.organization_id == invitation.organization_id, Role.archived_at.is_(None)))
    if org is None or org.status != "active" or org.archived_at is not None or role is None:
        raise HTTPException(400, "Invalid, expired or ineligible invitation")
    membership = db.scalar(select(Membership).where(Membership.organization_id == org.id,
        Membership.user_id == principal.user_id))
    if membership and membership.status == "active":
        raise HTTPException(409, "User is already an active member")
    if membership is None:
        membership = Membership(organization_id=org.id, user_id=principal.user_id, status="active")
        db.add(membership)
        db.flush()
    else:
        membership.status = "active"
    db.query(MembershipRole).filter(MembershipRole.organization_id == org.id,
        MembershipRole.membership_id == membership.id).delete(synchronize_session=False)
    db.add(MembershipRole(organization_id=org.id, membership_id=membership.id, role_id=role.id))
    invitation.accepted_at = now
    record_event(db, action="organization.invitation.accept", target_type="invitation",
        organization_id=org.id, actor_user_id=principal.user_id, target_id=invitation.id)
    db.commit()
    return {"organization_id": org.id, "membership_id": membership.id}
