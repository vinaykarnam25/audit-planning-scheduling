def test_health_returns_ok(client):
    response = client.get("/health")
    assert response.status_code == 200
    body = response.get_json()
    assert body["status"] == "ok"
    assert "rag_document_count" in body


def test_describe_returns_structured_payload(client):
    response = client.post("/describe", json={"text": "High-risk audit with multiple dependencies"})
    assert response.status_code == 200
    body = response.get_json()
    assert "description" in body
    assert "context_sources" in body


def test_describe_rejects_empty_text(client):
    response = client.post("/describe", json={"text": ""})
    assert response.status_code == 400


def test_recommend_returns_three_items(client):
    response = client.post("/recommend", json={"text": "Audit delayed by missing evidence"})
    assert response.status_code == 200
    body = response.get_json()
    assert len(body["recommendations"]) == 3


def test_generate_report_returns_sections(client):
    response = client.post("/generate-report", json={"text": "Prepare report for overdue audit"})
    assert response.status_code == 200
    body = response.get_json()
    assert "title" in body
    assert "recommendations" in body


def test_generate_report_streams_sse(client):
    response = client.post(
        "/generate-report?stream=true",
        json={"text": "Prepare report for overdue audit"},
        headers={"Accept": "text/event-stream"},
    )
    assert response.status_code == 200
    assert response.mimetype == "text/event-stream"
    assert b"data:" in response.data


def test_analyse_document_returns_findings(client):
    response = client.post(
        "/analyse-document",
        json={"text": "Kickoff delayed. Dependency on approval remains open."},
    )
    assert response.status_code == 200
    body = response.get_json()
    assert "summary" in body
    assert len(body["findings"]) >= 1


def test_batch_process_accepts_up_to_twenty_items(client):
    response = client.post("/batch-process", json={"items": ["one", "two"]})
    assert response.status_code == 200
    body = response.get_json()
    assert len(body["results"]) == 2


def test_batch_process_rejects_too_many_items(client):
    response = client.post("/batch-process", json={"items": [str(i) for i in range(21)]})
    assert response.status_code == 400


def test_query_returns_answer_and_sources(client):
    response = client.post(
        "/query",
        json={"question": "What should be checked first in audit planning?"},
    )
    assert response.status_code == 200
    body = response.get_json()
    assert "answer" in body
    assert "sources" in body
