from datetime import date, timedelta
from decimal import Decimal

import pytest

from apps.accounts.models import CustomUser
from apps.billing.models import Invoice, TimeEntry
from apps.cases.models import Case


@pytest.fixture
def assistant(db):
    return CustomUser.objects.create_user(
        username='helper', email='h@test.com', password='Vq7#strong-pass',
        role='assistant', first_name='Пётр', last_name='Помощников')


@pytest.fixture
def invoice(db, case_a, client_a):
    inv = Invoice.objects.create(
        case=case_a, client=client_a, status='sent',
        due_date=date.today() + timedelta(days=10))
    inv.subtotal = Decimal('1000')
    inv.save()
    return inv


@pytest.mark.django_db
class TestAssistantScoping:
    def test_sees_only_assigned_cases(self, api, assistant, case_a, client_a, lawyer_a):
        # регрессия: скоупинг был завязан на is_lawyer, поэтому новая роль
        # автоматически получала админский обзор всех дел
        api.force_authenticate(assistant)
        assert api.get('/api/v1/cases/').data['count'] == 0
        assert api.get(f'/api/v1/cases/{case_a.uuid}/').status_code == 404

        case_a.assigned_lawyers.add(assistant)
        assert api.get('/api/v1/cases/').data['count'] == 1
        assert api.get(f'/api/v1/cases/{case_a.uuid}/').status_code == 200

    def test_sees_only_own_time_entries(self, api, assistant, case_a, lawyer_a):
        TimeEntry.objects.create(case=case_a, lawyer=lawyer_a, date=date.today(),
                                 hours=Decimal('1'), description='чужое',
                                 hourly_rate=Decimal('1000'))
        api.force_authenticate(assistant)
        assert api.get('/api/v1/billing/time-entries/').data['count'] == 0

    def test_can_log_own_time(self, api, assistant, case_a):
        case_a.assigned_lawyers.add(assistant)
        api.force_authenticate(assistant)
        resp = api.post('/api/v1/billing/time-entries/', {
            'case': case_a.id, 'date': str(date.today()), 'hours': '1.50',
            'description': 'Подготовка копий', 'hourly_rate': '500.00'})
        assert resp.status_code == 201
        assert resp.data['lawyer'] == assistant.id

    def test_keeps_access_to_case_they_created(self, api, assistant, client_a):
        api.force_authenticate(assistant)
        resp = api.post('/api/v1/cases/', {
            'title': 'Дело помощника', 'client': client_a.id, 'category': 'civil'})
        assert resp.status_code == 201
        assert resp.data['lead_lawyer'] is None  # ведущим помощник не становится
        assert assistant.id in resp.data['assigned_lawyers']
        assert api.get(f"/api/v1/cases/{resp.data['uuid']}/").status_code == 200


@pytest.mark.django_db
class TestAssistantBillingReadOnly:
    def test_cannot_touch_invoices(self, api, assistant, case_a, client_a, invoice):
        case_a.assigned_lawyers.add(assistant)
        api.force_authenticate(assistant)

        assert api.get('/api/v1/billing/invoices/').status_code == 200  # смотреть можно
        assert api.post('/api/v1/billing/invoices/', {
            'case': case_a.id, 'client': client_a.id,
            'due_date': str(date.today())}).status_code == 403
        assert api.patch(f'/api/v1/billing/invoices/{invoice.id}/mark-paid/').status_code == 403
        assert api.post('/api/v1/billing/payments/', {
            'invoice': invoice.id, 'amount': '100'}).status_code == 403
        assert api.post('/api/v1/billing/recurring/', {
            'case': case_a.id, 'amount': '100', 'day_of_month': 1,
            'start_date': str(date.today())}).status_code == 403

    def test_lawyer_still_allowed(self, api, lawyer_a, invoice):
        api.force_authenticate(lawyer_a)
        assert api.post('/api/v1/billing/payments/', {
            'invoice': invoice.id, 'amount': '100'}).status_code == 201


@pytest.mark.django_db
class TestRecurringTasks:
    def test_completion_spawns_next(self, api, lawyer_a, case_a):
        from apps.tasks.models import Task
        task = Task.objects.create(
            title='Ежемесячный отчёт', case=case_a, assigned_to=lawyer_a,
            created_by=lawyer_a, due_date=date(2026, 1, 31), recurrence='monthly')
        api.force_authenticate(lawyer_a)
        assert api.patch(f'/api/v1/tasks/{task.id}/complete/').status_code == 200

        nxt = Task.objects.filter(title='Ежемесячный отчёт').exclude(pk=task.pk).get()
        assert nxt.due_date == date(2026, 2, 28)  # короткий месяц не «сдвигает» серию
        assert nxt.status == 'todo'
        assert nxt.recurrence == 'monthly'
        assert nxt.assigned_to_id == lawyer_a.id

    def test_weekly_and_biweekly(self, lawyer_a):
        from apps.tasks.models import Task
        weekly = Task.objects.create(title='w', assigned_to=lawyer_a, created_by=lawyer_a,
                                     due_date=date(2026, 3, 2), recurrence='weekly')
        assert weekly.spawn_next().due_date == date(2026, 3, 9)
        bi = Task.objects.create(title='b', assigned_to=lawyer_a, created_by=lawyer_a,
                                 due_date=date(2026, 3, 2), recurrence='biweekly')
        assert bi.spawn_next().due_date == date(2026, 3, 16)

    def test_non_recurring_spawns_nothing(self, api, lawyer_a):
        from apps.tasks.models import Task
        task = Task.objects.create(title='Разовая', assigned_to=lawyer_a,
                                   created_by=lawyer_a, due_date=date.today())
        api.force_authenticate(lawyer_a)
        api.patch(f'/api/v1/tasks/{task.id}/complete/')
        assert Task.objects.count() == 1
