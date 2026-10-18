"""Synthetic UI server. Signature/tenant enforcement is tested against the real stack."""
import main
async def fixture_identity(token):
    if token!='browser-layout-fixture':
        from fastapi import HTTPException
        raise HTTPException(401,'Invalid browser fixture')
    return {'sub':'10000000-0000-4000-8000-000000000001'}
main.verify=fixture_identity
app=main.app
