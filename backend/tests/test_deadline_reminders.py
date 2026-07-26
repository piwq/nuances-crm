from datetime import date, timedelta

import pytest
from django.core.management import call_command

from apps.notifications.models import Notification
from apps.notifications.management.commands.send_deadline_reminders import _days_word


def test_days_word():
    assert _days_word(1) == 'день'
    assert _days_word(3) == 'дня'
    assert _days_word(7) == 'дней'
    assert _days_word(11) == 'дней'
    assert _days_word(21) == 'день'


@pytest.mark.django_db
def test_case_deadline_reminder_created_once(case_a, lawyer_a):
    case_a.key_deadline = date.today() + timedelta(days=3)
    case_a.status = 'active'
    case_a.save()
    # сигналы о назначении/переносе срока к этому тесту не относятся
    Notification.objects.all().delete()

    call_command('send_deadline_reminders')
    notes = Notification.objects.filter(user=lawyer_a)
    assert notes.count() == 1
    assert notes.first().link == f'/cases/{case_a.uuid}'

    # повторный прогон — дедуп по key, дублей нет (планировщик крутится каждый час)
    call_command('send_deadline_reminders')
    assert Notification.objects.filter(user=lawyer_a).count() == 1


@pytest.mark.django_db
def test_task_reminder_uses_correct_plural(case_a, lawyer_a):
    from apps.tasks.models import Task
    Task.objects.create(
        title='Подать апелляцию', case=case_a, assigned_to=lawyer_a,
        created_by=lawyer_a, due_date=date.today() + timedelta(days=3))
    Notification.objects.all().delete()  # сигнал о назначении задачи не относится к тесту

    call_command('send_deadline_reminders')
    reminder = Notification.objects.get(user=lawyer_a)
    assert 'осталось 3 дня' in reminder.body
