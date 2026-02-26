"""
access_engine.py - Core Access Expiry Engine
Member 1 Responsibility: grant, validate, track, renew, revoke logic
"""

from datetime import datetime, timedelta
from enum import Enum


# ─────────────────────────────────────────────
# AccessState Enum (coordinate with Member 2)
# Member 2 will move this to models/access_state.py
# ─────────────────────────────────────────────
class AccessState(Enum):
    ACTIVE = "ACTIVE"
    GRACE = "GRACE"
    EXPIRED = "EXPIRED"
    REVOKED = "REVOKED"


# ─────────────────────────────────────────────
# AccessRecord (coordinate with Member 2)
# Member 2 will move this to models/access_record.py
# ─────────────────────────────────────────────
class AccessRecord:
    def __init__(self, user_id, resource_id, duration_minutes, usage_limit):
        self.user_id = user_id
        self.resource_id = resource_id
        self.granted_at = datetime.utcnow()
        self.expires_at = datetime.utcnow() + timedelta(minutes=duration_minutes)
        self.usage_limit = usage_limit       # Max number of uses allowed (None = unlimited)
        self.usage_count = 0                 # How many times access has been used
        self.state = AccessState.ACTIVE
        self.grace_period_minutes = 5        # Grace window before fully expiring

    def to_dict(self):
        return {
            "user_id": self.user_id,
            "resource_id": self.resource_id,
            "granted_at": self.granted_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "usage_limit": self.usage_limit,
            "usage_count": self.usage_count,
            "state": self.state.value,
        }


# ─────────────────────────────────────────────
# In-memory store (acts as our "database" for now)
# Key: (user_id, resource_id)
# ─────────────────────────────────────────────
_access_store: dict = {}


def _make_key(user_id: str, resource_id: str) -> tuple:
    return (user_id, resource_id)


# ─────────────────────────────────────────────
# CORE FUNCTIONS
# ─────────────────────────────────────────────

def grant_access(user_id: str, resource_id: str, duration_minutes: int, usage_limit: int = None) -> dict:
    """
    Grant access to a user for a specific resource.

    Args:
        user_id:          Unique identifier for the user
        resource_id:      Unique identifier for the resource
        duration_minutes: How long the access lasts (in minutes)
        usage_limit:      Max number of uses allowed (None = unlimited)

    Returns:
        dict with access record details
    """
    key = _make_key(user_id, resource_id)

    record = AccessRecord(user_id, resource_id, duration_minutes, usage_limit)
    _access_store[key] = record

    print(f"[GRANT] User '{user_id}' granted access to '{resource_id}' "
          f"for {duration_minutes} mins | Limit: {usage_limit or 'unlimited'}")

    return {
        "success": True,
        "message": "Access granted",
        "access": record.to_dict()
    }


def validate_access(user_id: str, resource_id: str) -> dict:
    """
    Check if a user currently has valid access to a resource.
    Also updates state to GRACE or EXPIRED if needed.

    Returns:
        dict: { allowed: bool, state: str, reason: str }
    """
    key = _make_key(user_id, resource_id)
    record = _access_store.get(key)

    if not record:
        return {"allowed": False, "state": None, "reason": "No access record found"}

    now = datetime.utcnow()

    # Already revoked
    if record.state == AccessState.REVOKED:
        return {"allowed": False, "state": "REVOKED", "reason": "Access has been revoked"}

    # Check usage limit
    if record.usage_limit is not None and record.usage_count >= record.usage_limit:
        record.state = AccessState.EXPIRED
        return {"allowed": False, "state": "EXPIRED", "reason": "Usage limit reached"}

    # Check expiry
    if now > record.expires_at:
        grace_deadline = record.expires_at + timedelta(minutes=record.grace_period_minutes)

        if now <= grace_deadline and record.state != AccessState.EXPIRED:
            record.state = AccessState.GRACE
            print(f"[VALIDATE] User '{user_id}' is in GRACE period for '{resource_id}'")
            return {"allowed": True, "state": "GRACE", "reason": "Access in grace period"}
        else:
            record.state = AccessState.EXPIRED
            return {"allowed": False, "state": "EXPIRED", "reason": "Access has expired"}

    # All good
    record.state = AccessState.ACTIVE
    return {"allowed": True, "state": "ACTIVE", "reason": "Access is valid"}


def track_usage(user_id: str, resource_id: str) -> dict:
    """
    Increment usage count for a user's access to a resource.
    Triggers state change if usage limit is hit.

    Returns:
        dict with updated usage info
    """
    key = _make_key(user_id, resource_id)
    record = _access_store.get(key)

    if not record:
        return {"success": False, "message": "No access record found"}

    # First validate that access is still allowed
    validation = validate_access(user_id, resource_id)
    if not validation["allowed"]:
        return {"success": False, "message": f"Access not allowed: {validation['reason']}"}

    record.usage_count += 1

    print(f"[USAGE] User '{user_id}' used '{resource_id}' "
          f"({record.usage_count}/{record.usage_limit or 'unlimited'})")

    # Check if usage limit is now hit
    if record.usage_limit is not None and record.usage_count >= record.usage_limit:
        record.state = AccessState.EXPIRED
        print(f"[USAGE] Usage limit reached — access EXPIRED for '{user_id}' on '{resource_id}'")

    return {
        "success": True,
        "usage_count": record.usage_count,
        "usage_limit": record.usage_limit,
        "state": record.state.value
    }


def renew_access(user_id: str, resource_id: str, extra_duration_minutes: int, reset_usage: bool = False) -> dict:
    """
    Extend an existing access record's expiry time.
    Optionally reset the usage counter.

    Args:
        user_id:                Unique identifier for the user
        resource_id:            Unique identifier for the resource
        extra_duration_minutes: How many more minutes to add
        reset_usage:            If True, reset usage_count to 0

    Returns:
        dict with updated access details
    """
    key = _make_key(user_id, resource_id)
    record = _access_store.get(key)

    if not record:
        return {"success": False, "message": "No access record found"}

    if record.state == AccessState.REVOKED:
        return {"success": False, "message": "Cannot renew revoked access"}

    record.expires_at += timedelta(minutes=extra_duration_minutes)
    record.state = AccessState.ACTIVE  # Reactivate if was GRACE or EXPIRED

    if reset_usage:
        record.usage_count = 0
        print(f"[RENEW] Usage count reset for '{user_id}' on '{resource_id}'")

    print(f"[RENEW] User '{user_id}' access to '{resource_id}' extended by {extra_duration_minutes} mins "
          f"| New expiry: {record.expires_at.isoformat()}")

    return {
        "success": True,
        "message": "Access renewed",
        "access": record.to_dict()
    }


def revoke_access(user_id: str, resource_id: str) -> dict:
    """
    Manually revoke a user's access to a resource immediately.

    Returns:
        dict confirming revocation
    """
    key = _make_key(user_id, resource_id)
    record = _access_store.get(key)

    if not record:
        return {"success": False, "message": "No access record found"}

    record.state = AccessState.REVOKED
    print(f"[REVOKE] User '{user_id}' access to '{resource_id}' has been REVOKED")

    return {
        "success": True,
        "message": "Access revoked",
        "access": record.to_dict()
    }


def get_access_record(user_id: str, resource_id: str) -> dict:
    """
    Utility: Fetch the full access record for a user/resource pair.
    Useful for Member 3 (API) and Member 4 (Demo).
    """
    key = _make_key(user_id, resource_id)
    record = _access_store.get(key)

    if not record:
        return {"success": False, "message": "No record found"}

    return {"success": True, "access": record.to_dict()}