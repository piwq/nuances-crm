import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.documents.models import Document


def _upload(api, case, **extra):
    data = {
        'case': case.id,
        'title': 'Договор',
        'document_type': 'contract',
        'file': SimpleUploadedFile('contract.txt', 'текст'.encode('utf-8')),
    }
    data.update(extra)
    return api.post('/api/v1/documents/', data, format='multipart')


@pytest.fixture
def doc_a(db, case_a, lawyer_a):
    return Document.objects.create(
        case=case_a, title='Иск', document_type='court_filing',
        file=SimpleUploadedFile('claim.txt', b'claim'), uploaded_by=lawyer_a)


@pytest.mark.django_db
class TestDocumentsSecurity:
    def test_upload_ok(self, api, lawyer_a, case_a):
        api.force_authenticate(lawyer_a)
        resp = _upload(api, case_a)
        assert resp.status_code == 201
        assert resp.data['title'] == 'Договор'

    def test_upload_requires_title_and_type(self, api, lawyer_a, case_a):
        # контракт с фронтендом: title и document_type обязательны
        api.force_authenticate(lawyer_a)
        resp = api.post('/api/v1/documents/', {
            'case': case_a.id,
            'file': SimpleUploadedFile('x.txt', b'x'),
        }, format='multipart')
        assert resp.status_code == 400
        assert 'title' in resp.data
        assert 'document_type' in resp.data

    def test_upload_to_foreign_case_rejected(self, api, lawyer_b, case_a):
        api.force_authenticate(lawyer_b)
        assert _upload(api, case_a).status_code == 400

    def test_foreign_document_hidden(self, api, lawyer_b, doc_a):
        api.force_authenticate(lawyer_b)
        assert api.get(f'/api/v1/documents/{doc_a.uuid}/').status_code == 404
        assert api.delete(f'/api/v1/documents/{doc_a.uuid}/').status_code == 404
        assert api.get(f'/api/v1/documents/{doc_a.uuid}/download/').status_code == 403

    def test_own_document_accessible(self, api, lawyer_a, doc_a):
        api.force_authenticate(lawyer_a)
        assert api.get(f'/api/v1/documents/{doc_a.uuid}/').status_code == 200
        assert api.get(f'/api/v1/documents/{doc_a.uuid}/download/').status_code == 200
