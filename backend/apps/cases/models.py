import uuid
from datetime import date
from django.db import models, transaction, IntegrityError
from django.conf import settings


class Case(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, db_index=True)
    STATUS_NEW = 'new'
    STATUS_ACTIVE = 'active'
    STATUS_ON_HOLD = 'on_hold'
    STATUS_CLOSED = 'closed'
    STATUS_ARCHIVED = 'archived'
    STATUS_CHOICES = [
        (STATUS_NEW, 'Новое'),
        (STATUS_ACTIVE, 'Активное'),
        (STATUS_ON_HOLD, 'Приостановлено'),
        (STATUS_CLOSED, 'Закрыто'),
        (STATUS_ARCHIVED, 'В архиве'),
    ]

    CATEGORY_CIVIL = 'civil'
    CATEGORY_CRIMINAL = 'criminal'
    CATEGORY_CORPORATE = 'corporate'
    CATEGORY_FAMILY = 'family'
    CATEGORY_LABOR = 'labor'
    CATEGORY_PROPERTY = 'property'
    CATEGORY_BANKRUPTCY = 'bankruptcy'
    CATEGORY_OTHER = 'other'
    CATEGORY_CHOICES = [
        (CATEGORY_CIVIL, 'Гражданское'),
        (CATEGORY_CRIMINAL, 'Уголовное'),
        (CATEGORY_CORPORATE, 'Корпоративное'),
        (CATEGORY_FAMILY, 'Семейное'),
        (CATEGORY_LABOR, 'Трудовое'),
        (CATEGORY_PROPERTY, 'Имущественное'),
        (CATEGORY_BANKRUPTCY, 'Банкротство'),
        (CATEGORY_OTHER, 'Прочее'),
    ]

    title = models.CharField(max_length=255, verbose_name='Название')
    case_number = models.CharField(max_length=100, unique=True, blank=True, verbose_name='Номер дела')
    client = models.ForeignKey(
        'clients.Client',
        on_delete=models.PROTECT,
        related_name='cases',
        verbose_name='Клиент',
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_NEW, verbose_name='Статус')
    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES, verbose_name='Категория')
    description = models.TextField(blank=True, verbose_name='Описание')
    court_name = models.CharField(max_length=255, blank=True, verbose_name='Суд')
    court_case_number = models.CharField(max_length=100, blank=True, verbose_name='Номер дела в суде')
    opposing_party = models.CharField(
        max_length=255, blank=True, verbose_name='Противоположная сторона',
        help_text='ФИО или название организации — для проверки конфликта интересов',
    )
    opposing_party_inn = models.CharField(
        max_length=20, blank=True, verbose_name='ИНН противоположной стороны',
    )

    assigned_lawyers = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='assigned_cases',
        limit_choices_to={'role': 'lawyer'},
        blank=True,
        verbose_name='Юристы',
    )
    lead_lawyer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='lead_cases',
        verbose_name='Ответственный юрист',
    )

    opened_at = models.DateField(default=date.today, verbose_name='Дата открытия')
    closed_at = models.DateField(null=True, blank=True, verbose_name='Дата закрытия')
    expected_close_date = models.DateField(null=True, blank=True, verbose_name='Планируемая дата закрытия')
    key_deadline = models.DateField(
        null=True, blank=True, verbose_name='Ключевой процессуальный срок',
    )
    key_deadline_note = models.CharField(
        max_length=255, blank=True, verbose_name='Описание срока',
        help_text='Напр.: срок исковой давности, подача апелляции',
    )

    hourly_rate = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        verbose_name='Часовая ставка (руб.)',
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_cases',
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Дело'
        verbose_name_plural = 'Дела'
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['category']),
            models.Index(fields=['key_deadline']),
            models.Index(fields=['-created_at']),
        ]

    def __str__(self):
        return f'{self.case_number}: {self.title}'

    @staticmethod
    def _next_number():
        prefix = f'CASE-{date.today().year}-'
        last = (Case.objects.filter(case_number__startswith=prefix)
                .order_by('-case_number')
                .values_list('case_number', flat=True).first())
        seq = int(last[len(prefix):]) + 1 if last else 1
        return f'{prefix}{seq:04d}'

    def save(self, *args, **kwargs):
        if self.case_number:
            return super().save(*args, **kwargs)
        # номер от максимума существующих (count ломался после удалений)
        # + retry на гонку одновременного создания
        for attempt in range(5):
            self.case_number = self._next_number()
            try:
                with transaction.atomic():
                    return super().save(*args, **kwargs)
            except IntegrityError:
                if attempt == 4:
                    raise


class CaseNote(models.Model):
    case = models.ForeignKey(Case, on_delete=models.CASCADE, related_name='notes')
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='case_notes',
    )
    text = models.TextField(verbose_name='Текст заметки')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Заметка по делу'
        verbose_name_plural = 'Заметки по делу'

    def __str__(self):
        return f'{self.case} — {self.author}'
