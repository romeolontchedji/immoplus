from django.urls import path

from .consumers import MessagerieConsumer

websocket_urlpatterns = [path("ws/v1/", MessagerieConsumer.as_asgi())]
