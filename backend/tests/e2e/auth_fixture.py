"""Loopback-only asymmetric Auth fixture. No production keys or email delivery."""
import json
import time
import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
USER_A='10000000-0000-4000-8000-000000000001'
USER_B='10000000-0000-4000-8000-000000000002'
VIEWER='10000000-0000-4000-8000-000000000003'
DISABLED='10000000-0000-4000-8000-000000000004'
def generate(directory,issuer):
    key=ec.generate_private_key(ec.SECP256R1())
    private=key.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.NoEncryption())
    path=directory/'auth-fixture-key.pem';path.write_bytes(private);path.chmod(0o600)
    jwk=json.loads(jwt.algorithms.ECAlgorithm.to_jwk(key.public_key()));jwk.update(kid='dation-local-test',alg='ES256',use='sig')
    (directory/'auth-fixture-jwks.json').write_text(json.dumps({'keys':[jwk]}));return private
def token(private,issuer,user=USER_A,*,expires=3600):
    now=int(time.time())
    return jwt.encode({'sub':user,'iss':issuer+'/auth/v1','aud':'authenticated','role':'authenticated',
        'iat':now,'exp':now+expires,'email':'user-'+user[-1]+'@example.test',
        'user_metadata':{'first_name':'Synthetic','last_name':'User'}},private,algorithm='ES256',headers={'kid':'dation-local-test'})
