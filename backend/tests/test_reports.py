from datetime import date
from decimal import Decimal

import pytest

from apps.billing.models import TimeEntry
from apps.cases.models import Case


@pytest.fixture
def entries_both(db, case_a, lawyer_a, lawyer_b, client_a):
    """По записи времени у каждого юриста: 2ч × 1000 у A, 3ч × 2000 у B."""
    case_b = Case.objects.create(
        title='Дело Б', client=client_a, lead_lawyer=lawyer_b, created_by=lawyer_b)
    TimeEntry.objects.create(case=case_a, lawyer=lawyer_a, date=date.today(),
                             hours=Decimal('2.00'), description='a',
                             hourly_rate=Decimal('1000.00'))
    TimeEntry.objects.create(case=case_b, lawyer=lawyer_b, date=date.today(),
                             hours=Decimal('3.00'), description='b',
                             hourly_rate=Decimal('2000.00'))
    return case_b


@pytest.mark.django_db
class TestMonthlyStats:
    def test_returns_200_with_correct_amount(self, api, lawyer_a, entries_both):
        # регрессия: Sum('amount') по @property падал с FieldError,
        # rows[-months:] — с AssertionError (negative indexing)
        api.force_authenticate(lawyer_a)
        resp = api.get('/api/v1/billing/monthly-stats/')
        assert resp.status_code == 200
        assert resp.data[-1]['total_amount'] == 2000.0  # только свои часы

    def test_invalid_months_is_400(self, api, lawyer_a):
        api.force_authenticate(lawyer_a)
        assert api.get('/api/v1/billing/monthly-stats/?months=abc').status_code == 400


@pytest.mark.django_db
class TestReports:
    def test_scoped_for_lawyer(self, api, lawyer_a, entries_both):
        api.force_authenticate(lawyer_a)
        resp = api.get('/api/v1/billing/reports/')
        assert resp.status_code == 200
        total = sum(r['total_amount'] for r in resp.data['revenue_by_month'])
        assert total == 2000.0
        assert [r['name'] for r in resp.data['lawyers_stats']] == ['Александрова Анна']
        assert resp.data['cases_by_status'] == {'new': 1}

    def test_admin_sees_all(self, api, admin_user, entries_both):
        api.force_authenticate(admin_user)
        resp = api.get('/api/v1/billing/reports/')
        assert resp.status_code == 200
        total = sum(r['total_amount'] for r in resp.data['revenue_by_month'])
        assert total == 8000.0
        assert resp.data['cases_by_status'] == {'new': 2}

    def test_invalid_months_is_400(self, api, admin_user):
        api.force_authenticate(admin_user)
        assert api.get('/api/v1/billing/reports/?months=oops').status_code == 400
