from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone

from apps.billing.models import Invoice, InvoicePayment, CaseExpense
from apps.cases.models import CaseNote
from apps.documents.models import Document
from apps.tasks.models import Task, Event


@pytest.fixture
def rich_case(case_a, lawyer_a, client_a):
    """Дело со всеми видами активности."""
    Document.objects.create(
        case=case_a, title='Исковое заявление', document_type='court_filing',
        file=SimpleUploadedFile('claim.txt', b'x'), uploaded_by=lawyer_a)
    task = Task.objects.create(
        title='Подготовить отзыв', case=case_a, assigned_to=lawyer_a,
        created_by=lawyer_a, due_date=date.today() + timedelta(days=5))
    task.status = 'done'
    task.completed_at = timezone.now()
    task.save()
    CaseNote.objects.create(case=case_a, author=lawyer_a, text='Созвон с клиентом состоялся.')
    Event.objects.create(
        title='Заседание', event_type='court_hearing', case=case_a,
        created_by=lawyer_a, start_datetime=timezone.now() + timedelta(days=2))
    invoice = Invoice.objects.create(
        case=case_a, client=client_a, due_date=date.today() + timedelta(days=10))
    invoice.subtotal = Decimal('5000.00')
    invoice.save()
    # оплата регистрируется платежом — статус счёта производный от них
    InvoicePayment.objects.create(invoice=invoice, amount=Decimal('5000.00'),
                                  created_by=lawyer_a)
    invoice.sync_payment_status()
    CaseExpense.objects.create(
        case=case_a, category='state_fee', description='Госпошлина',
        amount=Decimal('6000.00'), created_by=lawyer_a)
    case_a.key_deadline = date.today() + timedelta(days=14)
    case_a.key_deadline_note = 'Подача апелляции'
    case_a.save()
    return case_a


@pytest.mark.django_db
class TestCaseTimeline:
    def test_contains_every_kind(self, api, lawyer_a, rich_case):
        api.force_authenticate(lawyer_a)
        resp = api.get(f'/api/v1/cases/{rich_case.uuid}/timeline/')
        assert resp.status_code == 200
        kinds = {i['kind'] for i in resp.data['results']}
        assert {'case_created', 'document', 'task', 'task_done', 'note',
                'event', 'invoice', 'invoice_paid', 'deadline', 'expense'} <= kinds

    def test_sorted_newest_first(self, api, lawyer_a, rich_case):
        api.force_authenticate(lawyer_a)
        stamps = [i['timestamp'] for i in
                  api.get(f'/api/v1/cases/{rich_case.uuid}/timeline/').data['results']]
        assert stamps == sorted(stamps, reverse=True)

    def test_items_carry_author_and_subtitle(self, api, lawyer_a, rich_case):
        api.force_authenticate(lawyer_a)
        items = api.get(f'/api/v1/cases/{rich_case.uuid}/timeline/').data['results']
        doc = next(i for i in items if i['kind'] == 'document')
        assert doc['title'] == 'Исковое заявление'
        assert doc['subtitle'] == 'Судебное обращение'
        assert doc['author'] == 'Анна Александрова'
        note = next(i for i in items if i['kind'] == 'note')
        assert 'Созвон' in note['subtitle']

    def test_scoped_to_own_cases(self, api, lawyer_b, rich_case):
        api.force_authenticate(lawyer_b)
        assert api.get(f'/api/v1/cases/{rich_case.uuid}/timeline/').status_code == 404

    def test_admin_sees_any_case(self, api, admin_user, rich_case):
        api.force_authenticate(admin_user)
        assert api.get(f'/api/v1/cases/{rich_case.uuid}/timeline/').status_code == 200

    def test_status_change_appears(self, api, lawyer_a, case_a):
        api.force_authenticate(lawyer_a)
        api.patch(f'/api/v1/cases/{case_a.uuid}/change-status/', {'status': 'active'})
        items = api.get(f'/api/v1/cases/{case_a.uuid}/timeline/').data['results']
        activity = [i for i in items if i['kind'] == 'activity']
        assert any('Статус изменён' in i['title'] for i in activity)
