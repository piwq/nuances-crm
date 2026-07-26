from datetime import date, timedelta

import pytest
from django.core import mail

from apps.billing.models import Invoice


@pytest.fixture
def invoice_a(db, case_a, client_a):
    return Invoice.objects.create(
        case=case_a, client=client_a, due_date=date.today() + timedelta(days=14))


@pytest.mark.django_db
class TestInvoiceEmail:
    def test_preview_rendered_with_message(self, api, lawyer_a, invoice_a):
        api.force_authenticate(lawyer_a)
        resp = api.get(
            f'/api/v1/billing/invoices/{invoice_a.id}/email-preview/',
            {'message': 'Добрый день! Направляю по договорённости.'})
        assert resp.status_code == 200
        html = resp.content.decode()
        assert invoice_a.invoice_number in html
        assert 'Добрый день! Направляю по договорённости.' in html
        assert 'Нюансы' in html

    def test_preview_foreign_hidden(self, api, lawyer_b, invoice_a):
        api.force_authenticate(lawyer_b)
        assert api.get(
            f'/api/v1/billing/invoices/{invoice_a.id}/email-preview/').status_code == 404

    def test_send_includes_html_alternative_and_pdf(self, api, lawyer_a, invoice_a):
        api.force_authenticate(lawyer_a)
        resp = api.post(
            f'/api/v1/billing/invoices/{invoice_a.id}/send-email/',
            {'email': 'client@example.com', 'message': 'Личный сопроводительный текст'})
        assert resp.status_code == 200

        assert len(mail.outbox) == 1
        msg = mail.outbox[0]
        assert msg.to == ['client@example.com']
        assert 'Личный сопроводительный текст' in msg.body  # plain-text версия

        html, mime = msg.alternatives[0]
        assert mime == 'text/html'
        assert invoice_a.invoice_number in html
        assert 'Личный сопроводительный текст' in html

        name, content, ctype = msg.attachments[0]
        assert ctype == 'application/pdf'
        assert content[:4] == b'%PDF'

        invoice_a.refresh_from_db()
        assert invoice_a.status == 'sent'

    def test_resend_for_sent_invoice(self, api, lawyer_a, invoice_a):
        # повторная отправка (напоминание клиенту) не меняет статус
        invoice_a.status = 'sent'
        invoice_a.save()
        api.force_authenticate(lawyer_a)
        resp = api.post(
            f'/api/v1/billing/invoices/{invoice_a.id}/send-email/',
            {'email': 'client@example.com', 'message': 'Напоминаем об оплате.'})
        assert resp.status_code == 200
        assert len(mail.outbox) == 1
        invoice_a.refresh_from_db()
        assert invoice_a.status == 'sent'
