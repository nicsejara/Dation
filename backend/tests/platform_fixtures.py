"""Explicit authority for isolated service tests; not imported by the application."""
import unittest
import os
from unittest.mock import patch
from app.platform.context import RequestContext, bind

WORKSPACE='00000000-0000-4000-8000-00000000da71'
USER='10000000-0000-4000-8000-000000000001'
CONTEXT=RequestContext(USER,WORKSPACE,'admin',enabled_ddas=frozenset({'logistics'}))

class TenantTestCase(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        mode=patch.dict(os.environ,{"DATION_EXECUTION_MODE":"legacy"});mode.start();self.addCleanup(mode.stop)
        destination=patch("app.platform.repository.SUPABASE_URL","https://qa.invalid");destination.start();self.addCleanup(destination.stop)
        scope=bind(CONTEXT);scope.__enter__();self.addCleanup(scope.__exit__,None,None,None)
