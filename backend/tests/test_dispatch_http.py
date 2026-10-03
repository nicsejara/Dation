import unittest
from unittest.mock import AsyncMock, patch
import httpx
from main import app
from app.auth import require_upload_access
from app.services import dispatch_service

O='00000000-0000-4000-8000-000000000001'
F='00000000-0000-4000-8000-000000000002'


class DispatchHTTPTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.client=httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://test')

    async def asyncTearDown(self):
        app.dependency_overrides.clear();await self.client.aclose()

    async def test_authentication_required(self):
        for path in ['/api/dispatch/status','/api/system/supabase-check']:
            self.assertEqual((await self.client.get(path)).status_code,401)
        self.assertEqual((await self.client.post('/api/runs',json={})).status_code,401)

    async def test_preflight_and_new_run(self):
        app.dependency_overrides[require_upload_access]=lambda:'dation'
        with patch.object(dispatch_service,'check_inputs',AsyncMock(return_value={'valid':True})):
            r=await self.client.post('/api/runs/preflight',json={'orders_dataset_id':O,'fleet_dataset_id':F})
            self.assertEqual(r.status_code,200);self.assertTrue(r.json()['valid'])
        with patch.object(dispatch_service,'available',AsyncMock(return_value=True)),patch.object(dispatch_service,'execute',AsyncMock(return_value={'id':O,'status':'completed'})) as execute:
            r=await self.client.post('/api/runs?run_id='+O,json={'orders_dataset_id':O,'fleet_dataset_id':F,'configuration':{'objective':'min_time'}})
            self.assertEqual(r.status_code,200);self.assertEqual(execute.call_args.args[2]['weights']['time'],1)
        r=await self.client.post('/api/runs',json={'orders_dataset_id':O,'fleet_dataset_id':F,'configuration':{'mode':'custom','objective':'custom','weights':{'cost':1,'trips':1}}})
        self.assertEqual(r.status_code,422)

    async def test_run_accepts_decision_case_lineage(self):
        app.dependency_overrides[require_upload_access]=lambda:'dation'
        case_id='00000000-0000-4000-8000-000000000099'
        with patch.object(
            dispatch_service,
            'available',
            AsyncMock(return_value=True),
        ), patch.object(
            dispatch_service,
            'execute',
            AsyncMock(return_value={'id':O,'status':'completed'}),
        ) as execute:
            response=await self.client.post(
                '/api/runs?run_id='+O,
                json={
                    'orders_dataset_id':O,
                    'fleet_dataset_id':F,
                    'decision_case':{
                        'case_id':case_id,
                        'node_id':'logistics_assignment',
                    },
                },
            )
            self.assertEqual(response.status_code,200)
            self.assertEqual(
                execute.call_args.args[5],
                {
                    'case_id':case_id,
                    'node_id':'logistics_assignment',
                },
            )

    async def test_migration_gate_and_default(self):
        app.dependency_overrides[require_upload_access]=lambda:'dation'
        with patch.object(dispatch_service,'available',AsyncMock(return_value=False)):
            r=await self.client.post('/api/runs',json={'orders_dataset_id':O,'fleet_dataset_id':F})
            self.assertEqual(r.status_code,503)
        with patch.object(dispatch_service,'db',AsyncMock(return_value=None)) as db:
            self.assertEqual((await self.client.post('/api/datasets/'+F+'/default')).status_code,200)
            self.assertEqual(db.call_args.args[1],'rpc/set_default_fleet')

    async def test_typed_list(self):
        app.dependency_overrides[require_upload_access]=lambda:'dation'
        with patch.object(dispatch_service,'list_typed',AsyncMock(return_value=[{'id':F,'dataset_type':'fleet'}])):
            r=await self.client.get('/api/datasets?type=fleet')
            self.assertEqual(r.json()['items'][0]['dataset_type'],'fleet')

    async def test_typed_upload_validation_and_templates(self):
        app.dependency_overrides[require_upload_access]=lambda:'dation'
        from test_dispatch_engine import csv_bytes,COLUMNS,order
        contents=csv_bytes(COLUMNS,[order()])
        with patch('main.supabase_configured',return_value=True),patch.object(dispatch_service,'available',AsyncMock(return_value=True)):
            with patch.object(dispatch_service,'store_input',AsyncMock(return_value={'dataset':{'id':O},'duplicate':False})) as store:
                r=await self.client.post('/api/datasets/upload?dataset_type=orders',files={'file':('orders.csv',contents,'text/csv')})
                self.assertEqual(r.status_code,200)
                self.assertEqual(store.call_args.args[:3],('orders.csv',contents,'orders'))
            with patch.object(dispatch_service,'store_input',AsyncMock(side_effect=ValueError('Fila 2: dato inválido'))):
                r=await self.client.post('/api/datasets/upload?dataset_type=orders',files={'file':('orders.csv',contents,'text/csv')})
                self.assertEqual(r.status_code,422)
        response=await self.client.get('/api/dispatch/templates/fleet')
        self.assertEqual(response.status_code,200)
        self.assertIn('vehicle_id',response.text)
        self.assertIn('license_plate',response.text)
        self.assertNotIn('fleet_pool_id',response.text)
        self.assertNotIn('units_available',response.text)
        self.assertEqual((await self.client.get('/api/dispatch/templates/unknown')).status_code,404)
