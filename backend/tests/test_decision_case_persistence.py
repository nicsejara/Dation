import unittest
from unittest.mock import AsyncMock, patch

import httpx

from main import app
from app.auth import require_upload_access
from app.services import decision_case_service as cases


CASE_ID = "00000000-0000-4000-8000-000000000090"
ORDERS_ID = "00000000-0000-4000-8000-000000000001"
FLEET_ID = "00000000-0000-4000-8000-000000000002"
OTHER_FLEET_ID = "00000000-0000-4000-8000-000000000003"
RUN_ID = "00000000-0000-4000-8000-000000000010"


class DecisionCaseServiceTests(unittest.IsolatedAsyncioTestCase):
    def test_base_state_is_bound_to_immutable_data_pack(self):
        state = cases._base_state(CASE_ID, ORDERS_ID, FLEET_ID)
        self.assertEqual(state["id"], CASE_ID)
        self.assertEqual(
            state["signature"],
            f"{ORDERS_ID}:{FLEET_ID}",
        )
        self.assertEqual(
            state["inputs"],
            {
                "orders_dataset_id": ORDERS_ID,
                "fleet_dataset_id": FLEET_ID,
            },
        )
        self.assertEqual(
            state["nodes"]["logistics_assignment"]["status"],
            "available",
        )
        self.assertEqual(
            state["nodes"]["logistics_scheduling"]["status"],
            "locked",
        )

    def test_state_cannot_move_to_another_data_pack(self):
        state = cases._base_state(CASE_ID, ORDERS_ID, FLEET_ID)
        state["inputs"]["fleet_dataset_id"] = OTHER_FLEET_ID
        with self.assertRaisesRegex(ValueError, "otro dataset de Flota"):
            cases._validate_state(
                state,
                case_id=CASE_ID,
                orders_dataset_id=ORDERS_ID,
                fleet_dataset_id=FLEET_ID,
            )

    async def test_existing_case_cannot_be_rebound(self):
        row = {
            "id": CASE_ID,
            "orders_dataset_id": ORDERS_ID,
            "fleet_dataset_id": FLEET_ID,
        }
        with patch.object(
            cases,
            "get_case_row",
            AsyncMock(return_value=row),
        ):
            with self.assertRaisesRegex(ValueError, "otro Data Pack"):
                await cases.ensure_case(
                    CASE_ID,
                    ORDERS_ID,
                    OTHER_FLEET_ID,
                )

    async def test_approval_unlocks_next_node_without_losing_case_identity(self):
        state = cases._base_state(CASE_ID, ORDERS_ID, FLEET_ID)
        row = {
            "id": CASE_ID,
            "orders_dataset_id": ORDERS_ID,
            "fleet_dataset_id": FLEET_ID,
            "created_at": "2026-10-05T00:00:00+00:00",
            "state_json": state,
        }
        with patch.object(
            cases,
            "get_case_row",
            AsyncMock(return_value=row),
        ), patch.object(
            cases,
            "update_case",
            AsyncMock(return_value={"id": CASE_ID}),
        ) as update_case:
            await cases.record_node_state(
                CASE_ID,
                "logistics_assignment",
                run_id=RUN_ID,
                status="approved",
                approved_at="2026-10-05T01:00:00+00:00",
            )
            snapshot = update_case.await_args.kwargs["state"]
            self.assertEqual(snapshot["id"], CASE_ID)
            self.assertEqual(
                snapshot["nodes"]["logistics_assignment"]["run_id"],
                RUN_ID,
            )
            self.assertEqual(
                snapshot["nodes"]["logistics_assignment"]["status"],
                "approved",
            )
            self.assertEqual(
                snapshot["nodes"]["logistics_scheduling"]["status"],
                "available",
            )


class DecisionCaseHTTPTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.client = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://test",
        )
        app.dependency_overrides[require_upload_access] = lambda: "dation"

    async def asyncTearDown(self):
        app.dependency_overrides.clear()
        await self.client.aclose()

    async def test_list_and_restore_case_contract(self):
        hydrated = {
            "case": {
                "id": CASE_ID,
                "status": "active",
                "orders_dataset_id": ORDERS_ID,
                "fleet_dataset_id": FLEET_ID,
            },
            "decision_case": cases._base_state(
                CASE_ID,
                ORDERS_ID,
                FLEET_ID,
            ),
            "orders": {"id": ORDERS_ID, "dataset_type": "orders"},
            "fleet": {"id": FLEET_ID, "dataset_type": "fleet"},
        }
        with patch.object(
            cases,
            "list_cases",
            AsyncMock(return_value=[hydrated]),
        ) as list_cases, patch.object(
            cases,
            "get_case",
            AsyncMock(return_value=hydrated),
        ):
            response = await self.client.get("/api/decision-cases")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["cases"][0]["case"]["id"], CASE_ID)
            list_cases.assert_awaited_once_with(
                status="active",
                limit=50,
                offset=0,
            )

            restored = await self.client.get(
                f"/api/decision-cases/{CASE_ID}"
            )
            self.assertEqual(restored.status_code, 200)
            self.assertEqual(restored.json()["orders"]["id"], ORDERS_ID)
            self.assertEqual(restored.json()["fleet"]["id"], FLEET_ID)

    async def test_create_case_accepts_client_case_id_and_data_pack(self):
        with patch.object(
            cases,
            "ensure_case",
            AsyncMock(return_value={"id": CASE_ID, "status": "active"}),
        ) as ensure_case:
            response = await self.client.post(
                "/api/decision-cases",
                json={
                    "id": CASE_ID,
                    "orders_dataset_id": ORDERS_ID,
                    "fleet_dataset_id": FLEET_ID,
                },
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["case"]["id"], CASE_ID)
            ensure_case.assert_awaited_once_with(
                CASE_ID,
                ORDERS_ID,
                FLEET_ID,
                state=None,
            )


if __name__ == "__main__":
    unittest.main()
