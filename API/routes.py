"""
routes.py
---------
REST API endpoints for the Access Expiry Engine.

Member 3 – API Layer

All endpoints accept JSON and return JSON.
This layer only calls engine functions — it never modifies engine logic.

Endpoints
---------
GET  /health                → API health check
POST /grant-access          → Grant a user access to a resource
POST /validate-access       → Check if a user currently has valid access
POST /track-usage           → Increment usage counter for a user's access
POST /renew-access          → Extend an existing access record
POST /revoke-access         → Manually revoke a user's access
GET  /get-record            → Fetch the full access record for a user/resource
"""

from flask import Blueprint, request, jsonify
from engine.access_engine import (
    grant_access,
    validate_access,
    track_usage,
    renew_access,
    revoke_access,
    get_access_record,
)

routes_blueprint = Blueprint("routes", __name__)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def get_json():
    """Safely parse JSON body from request."""
    data = request.get_json(silent=True)
    if data is None:
        return None, jsonify({
            "success": False,
            "error": "Request body must be valid JSON with Content-Type: application/json"
        }), 400
    return data, None, None


def require_fields(data: dict, *fields):
    """Check that all required fields are present in the request body."""
    missing = [f for f in fields if f not in data or data[f] is None]
    if missing:
        return jsonify({
            "success": False,
            "error": f"Missing required fields: {', '.join(missing)}"
        }), 400
    return None


# ─────────────────────────────────────────────────────────────────────────────
# GET /health
# ─────────────────────────────────────────────────────────────────────────────

@routes_blueprint.route("/health", methods=["GET"])
def health():
    """
    Health check endpoint.
    Used by Member 4's demo to confirm the API is reachable.

    Response:
        200 { status: "ok", message: "API is running" }
    """
    return jsonify({
        "status": "ok",
        "message": "Access Expiry Engine API is running"
    }), 200


# ─────────────────────────────────────────────────────────────────────────────
# POST /grant-access
# ─────────────────────────────────────────────────────────────────────────────

@routes_blueprint.route("/grant-access", methods=["POST"])
def api_grant_access():
    """
    Grant a user access to a resource.

    Request body:
        {
            "user_id":          str  (required),
            "resource_id":      str  (required),
            "duration_seconds": int  (required) — how long access lasts,
            "usage_limit":      int  (optional) — max uses, omit for unlimited
        }

    Response 200:
        { "success": true, "message": "Access granted", "record": { ... } }

    Response 400:
        { "success": false, "error": "..." }
    """
    data, err, code = get_json()
    if err:
        return err, code

    validation_error = require_fields(data, "user_id", "resource_id", "duration_seconds")
    if validation_error:
        return validation_error

    user_id         = str(data["user_id"])
    resource_id     = str(data["resource_id"])
    duration_seconds = int(data["duration_seconds"])
    usage_limit     = data.get("usage_limit")

    if duration_seconds <= 0:
        return jsonify({"success": False, "error": "duration_seconds must be greater than 0"}), 400

    if usage_limit is not None:
        usage_limit = int(usage_limit)
        if usage_limit <= 0:
            return jsonify({"success": False, "error": "usage_limit must be greater than 0"}), 400

    # Convert seconds to minutes for the engine
    duration_minutes = duration_seconds // 60 or 1

    result = grant_access(user_id, resource_id, duration_minutes, usage_limit)

    return jsonify({
        "success": result["success"],
        "message": result.get("message"),
        "record":  result.get("access"),
    }), 200


# ─────────────────────────────────────────────────────────────────────────────
# POST /validate-access
# ─────────────────────────────────────────────────────────────────────────────

@routes_blueprint.route("/validate-access", methods=["POST"])
def api_validate_access():
    """
    Check if a user currently has valid access to a resource.
    Also updates state to GRACE or EXPIRED if limits have been hit.

    Request body:
        {
            "user_id":     str (required),
            "resource_id": str (required)
        }

    Response 200:
        { "allowed": bool, "state": str, "reason": str, "record": { ... } }

    Response 400:
        { "success": false, "error": "..." }
    """
    data, err, code = get_json()
    if err:
        return err, code

    validation_error = require_fields(data, "user_id", "resource_id")
    if validation_error:
        return validation_error

    user_id     = str(data["user_id"])
    resource_id = str(data["resource_id"])

    result = validate_access(user_id, resource_id)

    # Also pull the full record for Member 4's UI
    record_result = get_access_record(user_id, resource_id)

    return jsonify({
        "allowed": result["allowed"],
        "state":   result["state"],
        "reason":  result["reason"],
        "record":  record_result.get("access"),
    }), 200


# ─────────────────────────────────────────────────────────────────────────────
# POST /track-usage
# ─────────────────────────────────────────────────────────────────────────────

@routes_blueprint.route("/track-usage", methods=["POST"])
def api_track_usage():
    """
    Increment the usage counter for a user's access to a resource.
    Will fail gracefully if access is already expired or revoked.

    Request body:
        {
            "user_id":     str (required),
            "resource_id": str (required)
        }

    Response 200:
        { "success": bool, "usage_count": int, "usage_limit": int|null,
          "state": str, "record": { ... } }

    Response 400:
        { "success": false, "error": "..." }
    """
    data, err, code = get_json()
    if err:
        return err, code

    validation_error = require_fields(data, "user_id", "resource_id")
    if validation_error:
        return validation_error

    user_id     = str(data["user_id"])
    resource_id = str(data["resource_id"])

    result = track_usage(user_id, resource_id)

    record_result = get_access_record(user_id, resource_id)

    return jsonify({
        "success":     result["success"],
        "message":     result.get("message"),
        "usage_count": result.get("usage_count"),
        "usage_limit": result.get("usage_limit"),
        "state":       result.get("state"),
        "record":      record_result.get("access"),
    }), 200


# ─────────────────────────────────────────────────────────────────────────────
# POST /renew-access
# ─────────────────────────────────────────────────────────────────────────────

@routes_blueprint.route("/renew-access", methods=["POST"])
def api_renew_access():
    """
    Extend an existing access record's expiry time.
    Optionally reset the usage counter.

    Request body:
        {
            "user_id":                str  (required),
            "resource_id":            str  (required),
            "extra_duration_seconds": int  (required) — seconds to add,
            "reset_usage":            bool (optional, default false)
        }

    Response 200:
        { "success": bool, "message": str, "record": { ... } }

    Response 400:
        { "success": false, "error": "..." }
    """
    data, err, code = get_json()
    if err:
        return err, code

    validation_error = require_fields(data, "user_id", "resource_id", "extra_duration_seconds")
    if validation_error:
        return validation_error

    user_id                  = str(data["user_id"])
    resource_id              = str(data["resource_id"])
    extra_duration_seconds   = int(data["extra_duration_seconds"])
    reset_usage              = bool(data.get("reset_usage", False))

    if extra_duration_seconds <= 0:
        return jsonify({"success": False, "error": "extra_duration_seconds must be greater than 0"}), 400

    extra_duration_minutes = extra_duration_seconds // 60 or 1

    result = renew_access(user_id, resource_id, extra_duration_minutes, reset_usage)

    return jsonify({
        "success": result["success"],
        "message": result.get("message"),
        "record":  result.get("access"),
    }), 200


# ─────────────────────────────────────────────────────────────────────────────
# POST /revoke-access
# ─────────────────────────────────────────────────────────────────────────────

@routes_blueprint.route("/revoke-access", methods=["POST"])
def api_revoke_access():
    """
    Manually revoke a user's access to a resource immediately.

    Request body:
        {
            "user_id":     str (required),
            "resource_id": str (required)
        }

    Response 200:
        { "success": bool, "message": str, "record": { ... } }

    Response 400:
        { "success": false, "error": "..." }
    """
    data, err, code = get_json()
    if err:
        return err, code

    validation_error = require_fields(data, "user_id", "resource_id")
    if validation_error:
        return validation_error

    user_id     = str(data["user_id"])
    resource_id = str(data["resource_id"])

    result = revoke_access(user_id, resource_id)

    return jsonify({
        "success": result["success"],
        "message": result.get("message"),
        "record":  result.get("access"),
    }), 200


# ─────────────────────────────────────────────────────────────────────────────
# GET /get-record
# ─────────────────────────────────────────────────────────────────────────────

@routes_blueprint.route("/get-record", methods=["GET"])
def api_get_record():
    """
    Fetch the full access record for a user/resource pair.
    Useful for Member 4's demo to display current state.

    Query params:
        ?user_id=user_42&resource_id=course_101

    Response 200:
        { "success": bool, "record": { ... } }

    Response 404:
        { "success": false, "error": "No record found" }
    """
    user_id     = request.args.get("user_id")
    resource_id = request.args.get("resource_id")

    if not user_id or not resource_id:
        return jsonify({
            "success": False,
            "error": "Query params user_id and resource_id are required"
        }), 400

    result = get_access_record(user_id, resource_id)

    if not result["success"]:
        return jsonify({
            "success": False,
            "error":   "No access record found for this user/resource pair"
        }), 404

    return jsonify({
        "success": True,
        "record":  result.get("access"),
    }), 200