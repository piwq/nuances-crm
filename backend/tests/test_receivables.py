from datetime import date, timedelta
from decimal import Decimal

import pytest

from apps.billing.models import Invoice, InvoicePayment


def _invoice(case, client, *, status, days, subtotal='10000.00'):
    inv = Invoice.objects.create(
        case=case, client=client, status=status,
        due_date=date.today() + timedelta(days=days))
    inv.subtotal = Decimal(subtotal)
    inv.save()
    return inv


@pytest.mark.django_db
class TestReceivables:
    def test_counts_only_unpaid_remainder(self, api, lawyer_a, case_a, client_a):
        sent = _invoice(case_a, client_a, status='sent', days=7)
        InvoicePayment.objects.create(invoice=sent, amount=Decimal('4000.00'))
        overdue = _invoice(case_a, client_a, status='overdue', days=-5, subtotal='5000.00')
        _invoice(case_a, client_a, status='draft', days=3)      # черновик не в счёт
        paid = _invoice(case_a, client_a, status='sent', days=2, subtotal='2000.00')
        InvoicePayment.objects.create(invoice=paid, amount=Decimal('2000.00'))
        paid.sync_payment_status()

        api.force_authenticate(lawyer_a)
        data = api.get('/api/v1/billing/receivables/').data
        assert data['outstanding'] == 11000.0   # 6000 остаток + 5000 просрочка
        assert data['overdue'] == 5000.0
        assert data['invoices_count'] == 2
        assert data['overdue_count'] == 1
        assert overdue.id  # просроченный учтён

    def test_scoped(self, api, lawyer_b, case_a, client_a):
        _invoice(case_a, client_a, status='sent', days=7)
        api.force_authenticate(lawyer_b)
        assert api.get('/api/v1/billing/receivables/').data['outstanding'] == 0.0

    def test_empty(self, api, lawyer_a):
        api.force_authenticate(lawyer_a)
        assert api.get('/api/v1/billing/receivables/').data == {
            'outstanding': 0.0, 'overdue': 0.0, 'invoices_count': 0, 'overdue_count': 0}
