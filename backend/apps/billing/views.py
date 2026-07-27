import csv
from datetime import date
from django.http import HttpResponse
from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
import django_filters
from django.db.models import Sum, Count, Q, F, DecimalField
from django.db.models.functions import TruncMonth

from common.permissions import IsAdmin, IsLawyerOrAdmin
from common.scoping import scope_by_case
from .models import TimeEntry, Invoice, InvoiceItem, InvoicePayment, RecurringInvoice
from .serializers import (
    TimeEntrySerializer, InvoiceSerializer, InvoiceListSerializer, InvoiceItemSerializer,
    InvoicePaymentSerializer, RecurringInvoiceSerializer,
)


class TimeEntryFilter(django_filters.FilterSet):
    date_from = django_filters.DateFilter(field_name='date', lookup_expr='gte')
    date_to = django_filters.DateFilter(field_name='date', lookup_expr='lte')
    unbilled = django_filters.BooleanFilter(field_name='invoice', lookup_expr='isnull')

    class Meta:
        model = TimeEntry
        fields = ['case', 'lawyer', 'is_billable']


class TimeEntryListCreateView(generics.ListCreateAPIView):
    serializer_class = TimeEntrySerializer
    filterset_class = TimeEntryFilter
    ordering_fields = ['date', 'hours']
    ordering = ['-date']

    def get_queryset(self):
        qs = TimeEntry.objects.select_related('case', 'lawyer')
        if self.request.user.is_scoped:
            qs = qs.filter(lawyer=self.request.user)
        return qs


class TimeEntryDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = TimeEntrySerializer

    def get_queryset(self):
        qs = TimeEntry.objects.select_related('case', 'lawyer')
        if self.request.user.is_scoped:
            qs = qs.filter(lawyer=self.request.user)
        return qs


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def time_entry_summary_view(request):
    from django.db.models import Q
    qs = TimeEntry.objects.filter(is_billable=True)
    if request.user.is_scoped:
        qs = qs.filter(lawyer=request.user)

    case_id = request.query_params.get('case')
    if case_id:
        qs = qs.filter(case_id=case_id)

    summary = qs.values('case__id', 'case__title', 'case__case_number').annotate(
        total_hours=Sum('hours'),
        billed_hours=Sum('hours', filter=Q(invoice__isnull=False)),
        unbilled_hours=Sum('hours', filter=Q(invoice__isnull=True)),
    )
    return Response(list(summary))


class InvoiceFilter(django_filters.FilterSet):
    class Meta:
        model = Invoice
        fields = ['case', 'client', 'status']


class InvoiceListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated, IsLawyerOrAdmin]
    filterset_class = InvoiceFilter
    search_fields = ['invoice_number', 'case__title', 'client__last_name',
                     'client__company_name']
    ordering_fields = ['issue_date', 'due_date', 'total']
    ordering = ['-created_at']

    def get_serializer_class(self):
        if self.request.method == 'GET':
            return InvoiceListSerializer
        return InvoiceSerializer

    def get_queryset(self):
        # просрочку проставляет планировщик (mark_overdue_invoices)
        qs = Invoice.objects.select_related('case', 'client')
        if self.request.user.is_scoped:
            from django.db.models import Q
            qs = qs.filter(
                Q(case__assigned_lawyers=self.request.user) | Q(case__lead_lawyer=self.request.user)
            ).distinct()
        return qs


class InvoiceDetailView(generics.RetrieveUpdateDestroyAPIView):
    def get_queryset(self):
        return scope_by_case(
            Invoice.objects.prefetch_related('items', 'time_entries'),
            self.request.user,
        )

    def get_serializer_class(self):
        return InvoiceSerializer

    def get_permissions(self):
        if self.request.method == 'DELETE':
            return [IsAdmin()]
        return [IsAuthenticated(), IsLawyerOrAdmin()]


def _get_invoice_or_none(request, pk, qs=None):
    """Счёт по pk с учётом доступа юриста к делу; None, если нет или чужой."""
    try:
        return scope_by_case(qs or Invoice.objects.all(), request.user).get(pk=pk)
    except Invoice.DoesNotExist:
        return None


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsLawyerOrAdmin])
def generate_from_entries_view(request, pk):
    """Auto-create InvoiceItems from unbilled time entries of the invoice's case."""
    invoice = _get_invoice_or_none(request, pk)
    if invoice is None:
        return Response(status=status.HTTP_404_NOT_FOUND)

    if invoice.status != Invoice.STATUS_DRAFT:
        return Response({'detail': 'Можно генерировать только для черновика.'}, status=status.HTTP_400_BAD_REQUEST)

    entries = TimeEntry.objects.filter(case=invoice.case, invoice__isnull=True, is_billable=True)
    if not entries.exists():
        return Response({'detail': 'Нет невыставленных записей времени.'}, status=status.HTTP_400_BAD_REQUEST)

    created_items = []
    for entry in entries:
        item = InvoiceItem.objects.create(
            invoice=invoice,
            description=f'{entry.date} — {entry.description}',
            quantity=entry.hours,
            unit_price=entry.hourly_rate,
            amount=entry.amount,
            time_entry=entry,
        )
        entry.invoice = invoice
        entry.save(update_fields=['invoice'])
        created_items.append(item)

    invoice.recalculate_totals()
    return Response(InvoiceSerializer(invoice, context={'request': request}).data)


@api_view(['PATCH'])
@permission_classes([IsAuthenticated, IsLawyerOrAdmin])
def mark_sent_view(request, pk):
    invoice = _get_invoice_or_none(request, pk)
    if invoice is None:
        return Response(status=status.HTTP_404_NOT_FOUND)
    invoice.status = Invoice.STATUS_SENT
    invoice.save(update_fields=['status', 'updated_at'])
    return Response(InvoiceSerializer(invoice, context={'request': request}).data)


@api_view(['PATCH'])
@permission_classes([IsAuthenticated, IsLawyerOrAdmin])
def mark_paid_view(request, pk):
    """Полная оплата: регистрирует платёж на весь остаток.

    Статус и дата оплаты выводятся из платежей — единый источник правды.
    """
    invoice = _get_invoice_or_none(request, pk)
    if invoice is None:
        return Response(status=status.HTTP_404_NOT_FOUND)

    paid_date = request.data.get('paid_date') or date.today()
    serializer = InvoicePaymentSerializer(
        data={
            'invoice': invoice.id,
            'amount': invoice.balance_due,
            'paid_date': paid_date,
            'method': request.data.get('method', InvoicePayment.METHOD_TRANSFER),
            'note': 'Полная оплата',
        },
        context={'request': request},
    )
    if invoice.balance_due > 0:
        serializer.is_valid(raise_exception=True)
        serializer.save()
    invoice.sync_payment_status()
    invoice.refresh_from_db()
    return Response(InvoiceSerializer(invoice, context={'request': request}).data)


class RecurringInvoiceListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated, IsLawyerOrAdmin]
    serializer_class = RecurringInvoiceSerializer
    filterset_fields = ['case', 'is_active']

    def get_queryset(self):
        return scope_by_case(
            RecurringInvoice.objects.select_related('case'), self.request.user)


class RecurringInvoiceDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated, IsLawyerOrAdmin]
    serializer_class = RecurringInvoiceSerializer

    def get_queryset(self):
        return scope_by_case(RecurringInvoice.objects.all(), self.request.user)


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsLawyerOrAdmin])
def recurring_run_now_view(request, pk):
    """Выставить очередной счёт по правилу вручную, не дожидаясь расписания."""
    rule = scope_by_case(RecurringInvoice.objects.all(), request.user).filter(pk=pk).first()
    if rule is None:
        return Response(status=status.HTTP_404_NOT_FOUND)
    invoice = rule.generate_invoice()
    if invoice is None:
        return Response({'detail': 'Правило исчерпано: дата окончания уже прошла.'},
                        status=status.HTTP_400_BAD_REQUEST)
    return Response(InvoiceSerializer(invoice, context={'request': request}).data,
                    status=status.HTTP_201_CREATED)


class InvoicePaymentListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated, IsLawyerOrAdmin]
    serializer_class = InvoicePaymentSerializer

    def get_queryset(self):
        qs = InvoicePayment.objects.select_related('created_by', 'invoice')
        invoice_id = self.request.query_params.get('invoice')
        if invoice_id:
            qs = qs.filter(invoice_id=invoice_id)
        return scope_by_case(qs, self.request.user, case_field='invoice__case')

    def perform_create(self, serializer):
        payment = serializer.save()
        payment.invoice.sync_payment_status()


class InvoicePaymentDetailView(generics.RetrieveDestroyAPIView):
    permission_classes = [IsAuthenticated, IsLawyerOrAdmin]
    serializer_class = InvoicePaymentSerializer

    def get_queryset(self):
        return scope_by_case(InvoicePayment.objects.all(), self.request.user,
                             case_field='invoice__case')

    def perform_destroy(self, instance):
        invoice = instance.invoice
        instance.delete()
        invoice.sync_payment_status()


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def billing_monthly_stats_view(request):
    try:
        months = int(request.query_params.get('months', 6))
    except (TypeError, ValueError):
        return Response({'detail': 'Параметр months должен быть целым числом.'},
                        status=status.HTTP_400_BAD_REQUEST)
    months = max(1, min(months, 24))
    qs = TimeEntry.objects.filter(is_billable=True)
    if request.user.is_scoped:
        qs = qs.filter(lawyer=request.user)
    rows = (
        qs.annotate(month=TruncMonth('date'))
        .values('month')
        .annotate(
            total_hours=Sum('hours'),
            total_amount=Sum(F('hours') * F('hourly_rate'),
                             output_field=DecimalField(max_digits=14, decimal_places=2)),
        )
        .order_by('-month')[:months]
    )
    return Response([
        {
            'month': r['month'].strftime('%Y-%m'),
            'total_hours': float(r['total_hours'] or 0),
            'total_amount': float(r['total_amount'] or 0),
        }
        for r in reversed(list(rows))
    ])


class InvoiceItemListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated, IsLawyerOrAdmin]
    serializer_class = InvoiceItemSerializer

    def get_queryset(self):
        qs = InvoiceItem.objects.filter(invoice_id=self.request.query_params.get('invoice'))
        return scope_by_case(qs, self.request.user, case_field='invoice__case')

    def perform_create(self, serializer):
        item = serializer.save()
        item.invoice.recalculate_totals()


class InvoiceItemDetailView(generics.RetrieveDestroyAPIView):
    permission_classes = [IsAuthenticated, IsLawyerOrAdmin]
    serializer_class = InvoiceItemSerializer

    def get_queryset(self):
        return scope_by_case(InvoiceItem.objects.all(), self.request.user,
                             case_field='invoice__case')

    def perform_destroy(self, instance):
        invoice = instance.invoice
        instance.delete()
        invoice.recalculate_totals()


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def time_entries_csv_view(request):
    qs = TimeEntry.objects.select_related('case', 'lawyer')
    if request.user.is_scoped:
        qs = qs.filter(lawyer=request.user)
    qs = TimeEntryFilter(request.query_params, queryset=qs).qs.order_by('-date')

    response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
    response['Content-Disposition'] = 'attachment; filename="time_entries.csv"'
    writer = csv.writer(response)
    writer.writerow(['Дата', 'Дело', 'Юрист', 'Часов', 'Описание', 'Биллинговая', 'Ставка (₽/ч)', 'Сумма (₽)', 'Выставлено'])
    for e in qs:
        writer.writerow([
            e.date, str(e.case) if e.case else '', e.lawyer.get_full_name() if e.lawyer else '',
            e.hours, e.description or '', 'Да' if e.is_billable else 'Нет',
            e.hourly_rate or '', float(e.amount) if e.is_billable else '', 'Да' if e.invoice_id else 'Нет',
        ])
    return response


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def invoices_csv_view(request):
    qs = Invoice.objects.select_related('case', 'client')
    if request.user.is_scoped:
        qs = qs.filter(
            Q(case__assigned_lawyers=request.user) | Q(case__lead_lawyer=request.user)
        ).distinct()
    qs = InvoiceFilter(request.query_params, queryset=qs).qs.order_by('-created_at')

    response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
    response['Content-Disposition'] = 'attachment; filename="invoices.csv"'
    writer = csv.writer(response)
    writer.writerow(['№ счёта', 'Дело', 'Клиент', 'Статус', 'Выставлен', 'Срок оплаты', 'Оплачен', 'Сумма (₽)', 'НДС (₽)', 'Итого (₽)'])
    for inv in qs:
        writer.writerow([
            inv.invoice_number, str(inv.case) if inv.case else '', str(inv.client) if inv.client else '',
            inv.get_status_display(), inv.issue_date or '', inv.due_date or '', inv.paid_date or '',
            float(inv.subtotal), float(inv.tax_amount), float(inv.total),
        ])
    return response


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsLawyerOrAdmin])
def send_invoice_email_view(request, pk):
    invoice = _get_invoice_or_none(
        request, pk, Invoice.objects.prefetch_related('items').select_related('case', 'client'))
    if invoice is None:
        return Response(status=status.HTTP_404_NOT_FOUND)

    recipient_email = request.data.get('email') or (invoice.client.email if invoice.client else '')
    if not recipient_email:
        return Response({'detail': 'Не указан email клиента.'}, status=status.HTTP_400_BAD_REQUEST)

    personal_message = (request.data.get('message') or '').strip()
    subject = f'Счёт {invoice.invoice_number} — Юридическое бюро «Нюансы»'
    body = (
        f'Здравствуйте!\n\n'
        + (f'{personal_message}\n\n' if personal_message else '')
        + f'Направляем счёт {invoice.invoice_number} на сумму {invoice.total} ₽.\n'
        f'Срок оплаты: {invoice.due_date}.\n'
        f'PDF-версия счёта — во вложении.\n\n'
        f'С уважением,\nЮридическое бюро «Нюансы»'
    )

    from django.core.mail import EmailMultiAlternatives
    from django.template.loader import render_to_string
    html_body = render_to_string('billing/invoice_email.html',
                                 {'invoice': invoice, 'message': personal_message})
    msg = EmailMultiAlternatives(subject=subject, body=body, to=[recipient_email])
    msg.attach_alternative(html_body, 'text/html')

    try:
        import weasyprint
        html = render_to_string('billing/invoice_pdf.html', {'invoice': invoice})
        pdf = weasyprint.HTML(string=html).write_pdf()
        msg.attach(f'invoice_{invoice.invoice_number}.pdf', pdf, 'application/pdf')
    except Exception as e:
        # без вложения счёт клиенту не отправляем — это выглядело бы как успех
        return Response({'detail': f'PDF не сформирован, письмо не отправлено: {e}'},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    try:
        msg.send()
    except Exception as e:
        return Response({'detail': f'Ошибка отправки письма: {e}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    if invoice.status == Invoice.STATUS_DRAFT:
        invoice.status = Invoice.STATUS_SENT
        invoice.save(update_fields=['status'])

    return Response(InvoiceSerializer(invoice, context={'request': request}).data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def invoice_email_preview_view(request, pk):
    """HTML-предпросмотр письма со счётом — рендерится в диалоге отправки."""
    invoice = _get_invoice_or_none(
        request, pk, Invoice.objects.prefetch_related('items').select_related('case', 'client'))
    if invoice is None:
        return Response(status=status.HTTP_404_NOT_FOUND)
    from django.template.loader import render_to_string
    html = render_to_string('billing/invoice_email.html', {
        'invoice': invoice,
        'message': (request.query_params.get('message') or '').strip(),
    })
    return HttpResponse(html, content_type='text/html; charset=utf-8')


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def invoice_act_pdf_view(request, pk):
    """Акт выполненных работ к счёту (позиции счёта = оказанные услуги)."""
    invoice = _get_invoice_or_none(
        request, pk, Invoice.objects.prefetch_related('items').select_related('case', 'client'))
    if invoice is None:
        return Response(status=status.HTTP_404_NOT_FOUND)

    from django.template.loader import render_to_string
    try:
        import weasyprint
        html = render_to_string('billing/act_pdf.html', {
            'invoice': invoice,
            'act_number': invoice.invoice_number.replace('INV', 'ACT'),
            'act_date': (invoice.paid_date or date.today()).strftime('%d.%m.%Y'),
        })
        pdf = weasyprint.HTML(string=html).write_pdf()
        response = HttpResponse(pdf, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="act_{invoice.invoice_number}.pdf"'
        return response
    except Exception as e:
        return Response({'detail': f'Ошибка генерации акта: {e}'},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def invoice_pdf_view(request, pk):
    invoice = _get_invoice_or_none(
        request, pk, Invoice.objects.prefetch_related('items').select_related('case', 'client'))
    if invoice is None:
        return Response(status=status.HTTP_404_NOT_FOUND)

    from django.template.loader import render_to_string
    from django.http import HttpResponse
    try:
        import weasyprint
        html = render_to_string('billing/invoice_pdf.html', {'invoice': invoice})
        pdf = weasyprint.HTML(string=html).write_pdf()
        response = HttpResponse(pdf, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="invoice_{invoice.invoice_number}.pdf"'
        return response
    except Exception as e:
        return Response({'detail': f'Ошибка генерации PDF: {e}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
