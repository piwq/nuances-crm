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
