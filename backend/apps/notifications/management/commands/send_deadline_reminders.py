"""
Management command: send deadline reminders for tasks and events.
Run daily via cron or Django-Q / Celery beat:
    python manage.py send_deadline_reminders
"""
from datetime import date, timedelta

from django.core.management.base import BaseCommand
from django.db.models import Q

from apps.tasks.models import Task, Event
from apps.notifications.utils import create_notification


TASK_THRESHOLDS = [1, 3]   # days before due_date
EVENT_THRESHOLDS = [1]


class Command(BaseCommand):
    help = 'Send reminder notifications for upcoming task and event deadlines'

    def handle(self, *args, **options):
        today = date.today()
        created = 0

        # ── Tasks ──────────────────────────────────────────────────────────
        active_tasks = Task.objects.filter(
            status__in=[Task.STATUS_TODO, Task.STATUS_IN_PROGRESS],
            due_date__isnull=False,
            assigned_to__isnull=False,
        ).select_related('assigned_to', 'case')

        for days in TASK_THRESHOLDS:
            target = today + timedelta(days=days)
            for task in active_tasks.filter(due_date=target):
                key = f'task_{task.id}_due_{days}d'
                body = f'До срока осталось {days} {"день" if days == 1 else "дня"}'
                if task.case_id:
                    body += f' · дело: {task.case.title}'
                link = f'/cases/{task.case.uuid}' if task.case_id else '/tasks'
                n = create_notification(
                    user=task.assigned_to,
                    title=f'⏰ Дедлайн через {days}д: {task.title}',
                    body=body,
                    link=link,
                    key=key,
                )
                if n:
                    created += 1

        # ── Events ─────────────────────────────────────────────────────────
        from django.utils import timezone
        import datetime as dt

        for days in EVENT_THRESHOLDS:
            start = timezone.make_aware(dt.datetime.combine(today + timedelta(days=days), dt.time.min))
            end = timezone.make_aware(dt.datetime.combine(today + timedelta(days=days), dt.time.max))
            events = Event.objects.filter(
                start_datetime__range=(start, end),
                event_type__in=[Event.TYPE_HEARING, Event.TYPE_DEADLINE],
            ).select_related('created_by', 'case').prefetch_related('attendees')

            for event in events:
                recipients = set(event.attendees.all())
                if event.created_by:
                    recipients.add(event.created_by)
                for user in recipients:
                    key = f'event_{event.id}_due_{days}d_user_{user.id}'
                    link = f'/cases/{event.case.uuid}' if event.case_id else '/calendar'
                    n = create_notification(
                        user=user,
                        title=f'📅 Завтра: {event.title}',
                        body=f'{event.get_event_type_display()} в {event.start_datetime.strftime("%H:%M")}',
                        link=link,
                        key=key,
                    )
                    if n:
                        created += 1

        self.stdout.write(self.style.SUCCESS(f'Created {created} reminder notifications'))
