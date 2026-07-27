import pytest
from django.core.management import call_command

from apps.accounts.models import CustomUser
from apps.billing.models import Invoice, TimeEntry
from apps.cases.models import Case
from apps.clients.models import Client
from apps.documents.models import Document
from apps.tasks.models import Task


@pytest.mark.django_db
class TestSeedDemo:
    def test_seed_creates_consistent_dataset(self):
        """Prod-стек гоняет seed_demo при каждом старте — команда обязана
        переживать изменения моделей."""
        call_command('seed_demo')

        assert CustomUser.objects.filter(username='director').exists()
        assert Client.objects.exists()
        assert Case.objects.exists()
        assert Task.objects.exists()
        assert Document.objects.exists()
        assert TimeEntry.objects.exists()
        assert Invoice.objects.exists()

        # ссылки в демо-уведомлениях ведут на существующие дела (были по int id)
        from apps.notifications.models import Notification
        for link in Notification.objects.exclude(link='').values_list('link', flat=True):
            if link.startswith('/cases/'):
                assert Case.objects.filter(uuid=link.rsplit('/', 1)[1]).exists()

    def test_skip_if_exists_is_idempotent(self, client_a):
        call_command('seed_demo', '--skip-if-exists')
        assert Client.objects.count() == 1  # существующие данные не тронуты
