import uuid
from datetime import date, timedelta

import pytest
from django.utils import timezone

from apps.tasks.icalendar import build_calendar, _escape, _fold
from apps.tasks.models import Task, Event


class TestIcsPrimitives:
    def test_escape_specials(self):
        assert _escape('Иск; на 5,000 руб\\год\nвторая строка') == \
            'Иск\\; на 5\\,000 руб\\\\год\\nвторая строка'

    def test_fold_long_line(self):
        folded = _fold('SUMMARY:' + 'я' * 80)
        assert '\r\n ' in folded
        assert all(len(part.encode()) <= 75 for part in folded.split('\r\n '))

    def test_all_day_and_alarm(self):
        ics = build_calendar('Тест', [
            {'uid': 'a@x', 'summary': 'Срок', 'start': date(2026, 8, 1), 'all_day': True},
            {'uid': 'b@x', 'summary': 'Встреча',
             'start': timezone.make_aware(timezone.datetime(2026, 8, 1, 12, 0)),
             'alarm_minutes': 60},
        ])
        assert ics.startswith('BEGIN:VCALENDAR\r\n')
        assert ics.endswith('END:VCALENDAR\r\n')
        assert 'DTSTART;VALUE=DATE:20260801' in ics
        assert 'DTEND;VALUE=DATE:20260802' in ics  # день+1 для all-day
        assert 'TRIGGER:-PT60M' in ics
        assert ics.count('BEGIN:VEVENT') == 2


@pytest.mark.django_db
class TestCalendarFeed:
    def _token(self, api, user):
        api.force_authenticate(user)
        return api.post('/api/v1/auth/calendar-link/').data

    def test_link_issued_and_stable(self, api, lawyer_a):
        first = self._token(api, lawyer_a)
        assert first['path'].endswith('.ics')
        second = api.post('/api/v1/auth/calendar-link/').data
        assert first['path'] == second['path']  # повторный запрос не меняет ссылку

    def test_regenerate_invalidates_old(self, api, lawyer_a):
        old = self._token(api, lawyer_a)['path']
        new = api.post('/api/v1/auth/calendar-link/', {'regenerate': True}).data['path']
        assert old != new
        api.force_authenticate(None)
        assert api.get(old).status_code == 404
        assert api.get(new).status_code == 200

    def test_get_returns_existing_or_404(self, api, lawyer_a):
        api.force_authenticate(lawyer_a)
        assert api.get('/api/v1/auth/calendar-link/').status_code == 404
        created = api.post('/api/v1/auth/calendar-link/').data['path']
        assert api.get('/api/v1/auth/calendar-link/').data['path'] == created

    def test_revoke(self, api, lawyer_a):
        path = self._token(api, lawyer_a)['path']
        assert api.delete('/api/v1/auth/calendar-link/').status_code == 204
        api.force_authenticate(None)
        assert api.get(path).status_code == 404

    def test_feed_contains_events_deadlines_tasks(self, api, lawyer_a, case_a):
        Event.objects.create(
            title='Заседание', event_type='court_hearing', case=case_a,
            created_by=lawyer_a, location='Мосгорсуд',
            start_datetime=timezone.now() + timedelta(days=3))
        Task.objects.create(title='Подать иск', case=case_a, assigned_to=lawyer_a,
                            created_by=lawyer_a, due_date=date.today() + timedelta(days=2))
        case_a.key_deadline = date.today() + timedelta(days=10)
        case_a.status = 'active'
        case_a.save()

        path = self._token(api, lawyer_a)['path']
        api.force_authenticate(None)
        resp = api.get(path)
        assert resp.status_code == 200
        assert resp['Content-Type'].startswith('text/calendar')
        body = resp.content.decode()
        assert 'Заседание' in body
        assert 'Мосгорсуд' in body
        assert 'Подать иск' in body
        assert 'Срок: Дело А' in body

    def test_feed_scoped_to_user(self, api, lawyer_a, lawyer_b, case_a):
        Task.objects.create(title='Личная задача A', assigned_to=lawyer_a,
                            created_by=lawyer_a, due_date=date.today())
        path_b = self._token(api, lawyer_b)['path']
        api.force_authenticate(None)
        body = api.get(path_b).content.decode()
        assert 'Личная задача A' not in body
        assert 'Дело А' not in body

    def test_unknown_token_404(self, api):
        assert api.get(f'/api/v1/calendar/{uuid.uuid4()}.ics').status_code == 404

    def test_inactive_user_feed_disabled(self, api, lawyer_a):
        path = self._token(api, lawyer_a)['path']
        lawyer_a.is_active = False
        lawyer_a.save(update_fields=['is_active'])
        api.force_authenticate(None)
        assert api.get(path).status_code == 404
