from datetime import date, timedelta
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

    @property
    def paid_amount(self):
        annotated = getattr(self, 'paid_total_annotated', None)
        if annotated is not None:
            return annotated
        return self.payments.aggregate(s=models.Sum('amount'))['s'] or Decimal('0')

    @property
    def balance_due(self):
        return (self.total or Decimal('0')) - self.paid_amount

    def sync_payment_status(self):
        """Статус и дата оплаты — производные от платежей, а не наоборот."""
        paid = self.payments.aggregate(s=models.Sum('amount'))['s'] or Decimal('0')
        last = self.payments.order_by('-paid_date').first()
        fields = ['status', 'paid_date', 'updated_at']

        if self.total and paid >= self.total:
            self.status = self.STATUS_PAID
            self.paid_date = last.paid_date if last else date.today()
        elif self.status == self.STATUS_PAID:
            # платёж удалили или уменьшили — счёт снова ждёт оплаты
            self.status = (self.STATUS_OVERDUE
                           if self.due_date and self.due_date < date.today()
                           else self.STATUS_SENT)
            self.paid_date = None
        else:
            return
        self.save(update_fields=fields)


def _shift_months(year, month, step):
    total = year * 12 + (month - 1) + step
    return total // 12, total % 12 + 1


class RecurringInvoice(models.Model):
    """Правило абонентского обслуживания: счёт выставляется сам по расписанию."""
    FREQ_MONTHLY = 'monthly'
    FREQ_QUARTERLY = 'quarterly'
    FREQ_CHOICES = [
        (FREQ_MONTHLY, 'Ежемесячно'),
        (FREQ_QUARTERLY, 'Ежеквартально'),
    ]

    case = models.ForeignKey('cases.Case', on_delete=models.CASCADE,
                             related_name='recurring_invoices', verbose_name='Дело')
    description = models.CharField(
        max_length=255, default='Абонентское юридическое обслуживание',
        verbose_name='Описание услуги')
    amount = models.DecimalField(max_digits=12, decimal_places=2,
                                 verbose_name='Сумма без НДС')
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0,
                                   verbose_name='НДС (%)')
    frequency = models.CharField(max_length=20, choices=FREQ_CHOICES, default=FREQ_MONTHLY,
                                 verbose_name='Периодичность')
    day_of_month = models.PositiveSmallIntegerField(
        default=1, verbose_name='День выставления',
        help_text='1–28; в коротких месяцах переносится на последний день')
    payment_term_days = models.PositiveSmallIntegerField(
        default=14, verbose_name='Срок оплаты (дней)')
    start_date = models.DateField(default=date.today, verbose_name='Действует с')
    end_date = models.DateField(null=True, blank=True, verbose_name='Действует по')
    is_active = models.BooleanField(default=True, verbose_name='Активно')
    last_generated = models.DateField(null=True, blank=True, verbose_name='Последний счёт')
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        related_name='created_recurring_invoices')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Повторяющийся счёт'
        verbose_name_plural = 'Повторяющиеся счета'

    def __str__(self):
        return f'{self.get_frequency_display()} {self.amount} ₽ — {self.case}'

    @property
    def step_months(self):
        return 3 if self.frequency == self.FREQ_QUARTERLY else 1

    def _occurrence(self, year, month):
        import calendar
        day = min(self.day_of_month, calendar.monthrange(year, month)[1])
        return date(year, month, day)

    def next_occurrence(self):
        """Дата следующего выставления (None, если правило исчерпано)."""
        if self.last_generated:
            year, month = _shift_months(
                self.last_generated.year, self.last_generated.month, self.step_months)
            nxt = self._occurrence(year, month)
        else:
            nxt = self._occurrence(self.start_date.year, self.start_date.month)
            if nxt < self.start_date:
                year, month = _shift_months(
                    self.start_date.year, self.start_date.month, self.step_months)
                nxt = self._occurrence(year, month)
        if self.end_date and nxt > self.end_date:
            return None
        return nxt

    def is_due(self, today=None):
        today = today or date.today()
        if not self.is_active:
            return False
        nxt = self.next_occurrence()
        return nxt is not None and nxt <= today

    def generate_invoice(self):
        """Создать очередной счёт-черновик. Возвращает Invoice или None."""
        issue = self.next_occurrence()
        if issue is None:
            return None
        invoice = Invoice.objects.create(
            case=self.case,
            client=self.case.client,
            issue_date=issue,
            due_date=issue + timedelta(days=self.payment_term_days),
            tax_rate=self.tax_rate,
            notes=f'Автоматически по правилу «{self.description}»',
            created_by=self.created_by,
        )
        InvoiceItem.objects.create(
            invoice=invoice, description=self.description,
            quantity=1, unit_price=self.amount)
        invoice.recalculate_totals()
        self.last_generated = issue
        self.save(update_fields=['last_generated'])
        return invoice


class InvoicePayment(models.Model):
    """Платёж по счёту. Счёт может гаситься частями."""
    METHOD_TRANSFER = 'transfer'
    METHOD_CASH = 'cash'
    METHOD_CARD = 'card'
    METHOD_OTHER = 'other'
    METHOD_CHOICES = [
        (METHOD_TRANSFER, 'Банковский перевод'),
        (METHOD_CASH, 'Наличные'),
        (METHOD_CARD, 'Карта'),
        (METHOD_OTHER, 'Прочее'),
    ]

    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name='Сумма')
    paid_date = models.DateField(default=date.today, verbose_name='Дата платежа')
    method = models.CharField(
        max_length=20, choices=METHOD_CHOICES, default=METHOD_TRANSFER,
        verbose_name='Способ оплаты')
    note = models.CharField(max_length=255, blank=True, verbose_name='Примечание')
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        related_name='registered_payments')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-paid_date', '-id']
        verbose_name = 'Платёж'
        verbose_name_plural = 'Платежи'

    def __str__(self):
        return f'{self.paid_date} — {self.amount} ₽ по {self.invoice.invoice_number}'


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
