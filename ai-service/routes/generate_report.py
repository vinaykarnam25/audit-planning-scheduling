from flask import Blueprint, Response, jsonify, request

from extensions import limiter
from routes.sanitisation import sanitise_request_body
from services.ai_workflows import generate_report, stream_report_events


generate_report_bp = Blueprint(
    "generate_report", __name__, url_prefix="/generate-report"
)


@generate_report_bp.post("")
@limiter.limit("10 per minute")
def generate_report_endpoint():
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

    wants_stream = request.args.get("stream", "").lower() == "true" or (
        "text/event-stream" in request.headers.get("Accept", "")
    )

    if wants_stream:
        def event_stream():
            for event in stream_report_events(text):
                yield event

        return Response(
            event_stream(),
            mimetype="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )

    report = generate_report(text)
    return jsonify(report), 200
