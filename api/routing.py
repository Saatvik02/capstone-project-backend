from django.urls import path
from api.consumers import MyWebSocketConsumer  # Import consumer

websocket_urlpatterns = [
    path("ws/progress", MyWebSocketConsumer.as_asgi()),
]
