"""Перевод отправленных счетов с истёкшим сроком в «Просрочен».

Запускается планировщиком (сервис scheduler) раз в час; раньше это был
побочный UPDATE внутри GET-списка счетов.
"""
from datetime import date

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.billing.models import Invoice


class Command(BaseCommand):
    help = 'Mark sent invoices past their due date as overdue'

    def handle(self, *args, **options):
        n = Invoice.objects.filter(
            status=Invoice.STATUS_SENT,
            due_date__lt=date.today(),
        ).update(status=Invoice.STATUS_OVERDUE, updated_at=timezone.now())
        self.stdout.write(self.style.SUCCESS(f'Marked {n} invoices overdue'))
