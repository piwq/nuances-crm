from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.core.management import call_command

from apps.billing.models import Invoice, InvoiceItem
from apps.cases.models import Case


@pytest.mark.django_db
class TestNumberGeneration:
    def test_case_number_survives_middle_delete(self, client_a, lawyer_a):
        # раньше номер считался через count(): после удаления НЕ последнего дела
        # count давал уже занятый номер и создание падало с IntegrityError навсегда
        c1 = Case.objects.create(title='Первое', client=client_a, created_by=lawyer_a)
        c2 = Case.objects.create(title='Второе', client=client_a, created_by=lawyer_a)
        c3 = Case.objects.create(title='Третье', client=client_a, created_by=lawyer_a)
        assert c3.case_number.endswith('-0003')
        c1.delete()
        c4 = Case.objects.create(title='Четвёртое', client=client_a, created_by=lawyer_a)
        assert c4.case_number.endswith('-0004')

    def test_case_number_reuse_of_latest_is_allowed(self, client_a, lawyer_a):
        # номер = max существующих + 1: удаление последнего дела освобождает
        # его номер — это осознанно (строгая монотонность потребовала бы счётчик в БД)
        Case.objects.create(title='Первое', client=client_a, created_by=lawyer_a)
        c2 = Case.objects.create(title='Второе', client=client_a, created_by=lawyer_a)
        c2.delete()
        c3 = Case.objects.create(title='Третье', client=client_a, created_by=lawyer_a)
        assert c3.case_number.endswith('-0002')

    def test_invoice_number_survives_middle_delete(self, case_a, client_a):
        due = date.today() + timedelta(days=14)
        i1 = Invoice.objects.create(case=case_a, client=client_a, due_date=due)
        i2 = Invoice.objects.create(case=case_a, client=client_a, due_date=due)
        i3 = Invoice.objects.create(case=case_a, client=client_a, due_date=due)
        assert i3.invoice_number.endswith('-0003')
        i1.delete()
        i4 = Invoice.objects.create(case=case_a, client=client_a, due_date=due)
        assert i4.invoice_number.endswith('-0004')


@pytest.mark.django_db
class TestRounding:
    def test_invoice_tax_half_up(self, case_a, client_a):
        inv = Invoice.objects.create(
            case=case_a, client=client_a, due_date=date.today(),
            subtotal=Decimal('0.05'), tax_rate=Decimal('50'))
        assert inv.tax_amount == Decimal('0.03')  # 0.025 → HALF_UP
        assert inv.total == Decimal('0.08')

    def test_item_amount_half_up(self, case_a, client_a):
        inv = Invoice.objects.create(case=case_a, client=client_a, due_date=date.today())
        item = InvoiceItem.objects.create(
            invoice=inv, description='x',
            quantity=Decimal('0.25'), unit_price=Decimal('0.30'))
        assert item.amount == Decimal('0.08')  # 0.075 → HALF_UP


@pytest.mark.django_db
class TestOverdue:
    def test_marked_by_command_not_by_get(self, api, admin_user, case_a, client_a):
        inv = Invoice.objects.create(
            case=case_a, client=client_a, status='sent',
            due_date=date.today() - timedelta(days=1))

        api.force_authenticate(admin_user)
        api.get('/api/v1/billing/invoices/')
        inv.refresh_from_db()
        assert inv.status == 'sent'  # GET больше не мутирует БД

        call_command('mark_overdue_invoices')
        inv.refresh_from_db()
        assert inv.status == 'overdue'


@pytest.mark.django_db
def test_change_status_bumps_updated_at(api, lawyer_a, case_a):
    before = case_a.updated_at
    api.force_authenticate(lawyer_a)
    resp = api.patch(f'/api/v1/cases/{case_a.uuid}/change-status/', {'status': 'active'})
    assert resp.status_code == 200
    case_a.refresh_from_db()
    assert case_a.updated_at > before


@pytest.mark.django_db
def test_cases_list_has_no_n_plus_one(api, admin_user, client_a, lawyer_a,
                                      django_assert_max_num_queries):
    from apps.tasks.models import Task
    for i in range(6):
        c = Case.objects.create(title=f'Дело {i}', client=client_a, created_by=lawyer_a)
        Task.objects.create(title='t', case=c, created_by=lawyer_a)

    api.force_authenticate(admin_user)
    with django_assert_max_num_queries(5):
        resp = api.get('/api/v1/cases/')
    assert resp.status_code == 200
    assert resp.data['count'] == 6
    assert all(row['open_tasks_count'] == 1 for row in resp.data['results'])
