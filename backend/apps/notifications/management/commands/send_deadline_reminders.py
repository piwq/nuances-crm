"""
Management command: send deadline reminders for tasks and events.
Run daily via cron or Django-Q / Celery beat:
    python manage.py send_deadline_reminders
"""
from datetime import date, timedelta

from django.core.management.base import BaseCommand
from django.db.models import Q

from apps.tasks.models import Task, Event
from apps.cases.models import Case
from apps.notifications.utils import create_notification


TASK_THRESHOLDS = [1, 3]   # days before due_date
EVENT_THRESHOLDS = [1]
CASE_DEADLINE_THRESHOLDS = [1, 3, 7]   # процессуальные сроки — предупреждаем раньше
OVERDUE_TASK_DAYS = [1, 3, 7]          # напоминания после просрочки, дальше — раз в неделю


def _should_remind_overdue(days):
    """Первые дни просрочки напоминаем чаще, потом еженедельно — чтобы
    висящая месяцами задача не превратилась в ежедневный спам."""
    return days in OVERDUE_TASK_DAYS or (days > 7 and days % 7 == 0)


def _days_word(days):
    if days % 10 == 1 and days % 100 != 11:
        return 'день'
    if days % 10 in (2, 3, 4) and days % 100 not in (12, 13, 14):
        return 'дня'
    return 'дней'


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
                body = f'До срока осталось {days} {_days_word(days)}'
                if task.case_id:
                    body += f' · дело: {task.case.title}'
                link = f'/cases/{task.case.uuid}' if task.case_id else '/tasks'
                n = create_notification(
                    user=task.assigned_to,
                    title=f'⏰ Дедлайн через {days}д: {task.title}',
                    body=body,
                    link=link,
                    key=key,
                    tg_buttons=[[
                        {'text': '✅ Выполнено', 'callback_data': f'task_done:{task.id}'},
                        {'text': '⏰ +1 день', 'callback_data': f'task_snooze:{task.id}'},
                    ]],
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

        # ── Процессуальные сроки по делам ──────────────────────────────────
        open_cases = Case.objects.filter(
            key_deadline__isnull=False,
            status__in=[Case.STATUS_NEW, Case.STATUS_ACTIVE, Case.STATUS_ON_HOLD],
        ).select_related('lead_lawyer').prefetch_related('assigned_lawyers')

        for days in CASE_DEADLINE_THRESHOLDS:
            target = today + timedelta(days=days)
            for case in open_cases.filter(key_deadline=target):
                recipients = set(case.assigned_lawyers.all())
                if case.lead_lawyer:
                    recipients.add(case.lead_lawyer)
                note = f' · {case.key_deadline_note}' if case.key_deadline_note else ''
                for user in recipients:
                    key = f'case_{case.id}_deadline_{days}d_user_{user.id}'
                    n = create_notification(
                        user=user,
                        title=f'⚖️ Срок через {days}д по делу: {case.title}',
                        body=f'Процессуальный срок {case.key_deadline}{note}',
                        link=f'/cases/{case.uuid}',
                        key=key,
                    )
                    if n:
                        created += 1

        # ── Просроченные задачи ────────────────────────────────────────────
        for task in active_tasks.filter(due_date__lt=today):
            days = (today - task.due_date).days
            if not _should_remind_overdue(days):
                continue
            body = f'Просрочена на {days} {_days_word(days)}'
            if task.case_id:
                body += f' · дело: {task.case.title}'
            link = f'/cases/{task.case.uuid}' if task.case_id else '/tasks'
            n = create_notification(
                user=task.assigned_to,
                title=f'🔴 Просрочена задача: {task.title}',
                body=body,
                link=link,
                key=f'task_{task.id}_overdue_{days}d',
                tg_buttons=[[
                    {'text': '✅ Выполнено', 'callback_data': f'task_done:{task.id}'},
                    {'text': '⏰ +1 день', 'callback_data': f'task_snooze:{task.id}'},
                ]],
            )
            if n:
                created += 1

        # ── Просроченные процессуальные сроки ──────────────────────────────
        # напоминаем каждый день: пропущенный процессуальный срок необратим
        for case in open_cases.filter(key_deadline__lt=today):
            days = (today - case.key_deadline).days
            recipients = set(case.assigned_lawyers.all())
            if case.lead_lawyer:
                recipients.add(case.lead_lawyer)
            note = f' · {case.key_deadline_note}' if case.key_deadline_note else ''
            for user in recipients:
                n = create_notification(
                    user=user,
                    title=f'🔴 ПРОСРОЧЕН срок по делу: {case.title}',
                    body=f'Срок был {case.key_deadline} — {days} {_days_word(days)} назад{note}',
                    link=f'/cases/{case.uuid}',
                    key=f'case_{case.id}_overdue_{today}_user_{user.id}',
                )
                if n:
                    created += 1

        self.stdout.write(self.style.SUCCESS(f'Created {created} reminder notifications'))
