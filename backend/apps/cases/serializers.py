from rest_framework import serializers
from apps.accounts.serializers import UserSerializer
from apps.clients.serializers import ClientListSerializer
from .models import Case


class CaseSerializer(serializers.ModelSerializer):
    assigned_lawyers_detail = UserSerializer(source='assigned_lawyers', many=True, read_only=True)
    lead_lawyer_detail = UserSerializer(source='lead_lawyer', read_only=True)
    client_detail = ClientListSerializer(source='client', read_only=True)
    documents_count = serializers.SerializerMethodField()
    tasks_count = serializers.SerializerMethodField()
    time_entries_count = serializers.SerializerMethodField()

    class Meta:
        model = Case
        fields = [
            'id', 'uuid', 'title', 'case_number', 'client', 'client_detail',
            'status', 'category', 'description',
            'court_name', 'court_case_number',
            'assigned_lawyers', 'assigned_lawyers_detail',
            'lead_lawyer', 'lead_lawyer_detail',
            'opened_at', 'closed_at', 'expected_close_date',
            'hourly_rate',
            'created_at', 'updated_at',
            'documents_count', 'tasks_count', 'time_entries_count',
        ]
        read_only_fields = ['uuid', 'case_number', 'created_at', 'updated_at']

    def get_documents_count(self, obj):
        return obj.documents.count()

    def get_tasks_count(self, obj):
        return obj.tasks.filter(status__in=['todo', 'in_progress']).count()

    def get_time_entries_count(self, obj):
        return obj.time_entries.count()

    def create(self, validated_data):
        assigned_lawyers = validated_data.pop('assigned_lawyers', [])
        validated_data['created_by'] = self.context['request'].user
        case = Case.objects.create(**validated_data)
        case.assigned_lawyers.set(assigned_lawyers)
        return case

    def update(self, instance, validated_data):
        assigned_lawyers = validated_data.pop('assigned_lawyers', None)
        instance = super().update(instance, validated_data)
        if assigned_lawyers is not None:
            instance.assigned_lawyers.set(assigned_lawyers)
        return instance


class CaseListSerializer(serializers.ModelSerializer):
    client_name = serializers.SerializerMethodField()
    lead_lawyer_name = serializers.SerializerMethodField()
    open_tasks_count = serializers.SerializerMethodField()

    class Meta:
        model = Case
        fields = [
            'id', 'uuid', 'title', 'case_number', 'client', 'client_name',
            'status', 'category',
            'lead_lawyer', 'lead_lawyer_name',
            'opened_at', 'expected_close_date',
            'open_tasks_count',
        ]

    def get_client_name(self, obj):
        return str(obj.client)

    def get_lead_lawyer_name(self, obj):
        return obj.lead_lawyer.get_full_name() if obj.lead_lawyer else None

    def get_open_tasks_count(self, obj):
        return obj.tasks.filter(status__in=['todo', 'in_progress']).count()
