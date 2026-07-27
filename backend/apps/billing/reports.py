from datetime import date
from django.db.models import Sum, Count, Q, F, DecimalField
from django.db.models.functions import TruncMonth
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from common.scoping import scope_cases, scope_by_case
from .models import TimeEntry, Invoice
from apps.cases.models import Case


def _amount_sum():
    return Sum(F('hours') * F('hourly_rate'),
               output_field=DecimalField(max_digits=14, decimal_places=2))


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def reports_view(request):
    try:
        period_months = int(request.query_params.get('months', 6))
    except (TypeError, ValueError):
        return Response({'detail': 'Параметр months должен быть целым числом.'},
                        status=status.HTTP_400_BAD_REQUEST)
    period_months = max(1, min(period_months, 24))
    # первый день месяца N-1 месяцев назад (настоящая месячная арифметика,
    # а не «месяц = 30 дней»)
    today = date.today()
    months_total = today.year * 12 + today.month - 1 - (period_months - 1)
    date_from = date(months_total // 12, months_total % 12 + 1, 1)

    # юрист видит цифры только по своим делам/часам, админ — по всей фирме.
    # pk__in-подзапрос, а не прямой filter: M2M-join скоупинга дублирует строки
    # и ломает агрегаты (Sum/Count).
    cases_qs = Case.objects.filter(
        pk__in=scope_cases(Case.objects.all(), request.user).values('pk'))
    invoices_qs = Invoice.objects.filter(
        pk__in=scope_by_case(Invoice.objects.all(), request.user).values('pk'))
    entries_qs = TimeEntry.objects.filter(is_billable=True, date__gte=date_from)
    if request.user.is_scoped:
        entries_qs = entries_qs.filter(lawyer=request.user)

    # Cases by status
    cases_by_status = {
        row['status']: row['count']
        for row in cases_qs.values('status').annotate(count=Count('id'))
    }

    # Cases by category
    cases_by_category = {
        row['category']: row['count']
        for row in cases_qs.values('category').annotate(count=Count('id'))
    }

    # Revenue by month
    revenue_by_month = list(
        entries_qs
        .annotate(month=TruncMonth('date'))
        .values('month')
        .annotate(total_hours=Sum('hours'), total_amount=_amount_sum())
        .order_by('month')
        .values('month', 'total_hours', 'total_amount')
    )

    # Top lawyers by hours (last period)
    lawyers_stats = list(
        entries_qs
        .values('lawyer__id', 'lawyer__first_name', 'lawyer__last_name', 'lawyer__username')
        .annotate(total_hours=Sum('hours'), total_amount=_amount_sum())
        .order_by('-total_hours')[:10]
    )

    # Invoices summary
    invoices_summary = {
        row['status']: {'count': row['count'], 'total': float(row['total'] or 0)}
        for row in invoices_qs
        .values('status')
        .annotate(count=Count('id', distinct=True), total=Sum('total'))
    }

    # Overdue invoices count
    overdue_count = invoices_qs.filter(
        status__in=['sent', 'overdue'],
        due_date__lt=date.today()
    ).count()

    return Response({
        'cases_by_status': cases_by_status,
        'cases_by_category': cases_by_category,
        'revenue_by_month': [
            {
                'month': r['month'].strftime('%Y-%m'),
                'total_hours': float(r['total_hours'] or 0),
                'total_amount': float(r['total_amount'] or 0),
            }
            for r in revenue_by_month
        ],
        'lawyers_stats': [
            {
                'name': f"{r['lawyer__last_name']} {r['lawyer__first_name']}".strip() or r['lawyer__username'],
                'total_hours': float(r['total_hours'] or 0),
                'total_amount': float(r['total_amount'] or 0),
            }
            for r in lawyers_stats
        ],
        'invoices_summary': invoices_summary,
        'overdue_invoices': overdue_count,
    })
