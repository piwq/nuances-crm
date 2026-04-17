from rest_framework import serializers
from .models import Task, Event


class TaskSerializer(serializers.ModelSerializer):
    assigned_to_name = serializers.SerializerMethodField()
    case_title = serializers.SerializerMethodField()

    class Meta:
        model = Task
        fields = [
            'id', 'title', 'description', 'case', 'case_title',
            'assigned_to', 'assigned_to_name',
            'priority', 'status', 'due_date', 'completed_at',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['completed_at', 'created_at', 'updated_at']

    def get_assigned_to_name(self, obj):
        return obj.assigned_to.get_full_name() if obj.assigned_to else None

    def get_case_title(self, obj):
        return str(obj.case) if obj.case else None

    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)


class EventSerializer(serializers.ModelSerializer):
    attendees_detail = serializers.SerializerMethodField()
    case_title = serializers.SerializerMethodField()

    class Meta:
        model = Event
        fields = [
            'id', 'title', 'event_type', 'case', 'case_title',
            'description', 'location',
            'start_datetime', 'end_datetime', 'all_day',
            'attendees', 'attendees_detail',
            'created_at',
        ]
        read_only_fields = ['created_at']

    def get_attendees_detail(self, obj):
        return [
            {'id': u.id, 'name': u.get_full_name() or u.username}
            for u in obj.attendees.all()
        ]

    def get_case_title(self, obj):
        return str(obj.case) if obj.case else None

    def create(self, validated_data):
        attendees = validated_data.pop('attendees', [])
        validated_data['created_by'] = self.context['request'].user
        event = Event.objects.create(**validated_data)
        event.attendees.set(attendees)
        return event

    def update(self, instance, validated_data):
        attendees = validated_data.pop('attendees', None)
        instance = super().update(instance, validated_data)
        if attendees is not None:
            instance.attendees.set(attendees)
        return instance
