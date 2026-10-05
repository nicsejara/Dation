import unittest
from unittest.mock import AsyncMock, patch

import httpx

from main import app
from app.auth import require_upload_access
from app.services import decision_case_service as cases
from app.services import run_service


CASE_ID = "00000000-0000-4000-8000-000000000090"
ORDERS_ID = "00000000-0000-4000-8000-000000000001"
FLEET_ID = "00000000-0000-4000-8000-000000000002"
ASSIGNMENT_1 = "00000000-0000-4000-8000-000000000011"
ASSIGNMENT_2 = "00000000-0000-4000-8000-000000000012"
SCHEDULING_1 = "00000000-0000-4000-8000-000000000021"


def run_row(
    run_id,
    node_id,
    *,
    created_at,
    upstream=None,
    status="completed",
    approved_at=None,
    superseded_at=None,
    superseded_by=None,
):
    return {
        "id": run_id,
        "decision_case_id": CASE_ID,
        "node_id": node_id,
        "upstream_run_id": upstream,
        "created_at": created_at,
        "started_at": created_at,
        "finished_at": created_at,
        "engine_name": "test",
        "engine_version": "1.0.0",
        "configuration_json": {},
        "status": status,
        "error_message": None,
        "duration_ms": 10,
        "schema_version": (
            "assignment_v1"
            if node_id == "logistics_assignment"
            else "scheduling_v1"
        ),
        "input_fingerprint": "input",
        "result_fingerprint": "result",
        "summary_json": {},
        "progress_json": {"stage": status},
        "approved_at": approved_at,
        "superseded_at": superseded_at,
        "superseded_by_run_id": superseded_by,
    }


class DecisionRunHistoryModelTests(unittest.IsolatedAsyncioTestCase):
    def test_insert_promotes_embedded_case_lineage(self):
        payload = run_service._promote_decision_history(
            {
                "id": SCHEDULING_1,
                "configuration_json": {
                    "decision_case": {
                        "case_id": CASE_ID,
                        "node_id": "logistics_scheduling",
                    },
                    "source_assignment_run_id": ASSIGNMENT_1,
                },
            }
        )
        self.assertEqual(payload["decision_case_id"], CASE_ID)
        self.assertEqual(payload["node_id"], "logistics_scheduling")
        self.assertEqual(payload["upstream_run_id"], ASSIGNMENT_1)

    def test_candidate_run_does_not_replace_current_approval(self):
        state = cases._base_state(CASE_ID, ORDERS_ID, FLEET_ID)
        history = [
            run_row(
                ASSIGNMENT_2,
                "logistics_assignment",
                created_at="2026-10-05T01:10:00+00:00",
            ),
            run_row(
                ASSIGNMENT_1,
                "logistics_assignment",
                created_at="2026-10-05T01:00:00+00:00",
                approved_at="2026-10-05T01:02:00+00:00",
            ),
        ]
        snapshot = cases._state_with_history(
            state,
            history,
            case_id=CASE_ID,
            orders_dataset_id=ORDERS_ID,
            fleet_dataset_id=FLEET_ID,
        )
        node = snapshot["nodes"]["logistics_assignment"]
        self.assertEqual(node["run_count"], 2)
        self.assertEqual(node["latest_run_id"], ASSIGNMENT_2)
        self.assertEqual(node["approved_run_id"], ASSIGNMENT_1)
        self.assertEqual(node["run_id"], ASSIGNMENT_1)
        self.assertEqual(node["status"], "approved")
        self.assertEqual(node["latest_execution_status"], "completed")

    def test_new_assignment_approval_marks_old_scheduling_stale(self):
        state = cases._base_state(CASE_ID, ORDERS_ID, FLEET_ID)
        history = [
            run_row(
                ASSIGNMENT_2,
                "logistics_assignment",
                created_at="2026-10-05T01:20:00+00:00",
                approved_at="2026-10-05T01:21:00+00:00",
            ),
            run_row(
                SCHEDULING_1,
                "logistics_scheduling",
                created_at="2026-10-05T01:10:00+00:00",
                upstream=ASSIGNMENT_1,
                approved_at="2026-10-05T01:11:00+00:00",
            ),
            run_row(
                ASSIGNMENT_1,
                "logistics_assignment",
                created_at="2026-10-05T01:00:00+00:00",
                approved_at="2026-10-05T01:02:00+00:00",
                superseded_at="2026-10-05T01:21:00+00:00",
                superseded_by=ASSIGNMENT_2,
            ),
        ]
        snapshot = cases._state_with_history(
            state,
            history,
            case_id=CASE_ID,
            orders_dataset_id=ORDERS_ID,
            fleet_dataset_id=FLEET_ID,
        )
        assignment = snapshot["nodes"]["logistics_assignment"]
        scheduling = snapshot["nodes"]["logistics_scheduling"]
        self.assertEqual(assignment["approved_run_id"], ASSIGNMENT_2)
        self.assertEqual(scheduling["approved_run_id"], SCHEDULING_1)
        self.assertEqual(scheduling["status"], "stale")
        self.assertEqual(scheduling["run_id"], SCHEDULING_1)

    async def test_superseded_upstream_cannot_seed_new_run(self):
        source = run_row(
            ASSIGNMENT_1,
            "logistics_assignment",
            created_at="2026-10-05T01:00:00+00:00",
            approved_at="2026-10-05T01:02:00+00:00",
            superseded_at="2026-10-05T01:20:00+00:00",
            superseded_by=ASSIGNMENT_2,
        )
        with patch.object(
            cases,
            "get_run",
            AsyncMock(return_value=source),
        ):
            with self.assertRaisesRegex(ValueError, "ya no es"):
                await cases.validate_upstream_run(
                    CASE_ID,
                    "logistics_scheduling",
                    ASSIGNMENT_1,
                )

    async def test_version_approval_uses_atomic_rpc(self):
        candidate = run_row(
            ASSIGNMENT_2,
            "logistics_assignment",
            created_at="2026-10-05T01:20:00+00:00",
        )
        approved = {
            **candidate,
            "approved_at": "2026-10-05T01:21:00+00:00",
        }
        with patch.object(
            cases,
            "get_run",
            AsyncMock(return_value=candidate),
        ), patch.object(
            cases,
            "_db",
            AsyncMock(return_value=[approved]),
        ) as db:
            result = await cases.approve_run_version(
                ASSIGNMENT_2,
                case_id=CASE_ID,
                node_id="logistics_assignment",
            )
        self.assertEqual(result["approved_at"], "2026-10-05T01:21:00+00:00")
        db.assert_awaited_once_with(
            "POST",
            "rpc/approve_decision_run_version",
            body={
                "target_run_id": ASSIGNMENT_2,
                "target_case_id": CASE_ID,
                "target_node_id": "logistics_assignment",
            },
        )


class DecisionRunHistoryHTTPTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.client = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://test",
        )
        app.dependency_overrides[require_upload_access] = lambda: "dation"

    async def asyncTearDown(self):
        app.dependency_overrides.clear()
        await self.client.aclose()

    async def test_history_endpoint_is_scoped_by_case_and_node(self):
        payload = {
            "case_id": CASE_ID,
            "node_id": "logistics_assignment",
            "total": 2,
            "limit": 20,
            "offset": 0,
            "summary": {
                "run_count": 2,
                "latest_run_id": ASSIGNMENT_2,
                "approved_run_id": ASSIGNMENT_1,
                "status": "approved",
            },
            "runs": [],
        }
        with patch.object(
            cases,
            "get_run_history",
            AsyncMock(return_value=payload),
        ) as history:
            response = await self.client.get(
                f"/api/decision-cases/{CASE_ID}/runs",
                params={
                    "node_id": "logistics_assignment",
                    "limit": 20,
                },
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["total"], 2)
        history.assert_awaited_once_with(
            CASE_ID,
            node_id="logistics_assignment",
            limit=20,
            offset=0,
        )


if __name__ == "__main__":
    unittest.main()
