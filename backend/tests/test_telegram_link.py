from datetime import date, timedelta

import pytest
from django.utils import timezone

from apps.accounts.models import TelegramLinkToken
from apps.accounts.telegram_link import create_link_token, use_link_token
from apps.notifications.bot import get_user_by_chat, tasks_text, cases_text


@pytest.mark.django_db
class TestTelegramLink:
    def test_link_flow(self, lawyer_a):
        token = create_link_token(lawyer_a)
        assert len(token) <= 64  # лимит Telegram на start-параметр
        user = use_link_token(token, 123456789)
        assert user == lawyer_a
        lawyer_a.refresh_from_db()
        assert lawyer_a.telegram_chat_id == '123456789'
        assert use_link_token(token, 1) is None  # токен одноразовый

    def test_expired_token_rejected(self, lawyer_a):
        token = create_link_token(lawyer_a)
        TelegramLinkToken.objects.update(created_at=timezone.now() - timedelta(minutes=16))
        assert use_link_token(token, 1) is None

    def test_new_token_replaces_old(self, lawyer_a):
        t1 = create_link_token(lawyer_a)
        t2 = create_link_token(lawyer_a)
        assert use_link_token(t1, 1) is None
        assert use_link_token(t2, 2) == lawyer_a

    def test_endpoint_503_without_bot(self, api, lawyer_a, settings):
        settings.TELEGRAM_BOT_TOKEN = ''
        api.force_authenticate(lawyer_a)
        assert api.post('/api/v1/auth/telegram-link/').status_code == 503

    def test_endpoint_returns_deeplink(self, api, lawyer_a, monkeypatch):
        from apps.notifications import telegram as tg
        monkeypatch.setattr(tg, 'get_bot_username', lambda: 'NuancesCrmBot')
        api.force_authenticate(lawyer_a)
        resp = api.post('/api/v1/auth/telegram-link/')
        assert resp.status_code == 200
        assert resp.data['link'].startswith('https://t.me/NuancesCrmBot?start=')
        token = resp.data['link'].split('start=')[1]
        assert use_link_token(token, 555) == lawyer_a


@pytest.mark.django_db
class TestBotTexts:
    def test_tasks_and_cases_text(self, lawyer_a, lawyer_b, case_a):
        from apps.tasks.models import Task
        Task.objects.create(
            title='Подать иск', case=case_a, assigned_to=lawyer_a,
            created_by=lawyer_a, due_date=date(2026, 8, 1))
        lawyer_a.telegram_chat_id = '42'
        lawyer_a.save(update_fields=['telegram_chat_id'])

        assert get_user_by_chat(42) == lawyer_a
        assert get_user_by_chat(999) is None

        text = tasks_text(lawyer_a)
        assert 'Подать иск' in text
        assert '01.08.2026' in text
        assert case_a.case_number in text

        text = cases_text(lawyer_a)
        assert case_a.case_number in text
        assert 'Дело А' in text

        # у второго юриста пусто, и чужие данные не светятся
        assert tasks_text(lawyer_b) == 'Активных задач нет 🎉'
        assert cases_text(lawyer_b) == 'Открытых дел нет.'
