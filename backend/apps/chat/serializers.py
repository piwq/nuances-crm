from rest_framework import serializers
from .models import ChatMessage
from apps.accounts.serializers import UserSerializer

class ChatMessageSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    recipient = UserSerializer(read_only=True)

    class Meta:
        model = ChatMessage
        fields = ['id', 'user', 'recipient', 'text', 'is_read', 'created_at']
        read_only_fields = ['id', 'created_at', 'user']
