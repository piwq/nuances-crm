import pytest


@pytest.mark.django_db
class TestPasswordValidation:
    def test_weak_password_rejected(self, api, lawyer_a):
        # раньше проверялась только длина — '12345678' проходил
        api.force_authenticate(lawyer_a)
        resp = api.post('/api/v1/auth/change-password/', {
            'current_password': 'Vq7#strong-pass', 'new_password': '12345678'})
        assert resp.status_code == 400

    def test_wrong_current_rejected(self, api, lawyer_a):
        api.force_authenticate(lawyer_a)
        resp = api.post('/api/v1/auth/change-password/', {
            'current_password': 'nope', 'new_password': 'Zx9#new-strong'})
        assert resp.status_code == 400

    def test_strong_password_accepted(self, api, lawyer_a):
        api.force_authenticate(lawyer_a)
        resp = api.post('/api/v1/auth/change-password/', {
            'current_password': 'Vq7#strong-pass', 'new_password': 'Zx9#new-strong'})
        assert resp.status_code == 200
        lawyer_a.refresh_from_db()
        assert lawyer_a.check_password('Zx9#new-strong')

    def test_admin_cannot_create_user_with_weak_password(self, api, admin_user):
        api.force_authenticate(admin_user)
        resp = api.post('/api/v1/users/', {
            'username': 'newbie', 'email': 'n@test.com', 'password': 'password1',
            'first_name': 'Новый', 'last_name': 'Юрист', 'role': 'lawyer'})
        assert resp.status_code == 400


@pytest.mark.django_db
class TestPublicProfile:
    def test_lawyers_list_has_no_private_fields(self, api, lawyer_a, lawyer_b):
        # email/phone/telegram_chat_id не должны утекать коллегам
        api.force_authenticate(lawyer_a)
        resp = api.get('/api/v1/users/lawyers/')
        assert resp.status_code == 200
        assert resp.data, 'список юристов пуст'
        for row in resp.data:
            for field in ('email', 'phone', 'telegram_chat_id'):
                assert field not in row

    def test_chat_lawyers_list_has_no_private_fields(self, api, lawyer_a, lawyer_b):
        api.force_authenticate(lawyer_a)
        resp = api.get('/api/v1/chat/lawyers/')
        assert resp.status_code == 200
        assert resp.data, 'список юристов пуст'
        for row in resp.data:
            for field in ('email', 'phone', 'telegram_chat_id'):
                assert field not in row
