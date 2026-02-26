"""
access_state.py
---------------
Defines the AccessState enum representing the lifecycle stages of an access record.

State Transitions:
    ACTIVE --> GRACE   : time or usage limit reached, grace period kicks in
    GRACE  --> EXPIRED : grace period ends
    ACTIVE --> REVOKED : manually revoked
    GRACE  --> REVOKED : manually revoked during grace period
    GRACE  --> ACTIVE  : access renewed during grace period
"""

from enum import Enum


class AccessState(Enum):
    """
    Represents the current lifecycle state of an access grant.

    States:
        ACTIVE   - Access is valid and within all defined limits.
        GRACE    - Access has technically expired but a grace window is still open.
        EXPIRED  - Access has fully expired; no further use is permitted.
        REVOKED  - Access was manually terminated before natural expiry.
    """

    ACTIVE = "ACTIVE"
    GRACE = "GRACE"
    EXPIRED = "EXPIRED"
    REVOKED = "REVOKED"

    def is_usable(self) -> bool:
        """
        Returns True if the access can still be used.
        Both ACTIVE and GRACE states allow usage.
        """
        return self in (AccessState.ACTIVE, AccessState.GRACE)

    def is_accessible(self) -> bool:
        """Alias for is_usable(). Returns True if state is ACTIVE or GRACE."""
        return self.is_usable()

    def is_terminal(self) -> bool:
        """
        Returns True if the access has reached a final, non-recoverable state.
        EXPIRED and REVOKED states cannot be renewed or reactivated.
        """
        return self in (AccessState.EXPIRED, AccessState.REVOKED)

    def __str__(self) -> str:
        return self.value