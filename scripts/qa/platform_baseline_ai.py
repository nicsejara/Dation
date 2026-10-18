"""Verify interpreter persistence against an owned, disposable local stack.

Run with backend dependencies, Docker and the sandbox images available:
    .venv/bin/python scripts/qa/platform_baseline_ai.py --artifacts /tmp/dation-ai-baseline

The existing E2E sandbox creates its own PostgreSQL/PostgREST, Storage gateway,
API and worker. It clears external credentials. An HTTP provider on loopback
returns fixed QA text; this verifies integration and persistence, not LLM quality.
All containers and processes created here are removed on exit.
"""
import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import subprocess
import sys
import threading
from uuid import uuid4


REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "backend/tests/e2e"))
from sandbox import Sandbox, wait_for  # noqa: E402
from test_workflow import WorkflowTests  # noqa: E402


SUMMARY = {
    "executive_summary": "Resumen sintético para verificar persistencia del intérprete.",
    "recommendation": "Revisar la evidencia publicada.",
    "why_recommended": "El cálculo permanece en el motor determinístico.",
    "business_impact": {
        "cost": "Según evidencia.",
        "trips": "Según evidencia.",
        "distance": "Según evidencia.",
    },
    "key_drivers": ["Evidencia publicada."],
    "tradeoffs": ["No se recalcula el plan."],
    "assumptions": ["Fixture local de QA."],
    "caveats": ["No se verifica calidad de un proveedor real."],
    "suggested_questions": ["¿Qué límites tiene la evidencia?"],
}


def provider_handler(calls):
    class Provider(BaseHTTPRequestHandler):
        def do_POST(self):
            if self.path != "/v1/chat/completions":
                self.send_error(404)
                return
            payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            structured = bool(payload.get("response_format"))
            calls.append({"structured": structured, "model": payload["model"]})
            content = (
                json.dumps(SUMMARY, ensure_ascii=False)
                if structured
                else "Respuesta sintética persistida; revisar la evidencia publicada."
            )
            body = json.dumps({
                "id": "synthetic-local",
                "choices": [{"message": {"content": content}}],
                "usage": {"prompt_tokens": 5, "completion_tokens": 4, "total_tokens": 9},
            }).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    return Provider


def verify(provider, calls):
    with Sandbox() as sandbox:
        # Reuse the existing workflow's real HTTP admission/worker/approval helpers.
        workflow = WorkflowTests("runTest")
        workflow.s = sandbox
        case, orders, fleet = workflow.case()
        sandbox.start_worker()
        assignment = workflow.finish(workflow.admit(workflow.body(case, orders, fleet)))
        workflow.approve(assignment["id"], case)
        scheduling = workflow.finish(workflow.admit(workflow.body(
            case, orders, fleet, "logistics_scheduling", assignment["id"],
        )))
        workflow.approve(scheduling["id"], case, "logistics_scheduling")
        wait_for(
            lambda: workflow.checked(sandbox.db.get("decision_case_reconciliations")) == [],
            "settled approvals",
        )
        sandbox.stop(sandbox.worker)

        def business_snapshot():
            return {
                table: workflow.checked(sandbox.db.get(table, params={"order": "id.asc"}))
                for table in ("decision_runs", "decision_cases", "decision_approval_events")
            }

        before = business_snapshot()
        for run in (assignment, scheduling):
            response = sandbox.api_client.post("/api/runs/" + run["id"] + "/explain")
            assert response.status_code == 503, response.text
        assert calls == []

        sandbox.stop(sandbox.api)
        sandbox.env.update(
            LLM_API_KEY="synthetic-loopback-only",
            LLM_BASE_URL=f"http://127.0.0.1:{provider.server_port}/v1",
            LLM_PROVIDER="openai",
            LLM_MODEL="synthetic-baseline",
        )
        sandbox.start_api()
        saved = []
        for run in (assignment, scheduling):
            prefix = "/api/runs/" + run["id"]
            explanation = workflow.checked(sandbox.api_client.post(prefix + "/explain"))
            assert explanation["explanation"] == SUMMARY, explanation
            turn = str(uuid4())
            question = "¿Qué límites tiene la evidencia?"
            answer = workflow.checked(sandbox.api_client.post(
                prefix + "/chat", json={"question": question, "turn_id": turn},
            ))
            persisted = workflow.checked(sandbox.api_client.get(prefix + "/interpretation"))
            assert persisted["explanation"]["id"] == explanation["id"]
            assert len(persisted["messages"]) == 2, persisted
            assert [message["role"] for message in persisted["messages"]] == ["user", "assistant"]
            assert all(message["turn_id"] == turn for message in persisted["messages"])
            saved.append((prefix, turn, question, answer, persisted))
        assert len(calls) == 4, calls

        sandbox.stop(sandbox.api)
        sandbox.start_api()
        for prefix, turn, question, answer, persisted in saved:
            restored = workflow.checked(sandbox.api_client.get(prefix + "/interpretation"))
            assert restored == persisted
            replay = workflow.checked(sandbox.api_client.post(
                prefix + "/chat", json={"question": question, "turn_id": turn},
            ))
            assert replay == answer
        assert len(calls) == 4, "Restoration or replay unexpectedly called provider"
        assert business_snapshot() == before, "Interpreter mutated runs, cases or approvals"

        return {
            "passed": True,
            "source_sha": subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=REPO, text=True,
            ).strip(),
            "datasets_uploaded": 2,
            "approved_decisions": 2,
            "saved_explanations": 2,
            "saved_chat_turns": 2,
            "provider": "deterministic HTTP loopback; no real inference",
            "provider_calls": len(calls),
            "api_restart_restore": True,
            "idempotent_chat_replay_without_inference": True,
            "business_state_unchanged": True,
            "unconfigured_llm_returns_503": True,
            "scope": "owned loopback PostgreSQL/PostgREST/Storage/API/worker only; no production writes",
        }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifacts", type=Path, help="Optional local directory for the JSON report.")
    args = parser.parse_args()
    calls = []
    provider = ThreadingHTTPServer(("127.0.0.1", 0), provider_handler(calls))
    thread = threading.Thread(target=provider.serve_forever, daemon=True)
    thread.start()
    try:
        report = verify(provider, calls)
        if args.artifacts:
            args.artifacts.mkdir(parents=True, exist_ok=True)
            (args.artifacts / "ia-restore-report.json").write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps(report))
    finally:
        provider.shutdown()
        provider.server_close()
        thread.join(timeout=5)


if __name__ == "__main__":
    main()
