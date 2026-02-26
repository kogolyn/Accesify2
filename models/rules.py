"""
rules.py
--------
Defines the rule structures that control HOW access expires.

The engine (Member 1) reads these rules when evaluating an AccessRecord.
Rules are pure data — no side effects, no database calls.

Two rule types are supported:
  - TimeRule   : expires access after a fixed duration
  - UsageRule  : expires access after a fixed number of uses

Both can be active on the same record simultaneously.
Expiry triggers as soon as EITHER condition is met (whichever comes first).

Member 2 – Data Models & State
"""

from dataclasses import dataclass
from datetime import timedelta
from typing import Optional


# ─────────────────────────────────────────────────────────────────────────── #
# Base                                                                        #
# ─────────────────────────────────────────────────────────────────────────── #

@dataclass
class BaseRule:
    """
    Shared fields inherited by every rule type.

    Attributes
    ----------
    grace_period : Optional[timedelta]
        If set, the engine moves the record to GRACE state rather than
        directly to EXPIRED when the limit is first hit.
        The record stays GRACE until this duration elapses, then → EXPIRED.
        Example: timedelta(hours=24) gives a 24-hour grace window.
    """
    grace_period: Optional[timedelta] = None

    @property
    def has_grace_period(self) -> bool:
        return self.grace_period is not None


# ─────────────────────────────────────────────────────────────────────────── #
# Time-based rule                                                             #
# ─────────────────────────────────────────────────────────────────────────── #

@dataclass
class TimeRule(BaseRule):
    """
    Expires access after a fixed duration from the grant time.

    Attributes
    ----------
    duration : timedelta
        How long the access is valid from the moment it is granted.
        Example: timedelta(days=30) for a 30-day trial.

    Examples
    --------
    # 7-day access, no grace period
    rule = TimeRule(duration=timedelta(days=7))

    # 30-day access with a 48-hour grace window
    rule = TimeRule(duration=timedelta(days=30), grace_period=timedelta(hours=48))
    """
    duration: timedelta = timedelta(days=30)   # sensible default: 30 days

    def __post_init__(self):
        if self.duration.total_seconds() <= 0:
            raise ValueError("TimeRule.duration must be a positive timedelta.")
        if self.grace_period and self.grace_period.total_seconds() <= 0:
            raise ValueError("TimeRule.grace_period must be a positive timedelta.")

    def to_dict(self) -> dict:
        return {
            "type": "time",
            "duration_seconds": int(self.duration.total_seconds()),
            "grace_period_seconds": (
                int(self.grace_period.total_seconds()) if self.grace_period else None
            ),
        }


# ─────────────────────────────────────────────────────────────────────────── #
# Usage-based rule                                                            #
# ─────────────────────────────────────────────────────────────────────────── #

@dataclass
class UsageRule(BaseRule):
    """
    Expires access after a fixed number of resource accesses.

    Attributes
    ----------
    max_uses : int
        Maximum number of times the resource may be accessed.
        Example: 10 for a 10-download limit.

    Examples
    --------
    # 5-use limit, no grace period
    rule = UsageRule(max_uses=5)

    # 100-use limit with a 10-use grace buffer
    # (grace doesn't have a 'uses' concept — it's still time-based)
    rule = UsageRule(max_uses=100, grace_period=timedelta(hours=1))
    """
    max_uses: int = 10   # sensible default

    def __post_init__(self):
        if self.max_uses <= 0:
            raise ValueError("UsageRule.max_uses must be a positive integer.")

    def to_dict(self) -> dict:
        return {
            "type": "usage",
            "max_uses": self.max_uses,
            "grace_period_seconds": (
                int(self.grace_period.total_seconds()) if self.grace_period else None
            ),
        }


# ─────────────────────────────────────────────────────────────────────────── #
# Preset rule factory                                                         #
# ─────────────────────────────────────────────────────────────────────────── #

class RulePresets:
    """
    Ready-made rule combinations for common access scenarios.

    The engine or API layer can call these instead of constructing
    rules manually, keeping grant_access() calls concise.

    Usage
    -----
        time_rule, usage_rule = RulePresets.trial()
        time_rule, usage_rule = RulePresets.premium_monthly()
        time_rule, usage_rule = RulePresets.one_time_download()
    """

    @staticmethod
    def trial() -> tuple[TimeRule, None]:
        """7-day free trial with a 24-hour grace window. No usage limit."""
        return (
            TimeRule(duration=timedelta(days=7), grace_period=timedelta(hours=24)),
            None,
        )

    @staticmethod
    def premium_monthly() -> tuple[TimeRule, None]:
        """30-day paid subscription with a 48-hour grace window."""
        return (
            TimeRule(duration=timedelta(days=30), grace_period=timedelta(hours=48)),
            None,
        )

    @staticmethod
    def one_time_download() -> tuple[None, UsageRule]:
        """Single-use download link. No time limit; 1 use allowed."""
        return (None, UsageRule(max_uses=1))

    @staticmethod
    def limited_api_access() -> tuple[TimeRule, UsageRule]:
        """
        30-day window AND a 1000-call cap — whichever hits first expires access.
        Grace: 1 hour after either limit is reached.
        """
        return (
            TimeRule(duration=timedelta(days=30), grace_period=timedelta(hours=1)),
            UsageRule(max_uses=1000, grace_period=timedelta(hours=1)),
        )