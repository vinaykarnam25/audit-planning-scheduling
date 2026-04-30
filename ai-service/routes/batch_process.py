import time

from flask import Blueprint, jsonify, request

from routes.sanitisation import sanitise_request_body
from services.ai_workflows import generate_description


batch_process_bp = Blueprint("batch_process", __name__, url_prefix="/batch-process")


@batch_process_bp.post("")
def batch_process():
    body = request.get_json(silent=True)
    if body is None:
        return jsonify({"error": "Request body must be valid JSON", "status": 400}), 400

    items = body.get("items", [])
    if not isinstance(items, list) or not items or len(items) > 20:
        return (
            jsonify(
                {
                    "error": "Field 'items' must be a non-empty array with at most 20 entries.",
                    "status": 400,
                }
            ),
            400,
        )

    results = []
    for item in items:
        sanitised = sanitise_request_body({"text": item})
        if not sanitised["is_safe"]:
            return (
                jsonify(
                    {
                        "error": sanitised["reason"],
                        "field": "items",
                        "status": 400,
                    }
                ),
                400,
            )
        text = sanitised["clean_body"].get("text", "").strip()
        if not text:
            return jsonify({"error": "Each batch item must be non-empty.", "status": 400}), 400

        time.sleep(0.1)
        result = generate_description(text)
        results.append(
            {
                "input": text,
                "description": result.get("description", ""),
                "meta": result.get("meta", {}),
            }
        )

    return jsonify({"results": results}), 200
