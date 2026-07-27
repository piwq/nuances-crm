from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone

from apps.billing.models import Invoice, InvoicePayment, TimeEntry, CaseExpense
from apps.cases.models import CaseNote
from apps.documents.models import Document
from apps.tasks.models import Task, Event


@pytest.fixture
def full_case(case_a, lawyer_a, client_a):
    case_a.court_name = 'Арбитражный суд г. Москвы'
    case_a.opposing_party = 'ООО «Ромашка»'
    case_a.key_deadline = date.today() + timedelta(days=5)
    case_a.hourly_rate = Decimal('5000')
    case_a.save()
    Task.objects.create(title='Подготовить отзыв', case=case_a,
                        assigned_to=lawyer_a, created_by=lawyer_a,
                        due_date=date.today() + timedelta(days=2))
    Event.objects.create(title='Заседание', event_type='court_hearing', case=case_a,
                         created_by=lawyer_a, location='зал 5',
                         start_datetime=timezone.now() + timedelta(days=3))
    Document.objects.create(case=case_a, title='Иск', document_type='court_filing',
                            file=SimpleUploadedFile('c.txt', b'x'), uploaded_by=lawyer_a)
    TimeEntry.objects.create(case=case_a, lawyer=lawyer_a, date=date.today(),
                             hours=Decimal('3'), description='работа',
                             hourly_rate=Decimal('5000'))
    CaseExpense.objects.create(case=case_a, description='Госпошлина', amount=Decimal('6000'))
    CaseNote.objects.create(case=case_a, author=lawyer_a, text='Клиент на связи')
    inv = Invoice.objects.create(case=case_a, client=client_a, status='sent',
                                 due_date=date.today() + timedelta(days=10))
    inv.subtotal = Decimal('15000')
    inv.save()
    InvoicePayment.objects.create(invoice=inv, amount=Decimal('5000'))
    return case_a


@pytest.mark.django_db
class TestCaseDossier:
    def test_pdf_generated(self, api, lawyer_a, full_case):
        api.force_authenticate(lawyer_a)
        resp = api.get(f'/api/v1/cases/{full_case.uuid}/dossier/')
        assert resp.status_code == 200, getattr(resp, 'data', None)
        assert resp['Content-Type'] == 'application/pdf'
        assert resp.content[:4] == b'%PDF'
        assert full_case.case_number in resp['Content-Disposition']

    def test_scoped(self, api, lawyer_b, full_case):
        api.force_authenticate(lawyer_b)
        assert api.get(f'/api/v1/cases/{full_case.uuid}/dossier/').status_code == 404

    def test_minimal_case_does_not_crash(self, api, lawyer_a, case_a):
        api.force_authenticate(lawyer_a)
        assert api.get(f'/api/v1/cases/{case_a.uuid}/dossier/').status_code == 200
