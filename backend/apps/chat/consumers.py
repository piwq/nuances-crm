import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import ChatMessage
from .serializers import ChatMessageSerializer

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope['user']
        if not self.user.is_authenticated:
            await self.close()
            return

        self.recipient_id = self.scope['url_route']['kwargs']['recipient_id']
        
        # Consistent stable room name for two users
        ids = sorted([int(self.user.id), int(self.recipient_id)])
        self.room_group_name = f'chat_{ids[0]}_{ids[1]}'

        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, 'room_group_name'):
            # Leave room group
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )

    async def receive(self, text_data):
        data = json.loads(text_data)
        event_type = data.get('type', 'chat_message')
        
        if event_type == 'typing':
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_typing',
                    'user_id': self.user.id,
                    'is_typing': data.get('is_typing', True)
                }
            )
            return

        message_text = data.get('message')
        if not message_text:
            return

        # Save message to database
        saved_message = await self.save_message(self.user, self.recipient_id, message_text)
        
        # Broadcast message to room group
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': saved_message
            }
        )

    async def chat_message(self, event):
        message = event['message']
        await self.send(text_data=json.dumps({
            'type': 'chat_message',
            'message': message
        }))

    async def chat_typing(self, event):
        await self.send(text_data=json.dumps({
            'type': 'typing',
            'user_id': event['user_id'],
            'is_typing': event['is_typing']
        }))

    @database_sync_to_async
    def save_message(self, user, recipient_id, text):
        from .models import ChatMessage
        from .serializers import ChatMessageSerializer
        from django.contrib.auth import get_user_model
        
        User = get_user_model()
        recipient = User.objects.get(id=recipient_id)
        
        msg = ChatMessage.objects.create(user=user, recipient=recipient, text=text)
        return ChatMessageSerializer(msg).data
