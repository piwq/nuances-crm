from rest_framework import serializers
from .models import Client, ContactPerson


class ContactPersonSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactPerson
        fields = ['id', 'first_name', 'last_name', 'middle_name', 'position', 'phone', 'email', 'is_primary']


class ClientSerializer(serializers.ModelSerializer):
    display_name = serializers.ReadOnlyField()
    contact_persons = ContactPersonSerializer(many=True, read_only=True)
    cases_count = serializers.SerializerMethodField()

    class Meta:
        model = Client
        fields = [
            'id', 'uuid', 'client_type', 'display_name',
            # individual
            'first_name', 'last_name', 'middle_name', 'date_of_birth', 'passport_number', 'tax_id',
            # legal
            'company_name', 'registration_number', 'legal_address',
            # shared
            'email', 'phone', 'address', 'notes',
            'created_at', 'updated_at', 'contact_persons', 'cases_count',
        ]
        read_only_fields = ['uuid', 'created_at', 'updated_at']

    def get_cases_count(self, obj):
        return obj.cases.count()

    def validate(self, data):
        client_type = data.get('client_type', getattr(self.instance, 'client_type', None))
        if client_type == Client.TYPE_INDIVIDUAL:
            if not data.get('last_name') and not getattr(self.instance, 'last_name', None):
                raise serializers.ValidationError({'last_name': 'Обязательное поле для физлица.'})
        elif client_type == Client.TYPE_LEGAL:
            if not data.get('company_name') and not getattr(self.instance, 'company_name', None):
                raise serializers.ValidationError({'company_name': 'Обязательное поле для юрлица.'})
        return data

    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)


class ClientListSerializer(serializers.ModelSerializer):
    display_name = serializers.ReadOnlyField()
    cases_count = serializers.SerializerMethodField()

    class Meta:
        model = Client
        fields = ['id', 'uuid', 'client_type', 'display_name', 'email', 'phone', 'created_at', 'cases_count']

    def get_cases_count(self, obj):
        return obj.cases.count()
