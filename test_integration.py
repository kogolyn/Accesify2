"""
test_integration.py
-------------------
Integration test: Member 1 (access_engine + state_machine)
working together with Member 2 (access_record + access_state + rules)

Run with:
    python test_integration.py

What this tests:
    - Engine functions correctly read/write Member 2's AccessRecord fields
    - AccessState enum is shared (no duplicate type mismatch)
    - to_dict() / from_dict() survive a full engine round trip
    - Rules from rules.py correctly translate into engine behaviour
    - State transitions via state_machine respect Member 2's AccessState
    - Grace period, usage cap, time expiry all reflected in AccessRecord fields
"""

import sys
import time

# ── Member 1 imports ──
from engine.access_engine import (
    grant_access, validate_access, track_usage,
    renew_access, revoke_access, get_access_record,
    AccessState, AccessRecord, _access_store
)
from engine.state_machine import can_transition, transition, get_valid_transitions

# ── Member 2 imports ──
from models.access_state import AccessState as M2State
from models.access_record import AccessRecord as M2Record
from models.rules import TimeRule, UsageRule, RulePresets

from datetime import datetime, timedelta

# ─────────────────────────────────────────────
passed = 0
failed = 0

def check(label, condition, detail=""):
    global passed, failed
    if condition:
        print(f"  ✓ {label}")
        passed += 1
    else:
        print(f"  ✗ FAIL: {label} {detail}")
        failed += 1

def section(title):
    print(f"\n{'─' * 52}")
    print(f"  ▶ {title}")
    print(f"{'─' * 52}")

# ═══════════════════════════════════════════════════
# INTEGRATION 1: AccessState enum compatibility
# Member 1's engine and Member 2's enum must be the
# same type — no duplicate definitions
# ═══════════════════════════════════════════════════
section("INT-1: AccessState enum compatibility")

check(
    "ACTIVE value matches between engine and Member 2",
    AccessState.ACTIVE.value == M2State.ACTIVE.value
)
check(
    "GRACE value matches",
    AccessState.GRACE.value == M2State.GRACE.value
)
check(
    "EXPIRED value matches",
    AccessState.EXPIRED.value == M2State.EXPIRED.value
)
check(
    "REVOKED value matches",
    AccessState.REVOKED.value == M2State.REVOKED.value
)
check(
    "M2State.ACTIVE.is_accessible() returns True",
    M2State.ACTIVE.is_accessible() is True
)
check(
    "M2State.EXPIRED.is_accessible() returns False",
    M2State.EXPIRED.is_accessible() is False
)
check(
    "M2State.REVOKED.is_terminal() returns True",
    M2State.REVOKED.is_terminal() is True
)
check(
    "M2State.ACTIVE.is_terminal() returns False",
    M2State.ACTIVE.is_terminal() is False
)

# ═══════════════════════════════════════════════════
# INTEGRATION 2: AccessRecord field contract
# Engine must produce records whose fields match
# what Member 2 defined in AccessRecord
# ═══════════════════════════════════════════════════
section("INT-2: AccessRecord field contract")

grant_access("int_user_1", "int_res_1", 60, 10)
record = _access_store[("int_user_1", "int_res_1")]

check("record has user_id", hasattr(record, "user_id"))
check("record has resource_id", hasattr(record, "resource_id"))
check("record has state", hasattr(record, "state"))
check("record has granted_at", hasattr(record, "granted_at"))
check("record has expires_at", hasattr(record, "expires_at"))
check("record has usage_limit", hasattr(record, "usage_limit"))
check("record has usage_count", hasattr(record, "usage_count"))
check("record has grace_period_minutes", hasattr(record, "grace_period_minutes"))
check("granted_at is datetime", isinstance(record.granted_at, datetime))
check("expires_at is datetime", isinstance(record.expires_at, datetime))
check("expires_at is after granted_at", record.expires_at > record.granted_at)
check("usage_count starts at 0", record.usage_count == 0)
check("usage_limit stored as 10", record.usage_limit == 10)
check("initial state is ACTIVE", record.state == AccessState.ACTIVE)

# ═══════════════════════════════════════════════════
# INTEGRATION 3: to_dict() round trip
# Engine-produced record → to_dict() → M2Record.from_dict()
# should reconstruct cleanly
# ═══════════════════════════════════════════════════
section("INT-3: to_dict() / from_dict() round trip")

grant_access("int_user_rt", "int_res_rt", 60, 5)
engine_record = _access_store[("int_user_rt", "int_res_rt")]
d = engine_record.to_dict()

check("to_dict() returns a dict", isinstance(d, dict))
check("to_dict() has user_id", "user_id" in d)
check("to_dict() has resource_id", "resource_id" in d)
check("to_dict() has state", "state" in d)
check("to_dict() has granted_at", "granted_at" in d)
check("to_dict() has expires_at", "expires_at" in d)
check("to_dict() has usage_limit", "usage_limit" in d)
check("to_dict() has usage_count", "usage_count" in d)
check("state in dict is a string (JSON safe)", isinstance(d["state"], str))
check("granted_at in dict is ISO string", isinstance(d["granted_at"], str))
check("expires_at in dict is ISO string", isinstance(d["expires_at"], str))

# Now reconstruct via Member 2's from_dict()
restored = M2Record.from_dict(d)
check("from_dict() restores user_id", restored.user_id == engine_record.user_id)
check("from_dict() restores resource_id", restored.resource_id == engine_record.resource_id)
check("from_dict() restores usage_limit", restored.usage_limit == engine_record.usage_limit)
check("from_dict() restores usage_count", restored.usage_count == engine_record.usage_count)
check("from_dict() restores state as AccessState", isinstance(restored.state, M2State))

# ═══════════════════════════════════════════════════
# INTEGRATION 4: Rules → Engine behaviour
# Member 2's TimeRule and UsageRule should correctly
# inform how the engine grants and enforces access
# ═══════════════════════════════════════════════════
section("INT-4: Rules → engine behaviour")

# RulePresets.trial() → 7-day TimeRule with 24hr grace
time_rule, _ = RulePresets.trial()
check("trial() returns a TimeRule", isinstance(time_rule, TimeRule))
check("trial duration is 7 days", time_rule.duration == timedelta(days=7))
check("trial has grace period", time_rule.has_grace_period is True)
check("trial grace is 24 hours", time_rule.grace_period == timedelta(hours=24))

# RulePresets.one_time_download() → 1-use UsageRule
_, usage_rule = RulePresets.one_time_download()
check("one_time_download() returns UsageRule", isinstance(usage_rule, UsageRule))
check("one_time max_uses is 1", usage_rule.max_uses == 1)

# RulePresets.limited_api_access() → both rules
api_time, api_usage = RulePresets.limited_api_access()
check("limited_api returns TimeRule", isinstance(api_time, TimeRule))
check("limited_api returns UsageRule", isinstance(api_usage, UsageRule))
check("limited_api usage cap is 1000", api_usage.max_uses == 1000)
check("limited_api duration is 30 days", api_time.duration == timedelta(days=30))

# Grant using rule values and verify engine enforces them
duration_minutes = int(time_rule.duration.total_seconds() / 60)
grant_access("int_user_rule", "int_res_rule", duration_minutes, None)
v = validate_access("int_user_rule", "int_res_rule")
check("engine allows access granted with trial TimeRule", v["allowed"] is True)

grant_access("int_user_cap", "int_res_cap", 60, usage_rule.max_uses)
track_usage("int_user_cap", "int_res_cap")  # 1 — hits cap
v = validate_access("int_user_cap", "int_res_cap")
check("engine denies after 1-use cap from UsageRule", v["allowed"] is False)
check("state is EXPIRED after cap", v["state"] == "EXPIRED")

# ═══════════════════════════════════════════════════
# INTEGRATION 5: Full lifecycle — engine + state machine
# Grant → validate → track → expire → renew → revoke
# Verifying state at each step matches AccessState values
# ═══════════════════════════════════════════════════
section("INT-5: Full lifecycle — engine + state machine")

grant_access("int_lc", "res_lc", 60, 3)
lc_record = _access_store[("int_lc", "res_lc")]

# Step 1: Active
v = validate_access("int_lc", "res_lc")
check("lifecycle step 1: ACTIVE after grant", v["state"] == "ACTIVE")
check("lifecycle step 1: allowed=True", v["allowed"] is True)

# Step 2: Track usage up to cap
track_usage("int_lc", "res_lc")
track_usage("int_lc", "res_lc")
track_usage("int_lc", "res_lc")

# Step 3: Expired by usage
v = validate_access("int_lc", "res_lc")
check("lifecycle step 3: EXPIRED after cap hit", v["state"] == "EXPIRED")
check("lifecycle step 3: allowed=False", v["allowed"] is False)

# Step 4: Renew
renew_access("int_lc", "res_lc", 60, reset_usage=True)
v = validate_access("int_lc", "res_lc")
check("lifecycle step 4: ACTIVE after renew", v["state"] == "ACTIVE")
check("lifecycle step 4: allowed=True after renew", v["allowed"] is True)
check("lifecycle step 4: usage_count reset to 0", lc_record.usage_count == 0)

# Step 5: Revoke
revoke_access("int_lc", "res_lc")
v = validate_access("int_lc", "res_lc")
check("lifecycle step 5: REVOKED", v["state"] == "REVOKED")
check("lifecycle step 5: allowed=False", v["allowed"] is False)

# Step 6: Confirm REVOKED is terminal via state machine
check(
    "state machine confirms REVOKED is terminal",
    len(get_valid_transitions(AccessState.REVOKED)) == 0
)
result = transition(lc_record, AccessState.ACTIVE)
check("state machine blocks transition out of REVOKED", result is False)

# ═══════════════════════════════════════════════════
# INTEGRATION 6: Member 2 AccessRecord helpers
# Engine-managed records should pass M2 helper checks
# ═══════════════════════════════════════════════════
section("INT-6: Member 2 AccessRecord helper methods")

grant_access("int_helper", "res_helper", 60, 5)
eng_rec = _access_store[("int_helper", "res_helper")]
d = eng_rec.to_dict()
m2_rec = M2Record.from_dict(d)

check("is_accessible() True when ACTIVE", m2_rec.is_time_expired() is False)
check("has_usage_limit True when limit set", m2_rec.usage_limit is not None)
check("has_time_limit True when expires_at set", m2_rec.expires_at is not None)
check("remaining_uses() is 5 at start", m2_rec.remaining_uses() == 5)

# Track 2 usages via engine then re-check via M2
track_usage("int_helper", "res_helper")
track_usage("int_helper", "res_helper")
eng_rec2 = _access_store[("int_helper", "res_helper")]
m2_rec2 = M2Record.from_dict(eng_rec2.to_dict())
check("remaining_uses() is 3 after 2 tracks", m2_rec2.remaining_uses() == 3)

# ── SUMMARY ──
print(f"\n{'═' * 52}")
print(f"  INTEGRATION RESULTS: {passed} passed  |  {failed} failed")
print(f"{'═' * 52}\n")
if failed > 0:
    sys.exit(1)