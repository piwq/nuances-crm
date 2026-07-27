from django.db import models
from django.conf import settings


class Task(models.Model):
    PRIORITY_LOW = 'low'
    PRIORITY_MEDIUM = 'medium'
    PRIORITY_HIGH = 'high'
    PRIORITY_URGENT = 'urgent'
    PRIORITY_CHOICES = [
        (PRIORITY_LOW, 'Низкий'),
        (PRIORITY_MEDIUM, 'Средний'),
        (PRIORITY_HIGH, 'Высокий'),
        (PRIORITY_URGENT, 'Срочно'),
    ]

    STATUS_TODO = 'todo'
    STATUS_IN_PROGRESS = 'in_progress'
    STATUS_DONE = 'done'
    STATUS_CANCELLED = 'cancelled'
    STATUS_CHOICES = [
        (STATUS_TODO, 'К выполнению'),
        (STATUS_IN_PROGRESS, 'В работе'),
        (STATUS_DONE, 'Выполнено'),
        (STATUS_CANCELLED, 'Отменено'),
    ]

    title = models.CharField(max_length=255, verbose_name='Название')
    description = models.TextField(blank=True, verbose_name='Описание')
    case = models.ForeignKey(
        'cases.Case',
        on_delete=models.CASCADE,
        related_name='tasks',
        null=True,
        blank=True,
        verbose_name='Дело',
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_tasks',
        verbose_name='Исполнитель',
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_tasks',
    )
    RECUR_NONE = 'none'
    RECUR_WEEKLY = 'weekly'
    RECUR_BIWEEKLY = 'biweekly'
    RECUR_MONTHLY = 'monthly'
    RECUR_QUARTERLY = 'quarterly'
    RECUR_CHOICES = [
        (RECUR_NONE, 'Не повторять'),
        (RECUR_WEEKLY, 'Каждую неделю'),
        (RECUR_BIWEEKLY, 'Раз в две недели'),
        (RECUR_MONTHLY, 'Каждый месяц'),
        (RECUR_QUARTERLY, 'Раз в квартал'),
    ]

    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default=PRIORITY_MEDIUM)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_TODO)
    due_date = models.DateField(null=True, blank=True, verbose_name='Срок')
    recurrence = models.CharField(
        max_length=20, choices=RECUR_CHOICES, default=RECUR_NONE,
        verbose_name='Повторение',
        help_text='После выполнения автоматически создаётся следующая задача')
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['due_date', '-priority']
        verbose_name = 'Задача'
        verbose_name_plural = 'Задачи'
        indexes = [
            models.Index(fields=['status', 'due_date']),
            models.Index(fields=['assigned_to', 'status']),
        ]

    def __str__(self):
        return self.title

    def spawn_next(self):
        """Создать следующую задачу серии. Возвращает Task или None."""
        from datetime import date, timedelta

        if self.recurrence == self.RECUR_NONE:
            return None

        base = self.due_date or date.today()
        if self.recurrence == self.RECUR_WEEKLY:
            nxt = base + timedelta(weeks=1)
        elif self.recurrence == self.RECUR_BIWEEKLY:
            nxt = base + timedelta(weeks=2)
        else:
            step = 3 if self.recurrence == self.RECUR_QUARTERLY else 1
            total = base.year * 12 + (base.month - 1) + step
            year, month = total // 12, total % 12 + 1
            import calendar
            nxt = date(year, month, min(base.day, calendar.monthrange(year, month)[1]))

        return Task.objects.create(
            title=self.title,
            description=self.description,
            case=self.case,
            assigned_to=self.assigned_to,
            created_by=self.created_by,
            priority=self.priority,
            due_date=nxt,
            recurrence=self.recurrence,
        )


class Event(models.Model):
    TYPE_HEARING = 'court_hearing'
    TYPE_MEETING = 'meeting'
    TYPE_DEADLINE = 'deadline'
    TYPE_OTHER = 'other'
    TYPE_CHOICES = [
        (TYPE_HEARING, 'Судебное заседание'),
        (TYPE_MEETING, 'Встреча'),
        (TYPE_DEADLINE, 'Дедлайн'),
        (TYPE_OTHER, 'Прочее'),
    ]

    title = models.CharField(max_length=255, verbose_name='Название')
    event_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default=TYPE_OTHER, verbose_name='Тип')
    case = models.ForeignKey(
        'cases.Case',
        on_delete=models.CASCADE,
        related_name='events',
        null=True,
        blank=True,
        verbose_name='Дело',
    )
    description = models.TextField(blank=True)
    location = models.CharField(max_length=255, blank=True, verbose_name='Место')

    start_datetime = models.DateTimeField(verbose_name='Начало')
    end_datetime = models.DateTimeField(null=True, blank=True, verbose_name='Конец')
    all_day = models.BooleanField(default=False, verbose_name='Весь день')

    attendees = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='events',
        blank=True,
        verbose_name='Участники',
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_events',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['start_datetime']
        verbose_name = 'Событие'
        verbose_name_plural = 'События'
        indexes = [
            models.Index(fields=['start_datetime']),
        ]

    def __str__(self):
        return f'{self.get_event_type_display()}: {self.title}'
