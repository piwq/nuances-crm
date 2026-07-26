import pytest
from rest_framework.test import APIClient
from apps.accounts.models import CustomUser
from apps.cases.models import Case
from apps.clients.models import Client
from apps.documents.models import Document
import uuid

@pytest.fixture
def api_client():
    return APIClient()

@pytest.fixture
def lawyers(db):
    l1 = CustomUser.objects.create_user(username='lawyer1', email='lawyer1@test.com', password='password123', role='lawyer', first_name='L1', last_name='Test')
    l2 = CustomUser.objects.create_user(username='lawyer2', email='lawyer2@test.com', password='password123', role='lawyer', first_name='L2', last_name='Test')
    return l1, l2

@pytest.fixture
def client_l1(db, lawyers):
    l1, _ = lawyers
    return Client.objects.create(client_type='individual', last_name='Client1', created_by=l1)

@pytest.fixture
def case_l1(db, lawyers, client_l1):
    l1, _ = lawyers
    case = Case.objects.create(title='Case L1', client=client_l1, lead_lawyer=l1, created_by=l1)
    return case

@pytest.mark.django_db
class TestIDORSecurity:
    
    def test_lawyer_cannot_view_other_lawyers_case_detail(self, api_client, lawyers, case_l1):
        _, l2 = lawyers
        api_client.force_authenticate(user=l2)
        url = f'/api/v1/cases/{case_l1.uuid}/'
        response = api_client.get(url)
        # Should be 404 because queryset filters by assigned/lead lawyer
        assert response.status_code == 404

    def test_lawyer_can_view_own_case_detail(self, api_client, lawyers, case_l1):
        l1, _ = lawyers
        api_client.force_authenticate(user=l1)
        url = f'/api/v1/cases/{case_l1.uuid}/'
        response = api_client.get(url)
        assert response.status_code == 200
        assert response.data['uuid'] == str(case_l1.uuid)

    def test_chat_history_limited_to_own_conversations(self, api_client, lawyers):
        from apps.chat.models import ChatMessage
        l1, l2 = lawyers
        l3 = CustomUser.objects.create_user(
            username='lawyer3', email='lawyer3@test.com', password='password123',
            role='lawyer', first_name='L3', last_name='Test')
        ChatMessage.objects.create(user=l1, recipient=l2, text='для l2')
        ChatMessage.objects.create(user=l1, recipient=l3, text='для l3')
        api_client.force_authenticate(user=l2)
        response = api_client.get(f'/api/v1/chat/history/?recipient_id={l1.id}')
        assert response.status_code == 200
        texts = [m['text'] for m in response.data['results']]
        # l2 видит только свою переписку с l1, чужое сообщение l1→l3 не отдаётся
        assert texts == ['для l2']

    def test_uuid_enumeration_prevention(self, api_client, lawyers):
        l1, _ = lawyers
        api_client.force_authenticate(user=l1)
        # Try a random UUID
        random_uuid = uuid.uuid4()
        url = f'/api/v1/cases/{random_uuid}/'
        response = api_client.get(url)
        assert response.status_code == 404
