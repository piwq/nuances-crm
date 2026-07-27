from datetime import date, timedelta
from decimal import Decimal

import pytest

from apps.billing.models import Invoice, InvoicePayment


@pytest.fixture
def invoice(db, case_a, client_a, lawyer_a):
    inv = Invoice.objects.create(
        case=case_a, client=client_a, status='sent',
        due_date=date.today() + timedelta(days=10), created_by=lawyer_a)
    inv.subtotal = Decimal('10000.00')
    inv.save()
    return inv


@pytest.mark.django_db
class TestPartialPayments:
    def test_partial_then_full(self, api, lawyer_a, invoice):
        api.force_authenticate(lawyer_a)

        resp = api.post('/api/v1/billing/payments/', {
            'invoice': invoice.id, 'amount': '4000.00', 'method': 'transfer'})
        assert resp.status_code == 201
        invoice.refresh_from_db()
        assert invoice.paid_amount == Decimal('4000.00')
        assert invoice.balance_due == Decimal('6000.00')
        assert invoice.status == 'sent'  # частичная оплата не закрывает счёт

        api.post('/api/v1/billing/payments/', {
            'invoice': invoice.id, 'amount': '6000.00', 'method': 'cash'})
        invoice.refresh_from_db()
        assert invoice.status == 'paid'
        assert invoice.paid_date == date.today()
        assert invoice.balance_due == Decimal('0.00')

    def test_overpayment_rejected(self, api, lawyer_a, invoice):
        api.force_authenticate(lawyer_a)
        resp = api.post('/api/v1/billing/payments/', {
            'invoice': invoice.id, 'amount': '10500.00'})
        assert resp.status_code == 400
        assert 'Переплата' in str(resp.data)

    def test_non_positive_rejected(self, api, lawyer_a, invoice):
        api.force_authenticate(lawyer_a)
        assert api.post('/api/v1/billing/payments/', {
            'invoice': invoice.id, 'amount': '0'}).status_code == 400

    def test_delete_payment_reopens_invoice(self, api, lawyer_a, invoice):
        api.force_authenticate(lawyer_a)
        pid = api.post('/api/v1/billing/payments/', {
            'invoice': invoice.id, 'amount': '10000.00'}).data['id']
        invoice.refresh_from_db()
        assert invoice.status == 'paid'

        assert api.delete(f'/api/v1/billing/payments/{pid}/').status_code == 204
        invoice.refresh_from_db()
        assert invoice.status == 'sent'
        assert invoice.paid_date is None
        assert invoice.paid_amount == Decimal('0')

    def test_deleted_payment_of_overdue_invoice_returns_overdue(self, api, lawyer_a, invoice):
        invoice.due_date = date.today() - timedelta(days=1)
        invoice.save()
        api.force_authenticate(lawyer_a)
        pid = api.post('/api/v1/billing/payments/', {
            'invoice': invoice.id, 'amount': '10000.00'}).data['id']
        api.delete(f'/api/v1/billing/payments/{pid}/')
        invoice.refresh_from_db()
        assert invoice.status == 'overdue'

    def test_mark_paid_creates_payment_for_balance(self, api, lawyer_a, invoice):
        api.force_authenticate(lawyer_a)
        api.post('/api/v1/billing/payments/', {'invoice': invoice.id, 'amount': '2500.00'})
        resp = api.patch(f'/api/v1/billing/invoices/{invoice.id}/mark-paid/')
        assert resp.status_code == 200
        assert resp.data['status'] == 'paid'
        assert Decimal(resp.data['balance_due']) == Decimal('0.00')
        assert invoice.payments.count() == 2  # частичный + добивка остатка

    def test_serializer_exposes_totals(self, api, lawyer_a, invoice):
        api.force_authenticate(lawyer_a)
        api.post('/api/v1/billing/payments/', {'invoice': invoice.id, 'amount': '1000.00'})
        data = api.get(f'/api/v1/billing/invoices/{invoice.id}/').data
        assert Decimal(data['paid_amount']) == Decimal('1000.00')
        assert Decimal(data['balance_due']) == Decimal('9000.00')
        assert data['payments'][0]['method_display'] == 'Банковский перевод'
        assert data['payments'][0]['created_by_name'] == 'Анна Александрова'


@pytest.mark.django_db
class TestPaymentScoping:
    def test_foreign_invoice_payment_rejected(self, api, lawyer_b, invoice):
        api.force_authenticate(lawyer_b)
        assert api.post('/api/v1/billing/payments/', {
            'invoice': invoice.id, 'amount': '100.00'}).status_code == 400

    def test_foreign_payments_hidden(self, api, lawyer_a, lawyer_b, invoice):
        payment = InvoicePayment.objects.create(invoice=invoice, amount=Decimal('100'))
        api.force_authenticate(lawyer_b)
        assert api.get('/api/v1/billing/payments/').data['results'] == []
        assert api.delete(f'/api/v1/billing/payments/{payment.id}/').status_code == 404

        api.force_authenticate(lawyer_a)
        assert len(api.get('/api/v1/billing/payments/').data['results']) == 1
