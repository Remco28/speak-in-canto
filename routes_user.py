from __future__ import annotations

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from models import UserVoicePin, db


user_bp = Blueprint("user", __name__, url_prefix="/api/user")


@user_bp.route("/voice-pins", methods=["GET"])
@login_required
def get_voice_pins():
    rows = (
        UserVoicePin.query.filter_by(user_id=current_user.id)
        .order_by(UserVoicePin.created_at.asc())
        .all()
    )
    return jsonify(
        {
            "pins": [
                {
                    "voice_id": row.voice_id,
                    "voice_mode": row.voice_mode,
                }
                for row in rows
            ]
        }
    )


@user_bp.route("/voice-pins/toggle", methods=["POST"])
@login_required
def toggle_voice_pin():
    payload = request.get_json(silent=True) or {}
    voice_id = str(payload.get("voice_id") or "").strip()
    voice_mode = str(payload.get("voice_mode") or "standard").strip()
    if not voice_id:
        return jsonify({"error": "voice_id is required"}), 400
    if voice_mode not in ("standard", "high_quality"):
        return jsonify({"error": "voice_mode is invalid"}), 400

    existing = UserVoicePin.query.filter_by(user_id=current_user.id, voice_id=voice_id).first()
    if existing:
        db.session.delete(existing)
        db.session.commit()
        return jsonify({"pinned": False}), 200

    row = UserVoicePin(user_id=current_user.id, voice_id=voice_id, voice_mode=voice_mode)
    db.session.add(row)
    db.session.commit()
    return jsonify({"pinned": True}), 200
