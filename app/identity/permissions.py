"""Canonical permission vocabulary; only this module defines assignable keys."""

PERMISSIONS: dict[str, str] = {
    "organization.read": "View the active organization",
    "organization.update": "Update the active organization",
    "organization.archive": "Archive the active organization",
    "members.read": "List organization members",
    "members.invite": "Invite users to the organization",
    "organization.units.read": "View organisation hierarchy",
    "organization.units.create": "Create organisation hierarchy records",
    "organization.units.update": "Update organisation hierarchy records",
    "organization.units.archive": "Archive organisation hierarchy records",
    "members.update": "Change membership status or roles",
    "roles.read": "View organization roles",
    "roles.create": "Create organization roles",
    "roles.update": "Update organization roles",
    "roles.archive": "Archive organization roles",
    "audit.read": "Read organization audit events",
    "inventory.products.read": "View inventory products, categories and units",
    "inventory.products.write": "Create and update inventory products, categories and units",
    "inventory.stock.read": "View stock balances and movement history",
    "inventory.stock.write": "Post stock movements, counts and reservations",
    "inventory.counts.read": "View inventory counts and variance history",
    "inventory.counts.write": "Create and submit inventory counts",
    "inventory.counts.approve": "Approve inventory count variances",
    "warehouse.locations.read": "View warehouses and locations",
    "warehouse.locations.write": "Create and update warehouses and locations",
}

OWNER_PERMISSIONS = frozenset(PERMISSIONS)
