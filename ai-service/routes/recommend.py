from flask import Blueprint, jsonify, request

from routes.sanitisation import sanitise_request_body
from services.ai_workflows import generate_recommendations


recommend_bp = Blueprint("recommend", __name__, url_prefix="/recommend")


@recommend_bp.post("")
def recommend():
    body = request.get_json(silent=True)
    if body is None:
        return jsonify({"error": "Request body must be valid JSON", "status": 400}), 400

    result = sanitise_request_body(body)
    if not result["is_safe"]:
        return (
            jsonify(
                {
                    "error": result["reason"],
                    "field": result["field"],
                    "status": 400,
                }
            ),
            400,
        )

    text = result["clean_body"].get("text", "").strip()
    if not text:
        return jsonify({"error": "Field 'text' is required.", "status": 400}), 400

    response = generate_recommendations(text)
    return (
        jsonify(
            {
                "input": text,
                "recommendations": response.get("recommendations", []),
                "meta": response.get("meta", {}),
            }
        ),
        200,
    )
