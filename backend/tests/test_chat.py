import pytest

from apps.chat.models import ChatMessage


@pytest.mark.django_db
class TestChatContacts:
    def test_admin_present_in_contacts(self, api, lawyer_a, admin_user):
        # юрист должен иметь возможность написать администратору
        api.force_authenticate(lawyer_a)
        resp = api.get('/api/v1/chat/lawyers/')
        assert resp.status_code == 200
        roles = {row['role'] for row in resp.data}
        assert 'admin' in roles
        assert lawyer_a.id not in {row['id'] for row in resp.data}

    def test_inactive_users_hidden(self, api, lawyer_a, lawyer_b):
        lawyer_b.is_active = False
        lawyer_b.save(update_fields=['is_active'])
        api.force_authenticate(lawyer_a)
        resp = api.get('/api/v1/chat/lawyers/')
        assert lawyer_b.id not in {row['id'] for row in resp.data}


@pytest.mark.django_db
class TestChatHistoryPagination:
    def test_newest_first_with_pagination(self, api, lawyer_a, lawyer_b):
        for i in range(30):
            ChatMessage.objects.create(user=lawyer_a, recipient=lawyer_b, text=f'm{i}')
        api.force_authenticate(lawyer_b)

        resp = api.get('/api/v1/chat/history/', {'recipient_id': lawyer_a.id, 'page': 1})
        texts = [m['text'] for m in resp.data['results']]
        assert len(texts) == 25
        assert texts[0] == 'm29'  # свежие первыми
        assert resp.data['next']

        resp2 = api.get('/api/v1/chat/history/', {'recipient_id': lawyer_a.id, 'page': 2})
        texts2 = [m['text'] for m in resp2.data['results']]
        assert len(texts2) == 5
        assert texts2[-1] == 'm0'
        assert resp2.data['next'] is None
