import os
import django
import json

from channels.generic.websocket import AsyncWebsocketConsumer
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack

from django.core.asgi import get_asgi_application

from api.routing import websocket_urlpatterns

from channels.generic.websocket import AsyncWebsocketConsumer

from .models import Room
from .serializers import RoomSerializer

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter(websocket_urlpatterns)
    ),
})

class RoomConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.channel_layer.group_add("rooms", self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard("rooms", self.channel_name)

    async def receive(self, text_data):
        await self.send_room_update()

    async def send_room_update(self):
        rooms = Room.objects.all()
        serializer = RoomSerializer(rooms, many=True)
        await self.send(text_data=json.dumps({'rooms': serializer.data}))

    async def room_update(self, event):
        await self.send_room_update()

