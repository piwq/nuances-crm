import pytest

from apps.cases.models import CaseNote


@pytest.mark.django_db
class TestClientCasesScoping:
    def test_lawyer_sees_only_own_cases_of_client(self, api, lawyer_a, lawyer_b, client_a, case_a):
        api.force_authenticate(lawyer_b)
        resp = api.get(f'/api/v1/clients/{client_a.uuid}/cases/')
        assert resp.status_code == 200
        assert resp.data == []

        api.force_authenticate(lawyer_a)
        resp = api.get(f'/api/v1/clients/{client_a.uuid}/cases/')
        assert [c['uuid'] for c in resp.data] == [str(case_a.uuid)]

    def test_admin_sees_all_cases_of_client(self, api, admin_user, client_a, case_a):
        api.force_authenticate(admin_user)
        resp = api.get(f'/api/v1/clients/{client_a.uuid}/cases/')
        assert len(resp.data) == 1


@pytest.mark.django_db
class TestCaseNotesScoping:
    def test_foreign_notes_hidden(self, api, lawyer_a, lawyer_b, case_a):
        note = CaseNote.objects.create(case=case_a, author=lawyer_a, text='секрет')
        api.force_authenticate(lawyer_b)
        resp = api.get(f'/api/v1/cases/{case_a.id}/notes/')
        assert resp.status_code == 200
        assert resp.data['results'] == []
        assert api.post(f'/api/v1/cases/{case_a.id}/notes/', {'text': 'x'}).status_code == 404
        assert api.delete(f'/api/v1/cases/{case_a.id}/notes/{note.id}/').status_code == 404

    def test_own_notes_work(self, api, lawyer_a, case_a):
        api.force_authenticate(lawyer_a)
        assert api.post(f'/api/v1/cases/{case_a.id}/notes/', {'text': 'заметка'}).status_code == 201
        resp = api.get(f'/api/v1/cases/{case_a.id}/notes/')
        assert len(resp.data['results']) == 1


@pytest.mark.django_db
class TestCaseCreatorAccess:
    def test_lawyer_creator_becomes_lead_and_sees_case(self, api, lawyer_a, client_a):
        # регрессия: юрист создавал дело без ведущего и сразу получал 404
        # на его карточке (created_by не входит в скоупинг видимости)
        api.force_authenticate(lawyer_a)
        resp = api.post('/api/v1/cases/', {
            'title': 'Свежее дело', 'client': client_a.id, 'category': 'civil'})
        assert resp.status_code == 201
        assert resp.data['lead_lawyer'] == lawyer_a.id
        assert api.get(f"/api/v1/cases/{resp.data['uuid']}/").status_code == 200

    def test_creator_kept_in_team_when_lead_is_other(self, api, lawyer_a, lawyer_b, client_a):
        api.force_authenticate(lawyer_a)
        resp = api.post('/api/v1/cases/', {
            'title': 'Дело для коллеги', 'client': client_a.id, 'category': 'civil',
            'lead_lawyer': lawyer_b.id})
        assert resp.status_code == 201
        assert lawyer_a.id in resp.data['assigned_lawyers']
        assert api.get(f"/api/v1/cases/{resp.data['uuid']}/").status_code == 200

    def test_no_self_notification_on_own_case(self, api, lawyer_a, client_a):
        from apps.notifications.models import Notification
        Notification.objects.all().delete()
        api.force_authenticate(lawyer_a)
        api.post('/api/v1/cases/', {
            'title': 'Тихое дело', 'client': client_a.id, 'category': 'civil'})
        assert not Notification.objects.filter(user=lawyer_a).exists()

    def test_admin_creation_keeps_lead_empty(self, api, admin_user, client_a):
        api.force_authenticate(admin_user)
        resp = api.post('/api/v1/cases/', {
            'title': 'Дело админа', 'client': client_a.id, 'category': 'civil'})
        assert resp.status_code == 201
        assert resp.data['lead_lawyer'] is None
        assert api.get(f"/api/v1/cases/{resp.data['uuid']}/").status_code == 200


@pytest.mark.django_db
class TestDeletionGuards:
    def test_client_delete_admin_only(self, api, lawyer_a, client_a):
        api.force_authenticate(lawyer_a)
        assert api.delete(f'/api/v1/clients/{client_a.uuid}/').status_code == 403

    def test_client_with_cases_delete_blocked(self, api, admin_user, client_a, case_a):
        api.force_authenticate(admin_user)
        resp = api.delete(f'/api/v1/clients/{client_a.uuid}/')
        assert resp.status_code == 400  # PROTECT: раньше падало 500-й ProtectedError

    def test_client_without_cases_deleted(self, api, admin_user, client_a):
        api.force_authenticate(admin_user)
        assert api.delete(f'/api/v1/clients/{client_a.uuid}/').status_code == 204

    def test_case_with_invoice_delete_blocked(self, api, admin_user, case_a, client_a):
        from datetime import date
        from apps.billing.models import Invoice
        Invoice.objects.create(case=case_a, client=client_a, due_date=date.today())
        api.force_authenticate(admin_user)
        assert api.delete(f'/api/v1/cases/{case_a.uuid}/').status_code == 400

    def test_case_delete_ok_for_admin(self, api, admin_user, case_a):
        api.force_authenticate(admin_user)
        assert api.delete(f'/api/v1/cases/{case_a.uuid}/').status_code == 204


@pytest.mark.django_db
class TestCaseListAnnotations:
    def test_task_count_not_multiplied_by_m2m_join(self, api, lawyer_a, lawyer_b, case_a):
        """Скоупинг джойнит assigned_lawyers — без distinct счётчик задач
        умножался бы на число назначенных юристов."""
        from apps.tasks.models import Task
        case_a.assigned_lawyers.add(lawyer_a, lawyer_b)
        for i in range(2):
            Task.objects.create(title=f'Задача {i}', case=case_a,
                                created_by=lawyer_a, status='todo')

        api.force_authenticate(lawyer_a)
        resp = api.get('/api/v1/cases/')
        assert resp.data['count'] == 1
        assert resp.data['results'][0]['open_tasks_count'] == 2
