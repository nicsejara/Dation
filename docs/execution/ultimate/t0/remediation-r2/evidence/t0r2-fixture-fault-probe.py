import asyncio,json
from test_navigation import NavigationTests
async def main():
 NavigationTests.setUpClass();b=NavigationTests()
 try:
  await b.asyncSetUp();original=b._route_api
  async def failed(route):raise KeyError('T0-R2 intentional fixture fault')
  b._route_api=failed
  result=await b.page.goto(f'http://127.0.0.1:{b.port}/api/fixture-fault')
  assert result.status==500,result.status
  assert len(b.fixture_errors)==1 and 'T0-R2 intentional fixture fault' in b.fixture_errors[0],b.fixture_errors
  b.fixture_errors.pop();b._route_api=original
  await b.asyncTearDown();print(json.dumps({'intentional_fixture_exception_recorded':True,'response_status':500,'teardown_completed':True}))
 finally:NavigationTests.tearDownClass()
asyncio.run(main())
