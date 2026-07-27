from datetime import date, timedelta

import pytest
from django.core.management import call_command

from apps.notifications.management.commands.send_deadline_reminders import (
    _should_remind_overdue,
)
from apps.notifications.models import Notification
from apps.tasks.models import Task


def test_overdue_cadence():
    # первые дни — часто, потом раз в неделю, чтобы не спамить
    assert [d for d in range(1, 30) if _should_remind_overdue(d)] == [1, 3, 7, 14, 21, 28]


@pytest.mark.django_db
class TestOverdueTasks:
    def _task(self, lawyer, case, days_overdue):
        return Task.objects.create(
            title='Подать отзыв', case=case, assigned_to=lawyer, created_by=lawyer,
            due_date=date.today() - timedelta(days=days_overdue))

    def test_reminds_and_dedupes(self, lawyer_a, case_a):
        self._task(lawyer_a, case_a, 3)
        Notification.objects.all().delete()

        call_command('send_deadline_reminders')
        note = Notification.objects.get(user=lawyer_a, title__startswith='🔴 Просрочена')
        assert 'Просрочена на 3 дня' in note.body

        call_command('send_deadline_reminders')  # тот же день — дубля нет
        assert Notification.objects.filter(title__startswith='🔴 Просрочена').count() == 1

    def test_silent_on_off_days(self, lawyer_a, case_a):
        self._task(lawyer_a, case_a, 5)  # 5-й день не в расписании
        Notification.objects.all().delete()
        call_command('send_deadline_reminders')
        assert not Notification.objects.filter(title__startswith='🔴 Просрочена').exists()

    def test_done_task_is_not_nagged(self, lawyer_a, case_a):
        task = self._task(lawyer_a, case_a, 7)
        task.status = 'done'
        task.save()
        Notification.objects.all().delete()
        call_command('send_deadline_reminders')
        assert not Notification.objects.filter(title__startswith='🔴 Просрочена').exists()


@pytest.mark.django_db
class TestOverdueCaseDeadline:
    def test_daily_reminder_for_missed_procedural_deadline(self, lawyer_a, case_a):
        case_a.key_deadline = date.today() - timedelta(days=2)
        case_a.status = 'active'
        case_a.key_deadline_note = 'Подача апелляции'
        case_a.save()
        Notification.objects.all().delete()

        call_command('send_deadline_reminders')
        note = Notification.objects.get(user=lawyer_a, title__startswith='🔴 ПРОСРОЧЕН')
        assert '2 дня назад' in note.body
        assert 'Подача апелляции' in note.body

        call_command('send_deadline_reminders')  # в тот же день — один раз
        assert Notification.objects.filter(title__startswith='🔴 ПРОСРОЧЕН').count() == 1

    def test_closed_case_is_not_nagged(self, lawyer_a, case_a):
        case_a.key_deadline = date.today() - timedelta(days=2)
        case_a.status = 'closed'
        case_a.save()
        Notification.objects.all().delete()
        call_command('send_deadline_reminders')
        assert not Notification.objects.filter(title__startswith='🔴 ПРОСРОЧЕН').exists()


@pytest.mark.django_db
def test_digest_lists_overdue(lawyer_a, case_a):
    from apps.notifications.bot import today_digest_text
    lawyer_a.telegram_chat_id = '777'
    lawyer_a.save(update_fields=['telegram_chat_id'])
    Task.objects.create(title='Забытая задача', case=case_a, assigned_to=lawyer_a,
                        created_by=lawyer_a, due_date=date.today() - timedelta(days=4))

    text = today_digest_text(lawyer_a)
    assert 'Просрочено' in text
    assert 'Забытая задача' in text
