from flask import Flask, jsonify
from werkzeug.exceptions import HTTPException

from extensions import limiter
from routes.analyse_document import analyse_document_bp
from routes.batch_process import batch_process_bp
from routes.describe import describe_bp
from routes.generate_report import generate_report_bp
from routes.query import query_bp
from routes.recommend import recommend_bp
from services.rag_service import RagService


app = Flask(__name__)
app.config["JSON_SORT_KEYS"] = False

limiter.init_app(app)

rag_service = RagService()
if not rag_service.has_documents() or rag_service.document_count() < 10:
    rag_service.seed_from_directory()
rag_service.preload_embedding_model()

app.register_blueprint(describe_bp)
app.register_blueprint(recommend_bp)
app.register_blueprint(generate_report_bp)
app.register_blueprint(analyse_document_bp)
app.register_blueprint(batch_process_bp)
app.register_blueprint(query_bp)


@app.after_request
def add_security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Content-Security-Policy"] = "default-src 'self'"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Server"] = "Tool-21-AI-Service"
    return response


@app.errorhandler(429)
def rate_limit_exceeded(_error):
    return (
        jsonify(
            {
                "error": "Too Many Requests",
                "message": "You have exceeded the allowed request limit. Please slow down.",
                "retry_after": 60,
                "retry_after_unit": "seconds",
                "status": 429,
            }
        ),
        429,
    )


@app.errorhandler(HTTPException)
def handle_http_exception(error: HTTPException):
    return jsonify({"error": error.description, "status": error.code}), error.code


@app.errorhandler(Exception)
def handle_unexpected_exception(error: Exception):
    return jsonify({"error": str(error), "status": 500}), 500


@app.route("/health", methods=["GET"])
@limiter.exempt
def health():
    return (
        jsonify(
            {
                "status": "ok",
                "message": "AI service is running",
                "rag_seeded": rag_service.has_documents(),
                "rag_document_count": rag_service.document_count(),
                "embedding_model_preloaded": rag_service.model_preloaded(),
                "security_headers": {
                    "X-Content-Type-Options": "nosniff",
                    "X-Frame-Options": "DENY",
                    "Content-Security-Policy": "default-src 'self'",
                    "X-XSS-Protection": "1; mode=block",
                },
                "rate_limits": {
                    "default": "30 requests per minute",
                    "generate_report": "10 requests per minute",
                },
            }
        ),
        200,
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
