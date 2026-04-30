from datetime import UTC, datetime

from flask import Blueprint, jsonify, request

from routes.sanitisation import sanitise_request_body
from services.ai_workflows import build_rag_context, generate_description


describe_bp = Blueprint("describe", __name__, url_prefix="/describe")


@describe_bp.post("")
def describe():
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

    context_items = build_rag_context(text, limit=2)
    description = generate_description(
        text,
        context="\n".join(item["content"] for item in context_items),
    )

    return (
        jsonify(
            {
                "input": text,
                "description": description.get("description", ""),
                "tone": description.get("tone", "professional"),
                "context_sources": [item["source"] for item in context_items],
                "meta": description.get("meta", {}),
                "generated_at": datetime.now(UTC).isoformat(),
            }
        ),
        200,
    )
