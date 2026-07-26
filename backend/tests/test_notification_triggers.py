from datetime import date, timedelta

import pytest

from apps.cases.models import Case
from apps.chat.models import ChatMessage
from apps.documents.models import Document
from apps.notifications.models import Notification


@pytest.mark.django_db
class TestNotificationTriggers:
    def test_lead_lawyer_notified_once(self, case_a, lawyer_a):
        notes = Notification.objects.filter(user=lawyer_a, title__startswith='Вы ответственный')
        assert notes.count() == 1
        assert notes.first().link == f'/cases/{case_a.uuid}'
        case_a.save()  # повторное сохранение без смены ответственного
        assert Notification.objects.filter(
            user=lawyer_a, title__startswith='Вы ответственный').count() == 1

    def test_assigned_lawyer_notified_once(self, case_a, lawyer_b):
        case_a.assigned_lawyers.add(lawyer_b)
        notes = Notification.objects.filter(user=lawyer_b, title__startswith='Вы назначены')
        assert notes.count() == 1
        case_a.assigned_lawyers.remove(lawyer_b)
        case_a.assigned_lawyers.add(lawyer_b)  # повторное назначение — дедуп по key
        assert Notification.objects.filter(
            user=lawyer_b, title__startswith='Вы назначены').count() == 1

    def test_deadline_change_notifies_team(self, case_a, lawyer_a, lawyer_b):
        case_a.assigned_lawyers.add(lawyer_b)
        Notification.objects.all().delete()

        case_a.key_deadline = date.today() + timedelta(days=10)
        case_a.save()
        for user in (lawyer_a, lawyer_b):
            assert Notification.objects.filter(
                user=user, title__startswith='Изменён процессуальный срок').count() == 1

        case_a.save()  # тот же срок — дублей нет
        assert Notification.objects.filter(
            title__startswith='Изменён процессуальный срок').count() == 2

    def test_new_document_notifies_team_except_uploader(self, case_a, lawyer_a, lawyer_b):
        from django.core.files.uploadedfile import SimpleUploadedFile
        case_a.assigned_lawyers.add(lawyer_b)
        Notification.objects.all().delete()

        Document.objects.create(
            case=case_a, title='Иск', document_type='court_filing',
            file=SimpleUploadedFile('claim.txt', b'x'), uploaded_by=lawyer_a)

        assert Notification.objects.filter(
            user=lawyer_b, title__startswith='Новый документ').count() == 1
        assert not Notification.objects.filter(
            user=lawyer_a, title__startswith='Новый документ').exists()

    def test_chat_message_notifies_recipient(self, lawyer_a, lawyer_b):
        ChatMessage.objects.create(user=lawyer_a, recipient=lawyer_b, text='Привет!')
        note = Notification.objects.get(user=lawyer_b, title__startswith='Сообщение от')
        assert 'Привет!' in note.body
        assert note.link == '/chat'
        assert not Notification.objects.filter(
            user=lawyer_a, title__startswith='Сообщение от').exists()
