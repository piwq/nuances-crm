from datetime import date, timedelta
from decimal import Decimal

import pytest

from apps.billing.models import TimeEntry, Invoice, InvoiceItem


@pytest.fixture
def entry_a(db, case_a, lawyer_a):
    return TimeEntry.objects.create(
        case=case_a, lawyer=lawyer_a, date=date.today(),
        hours=Decimal('2.50'), description='Составление иска',
        hourly_rate=Decimal('4000.00'))


@pytest.fixture
def invoice_a(db, case_a, client_a, lawyer_a):
    return Invoice.objects.create(
        case=case_a, client=client_a,
        due_date=date.today() + timedelta(days=14), created_by=lawyer_a)


@pytest.mark.django_db
class TestTimeEntryScoping:
    def test_foreign_time_entry_hidden(self, api, lawyer_b, entry_a):
        api.force_authenticate(lawyer_b)
        assert api.get(f'/api/v1/billing/time-entries/{entry_a.id}/').status_code == 404
        assert api.patch(f'/api/v1/billing/time-entries/{entry_a.id}/', {'hours': '1.00'}).status_code == 404
        assert api.delete(f'/api/v1/billing/time-entries/{entry_a.id}/').status_code == 404

    def test_own_time_entry_accessible(self, api, lawyer_a, entry_a):
        api.force_authenticate(lawyer_a)
        assert api.get(f'/api/v1/billing/time-entries/{entry_a.id}/').status_code == 200

    def test_admin_sees_any_time_entry(self, api, admin_user, entry_a):
        api.force_authenticate(admin_user)
        assert api.get(f'/api/v1/billing/time-entries/{entry_a.id}/').status_code == 200

    def test_lawyer_cannot_log_time_on_foreign_case(self, api, lawyer_b, case_a):
        api.force_authenticate(lawyer_b)
        resp = api.post('/api/v1/billing/time-entries/', {
            'case': case_a.id, 'date': str(date.today()),
            'hours': '1.00', 'description': 'x', 'hourly_rate': '1000.00'})
        assert resp.status_code == 400

    def test_timer_payload_without_lawyer_and_rate(self, api, lawyer_a, case_a):
        # регрессия: таймер шлёт только case/date/hours/description —
        # обязательные lawyer и hourly_rate давали 400 на каждой записи
        case_a.hourly_rate = Decimal('3000.00')
        case_a.save()
        api.force_authenticate(lawyer_a)
        resp = api.post('/api/v1/billing/time-entries/', {
            'case': case_a.id, 'date': str(date.today()),
            'hours': '0.75', 'description': 'Звонок клиенту', 'is_billable': True})
        assert resp.status_code == 201, resp.data
        assert resp.data['lawyer'] == lawyer_a.id
        assert Decimal(resp.data['hourly_rate']) == Decimal('3000.00')  # ставка из дела

    def test_lawyer_entry_forced_to_self(self, api, lawyer_a, lawyer_b, case_a):
        # юрист подставляет чужого исполнителя — запись всё равно пишется от его имени
        api.force_authenticate(lawyer_a)
        resp = api.post('/api/v1/billing/time-entries/', {
            'case': case_a.id, 'lawyer': lawyer_b.id, 'date': str(date.today()),
            'hours': '1.00', 'description': 'x', 'hourly_rate': '1000.00'})
        assert resp.status_code == 201
        assert resp.data['lawyer'] == lawyer_a.id


@pytest.mark.django_db
class TestInvoiceScoping:
    def test_foreign_invoice_hidden_everywhere(self, api, lawyer_b, invoice_a):
        api.force_authenticate(lawyer_b)
        pk = invoice_a.id
        assert api.get(f'/api/v1/billing/invoices/{pk}/').status_code == 404
        assert api.patch(f'/api/v1/billing/invoices/{pk}/mark-sent/').status_code == 404
        assert api.patch(f'/api/v1/billing/invoices/{pk}/mark-paid/').status_code == 404
        assert api.post(f'/api/v1/billing/invoices/{pk}/generate-from-entries/').status_code == 404
        assert api.get(f'/api/v1/billing/invoices/{pk}/pdf/').status_code == 404
        assert api.post(f'/api/v1/billing/invoices/{pk}/send-email/', {'email': 'x@y.z'}).status_code == 404

    def test_own_invoice_accessible(self, api, lawyer_a, invoice_a):
        api.force_authenticate(lawyer_a)
        resp = api.get(f'/api/v1/billing/invoices/{invoice_a.id}/')
        assert resp.status_code == 200
        assert resp.data['case_uuid'] == str(invoice_a.case.uuid)

    def test_lawyer_cannot_invoice_foreign_case(self, api, lawyer_b, case_a, client_a):
        api.force_authenticate(lawyer_b)
        resp = api.post('/api/v1/billing/invoices/', {
            'case': case_a.id, 'client': client_a.id,
            'due_date': str(date.today() + timedelta(days=14))})
        assert resp.status_code == 400


@pytest.mark.django_db
class TestInvoiceItems:
    def test_item_create_works_and_recalculates(self, api, lawyer_a, invoice_a):
        # регрессия: поле invoice отсутствовало в сериализаторе → IntegrityError/500
        api.force_authenticate(lawyer_a)
        resp = api.post('/api/v1/billing/invoice-items/', {
            'invoice': invoice_a.id, 'description': 'Консультация',
            'quantity': '2.00', 'unit_price': '3000.00'})
        assert resp.status_code == 201
        invoice_a.refresh_from_db()
        assert invoice_a.subtotal == Decimal('6000.00')

    def test_item_in_foreign_invoice_rejected(self, api, lawyer_b, invoice_a):
        api.force_authenticate(lawyer_b)
        resp = api.post('/api/v1/billing/invoice-items/', {
            'invoice': invoice_a.id, 'description': 'x',
            'quantity': '1.00', 'unit_price': '100.00'})
        assert resp.status_code == 400

    def test_foreign_item_delete_hidden(self, api, lawyer_b, invoice_a):
        item = InvoiceItem.objects.create(
            invoice=invoice_a, description='x', quantity=1, unit_price=100)
        api.force_authenticate(lawyer_b)
        assert api.delete(f'/api/v1/billing/invoice-items/{item.id}/').status_code == 404
