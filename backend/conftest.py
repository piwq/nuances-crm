import pytest
from rest_framework.test import APIClient

from apps.accounts.models import CustomUser
from apps.clients.models import Client
from apps.cases.models import Case


@pytest.fixture(autouse=True)
def _tmp_media(settings, tmp_path):
    settings.MEDIA_ROOT = str(tmp_path / 'media')


@pytest.fixture(autouse=True)
def _locmem_email(settings):
    # в .env настроен реальный SMTP — тесты не должны слать письма наружу
    settings.EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'


@pytest.fixture(autouse=True)
def _no_real_telegram(monkeypatch):
    # в окружении боевой TELEGRAM_BOT_TOKEN — тесты не должны ходить в Bot API
    monkeypatch.setattr(
        'apps.notifications.telegram.send_telegram_message',
        lambda *args, **kwargs: True)


@pytest.fixture(autouse=True)
def _inmemory_channel_layer(settings):
    # уведомления шлют group_send; в тестах Redis не нужен
    from channels.layers import channel_layers
    settings.CHANNEL_LAYERS = {'default': {'BACKEND': 'channels.layers.InMemoryChannelLayer'}}
    channel_layers.backends = {}
    yield
    channel_layers.backends = {}


@pytest.fixture
def api():
    return APIClient()


@pytest.fixture
def admin_user(db):
    return CustomUser.objects.create_user(
        username='boss', email='boss@test.com', password='Vq7#strong-pass',
        role='admin', first_name='Ольга', last_name='Директорова')


@pytest.fixture
def lawyer_a(db):
    return CustomUser.objects.create_user(
        username='lawyer_a', email='a@test.com', password='Vq7#strong-pass',
        role='lawyer', first_name='Анна', last_name='Александрова')


@pytest.fixture
def lawyer_b(db):
    return CustomUser.objects.create_user(
        username='lawyer_b', email='b@test.com', password='Vq7#strong-pass',
        role='lawyer', first_name='Борис', last_name='Борисов')


@pytest.fixture
def client_a(db, lawyer_a):
    return Client.objects.create(
        client_type='individual', last_name='Иванов', first_name='Иван', created_by=lawyer_a)


@pytest.fixture
def case_a(db, lawyer_a, client_a):
    """Дело, доступное только lawyer_a (ведущий юрист)."""
    return Case.objects.create(
        title='Дело А', client=client_a, lead_lawyer=lawyer_a, created_by=lawyer_a)
