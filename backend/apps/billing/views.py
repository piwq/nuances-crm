from datetime import date
from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
import django_filters
from django.db.models import Sum

from common.permissions import IsAdmin
from .models import TimeEntry, Invoice, InvoiceItem
from .serializers import (
    TimeEntrySerializer, InvoiceSerializer, InvoiceListSerializer, InvoiceItemSerializer
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
        if self.request.user.is_lawyer:
            qs = qs.filter(lawyer=self.request.user)
        return qs


class TimeEntryDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = TimeEntry.objects.all()
    serializer_class = TimeEntrySerializer


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def time_entry_summary_view(request):
    from django.db.models import Q
    qs = TimeEntry.objects.filter(is_billable=True)
    if request.user.is_lawyer:
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
    filterset_class = InvoiceFilter
    ordering_fields = ['issue_date', 'due_date', 'total']
    ordering = ['-created_at']

    def get_serializer_class(self):
        if self.request.method == 'GET':
            return InvoiceListSerializer
        return InvoiceSerializer

    def get_queryset(self):
        qs = Invoice.objects.select_related('case', 'client')
        if self.request.user.is_lawyer:
            from django.db.models import Q
            qs = qs.filter(
                Q(case__assigned_lawyers=self.request.user) | Q(case__lead_lawyer=self.request.user)
            ).distinct()
        return qs


class InvoiceDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Invoice.objects.prefetch_related('items', 'time_entries')

    def get_serializer_class(self):
        return InvoiceSerializer

    def get_permissions(self):
        if self.request.method == 'DELETE':
            return [IsAdmin()]
        return [IsAuthenticated()]


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def generate_from_entries_view(request, pk):
    """Auto-create InvoiceItems from unbilled time entries of the invoice's case."""
    try:
        invoice = Invoice.objects.get(pk=pk)
    except Invoice.DoesNotExist:
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
@permission_classes([IsAuthenticated])
def mark_sent_view(request, pk):
    try:
        invoice = Invoice.objects.get(pk=pk)
    except Invoice.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)
    invoice.status = Invoice.STATUS_SENT
    invoice.save(update_fields=['status'])
    return Response(InvoiceSerializer(invoice, context={'request': request}).data)


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def mark_paid_view(request, pk):
    try:
        invoice = Invoice.objects.get(pk=pk)
    except Invoice.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)
    invoice.status = Invoice.STATUS_PAID
    invoice.paid_date = request.data.get('paid_date') or date.today()
    invoice.save(update_fields=['status', 'paid_date'])
    return Response(InvoiceSerializer(invoice, context={'request': request}).data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def invoice_pdf_view(request, pk):
    try:
        invoice = Invoice.objects.prefetch_related('items').select_related('case', 'client').get(pk=pk)
    except Invoice.DoesNotExist:
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
