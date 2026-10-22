"""Explicit preconditions for existing engine/evidence regression scenarios.

The gate tests opt out and verify missing assignments themselves. These helpers
use the real checked API; they never disable a gate or alter a case's policy.
"""
from auth_fixture import USER_A

def checked(response):
    assert response.status_code==200,response.text
    return response.json()

def set_roles(client,uid,roles):
    member=next(m for m in checked(client.get('/api/platform/team'))['members'] if m['user_id']==uid)
    return checked(client.patch('/api/platform/team/members/'+uid+'/responsibilities',json={
        'expected_updated_at':member['updated_at'],'business_roles':roles}))

def prepare_stage(client,cid,node,*,approval=False,uid=USER_A):
    snapshot=checked(client.get(f'/api/platform/decisions/{cid}/responsibilities'))
    if not snapshot['gates_enforced']:return
    if not snapshot.get('attributes_applied'):
        case=checked(client.get(f'/api/platform/decisions/{cid}'))
        checked(client.patch(f'/api/platform/decisions/{cid}',json={'expected_updated_at':case['updated_at'],'label':case.get('label') or 'Synthetic Case','category':case.get('category') or 'simulation'}))
    for stage in ([node] if approval else ['data_owner',node]):
        value=snapshot['stages'][stage]
        if value['owner']:continue
        snapshot=checked(client.put(f'/api/platform/decisions/{cid}/responsibilities/{stage}',json={'expected_updated_at':value['updated_at'],'owner_user_id':uid}))
