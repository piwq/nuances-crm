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


class CaseChecklist(models.Model):
    """Типовой набор задач по делу: «подготовить иск → пошлина → подача»."""
    name = models.CharField(max_length=255, verbose_name='Название')
    category = models.CharField(
        max_length=30, blank=True, verbose_name='Категория дел',
        help_text='Пусто — подходит для любых дел')
    description = models.TextField(blank=True, verbose_name='Описание')
    is_active = models.BooleanField(default=True, verbose_name='Активен')
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        related_name='created_checklists')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Чек-лист дела'
        verbose_name_plural = 'Чек-листы дел'

    def __str__(self):
        return self.name

    def apply_to_case(self, case, start_date=None, assignee=None):
        """Развернуть чек-лист в задачи дела. Возвращает список созданных задач."""
        from datetime import date as date_cls, timedelta

        start = start_date or date_cls.today()
        assignee = assignee or case.lead_lawyer
        created = []
        for item in self.items.all():
            created.append(Task.objects.create(
                title=item.title,
                description=item.description,
                case=case,
                assigned_to=assignee,
                created_by=assignee,
                priority=item.priority,
                due_date=start + timedelta(days=item.days_offset),
            ))
        return created


class ChecklistItem(models.Model):
    checklist = models.ForeignKey(CaseChecklist, on_delete=models.CASCADE,
                                  related_name='items')
    title = models.CharField(max_length=255, verbose_name='Задача')
    description = models.TextField(blank=True, verbose_name='Описание')
    days_offset = models.IntegerField(
        default=0, verbose_name='Срок, дней от старта',
        help_text='0 — в день применения чек-листа')
    priority = models.CharField(max_length=10, choices=Task.PRIORITY_CHOICES,
                                default=Task.PRIORITY_MEDIUM, verbose_name='Приоритет')
    order = models.PositiveSmallIntegerField(default=0, verbose_name='Порядок')

    class Meta:
        ordering = ['order', 'days_offset', 'id']
        verbose_name = 'Пункт чек-листа'
        verbose_name_plural = 'Пункты чек-листа'

    def __str__(self):
        return self.title


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
