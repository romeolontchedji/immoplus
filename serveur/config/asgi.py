"""Point d'entrée ASGI : HTTP (Django) et WebSocket (Channels, routes ajoutées en phase 5)."""

import os

from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
application_http = get_asgi_application()

application = ProtocolTypeRouter({"http": application_http, "websocket": URLRouter([])})
