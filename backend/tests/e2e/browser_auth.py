"""Use the actual BFF/cookie/Bearer flow against the owned Auth contract fixture."""
async def authenticate(context,base):
    result=await context.request.post(base+'/auth/login',headers={'Origin':base},
        data={'email':'user-1@example.test','password':'dispatch-e2e-private'})
    assert result.status==200,await result.text()


async def api_get(context,url):
    from urllib.parse import urlsplit
    parsed=urlsplit(url);base=parsed.scheme+'://'+parsed.netloc
    response=await context.request.post(base+'/auth/session',headers={'Origin':base})
    assert response.status==200,await response.text()
    identity=await response.json()
    return await context.request.get(url,headers={'Authorization':'Bearer '+identity['access_token']})
