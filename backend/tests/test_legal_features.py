from datetime import date, timedelta

import pytest

from apps.billing.models import Invoice


@pytest.mark.django_db
class TestConflictCheck:
    def test_opposing_party_found_by_name_and_inn(self, api, lawyer_a, case_a):
        case_a.opposing_party = 'ООО «Ромашка»'
        case_a.opposing_party_inn = '7701234567'
        case_a.save()
        api.force_authenticate(lawyer_a)

        resp = api.get('/api/v1/conflict-check/', {'name': 'Ромашка'})
        assert resp.status_code == 200
        assert [m['case_number'] for m in resp.data['opposing_matches']] == [case_a.case_number]

        resp = api.get('/api/v1/conflict-check/', {'inn': '7701234567'})
        assert [m['case_number'] for m in resp.data['opposing_matches']] == [case_a.case_number]

    def test_existing_client_found(self, api, lawyer_b, client_a):
        # клиент Иванов уже наш — предупреждение при вводе его как оппонента
        api.force_authenticate(lawyer_b)
        resp = api.get('/api/v1/conflict-check/', {'name': 'Иванов'})
        assert resp.status_code == 200
        assert [m['display_name'] for m in resp.data['client_matches']] != []

    def test_short_query_returns_empty(self, api, lawyer_a):
        api.force_authenticate(lawyer_a)
        resp = api.get('/api/v1/conflict-check/', {'name': 'Ив'})
        assert resp.data == {'client_matches': [], 'opposing_matches': []}


@pytest.mark.django_db
class TestActPdf:
    def test_act_generated_for_own_invoice(self, api, lawyer_a, case_a, client_a):
        invoice = Invoice.objects.create(
            case=case_a, client=client_a, due_date=date.today() + timedelta(days=14))
        api.force_authenticate(lawyer_a)
        resp = api.get(f'/api/v1/billing/invoices/{invoice.id}/act/')
        assert resp.status_code == 200, getattr(resp, 'data', None)
        assert resp['Content-Type'] == 'application/pdf'
        assert resp.content[:4] == b'%PDF'

    def test_act_hidden_for_foreign_invoice(self, api, lawyer_b, case_a, client_a):
        invoice = Invoice.objects.create(
            case=case_a, client=client_a, due_date=date.today() + timedelta(days=14))
        api.force_authenticate(lawyer_b)
        assert api.get(f'/api/v1/billing/invoices/{invoice.id}/act/').status_code == 404
