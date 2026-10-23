"""Internal moves must remain compatible with lazy imports from existing tabs."""
import json
from pathlib import Path
import unittest

import httpx

from main import app


STATIC = Path(__file__).resolve().parents[1] / 'app/static'


class FoundationAssetsTests(unittest.IsolatedAsyncioTestCase):
    async def test_previous_module_urls_redirect_to_the_same_canonical_source(self):
        redirects = json.loads((STATIC / 'contracts/foundation-module-redirects.json').read_text())
        self.assertTrue(redirects)
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test') as client:
            for old, new in redirects.items():
                with self.subTest(module=old):
                    self.assertFalse((STATIC / old).exists(), 'Do not keep duplicate module implementations')
                    self.assertTrue((STATIC / new).resolve().is_relative_to(STATIC.resolve()))
                    self.assertNotIn(new, redirects, 'Compatibility must not redirect through another alias')
                    response = await client.get('/static/' + old + '?v=existing-tab')
                    self.assertEqual(response.status_code, 307)
                    self.assertEqual(response.headers['location'], '/static/' + new)
                    self.assertEqual(response.headers['cache-control'], 'no-cache')
                    canonical = await client.get(response.headers['location'])
                    self.assertEqual(canonical.status_code, 200)
                    self.assertEqual(canonical.content, (STATIC / new).read_bytes())
                    self.assertEqual(canonical.headers['cache-control'], 'no-cache')
