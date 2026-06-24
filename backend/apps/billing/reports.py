from datetime import date, timedelta
from django.db.models import Sum, Count, Q
from django.db.models.functions import TruncMonth
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import TimeEntry, Invoice
from apps.cases.models import Case
from apps.accounts.models import CustomUser


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def reports_view(request):
    period_months = int(request.query_params.get('months', 6))
    date_from = date.today().replace(day=1) - timedelta(days=30 * (period_months - 1))

    # Cases by status
    cases_by_status = {
        row['status']: row['count']
        for row in Case.objects.values('status').annotate(count=Count('id'))
    }

    # Cases by category
    cases_by_category = {
        row['category']: row['count']
        for row in Case.objects.values('category').annotate(count=Count('id'))
    }

    # Revenue by month
    revenue_by_month = list(
        TimeEntry.objects
        .filter(is_billable=True, date__gte=date_from)
        .annotate(month=TruncMonth('date'))
        .values('month')
        .annotate(total_hours=Sum('hours'), total_amount=Sum('amount'))
        .order_by('month')
        .values('month', 'total_hours', 'total_amount')
    )

    # Top lawyers by hours (last period)
    lawyers_stats = list(
        TimeEntry.objects
        .filter(is_billable=True, date__gte=date_from)
        .values('lawyer__id', 'lawyer__first_name', 'lawyer__last_name', 'lawyer__username')
        .annotate(total_hours=Sum('hours'), total_amount=Sum('amount'))
        .order_by('-total_hours')[:10]
    )

    # Invoices summary
    invoices_summary = {
        row['status']: {'count': row['count'], 'total': float(row['total'] or 0)}
        for row in Invoice.objects
        .values('status')
        .annotate(count=Count('id'), total=Sum('total'))
    }

    # Overdue invoices count
    overdue_count = Invoice.objects.filter(
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
