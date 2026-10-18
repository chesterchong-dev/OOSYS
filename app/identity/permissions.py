"""Canonical permission vocabulary; only this module defines assignable keys."""

PERMISSIONS: dict[str, str] = {
    "organization.read": "View the active organization",
    "organization.update": "Update the active organization",
    "organization.archive": "Archive the active organization",
    "members.read": "List organization members",
    "members.invite": "Invite users to the organization",
    "members.update": "Change membership status or roles",
    "roles.read": "View organization roles",
    "roles.create": "Create organization roles",
    "roles.update": "Update organization roles",
    "roles.archive": "Archive organization roles",
    "audit.read": "Read organization audit events",
}

OWNER_PERMISSIONS = frozenset(PERMISSIONS)
