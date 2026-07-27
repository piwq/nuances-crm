from rest_framework import serializers
from apps.accounts.models import CustomUser
from common.scoping import user_can_access_case
from .models import (
    TimeEntry, Invoice, InvoiceItem, InvoicePayment, RecurringInvoice, CaseExpense,
)


def _check_case_access(serializer, case):
    request = serializer.context.get('request')
    if request and case and not user_can_access_case(request.user, case):
        raise serializers.ValidationError('Дело недоступно.')
    return case


class TimeEntrySerializer(serializers.ModelSerializer):
    amount = serializers.ReadOnlyField()
    # оба поля подставляются сервером (текущий пользователь и ставка дела),
    # поэтому клиент (в т.ч. таймер) вправе их не присылать
    lawyer = serializers.PrimaryKeyRelatedField(
        queryset=CustomUser.objects.all(), required=False)
    hourly_rate = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=False)
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

    def validate_case(self, case):
        return _check_case_access(self, case)

    def validate(self, attrs):
        # юрист пишет время только от своего имени; выбирать юриста может админ
        request = self.context.get('request')
        if request and request.user.is_scoped:
            attrs['lawyer'] = request.user
        return attrs

    def create(self, validated_data):
        if not validated_data.get('lawyer'):
            validated_data['lawyer'] = self.context['request'].user
        if validated_data.get('hourly_rate') is None:
            case = validated_data.get('case')
            validated_data['hourly_rate'] = (case.hourly_rate if case else None) or 0
        return super().create(validated_data)


class InvoiceItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvoiceItem
        fields = ['id', 'invoice', 'description', 'quantity', 'unit_price', 'amount', 'time_entry']
        read_only_fields = ['amount']

    def validate_invoice(self, invoice):
        _check_case_access(self, invoice.case)
        return invoice


class CaseExpenseSerializer(serializers.ModelSerializer):
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    case_title = serializers.SerializerMethodField()
    is_invoiced = serializers.SerializerMethodField()

    class Meta:
        model = CaseExpense
        fields = ['id', 'case', 'case_title', 'date', 'category', 'category_display',
                  'description', 'amount', 'is_billable', 'receipt', 'invoice',
                  'is_invoiced', 'created_at']
        read_only_fields = ['invoice', 'created_at']

    def get_case_title(self, obj):
        return str(obj.case)

    def get_is_invoiced(self, obj):
        return obj.invoice_id is not None

    def validate_case(self, case):
        return _check_case_access(self, case)

    def validate_amount(self, amount):
        if amount <= 0:
            raise serializers.ValidationError('Сумма расхода должна быть больше нуля.')
        return amount

    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)


class InvoicePaymentSerializer(serializers.ModelSerializer):
    method_display = serializers.CharField(source='get_method_display', read_only=True)
    created_by_name = serializers.SerializerMethodField()

    class Meta:
        model = InvoicePayment
        fields = ['id', 'invoice', 'amount', 'paid_date', 'method', 'method_display',
                  'note', 'created_by_name', 'created_at']
        read_only_fields = ['created_at']

    def get_created_by_name(self, obj):
        return obj.created_by.get_full_name() if obj.created_by else None

    def validate_invoice(self, invoice):
        _check_case_access(self, invoice.case)
        return invoice

    def validate_amount(self, amount):
        if amount <= 0:
            raise serializers.ValidationError('Сумма платежа должна быть больше нуля.')
        return amount

    def validate(self, attrs):
        invoice = attrs.get('invoice') or getattr(self.instance, 'invoice', None)
        amount = attrs.get('amount')
        if invoice and amount:
            already = invoice.paid_amount
            if self.instance:
                already -= self.instance.amount
            if already + amount > invoice.total:
                raise serializers.ValidationError(
                    {'amount': f'Переплата: к оплате осталось {invoice.total - already} ₽.'})
        return attrs

    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)


class InvoiceSerializer(serializers.ModelSerializer):
    items = InvoiceItemSerializer(many=True, read_only=True)
    payments = InvoicePaymentSerializer(many=True, read_only=True)
    paid_amount = serializers.ReadOnlyField()
    balance_due = serializers.ReadOnlyField()
    case_uuid = serializers.UUIDField(source='case.uuid', read_only=True)
    client_name = serializers.SerializerMethodField()
    client_email = serializers.SerializerMethodField()
    case_title = serializers.SerializerMethodField()
    time_entries_count = serializers.SerializerMethodField()

    class Meta:
        model = Invoice
        fields = [
            'id', 'invoice_number', 'case', 'case_uuid', 'case_title', 'client', 'client_name', 'client_email',
            'status', 'issue_date', 'due_date', 'paid_date',
            'subtotal', 'tax_rate', 'tax_amount', 'total',
            'notes', 'items', 'time_entries_count',
            'payments', 'paid_amount', 'balance_due',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['invoice_number', 'tax_amount', 'total', 'created_at', 'updated_at']

    def get_client_name(self, obj):
        return str(obj.client)

    def get_client_email(self, obj):
        return obj.client.email if obj.client else ''

    def get_case_title(self, obj):
        return str(obj.case)

    def get_time_entries_count(self, obj):
        return obj.time_entries.count()

    def validate_case(self, case):
        return _check_case_access(self, case)

    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)


class RecurringInvoiceSerializer(serializers.ModelSerializer):
    frequency_display = serializers.CharField(source='get_frequency_display', read_only=True)
    next_date = serializers.SerializerMethodField()
    case_title = serializers.SerializerMethodField()

    class Meta:
        model = RecurringInvoice
        fields = [
            'id', 'case', 'case_title', 'description', 'amount', 'tax_rate',
            'frequency', 'frequency_display', 'day_of_month', 'payment_term_days',
            'start_date', 'end_date', 'is_active', 'last_generated', 'next_date',
            'created_at',
        ]
        read_only_fields = ['last_generated', 'created_at']

    def get_next_date(self, obj):
        nxt = obj.next_occurrence()
        return nxt.isoformat() if nxt else None

    def get_case_title(self, obj):
        return str(obj.case)

    def validate_case(self, case):
        return _check_case_access(self, case)

    def validate_day_of_month(self, day):
        if not 1 <= day <= 28:
            raise serializers.ValidationError(
                'День выставления — от 1 до 28 (иначе в феврале правило «поедет»).')
        return day

    def validate_amount(self, amount):
        if amount <= 0:
            raise serializers.ValidationError('Сумма должна быть больше нуля.')
        return amount

    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)


class InvoiceListSerializer(serializers.ModelSerializer):
    client_name = serializers.SerializerMethodField()
    case_title = serializers.SerializerMethodField()
    paid_amount = serializers.ReadOnlyField()
    balance_due = serializers.ReadOnlyField()

    class Meta:
        model = Invoice
        fields = [
            'id', 'invoice_number', 'case', 'case_title', 'client', 'client_name',
            'status', 'issue_date', 'due_date', 'total', 'paid_amount', 'balance_due',
            'created_at',
        ]

    def get_client_name(self, obj):
        return str(obj.client)

    def get_case_title(self, obj):
        return str(obj.case)
