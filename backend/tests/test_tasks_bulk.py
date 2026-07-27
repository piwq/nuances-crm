from datetime import date

import pytest

from apps.tasks.models import Task


@pytest.fixture
def tasks(db, lawyer_a, case_a):
    return [Task.objects.create(title=f'Задача {i}', case=case_a,
                                assigned_to=lawyer_a, created_by=lawyer_a)
            for i in range(3)]


@pytest.mark.django_db
class TestTasksBulk:
    def test_complete_many(self, api, lawyer_a, tasks):
        api.force_authenticate(lawyer_a)
        resp = api.post('/api/v1/tasks/bulk/',
                        {'action': 'complete', 'ids': [t.id for t in tasks]}, format='json')
        assert resp.status_code == 200
        assert resp.data['affected'] == 3
        assert Task.objects.filter(status='done').count() == 3

    def test_complete_keeps_recurrence_series(self, api, lawyer_a, case_a):
        task = Task.objects.create(title='Еженедельный отчёт', case=case_a,
                                   assigned_to=lawyer_a, created_by=lawyer_a,
                                   due_date=date(2026, 3, 2), recurrence='weekly')
        api.force_authenticate(lawyer_a)
        api.post('/api/v1/tasks/bulk/', {'action': 'complete', 'ids': [task.id]}, format='json')
        assert Task.objects.filter(title='Еженедельный отчёт', status='todo').count() == 1

    def test_reopen_and_delete(self, api, lawyer_a, tasks):
        ids = [t.id for t in tasks]
        api.force_authenticate(lawyer_a)
        api.post('/api/v1/tasks/bulk/', {'action': 'complete', 'ids': ids}, format='json')
        assert api.post('/api/v1/tasks/bulk/',
                        {'action': 'reopen', 'ids': ids}, format='json').data['affected'] == 3
        assert Task.objects.filter(status='todo').count() == 3
        assert api.post('/api/v1/tasks/bulk/',
                        {'action': 'delete', 'ids': ids}, format='json').data['affected'] == 3
        assert Task.objects.count() == 0

    def test_foreign_tasks_silently_skipped(self, api, lawyer_b, tasks):
        api.force_authenticate(lawyer_b)
        resp = api.post('/api/v1/tasks/bulk/',
                        {'action': 'delete', 'ids': [t.id for t in tasks]}, format='json')
        assert resp.data['affected'] == 0
        assert Task.objects.count() == 3

    def test_validation(self, api, lawyer_a, tasks):
        api.force_authenticate(lawyer_a)
        assert api.post('/api/v1/tasks/bulk/',
                        {'action': 'nuke', 'ids': [1]}, format='json').status_code == 400
        assert api.post('/api/v1/tasks/bulk/',
                        {'action': 'complete', 'ids': []}, format='json').status_code == 400
