from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.core.management import call_command

from apps.billing.models import Invoice, RecurringInvoice
from apps.notifications.models import Notification


@pytest.fixture
def rule(db, case_a, lawyer_a):
    # правило действует с 1-го числа текущего месяца → первый счёт уже «созрел»
    return RecurringInvoice.objects.create(
        case=case_a, amount=Decimal('30000.00'), tax_rate=Decimal('20.00'),
        frequency='monthly', day_of_month=1,
        start_date=date.today().replace(day=1), created_by=lawyer_a)


@pytest.mark.django_db
class TestSchedule:
    def test_no_invoice_before_rule_starts(self, case_a, lawyer_a):
        # день выставления в этом месяце уже прошёл до начала действия правила —
        # счёт задним числом не выставляем
        r = RecurringInvoice.objects.create(
            case=case_a, amount=Decimal('100'), day_of_month=1,
            start_date=date(2026, 3, 20), created_by=lawyer_a)
        assert r.next_occurrence() == date(2026, 4, 1)
        assert r.is_due(date(2026, 3, 25)) is False

    def test_first_occurrence_from_start_date(self, case_a, lawyer_a):
        r = RecurringInvoice.objects.create(
            case=case_a, amount=Decimal('100'), day_of_month=15,
            start_date=date(2026, 3, 20), created_by=lawyer_a)
        # 15 марта уже позади старта → первое выставление 15 апреля
        assert r.next_occurrence() == date(2026, 4, 15)

    def test_quarterly_step(self, case_a, lawyer_a):
        r = RecurringInvoice.objects.create(
            case=case_a, amount=Decimal('100'), frequency='quarterly',
            day_of_month=10, start_date=date(2026, 1, 1), created_by=lawyer_a)
        assert r.next_occurrence() == date(2026, 1, 10)
        r.last_generated = date(2026, 1, 10)
        assert r.next_occurrence() == date(2026, 4, 10)

    def test_year_rollover(self, case_a, lawyer_a):
        r = RecurringInvoice.objects.create(
            case=case_a, amount=Decimal('100'), day_of_month=5,
            start_date=date(2026, 12, 1), created_by=lawyer_a)
        r.last_generated = date(2026, 12, 5)
        assert r.next_occurrence() == date(2027, 1, 5)

    def test_end_date_exhausts_rule(self, case_a, lawyer_a):
        r = RecurringInvoice.objects.create(
            case=case_a, amount=Decimal('100'), day_of_month=1,
            start_date=date(2026, 1, 1), end_date=date(2026, 2, 1),
            created_by=lawyer_a)
        r.last_generated = date(2026, 2, 1)
        assert r.next_occurrence() is None
        assert r.is_due(date(2027, 1, 1)) is False


@pytest.mark.django_db
class TestGeneration:
    def test_command_creates_invoice_with_item_and_vat(self, rule, lawyer_a):
        call_command('generate_recurring_invoices')
        invoice = Invoice.objects.get(case=rule.case)
        assert invoice.status == 'draft'
        assert invoice.subtotal == Decimal('30000.00')
        assert invoice.tax_amount == Decimal('6000.00')
        assert invoice.total == Decimal('36000.00')
        assert invoice.items.first().description == 'Абонентское юридическое обслуживание'
        assert invoice.due_date == invoice.issue_date + timedelta(days=14)
        rule.refresh_from_db()
        assert rule.last_generated == invoice.issue_date

    def test_command_is_idempotent(self, rule):
        call_command('generate_recurring_invoices')
        call_command('generate_recurring_invoices')
        assert Invoice.objects.count() == 1

    def test_catches_up_missed_periods(self, case_a, lawyer_a):
        RecurringInvoice.objects.create(
            case=case_a, amount=Decimal('1000'), day_of_month=1,
            start_date=date.today().replace(day=1) - timedelta(days=70),
            created_by=lawyer_a)
        call_command('generate_recurring_invoices')
        assert Invoice.objects.count() >= 3  # пропущенные месяцы догенерированы

    def test_inactive_rule_skipped(self, rule):
        rule.is_active = False
        rule.save()
        call_command('generate_recurring_invoices')
        assert Invoice.objects.count() == 0

    def test_notifies_lead_lawyer(self, rule, lawyer_a):
        Notification.objects.all().delete()
        call_command('generate_recurring_invoices')
        assert Notification.objects.filter(
            user=lawyer_a, title__startswith='Выставлен счёт').count() == 1


@pytest.mark.django_db
class TestApi:
    def test_crud_and_run_now(self, api, lawyer_a, case_a):
        api.force_authenticate(lawyer_a)
        resp = api.post('/api/v1/billing/recurring/', {
            'case': case_a.id, 'amount': '15000.00', 'frequency': 'monthly',
            'day_of_month': 5, 'start_date': str(date.today())})
        assert resp.status_code == 201
        rule_id = resp.data['id']
        assert resp.data['next_date']
        assert resp.data['frequency_display'] == 'Ежемесячно'

        run = api.post(f'/api/v1/billing/recurring/{rule_id}/run/')
        assert run.status_code == 201
        assert Decimal(run.data['total']) == Decimal('15000.00')

        assert api.patch(f'/api/v1/billing/recurring/{rule_id}/',
                         {'is_active': False}).status_code == 200

    def test_day_of_month_validated(self, api, lawyer_a, case_a):
        api.force_authenticate(lawyer_a)
        resp = api.post('/api/v1/billing/recurring/', {
            'case': case_a.id, 'amount': '100', 'day_of_month': 31,
            'start_date': str(date.today())})
        assert resp.status_code == 400

    def test_scoped_by_case(self, api, lawyer_b, rule):
        api.force_authenticate(lawyer_b)
        assert api.get('/api/v1/billing/recurring/').data['results'] == []
        assert api.post(f'/api/v1/billing/recurring/{rule.id}/run/').status_code == 404
        assert api.post('/api/v1/billing/recurring/', {
            'case': rule.case.id, 'amount': '100', 'day_of_month': 1,
            'start_date': str(date.today())}).status_code == 400
