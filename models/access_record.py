"""
access_record.py
----------------
Defines the AccessRecord class — the core data structure that represents
a single user's access grant to a specific resource.

This model is consumed by:
    - access_engine.py  (core logic reads/writes these records)
    - app.py / routes.py (API layer serializes them to JSON)
    - test_scenarios.py (demo layer creates sample records)
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from models.access_state import AccessState


@dataclass
class AccessRecord:
    """
    Represents a single access grant for a user on a specific resource.

    Attributes:
        user_id         : Unique identifier for the user.
        resource_id     : Unique identifier for the resource being accessed.
        state           : Current lifecycle state (ACTIVE, GRACE, EXPIRED, REVOKED).
        granted_at      : Timestamp when access was originally granted.
        expires_at      : Timestamp when access is scheduled to expire.
        usage_limit     : Maximum number of times the resource can be accessed.
                          None means unlimited usage.
        usage_count     : Running count of how many times access has been used.
        grace_period_end: Timestamp when the grace period ends (if applicable).
                          None means no grace period is configured.
        last_accessed_at: Timestamp of the most recent successful access.
                          None if the resource has never been accessed.
        revoked_at      : Timestamp of manual revocation (if applicable).
                          None if the access was not manually revoked.
        notes           : Optional human-readable notes (e.g. reason for revocation).
    """

    user_id: str
    resource_id: str
    state: AccessState
    granted_at: datetime
    expires_at: datetime
    usage_limit: Optional[int] = None
    usage_count: int = 0
    grace_period_end: Optional[datetime] = None
    last_accessed_at: Optional[datetime] = None
    revoked_at: Optional[datetime] = None
    notes: Optional[str] = None

    # -------------------------------------------------------------------------
    # Computed helper properties
    # -------------------------------------------------------------------------

    def is_time_expired(self, now: Optional[datetime] = None) -> bool:
        """
        Returns True if the current time has passed the expiry timestamp.

        Args:
            now: The current datetime to compare against. Defaults to utcnow().
        """
        now = now or datetime.utcnow()
        return now >= self.expires_at

    def is_usage_exceeded(self) -> bool:
        """
        Returns True if the usage limit has been reached or exceeded.
        Always returns False if no usage limit is defined.
        """
        if self.usage_limit is None:
            return False
        return self.usage_count >= self.usage_limit

    def is_in_grace_period(self, now: Optional[datetime] = None) -> bool:
        """
        Returns True if we are currently inside the grace window.
        Grace period is only active if grace_period_end is set and not yet passed.

        Args:
            now: The current datetime to compare against. Defaults to utcnow().
        """
        if self.grace_period_end is None:
            return False
        now = now or datetime.utcnow()
        return now < self.grace_period_end

    def remaining_uses(self) -> Optional[int]:
        """
        Returns the number of uses remaining.
        Returns None if the access is unlimited.
        """
        if self.usage_limit is None:
            return None
        return max(0, self.usage_limit - self.usage_count)

    def time_until_expiry(self, now: Optional[datetime] = None) -> Optional[float]:
        """
        Returns the number of seconds until expiry.
        Returns 0 if already expired. Returns None if no expiry is set.

        Args:
            now: The current datetime. Defaults to utcnow().
        """
        now = now or datetime.utcnow()
        delta = (self.expires_at - now).total_seconds()
        return max(0.0, delta)

    # -------------------------------------------------------------------------
    # Serialization
    # -------------------------------------------------------------------------

    def to_dict(self) -> dict:
        """
        Converts this record to a plain dictionary for JSON serialization.
        Datetime fields are converted to ISO 8601 strings.
        """
        return {
            "user_id": self.user_id,
            "resource_id": self.resource_id,
            "state": str(self.state),
            "granted_at": self.granted_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "usage_limit": self.usage_limit,
            "usage_count": self.usage_count,
            "grace_period_end": self.grace_period_end.isoformat() if self.grace_period_end else None,
            "last_accessed_at": self.last_accessed_at.isoformat() if self.last_accessed_at else None,
            "revoked_at": self.revoked_at.isoformat() if self.revoked_at else None,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "AccessRecord":
        """
        Constructs an AccessRecord from a plain dictionary.
        Useful for deserializing from JSON or a database row.

        Args:
            data: A dictionary with the same keys as to_dict().

        Returns:
            A fully constructed AccessRecord instance.
        """
        return cls(
            user_id=data["user_id"],
            resource_id=data["resource_id"],
            state=AccessState(data["state"]),
            granted_at=datetime.fromisoformat(data["granted_at"]),
            expires_at=datetime.fromisoformat(data["expires_at"]),
            usage_limit=data.get("usage_limit"),
            usage_count=data.get("usage_count", 0),
            grace_period_end=(
                datetime.fromisoformat(data["grace_period_end"])
                if data.get("grace_period_end") else None
            ),
            last_accessed_at=(
                datetime.fromisoformat(data["last_accessed_at"])
                if data.get("last_accessed_at") else None
            ),
            revoked_at=(
                datetime.fromisoformat(data["revoked_at"])
                if data.get("revoked_at") else None
            ),
            notes=data.get("notes"),
        )

    def __repr__(self) -> str:
        return (
            f"AccessRecord(user={self.user_id!r}, resource={self.resource_id!r}, "
            f"state={self.state}, usage={self.usage_count}/{self.usage_limit or '∞'}, "
            f"expires={self.expires_at.isoformat()})"
        )