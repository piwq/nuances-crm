from datetime import date, timedelta
from decimal import Decimal

import pytest

from apps.billing.models import CaseExpense, Invoice


@pytest.fixture
def expense(db, case_a, lawyer_a):
    return CaseExpense.objects.create(
        case=case_a, category='state_fee', description='Госпошлина по иску',
        amount=Decimal('6000.00'), created_by=lawyer_a)


@pytest.fixture
def draft_invoice(db, case_a, client_a):
    return Invoice.objects.create(
        case=case_a, client=client_a, due_date=date.today() + timedelta(days=10))


@pytest.mark.django_db
class TestExpenses:
    def test_create_and_list(self, api, lawyer_a, case_a):
        api.force_authenticate(lawyer_a)
        resp = api.post('/api/v1/billing/expenses/', {
            'case': case_a.id, 'category': 'expert', 'description': 'Судебная экспертиза',
            'amount': '35000.00', 'date': str(date.today())})
        assert resp.status_code == 201
        assert resp.data['category_display'] == 'Экспертиза'
        assert resp.data['is_invoiced'] is False
        assert api.get('/api/v1/billing/expenses/').data['count'] == 1

    def test_amount_must_be_positive(self, api, lawyer_a, case_a):
        api.force_authenticate(lawyer_a)
        assert api.post('/api/v1/billing/expenses/', {
            'case': case_a.id, 'description': 'x', 'amount': '0'}).status_code == 400

    def test_scoped_by_case(self, api, lawyer_b, expense, case_a):
        api.force_authenticate(lawyer_b)
        assert api.get('/api/v1/billing/expenses/').data['results'] == []
        assert api.get(f'/api/v1/billing/expenses/{expense.id}/').status_code == 404
        assert api.post('/api/v1/billing/expenses/', {
            'case': case_a.id, 'description': 'чужое', 'amount': '10'}).status_code == 400

    def test_assistant_can_record_expense(self, api, case_a):
        from apps.accounts.models import CustomUser
        helper = CustomUser.objects.create_user(
            username='h2', password='Vq7#strong-pass', role='assistant')
        case_a.assigned_lawyers.add(helper)
        api.force_authenticate(helper)
        # расходы — часть повседневной работы помощника, в отличие от счетов
        assert api.post('/api/v1/billing/expenses/', {
            'case': case_a.id, 'description': 'Почта', 'amount': '350'}).status_code == 201


@pytest.mark.django_db
class TestExpensesToInvoice:
    def test_transferred_as_items(self, api, lawyer_a, expense, draft_invoice):
        api.force_authenticate(lawyer_a)
        resp = api.post(f'/api/v1/billing/invoices/{draft_invoice.id}/add-expenses/')
        assert resp.status_code == 200
        assert Decimal(resp.data['subtotal']) == Decimal('6000.00')
        item = resp.data['items'][0]
        assert item['description'] == 'Госпошлина: Госпошлина по иску'

        expense.refresh_from_db()
        assert expense.invoice_id == draft_invoice.id

        # повторно тот же расход не перевыставляется
        assert api.post(
            f'/api/v1/billing/invoices/{draft_invoice.id}/add-expenses/').status_code == 400

    def test_non_billable_stays_with_firm(self, api, lawyer_a, case_a, draft_invoice):
        CaseExpense.objects.create(case=case_a, description='Кофе для команды',
                                   amount=Decimal('500'), is_billable=False)
        api.force_authenticate(lawyer_a)
        assert api.post(
            f'/api/v1/billing/invoices/{draft_invoice.id}/add-expenses/').status_code == 400

    def test_only_into_draft(self, api, lawyer_a, expense, draft_invoice):
        draft_invoice.status = 'sent'
        draft_invoice.save()
        api.force_authenticate(lawyer_a)
        assert api.post(
            f'/api/v1/billing/invoices/{draft_invoice.id}/add-expenses/').status_code == 400

    def test_foreign_invoice_hidden(self, api, lawyer_b, draft_invoice):
        api.force_authenticate(lawyer_b)
        assert api.post(
            f'/api/v1/billing/invoices/{draft_invoice.id}/add-expenses/').status_code == 404
