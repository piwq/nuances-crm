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
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default=PRIORITY_MEDIUM)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_TODO)
    due_date = models.DateField(null=True, blank=True, verbose_name='Срок')
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['due_date', '-priority']
        verbose_name = 'Задача'
        verbose_name_plural = 'Задачи'

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

    def __str__(self):
        return f'{self.get_event_type_display()}: {self.title}'
