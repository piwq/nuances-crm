import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
django_asgi_app = get_asgi_application()

def get_application():
    from common.middleware import JWTAuthMiddleware
    from apps.chat.routing import websocket_urlpatterns
    return ProtocolTypeRouter({
        "http": django_asgi_app,
        "websocket": JWTAuthMiddleware(
            URLRouter(
                websocket_urlpatterns
            )
        ),
    })

application = get_application()
