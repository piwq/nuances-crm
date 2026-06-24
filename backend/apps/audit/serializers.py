from rest_framework import serializers
from .models import ActivityLog


class ActivityLogSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()

    class Meta:
        model = ActivityLog
        fields = ['id', 'action', 'resource_type', 'description', 'timestamp', 'user_name']

    def get_user_name(self, obj):
        return obj.user.get_full_name() or obj.user.username if obj.user else 'Система'
