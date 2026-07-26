import pytest


@pytest.mark.django_db
class TestApiDocs:
    def test_schema_served(self, api):
        resp = api.get('/api/schema/')
        assert resp.status_code == 200
        assert b'openapi' in resp.content[:200]

    def test_swagger_ui_served(self, api):
        resp = api.get('/api/docs/')
        assert resp.status_code == 200
