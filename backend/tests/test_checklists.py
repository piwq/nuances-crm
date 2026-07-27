from datetime import date, timedelta

import pytest

from apps.tasks.models import CaseChecklist, ChecklistItem, Task


@pytest.fixture
def checklist(db, admin_user):
    cl = CaseChecklist.objects.create(name='Исковое производство', category='civil',
                                      created_by=admin_user)
    ChecklistItem.objects.create(checklist=cl, title='Подготовить иск',
                                 days_offset=3, priority='high', order=1)
    ChecklistItem.objects.create(checklist=cl, title='Оплатить госпошлину',
                                 days_offset=5, order=2)
    ChecklistItem.objects.create(checklist=cl, title='Подать в суд',
                                 days_offset=7, priority='urgent', order=3)
    return cl


@pytest.mark.django_db
class TestChecklistCrud:
    def test_admin_creates_with_items(self, api, admin_user):
        api.force_authenticate(admin_user)
        resp = api.post('/api/v1/checklists/', {
            'name': 'Банкротство',
            'category': 'bankruptcy',
            'items': [
                {'title': 'Анализ документов', 'days_offset': 2},
                {'title': 'Заявление в суд', 'days_offset': 10, 'priority': 'high'},
            ],
        }, format='json')
        assert resp.status_code == 201
        assert [i['title'] for i in resp.data['items']] == ['Анализ документов', 'Заявление в суд']

    def test_lawyer_can_read_but_not_write(self, api, lawyer_a, checklist):
        api.force_authenticate(lawyer_a)
        assert api.get('/api/v1/checklists/').data['count'] == 1
        assert api.post('/api/v1/checklists/', {'name': 'x', 'items': []},
                        format='json').status_code == 403
        assert api.delete(f'/api/v1/checklists/{checklist.id}/').status_code == 403

    def test_update_replaces_items(self, api, admin_user, checklist):
        api.force_authenticate(admin_user)
        resp = api.patch(f'/api/v1/checklists/{checklist.id}/', {
            'items': [{'title': 'Единственный шаг', 'days_offset': 1}],
        }, format='json')
        assert resp.status_code == 200
        assert len(resp.data['items']) == 1
        assert checklist.items.count() == 1


@pytest.mark.django_db
class TestApplyChecklist:
    def test_creates_tasks_with_shifted_dates(self, api, lawyer_a, case_a, checklist):
        api.force_authenticate(lawyer_a)
        start = date.today()
        resp = api.post(f'/api/v1/cases/{case_a.uuid}/apply-checklist/',
                        {'checklist': checklist.id, 'start_date': str(start)}, format='json')
        assert resp.status_code == 201
        assert resp.data['created'] == 3

        tasks = Task.objects.filter(case=case_a).order_by('due_date')
        assert [t.title for t in tasks] == ['Подготовить иск', 'Оплатить госпошлину', 'Подать в суд']
        assert [t.due_date for t in tasks] == [start + timedelta(days=d) for d in (3, 5, 7)]
        assert tasks[0].priority == 'high'
        assert all(t.assigned_to_id == lawyer_a.id for t in tasks)  # ведущий юрист дела

    def test_defaults_to_today(self, api, lawyer_a, case_a, checklist):
        api.force_authenticate(lawyer_a)
        api.post(f'/api/v1/cases/{case_a.uuid}/apply-checklist/',
                 {'checklist': checklist.id}, format='json')
        assert Task.objects.filter(case=case_a).earliest('due_date').due_date == \
            date.today() + timedelta(days=3)

    def test_foreign_case_rejected(self, api, lawyer_b, case_a, checklist):
        api.force_authenticate(lawyer_b)
        assert api.post(f'/api/v1/cases/{case_a.uuid}/apply-checklist/',
                        {'checklist': checklist.id}, format='json').status_code == 404

    def test_inactive_checklist_rejected(self, api, lawyer_a, case_a, checklist):
        checklist.is_active = False
        checklist.save()
        api.force_authenticate(lawyer_a)
        assert api.post(f'/api/v1/cases/{case_a.uuid}/apply-checklist/',
                        {'checklist': checklist.id}, format='json').status_code == 404

    def test_bad_date_rejected(self, api, lawyer_a, case_a, checklist):
        api.force_authenticate(lawyer_a)
        assert api.post(f'/api/v1/cases/{case_a.uuid}/apply-checklist/',
                        {'checklist': checklist.id, 'start_date': '31.12.2026'},
                        format='json').status_code == 400
