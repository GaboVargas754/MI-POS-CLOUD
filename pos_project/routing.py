from django.urls import path

from core.consumers import NotificacionesConsumer


websocket_urlpatterns = [
    path('ws/notificaciones/', NotificacionesConsumer.as_asgi()),
]
