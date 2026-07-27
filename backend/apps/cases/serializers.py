from rest_framework import serializers
from apps.accounts.serializers import UserPublicSerializer
from apps.clients.serializers import ClientListSerializer
from .models import Case, CaseNote


class CaseSerializer(serializers.ModelSerializer):
    assigned_lawyers_detail = UserPublicSerializer(source='assigned_lawyers', many=True, read_only=True)
    lead_lawyer_detail = UserPublicSerializer(source='lead_lawyer', read_only=True)
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
            'opposing_party', 'opposing_party_inn',
            'assigned_lawyers', 'assigned_lawyers_detail',
            'lead_lawyer', 'lead_lawyer_detail',
            'opened_at', 'closed_at', 'expected_close_date',
            'key_deadline', 'key_deadline_note',
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
        user = self.context['request'].user
        validated_data['created_by'] = user
        case = Case(**validated_data)
        case._notify_skip_user = user.pk  # о собственных действиях не уведомляем
        if user.is_lawyer and not case.lead_lawyer_id:
            # иначе юрист-создатель сразу теряет доступ к своему делу:
            # скоупинг видимости учитывает только ведущего и назначенных
            case.lead_lawyer = user
        case.save()
        case.assigned_lawyers.set(assigned_lawyers)
        # помощник ведущим не становится, но доступ к заведённому делу сохраняет
        if user.is_scoped and case.lead_lawyer_id != user.pk and \
                not case.assigned_lawyers.filter(pk=user.pk).exists():
            case.assigned_lawyers.add(user)
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
            'opened_at', 'expected_close_date', 'key_deadline',
            'open_tasks_count',
        ]

    def get_client_name(self, obj):
        return str(obj.client)

    def get_lead_lawyer_name(self, obj):
        return obj.lead_lawyer.get_full_name() if obj.lead_lawyer else None

    def get_open_tasks_count(self, obj):
        annotated = getattr(obj, 'open_tasks_annotated', None)
        if annotated is not None:
            return annotated
        return obj.tasks.filter(status__in=['todo', 'in_progress']).count()


class CaseNoteSerializer(serializers.ModelSerializer):
    author_name = serializers.SerializerMethodField()
    author_initials = serializers.SerializerMethodField()

    class Meta:
        model = CaseNote
        fields = ['id', 'text', 'author', 'author_name', 'author_initials', 'created_at', 'updated_at']
        read_only_fields = ['author', 'created_at', 'updated_at']

    def get_author_name(self, obj):
        return obj.author.get_full_name() or obj.author.username if obj.author else '—'

    def get_author_initials(self, obj):
        if not obj.author:
            return '?'
        u = obj.author
        if u.first_name and u.last_name:
            return f'{u.first_name[0]}{u.last_name[0]}'
        return (u.username or '?')[0].upper()

    def create(self, validated_data):
        validated_data['author'] = self.context['request'].user
        return super().create(validated_data)
