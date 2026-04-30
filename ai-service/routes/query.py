from flask import Blueprint, jsonify, request

from routes.sanitisation import sanitise_request_body
from services.ai_workflows import build_rag_context, generate_query_answer


query_bp = Blueprint("query", __name__, url_prefix="/query")


@query_bp.post("")
def query():
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

    question = result["clean_body"].get("question", "").strip()
    if not question:
        return jsonify({"error": "Field 'question' is required.", "status": 400}), 400

    context_items = build_rag_context(question, limit=3)
    answer = generate_query_answer(question, context_items)
    return (
        jsonify(
            {
                "question": question,
                "answer": answer.get("answer", ""),
                "sources": [item["source"] for item in context_items],
                "meta": answer.get("meta", {}),
            }
        ),
        200,
    )
