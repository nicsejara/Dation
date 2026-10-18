"""Private responses must never survive in browser/shared HTTP caches."""
from starlette.datastructures import MutableHeaders

class PrivateResponses:
    def __init__(self,app):
        self.app=app

    async def __call__(self,scope,receive,send):
        private=scope['type']=='http' and scope.get('path','').startswith(('/api/','/auth/','/app'))
        async def private_send(message):
            if private and message['type']=='http.response.start':
                headers=MutableHeaders(scope=message)
                headers['Cache-Control']='no-store'
                headers['X-Content-Type-Options']='nosniff'
                if scope['path'].startswith('/auth/'):
                    headers['Referrer-Policy']='no-referrer'
            await send(message)
        await self.app(scope,receive,private_send)
