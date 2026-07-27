"""Выставление счетов по правилам абонентского обслуживания.

Запускается планировщиком; правило само знает свою следующую дату, поэтому
команда идемпотентна: повторный прогон в тот же день ничего не создаст.
Пропущенные периоды догоняются (не более MAX_CATCHUP за один запуск).
"""
from django.core.management.base import BaseCommand

from apps.billing.models import RecurringInvoice
from apps.notifications.utils import create_notification

MAX_CATCHUP = 12


class Command(BaseCommand):
    help = 'Generate invoices from active recurring (retainer) rules'

    def handle(self, *args, **options):
        created = 0
        for rule in RecurringInvoice.objects.filter(is_active=True).select_related(
                'case', 'case__client', 'case__lead_lawyer'):
            for _ in range(MAX_CATCHUP):
                if not rule.is_due():
                    break
                invoice = rule.generate_invoice()
                if invoice is None:
                    break
                created += 1
                lead = rule.case.lead_lawyer
                if lead:
                    create_notification(
                        user=lead,
                        title=f'Выставлен счёт {invoice.invoice_number}',
                        body=f'{rule.description} — {invoice.total} ₽ по делу {rule.case.title}',
                        link=f'/billing/invoices/{invoice.id}',
                        key=f'recurring_{rule.id}_{invoice.issue_date}',
                    )

        self.stdout.write(self.style.SUCCESS(f'Created {created} recurring invoices'))
