# consumers.py
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.layers import get_channel_layer

class MyWebSocketConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.group_name = "satellite_progress"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        await self.send(text_data=json.dumps({"message": "WebSocket Connected"}))

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        await self.send(text_data=json.dumps({"message": f"Received: {data}"}))

    async def send_notification(self, event):
        message = event["message"]
        await self.send(text_data=json.dumps({
            "type": message.get("type"),
            "startProgress": message.get("startProgress"),
            "endProgress": message.get("endProgress"),
            "message": message.get("message")
        }))