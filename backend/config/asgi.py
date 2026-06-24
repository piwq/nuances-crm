import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
django_asgi_app = get_asgi_application()

def get_application():
    from common.middleware import JWTAuthMiddleware
    from apps.chat.routing import websocket_urlpatterns as chat_ws
    from apps.notifications.routing import websocket_urlpatterns as notif_ws
    return ProtocolTypeRouter({
        "http": django_asgi_app,
        "websocket": JWTAuthMiddleware(
            URLRouter(chat_ws + notif_ws)
        ),
    })

application = get_application()
