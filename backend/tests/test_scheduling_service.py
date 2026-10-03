import unittest
from unittest.mock import AsyncMock, patch

from app.services import dispatch_service


CASE_ID = "00000000-0000-4000-8000-000000000010"
RUN_ID = "00000000-0000-4000-8000-000000000011"
ORDERS_ID = "00000000-0000-4000-8000-000000000012"
FLEET_ID = "00000000-0000-4000-8000-000000000013"


class SchedulingServiceTests(
    unittest.IsolatedAsyncioTestCase
):
    async def test_scheduling_rejects_unapproved_assignment(
        self,
    ):
        source_run = {
            "id": RUN_ID,
            "status": "completed",
            "orders_dataset_id": ORDERS_ID,
            "fleet_dataset_id": FLEET_ID,
            "result_json": {
                "schema_version": "assignment_v1",
                "decision_case": {
                    "case_id": CASE_ID,
                    "node_id": "logistics_assignment",
                },
                "handoff": {
                    "assignment_fingerprint": "assignment-fingerprint",
                },
            },
        }

        with patch.object(
            dispatch_service,
            "load_inputs",
            AsyncMock(
                return_value=(
                    {"id": ORDERS_ID},
                    {"id": FLEET_ID},
                    b"orders",
                    b"fleet",
                )
            ),
        ), patch.object(
            dispatch_service,
            "get_run",
            AsyncMock(
                return_value=source_run
            ),
        ):
            with self.assertRaisesRegex(
                ValueError,
                "Primero aprobá Assignment",
            ):
                await dispatch_service.execute(
                    ORDERS_ID,
                    FLEET_ID,
                    {
                        "strategy": "service_first",
                        "use_delivery_due_dates": True,
                    },
                    {},
                    decision_case={
                        "case_id": CASE_ID,
                        "node_id": "logistics_scheduling",
                    },
                    source_run_id=RUN_ID,
                )

    async def test_approval_preserves_result_fingerprint(
        self,
    ):
        original_fingerprint = (
            "stable-math-fingerprint"
        )
        run = {
            "id": RUN_ID,
            "status": "completed",
            "configuration_json": {
                "objective": "min_trips",
                "decision_case": {
                    "case_id": CASE_ID,
                    "node_id": "logistics_assignment",
                },
            },
            "result_json": {
                "schema_version": "assignment_v1",
                "result_fingerprint": original_fingerprint,
                "decision_case": {
                    "case_id": CASE_ID,
                    "node_id": "logistics_assignment",
                },
            },
        }

        async def fake_db(
            method,
            path,
            *,
            params=None,
            body=None,
        ):
            self.assertEqual(
                method,
                "PATCH",
            )
            self.assertEqual(
                path,
                "decision_runs",
            )
            self.assertEqual(
                body["result_json"][
                    "result_fingerprint"
                ],
                original_fingerprint,
            )
            self.assertEqual(
                body["result_json"][
                    "decision_case"
                ]["status"],
                "approved",
            )
            self.assertTrue(
                body["result_json"][
                    "decision_case"
                ]["approved_at"]
            )
            self.assertEqual(
                body["configuration_json"][
                    "decision_case"
                ]["status"],
                "approved",
            )
            return [
                {
                    **run,
                    **body,
                }
            ]

        with patch.object(
            dispatch_service,
            "get_run",
            AsyncMock(
                return_value=run
            ),
        ), patch.object(
            dispatch_service,
            "db",
            AsyncMock(
                side_effect=fake_db
            ),
        ):
            approved = (
                await dispatch_service
                .approve_decision_run(
                    RUN_ID,
                    case_id=CASE_ID,
                    node_id=(
                        "logistics_assignment"
                    ),
                )
            )

        self.assertEqual(
            approved["result_json"][
                "result_fingerprint"
            ],
            original_fingerprint,
        )
        self.assertEqual(
            approved["result_json"][
                "decision_case"
            ]["status"],
            "approved",
        )


if __name__ == "__main__":
    unittest.main()
