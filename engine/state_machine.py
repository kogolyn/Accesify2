"""
state_machine.py - State Transition Logic
Member 1 Responsibility: Define and enforce valid state transitions
"""

from enum import Enum


class AccessState(Enum):
    ACTIVE = "ACTIVE"
    GRACE = "GRACE"
    EXPIRED = "EXPIRED"
    REVOKED = "REVOKED"


# ─────────────────────────────────────────────
# Valid transitions map:
# Key   = current state
# Value = set of states it can move to
# ─────────────────────────────────────────────
VALID_TRANSITIONS = {
    AccessState.ACTIVE:  {AccessState.GRACE, AccessState.EXPIRED, AccessState.REVOKED},
    AccessState.GRACE:   {AccessState.ACTIVE, AccessState.EXPIRED, AccessState.REVOKED},
    AccessState.EXPIRED: {AccessState.ACTIVE},   # Only possible via renew
    AccessState.REVOKED: set(),                  # Terminal state — no transitions allowed
}


def can_transition(current_state: AccessState, new_state: AccessState) -> bool:
    """Check if a transition from current_state to new_state is valid."""
    return new_state in VALID_TRANSITIONS.get(current_state, set())


def transition(record, new_state: AccessState) -> bool:
    """
    Attempt to transition an AccessRecord to a new state.

    Args:
        record:     An AccessRecord object (must have a .state attribute)
        new_state:  The target AccessState

    Returns:
        True if transition succeeded, False if it was invalid
    """
    if can_transition(record.state, new_state):
        old_state = record.state.value
        record.state = new_state
        print(f"[STATE] {record.user_id} | '{record.resource_id}': {old_state} → {new_state.value}")
        return True
    else:
        print(f"[STATE] INVALID transition: {record.state.value} → {new_state.value} "
              f"for user '{record.user_id}' on '{record.resource_id}'")
        return False


def get_valid_transitions(current_state: AccessState) -> list:
    """Return list of valid next states from the current state."""
    return [s.value for s in VALID_TRANSITIONS.get(current_state, set())]