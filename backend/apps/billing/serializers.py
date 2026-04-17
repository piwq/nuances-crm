from rest_framework import serializers
from .models import TimeEntry, Invoice, InvoiceItem


class TimeEntrySerializer(serializers.ModelSerializer):
    amount = serializers.ReadOnlyField()
    lawyer_name = serializers.SerializerMethodField()
    case_title = serializers.SerializerMethodField()
    is_invoiced = serializers.SerializerMethodField()

    class Meta:
        model = TimeEntry
        fields = [
            'id', 'case', 'case_title', 'lawyer', 'lawyer_name',
            'date', 'hours', 'description', 'hourly_rate',
            'is_billable', 'invoice', 'is_invoiced', 'amount', 'created_at',
        ]
        read_only_fields = ['created_at']

    def get_lawyer_name(self, obj):
        return obj.lawyer.get_full_name() if obj.lawyer else None

    def get_case_title(self, obj):
        return str(obj.case) if obj.case else None

    def get_is_invoiced(self, obj):
        return obj.invoice_id is not None

    def create(self, validated_data):
        if 'lawyer' not in validated_data:
            validated_data['lawyer'] = self.context['request'].user
        if 'hourly_rate' not in validated_data and validated_data.get('case'):
            case = validated_data['case']
            validated_data['hourly_rate'] = case.hourly_rate or 0
        return super().create(validated_data)


class InvoiceItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvoiceItem
        fields = ['id', 'description', 'quantity', 'unit_price', 'amount', 'time_entry']
        read_only_fields = ['amount']


class InvoiceSerializer(serializers.ModelSerializer):
    items = InvoiceItemSerializer(many=True, read_only=True)
    client_name = serializers.SerializerMethodField()
    case_title = serializers.SerializerMethodField()
    time_entries_count = serializers.SerializerMethodField()

    class Meta:
        model = Invoice
        fields = [
            'id', 'invoice_number', 'case', 'case_title', 'client', 'client_name',
            'status', 'issue_date', 'due_date', 'paid_date',
            'subtotal', 'tax_rate', 'tax_amount', 'total',
            'notes', 'items', 'time_entries_count',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['invoice_number', 'tax_amount', 'total', 'created_at', 'updated_at']

    def get_client_name(self, obj):
        return str(obj.client)

    def get_case_title(self, obj):
        return str(obj.case)

    def get_time_entries_count(self, obj):
        return obj.time_entries.count()

    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)


class InvoiceListSerializer(serializers.ModelSerializer):
    client_name = serializers.SerializerMethodField()
    case_title = serializers.SerializerMethodField()

    class Meta:
        model = Invoice
        fields = [
            'id', 'invoice_number', 'case', 'case_title', 'client', 'client_name',
            'status', 'issue_date', 'due_date', 'total', 'created_at',
        ]

    def get_client_name(self, obj):
        return str(obj.client)

    def get_case_title(self, obj):
        return str(obj.case)
