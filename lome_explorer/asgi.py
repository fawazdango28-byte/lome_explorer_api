import os
import django

# IMPORTANT : Configurer Django AVANT tout import
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lome_explorer.settings')
django.setup()

from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack

# Importer les routes WebSocket APRÈS django.setup()
from FastAPI.routing import websocket_urlpatterns

# Application ASGI Django classique
django_asgi_app = get_asgi_application()

# Application ASGI complète avec WebSocket
application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AuthMiddlewareStack(
        URLRouter(websocket_urlpatterns)
    ),
})