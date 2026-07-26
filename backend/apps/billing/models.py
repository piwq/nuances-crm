from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from django.db import models, transaction, IntegrityError
from django.conf import settings


class TimeEntry(models.Model):
    case = models.ForeignKey(
        'cases.Case',
        on_delete=models.CASCADE,
        related_name='time_entries',
        verbose_name='Дело',
    )
    lawyer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='time_entries',
        verbose_name='Юрист',
    )
    date = models.DateField(verbose_name='Дата')
    hours = models.DecimalField(max_digits=5, decimal_places=2, verbose_name='Часы')
    description = models.TextField(verbose_name='Описание работ')
    hourly_rate = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Ставка (руб./час)')
    is_billable = models.BooleanField(default=True, verbose_name='Оплачиваемое')
    invoice = models.ForeignKey(
        'Invoice',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='time_entries',
        verbose_name='Счёт',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date']
        verbose_name = 'Запись времени'
        verbose_name_plural = 'Записи времени'

    def __str__(self):
        return f'{self.date} — {self.case} — {self.hours}ч'

    @property
    def amount(self):
        return self.hours * self.hourly_rate


class Invoice(models.Model):
    STATUS_DRAFT = 'draft'
    STATUS_SENT = 'sent'
    STATUS_PAID = 'paid'
    STATUS_OVERDUE = 'overdue'
    STATUS_CANCELLED = 'cancelled'
    STATUS_CHOICES = [
        (STATUS_DRAFT, 'Черновик'),
        (STATUS_SENT, 'Отправлен'),
        (STATUS_PAID, 'Оплачен'),
        (STATUS_OVERDUE, 'Просрочен'),
        (STATUS_CANCELLED, 'Отменён'),
    ]

    invoice_number = models.CharField(max_length=50, unique=True, verbose_name='Номер счёта')
    case = models.ForeignKey(
        'cases.Case',
        on_delete=models.PROTECT,
        related_name='invoices',
        verbose_name='Дело',
    )
    client = models.ForeignKey(
        'clients.Client',
        on_delete=models.PROTECT,
        related_name='invoices',
        verbose_name='Клиент',
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_DRAFT)

    issue_date = models.DateField(default=date.today, verbose_name='Дата выставления')
    due_date = models.DateField(verbose_name='Срок оплаты')
    paid_date = models.DateField(null=True, blank=True, verbose_name='Дата оплаты')

    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name='Сумма без НДС')
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name='НДС (%)')
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name='Сумма НДС')
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name='Итого')

    notes = models.TextField(blank=True, verbose_name='Примечания')
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_invoices',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Счёт'
        verbose_name_plural = 'Счета'

    def __str__(self):
        return f'{self.invoice_number} — {self.client}'

    @staticmethod
    def _next_number():
        prefix = f'INV-{date.today().year}-'
        last = (Invoice.objects.filter(invoice_number__startswith=prefix)
                .order_by('-invoice_number')
                .values_list('invoice_number', flat=True).first())
        seq = int(last[len(prefix):]) + 1 if last else 1
        return f'{prefix}{seq:04d}'

    def save(self, *args, **kwargs):
        subtotal = Decimal(self.subtotal or 0)
        rate = Decimal(self.tax_rate or 0)
        self.tax_amount = (subtotal * rate / Decimal('100')).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP)
        self.total = subtotal + self.tax_amount
        if self.invoice_number:
            return super().save(*args, **kwargs)
        # номер от максимума существующих (count ломался после удалений)
        # + retry на гонку одновременного создания
        for attempt in range(5):
            self.invoice_number = self._next_number()
            try:
                with transaction.atomic():
                    return super().save(*args, **kwargs)
            except IntegrityError:
                if attempt == 4:
                    raise

    def recalculate_totals(self):
        self.subtotal = sum(item.amount for item in self.items.all())
        self.save(update_fields=['subtotal', 'tax_amount', 'total'])


class InvoiceItem(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='items')
    description = models.CharField(max_length=500, verbose_name='Описание')
    quantity = models.DecimalField(max_digits=8, decimal_places=2, verbose_name='Кол-во (часы/ед.)')
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Цена за единицу')
    amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name='Сумма')
    time_entry = models.OneToOneField(
        TimeEntry,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='invoice_item',
    )

    class Meta:
        verbose_name = 'Строка счёта'
        verbose_name_plural = 'Строки счёта'

    def save(self, *args, **kwargs):
        self.amount = (Decimal(self.quantity) * Decimal(self.unit_price)).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP)
        super().save(*args, **kwargs)
