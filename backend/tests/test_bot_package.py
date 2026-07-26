from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.core.management import call_command
from django.utils import timezone

from apps.notifications.bot import (
    esc, expandable, tasks_text, deadlines_text, hours_text, find_text,
    today_digest_text, complete_task_via_chat, snooze_task_via_chat,
    cases_keyboard, case_info_text, case_tasks_view, case_docs_view,
)
from apps.notifications.models import Notification


class TestMarkdownHelpers:
    def test_esc_escapes_specials(self):
        assert esc('Дело №1 (тест)! a_b.c') == 'Дело №1 \\(тест\\)\\! a\\_b\\.c'

    def test_expandable_quote_syntax(self):
        assert expandable(['один']) == '**>один||'
        assert expandable(['a', 'b', 'c']) == '**>a\n>b\n>c||'


@pytest.fixture
def linked(lawyer_a):
    lawyer_a.telegram_chat_id = '777'
    lawyer_a.save(update_fields=['telegram_chat_id'])
    return lawyer_a


@pytest.mark.django_db
class TestBotTexts:
    def test_deadlines_text_marks_overdue(self, linked, case_a):
        case_a.key_deadline = date.today() - timedelta(days=2)
        case_a.status = 'active'
        case_a.save()
        text = deadlines_text(linked)
        assert '❗️' in text
        assert 'просрочен на 2 дн' in text

    def test_hours_text_counts_own_entries(self, linked, case_a):
        from apps.billing.models import TimeEntry
        TimeEntry.objects.create(
            case=case_a, lawyer=linked, date=date.today(),
            hours=Decimal('2.00'), description='x', hourly_rate=Decimal('1000'))
        text = hours_text(linked)
        assert '2' in text and '₽' in text

    def test_find_scoped(self, linked, lawyer_b, case_a):
        # lawyer_b не видит чужое дело, но видит клиента
        lawyer_b.telegram_chat_id = '888'
        lawyer_b.save(update_fields=['telegram_chat_id'])
        text = find_text(lawyer_b, 'Дело А')
        assert 'Дела' not in text
        text = find_text(linked, 'Дело А')
        assert esc(case_a.case_number) in text
        assert find_text(linked, 'ы') == 'Введите минимум 3 символа: `/find иванов`'

    def test_today_digest_lists_today_items(self, linked, case_a):
        from apps.tasks.models import Task, Event
        Task.objects.create(title='Сдать отчёт', assigned_to=linked,
                            created_by=linked, due_date=date.today())
        import datetime as dt
        # полдень СЕГОДНЯ по локальной TZ: сборка от UTC-компонент около
        # полуночи по Москве попадала во вчерашний день
        noon = timezone.make_aware(dt.datetime.combine(timezone.localdate(), dt.time(12, 0)))
        Event.objects.create(
            title='Заседание по иску', event_type='court_hearing',
            case=case_a, created_by=linked, start_datetime=noon)
        case_a.key_deadline = date.today() + timedelta(days=1)
        case_a.status = 'active'
        case_a.save()

        text = today_digest_text(linked)
        assert 'Сводка на' in text
        assert 'Сдать отчёт' in text
        assert 'Заседание по иску' in text
        assert 'Горящие сроки' in text

    def test_today_digest_empty_day(self, linked):
        assert '🎉' in today_digest_text(linked)


@pytest.mark.django_db
class TestCaseNavigation:
    def test_cases_keyboard_buttons(self, linked, case_a):
        text, rows = cases_keyboard(linked)
        assert 'нажмите' in text
        assert rows[0][0]['callback_data'] == f'case_info:{case_a.id}'
        assert case_a.case_number in rows[0][0]['text']

    def test_case_info_card(self, linked, case_a):
        case_a.key_deadline = date.today() + timedelta(days=5)
        case_a.opposing_party = 'ООО «Ромашка»'
        case_a.save()
        text, rows = case_info_text('777', case_a.id)
        assert esc(case_a.case_number) in text
        assert 'Ромашка' in text
        assert '⚖️' in text
        flat = [b['callback_data'] for row in rows for b in row]
        assert f'case_tasks:{case_a.id}' in flat
        assert f'case_docs:{case_a.id}' in flat
        assert 'cases_list' in flat

    def test_case_info_scoped(self, linked, lawyer_b, case_a):
        lawyer_b.telegram_chat_id = '888'
        lawyer_b.save(update_fields=['telegram_chat_id'])
        assert case_info_text('888', case_a.id) == (None, None)
        assert case_tasks_view('888', case_a.id) == (None, None)
        assert case_docs_view('888', case_a.id) == (None, None)

    def test_case_tasks_and_docs_views(self, linked, case_a):
        from apps.tasks.models import Task
        Task.objects.create(title='Подготовить отзыв', case=case_a,
                            assigned_to=linked, created_by=linked)
        text, rows = case_tasks_view('777', case_a.id)
        assert 'Подготовить отзыв' in text
        assert rows[0][0]['callback_data'] == f'case_info:{case_a.id}'
        text, _ = case_docs_view('777', case_a.id)
        assert 'документов нет' in text


@pytest.mark.django_db
class TestInlineActions:
    def test_complete_task_via_chat(self, linked, case_a):
        from apps.tasks.models import Task
        task = Task.objects.create(title='Позвонить', assigned_to=linked, created_by=linked)
        result = complete_task_via_chat('777', task.id)
        assert 'выполненной' in result
        task.refresh_from_db()
        assert task.status == 'done'
        assert 'уже была выполнена' in complete_task_via_chat('777', task.id)

    def test_foreign_chat_rejected(self, linked, lawyer_b, case_a):
        from apps.tasks.models import Task
        lawyer_b.telegram_chat_id = '999'
        lawyer_b.save(update_fields=['telegram_chat_id'])
        task = Task.objects.create(title='Секретная', assigned_to=linked, created_by=linked)
        assert complete_task_via_chat('999', task.id) == 'Эта задача вам недоступна.'
        assert complete_task_via_chat('000', task.id) is None  # непривязанный чат

    def test_snooze_shifts_due_date(self, linked):
        from apps.tasks.models import Task
        task = Task.objects.create(title='Отложить', assigned_to=linked,
                                   created_by=linked, due_date=date.today())
        result = snooze_task_via_chat('777', task.id)
        task.refresh_from_db()
        assert task.due_date == date.today() + timedelta(days=1)
        assert '⏰' in result


@pytest.mark.django_db
class TestDigestCommand:
    def test_force_sends_once_per_day(self, linked, monkeypatch):
        sent = []
        monkeypatch.setattr(
            'apps.notifications.management.commands.send_telegram_digest.send_telegram_message',
            lambda chat_id, text, **kw: sent.append((chat_id, text)) or True)

        call_command('send_telegram_digest', '--force')
        assert len(sent) == 1
        assert sent[0][0] == '777'
        assert Notification.objects.filter(key__startswith=f'digest_{linked.id}_').count() == 1

        call_command('send_telegram_digest', '--force')  # дедуп на день
        assert len(sent) == 1

    def test_outside_window_skips(self, linked, monkeypatch):
        sent = []
        monkeypatch.setattr(
            'apps.notifications.management.commands.send_telegram_digest.send_telegram_message',
            lambda *a, **kw: sent.append(a) or True)
        # без --force: команда сама проверяет будни/час — в большинстве запусков окно закрыто.
        # Здесь важно лишь, что вне окна ничего не шлётся и не падает.
        now = timezone.localtime()
        if now.weekday() >= 5 or now.hour != 7:
            call_command('send_telegram_digest')
            assert sent == []
