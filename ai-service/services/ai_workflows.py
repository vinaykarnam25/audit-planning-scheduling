from __future__ import annotations

import json
from datetime import UTC, datetime

from services.groq_client import GroqClientService
from services.prompt_loader import load_prompt_template
from services.rag_service import RagService


groq_client = GroqClientService()
rag_service = RagService()


def _compact_text(text: str, limit: int = 1200) -> str:
    compact = " ".join(text.split())
    return compact[:limit]


def generate_description(item_text: str, context: str = "") -> dict:
    template = load_prompt_template("describe_prompt.txt")
    fallback = {
        "description": (
            "This audit planning item requires structured review, scheduling alignment, "
            "stakeholder coordination, and clear follow-up actions."
        ),
        "tone": "professional",
    }
    return groq_client.generate_json(
        system_prompt=template,
        user_prompt=f"Context: {_compact_text(context or 'N/A', 500)}\nInput: {_compact_text(item_text, 600)}",
        fallback_payload=fallback,
    )


def generate_recommendations(item_text: str) -> dict:
    template = load_prompt_template("recommend_prompt.txt")
    fallback = {
        "recommendations": [
            {
                "action_type": "plan",
                "description": "Confirm scope, owners, and target dates for this audit item.",
                "priority": "high",
            },
            {
                "action_type": "review",
                "description": "Assess dependencies, risks, and documentation gaps before execution.",
                "priority": "medium",
            },
            {
                "action_type": "track",
                "description": "Monitor milestones weekly and escalate blockers early.",
                "priority": "medium",
            },
        ]
    }
    return groq_client.generate_json(
        system_prompt=template,
        user_prompt=f"Input: {_compact_text(item_text, 700)}",
        fallback_payload=fallback,
    )


def generate_report(item_text: str) -> dict:
    template = load_prompt_template("generate_report_prompt.txt")
    fallback = {
        "title": "Audit Planning Report",
        "executive_summary": "This item needs coordinated planning, timeline control, and risk visibility.",
        "overview": "The report summarises the audit item, major concerns, and practical next steps.",
        "top_items": [
            "Confirm audit scope and affected stakeholders.",
            "Review upcoming deadlines and resource constraints.",
            "Track unresolved risks or dependencies.",
        ],
        "recommendations": [
            "Assign a primary owner and due date.",
            "Review evidence readiness before execution.",
            "Escalate timeline risk if dependencies remain open.",
        ],
    }
    report = groq_client.generate_json(
        system_prompt=template,
        user_prompt=f"Input: {_compact_text(item_text, 700)}",
        fallback_payload=fallback,
    )
    report.setdefault("meta", {})
    report["meta"]["stream_ready"] = True
    return report


def stream_report_events(item_text: str) -> list[str]:
    report = generate_report(item_text)
    ordered_sections = [
        ("title", report.get("title", "")),
        ("executive_summary", report.get("executive_summary", "")),
        ("overview", report.get("overview", "")),
        ("top_items", report.get("top_items", [])),
        ("recommendations", report.get("recommendations", [])),
    ]
    events = []
    for section, value in ordered_sections:
        payload = {"section": section, "content": value}
        events.append(f"data: {json.dumps(payload)}\n\n")
    events.append(f"data: {json.dumps({'done': True, 'meta': report.get('meta', {})})}\n\n")
    return events


def generate_query_answer(question: str, context_items: list[dict]) -> dict:
    template = load_prompt_template("query_prompt.txt")
    context_block = "\n".join(item["content"] for item in context_items) or "No context available."
    fallback = {
        "answer": "Based on the available audit planning knowledge, review scope, dependencies, owners, and deadlines before proceeding.",
    }
    return groq_client.generate_json(
        system_prompt=template,
        user_prompt=f"Question: {_compact_text(question, 300)}\nContext:\n{_compact_text(context_block, 900)}",
        fallback_payload=fallback,
    )


def analyse_document_text(document_text: str) -> dict:
    findings = []
    lines = [line.strip() for line in document_text.splitlines() if line.strip()]
    risk_words = {"delay", "risk", "blocked", "late", "overdue", "dependency", "escalate"}
    for line in lines[:8]:
        lowered = line.lower()
        severity = "high" if any(word in lowered for word in {"overdue", "blocked", "escalate"}) else "medium" if any(word in lowered for word in risk_words) else "low"
        findings.append(
            {
                "finding": line[:180],
                "risk_level": severity,
                "insight_type": "risk" if severity in {"high", "medium"} else "observation",
            }
        )

    if not findings:
        findings.append(
            {
                "finding": "No significant insights were identified from the submitted text.",
                "risk_level": "low",
                "insight_type": "observation",
            }
        )

    summary = "Document contains planning signals that should be reviewed for ownership, timing, and dependencies."
    return {
        "summary": summary,
        "findings": findings,
        "generated_at": datetime.now(UTC).isoformat(),
    }


def ensure_rag_seeded() -> dict:
    return rag_service.seed_from_directory()


def build_rag_context(query: str, limit: int = 3) -> list[dict]:
    return rag_service.build_context(query, limit=limit)
